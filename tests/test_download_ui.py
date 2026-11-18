import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QSettings, QThread, QTimer, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog, QLineEdit, QWidget

from src.dvaStudio.core.downloader import DownloadWorker, MediaInfoWorker
from src.dvaStudio.ui import main_window


class BrowserStub(QWidget):
    urlChanged = pyqtSignal(QUrl)

    def __init__(self):
        super().__init__()
        self.back_action = QAction(self)
        self.back_action.setEnabled(False)
        self.web_settings = MagicMock()
        self.browser_page = MagicMock()

    def settings(self):
        return self.web_settings

    def page(self):
        return self.browser_page

    def pageAction(self, action):
        return self.back_action

    def setUrl(self, url):
        self.current_url = url


class SlowWorker(DownloadWorker):
    thread_id = None
    last_request = None

    @pyqtSlot()
    def run(self):
        type(self).thread_id = int(QThread.currentThreadId())
        type(self).last_request = self.request
        for step in range(15):
            time.sleep(0.02)
            self.progress.emit(step * 6, "Baixando...")
        path = self.request.output_dir / f"{self.request.output_filename}.mp3"
        path.write_bytes(b"download de teste")
        self.finished.emit(str(path), "teste")


class SlowInfoWorker(MediaInfoWorker):
    thread_id = None

    @pyqtSlot()
    def run(self):
        type(self).thread_id = int(QThread.currentThreadId())
        time.sleep(0.15)
        if not self._cancelled:
            self.title_ready.emit("Título original")
        self.done.emit()


class DownloadUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication(["test_download_ui"])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        config = root / "DVAStudio"
        config.mkdir()
        settings = QSettings(str(config / "settings.ini"), QSettings.Format.IniFormat)
        settings.setValue("download_dir", str(root / "downloads"))
        settings.sync()
        self.env = patch.dict(os.environ, {"APPDATA": str(root)})
        self.env.start()
        with patch.object(main_window, "QWebEngineView", BrowserStub), \
                patch.object(main_window.MainWindow, "showMaximized"):
            self.window = main_window.MainWindow()
        self.window.url_edit.setText("https://example.com/original")
        self.window.mode_combo.setCurrentIndex(1)
        self.metadata_patch = patch.object(self.window, "_fetch_original_name")
        self.metadata_patch.start()

    def tearDown(self):
        if self.window._save_dialog is not None:
            self.window._save_dialog.reject()
        self.window._stop_metadata_workers()
        for dialog in self.window.findChildren(QDialog):
            dialog.close()
        self.window.close()
        self.app.processEvents()
        self.env.stop()
        self.metadata_patch.stop()
        self.tmp.cleanup()

    def pump_until(self, predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.005)
        self.assertTrue(predicate(), "O loop da interface não concluiu a operação a tempo")

    def test_save_dialog_returns_without_blocking_browser_or_timers(self):
        with patch.object(QFileDialog, "getSaveFileName", side_effect=AssertionError("seletor bloqueante")):
            self.window._start_download()
        dialog = self.window._save_dialog
        self.assertIsNotNone(dialog)
        self.assertFalse(dialog.isModal())
        self.assertTrue(dialog.testOption(QFileDialog.Option.DontUseNativeDialog))
        self.assertTrue(self.window.web.isEnabled())
        self.assertIsNone(self.window._thread)
        ticks = []
        timer = QTimer()
        timer.timeout.connect(lambda: ticks.append(True))
        timer.start(10)
        self.pump_until(lambda: len(ticks) >= 4)
        timer.stop()
        dialog.reject()
        self.assertIsNone(self.window._save_dialog)
        self.assertIsNone(self.window._thread)

    def test_background_download_keeps_ui_active_and_uses_captured_url(self):
        self.window._start_download()
        dialog = self.window._save_dialog
        self.window.url_edit.setText("https://example.com/another-video")
        self.window.mode_combo.setCurrentIndex(2)
        destination = Path(self.tmp.name) / "audio.mp3"
        ticks = []
        timer = QTimer()
        timer.timeout.connect(lambda: ticks.append(self.window._worker is not None))
        timer.start(10)
        with patch.object(main_window, "DownloadWorker", SlowWorker):
            dialog.selectFile(str(destination))
            dialog.accept()
        self.pump_until(lambda: self.window._thread is None and destination.exists())
        timer.stop()
        self.assertNotEqual(SlowWorker.thread_id, int(QThread.currentThreadId()))
        self.assertGreaterEqual(sum(ticks), 4)
        self.assertEqual(SlowWorker.last_request.url, "https://example.com/original")
        self.assertEqual(SlowWorker.last_request.mode, "audio")
        self.assertEqual(SlowWorker.last_request.output_format, "mp3")
        self.assertTrue(self.window.web.isEnabled())
        self.assertEqual(self.window.progress.value(), 100)
        completion = [d for d in self.window.findChildren(QDialog) if d.windowTitle() == "Download concluído"]
        self.assertEqual(len(completion), 1)
        self.assertFalse(completion[0].isModal())

    def test_completion_and_failure_messages_do_not_block_browser(self):
        with patch.object(QDialog, "exec", side_effect=AssertionError("diálogo bloqueante")):
            self.window._on_finished(str(Path(self.tmp.name) / "audio.mp3"), "teste")
            self.window._on_failed("erro de teste")
        self.app.processEvents()
        self.assertTrue(self.window.web.isEnabled())
        self.assertTrue(all(not dialog.isModal() for dialog in self.window.findChildren(QDialog)))

    def test_portuguese_dialog_prefills_original_name_and_preserves_edits(self):
        self.window._start_download()
        dialog = self.window._save_dialog
        self.assertEqual(dialog.labelText(QFileDialog.DialogLabel.Accept), "Salvar")
        self.assertEqual(dialog.labelText(QFileDialog.DialogLabel.Reject), "Cancelar")
        self.assertEqual(dialog.labelText(QFileDialog.DialogLabel.LookIn), "Salvar em:")
        self.assertEqual(dialog.labelText(QFileDialog.DialogLabel.FileName), "Nome do arquivo:")
        self.assertEqual(self.app.translate("QFileSystemModel", "Name"), "Nome")
        editor = dialog.findChild(QLineEdit, "fileNameEdit")
        dialog.set_original_name("Alok - Hear Me Now")
        self.assertEqual(editor.text(), "Alok - Hear Me Now.mp3")
        editor.setText("Minha música.mp3")
        editor.textEdited.emit("Minha música.mp3")
        dialog.set_original_name("Outro nome")
        self.assertEqual(editor.text(), "Minha música.mp3")

    def test_name_lookup_is_background_and_cancelled_results_do_not_change_new_dialog(self):
        self.window._start_download()
        dialog = self.window._save_dialog
        ticks = []
        timer = QTimer()
        timer.timeout.connect(lambda: ticks.append(True))
        timer.start(10)
        with patch.object(main_window, "MediaInfoWorker", SlowInfoWorker):
            main_window.MainWindow._fetch_original_name(self.window, "https://example.com/music", dialog)
        self.pump_until(lambda: not self.window._metadata_jobs)
        timer.stop()
        self.assertGreaterEqual(len(ticks), 3)
        self.assertNotEqual(SlowInfoWorker.thread_id, int(QThread.currentThreadId()))
        self.assertEqual(dialog.findChild(QLineEdit, "fileNameEdit").text(), "Título original.mp3")
        dialog.reject()
        self.window._start_download()
        old_dialog = self.window._save_dialog
        with patch.object(main_window, "MediaInfoWorker", SlowInfoWorker):
            main_window.MainWindow._fetch_original_name(self.window, "https://example.com/music", old_dialog)
        old_dialog.reject()
        self.window._start_download()
        new_dialog = self.window._save_dialog
        self.pump_until(lambda: not self.window._metadata_jobs)
        self.assertEqual(new_dialog.findChild(QLineEdit, "fileNameEdit").text(), "download.mp3")

    def test_original_name_does_not_duplicate_extension(self):
        self.window._start_download()
        dialog = self.window._save_dialog
        dialog.set_original_name("Música.MP3")
        self.assertEqual(dialog.findChild(QLineEdit, "fileNameEdit").text(), "Música.mp3")


if __name__ == "__main__":
    unittest.main()
