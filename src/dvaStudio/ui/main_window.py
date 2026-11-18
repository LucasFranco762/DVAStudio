from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QSettings, QSize, QThread, Qt, QUrl, pyqtSlot
from PyQt6.QtGui import QColor, QCursor, QDesktopServices, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

try:
    from PyQt6.QtWebEngineCore import QWebEnginePage
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except Exception:  # pragma: no cover
    QWebEngineView = None

from ..core.downloader import DownloadRequest, DownloadWorker


def _back_icon() -> QIcon:
    """Seta de retorno curva, com traços arredondados e resolução dupla."""
    icon = QIcon()
    for mode, color in ((QIcon.Mode.Normal, "#C9F7FF"), (QIcon.Mode.Disabled, "#626980")):
        pixmap = QPixmap(48, 48)
        pixmap.setDevicePixelRatio(2)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(color), 1.9, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        path = QPainterPath()
        path.moveTo(10, 5)
        path.lineTo(6, 9)
        path.lineTo(10, 13)
        path.moveTo(6, 9)
        path.lineTo(13, 9)
        path.cubicTo(17, 9, 19, 11, 19, 15)
        path.lineTo(19, 18)
        painter.drawPath(path)
        painter.end()
        icon.addPixmap(pixmap, mode)
    return icon


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DVA Studio Desktop")
        self.resize(1280, 820)
        self.showMaximized()
        config_dir = Path(os.environ.get("APPDATA", str(Path.home()))) / "DVAStudio"
        config_dir.mkdir(parents=True, exist_ok=True)
        self._settings = QSettings(
            str(config_dir / "settings.ini"), QSettings.Format.IniFormat
        )
        default_dir = str(Path.home() / "Downloads" / "DVA Studio")
        self.download_dir = Path(self._settings.value("download_dir", default_dir))
        self._thread: QThread | None = None
        self._worker: DownloadWorker | None = None
        self._save_dialog: QFileDialog | None = None
        self._build_ui()
        self._load_downloads()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(22, 22, 22, 22)
        root_layout.setSpacing(18)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(250)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(22, 24, 22, 24)
        side_layout.setSpacing(12)

        logo = QLabel()
        if getattr(sys, 'frozen', False):
            icone_path = Path(sys._MEIPASS) / "Icone.png"
        else:
            icone_path = Path(__file__).parents[3] / "Icone.png"
        pixmap = QPixmap(str(icone_path))
        if not pixmap.isNull():
            pixmap = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo.setPixmap(pixmap)
        logo.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title = QLabel("DVA Studio")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Video & Áudio Studio")
        subtitle.setObjectName("Muted")
        side_layout.addWidget(logo)
        side_layout.addWidget(title)
        side_layout.addWidget(subtitle)
        side_layout.addSpacing(26)

        self.btn_browser = self._nav_button("Navegador")
        self.btn_downloads = self._nav_button("Downloads")
        self.btn_settings = self._nav_button("Configurações")
        self.btn_browser.setChecked(True)
        self.btn_browser.clicked.connect(lambda: self._switch_page(0))
        self.btn_downloads.clicked.connect(lambda: self._switch_page(1))
        self.btn_settings.clicked.connect(lambda: self._switch_page(2))
        side_layout.addWidget(self.btn_browser)
        side_layout.addWidget(self.btn_downloads)
        side_layout.addWidget(self.btn_settings)
        side_layout.addItem(QSpacerItem(1, 1, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        tip = QLabel("Developed by Lucas Pires Franco\nEngenharia de Computação\n2026\n\nVersão 1.1")
        tip.setObjectName("Muted")
        tip.setWordWrap(True)
        side_layout.addWidget(tip)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._browser_page())
        self.stack.addWidget(self._downloads_page())
        self.stack.addWidget(self._settings_page())

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

    def _update_format_combo(self, index: int = 0) -> None:
        self.format_combo.clear()
        mode = self.mode_combo.currentData()
        if mode == "audio":
            for fmt in ["mp3", "m4a", "opus", "flac", "wav"]:
                self.format_combo.addItem(fmt.upper(), fmt)
        else:
            for fmt in ["mp4", "mkv", "webm"]:
                self.format_combo.addItem(fmt.upper(), fmt)

    def _nav_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("NavButton")
        btn.setCheckable(True)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        return btn

    def _switch_page(self, index: int) -> None:
        for i, button in enumerate([self.btn_browser, self.btn_downloads, self.btn_settings]):
            button.setChecked(i == index)
        self.stack.setCurrentIndex(index)
        if index == 1:
            self._load_downloads()

    def _browser_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        top = QFrame()
        top.setObjectName("Card")
        top_layout = QVBoxLayout(top)
        header = QLabel("Navegue ou cole a URL do vídeo que deseja baixar.")
        header.setObjectName("SectionTitle")
        desc = QLabel("Interface desktop inspirada no app Android original, com visual moderno e downloads em segundo plano.")
        desc.setObjectName("Muted")
        top_layout.addWidget(header)
        top_layout.addWidget(desc)

        row = QHBoxLayout()
        self.btn_back = QPushButton()
        self.btn_back.setObjectName("BackButton")
        self.btn_back.setIcon(_back_icon())
        self.btn_back.setIconSize(QSize(24, 24))
        self.btn_back.setFixedSize(44, 44)
        self.btn_back.setAccessibleName("Voltar")
        self.btn_back.setToolTip("Voltar à página anterior (Alt+Esquerda)")
        self.btn_back.setShortcut("Alt+Left")
        self.btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_back.setEnabled(False)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Cole a URL do vídeo ou navegue pelo painel abaixo...")
        self.url_edit.returnPressed.connect(self._go_to_url)
        go_btn = QPushButton("Abrir")
        go_btn.clicked.connect(self._go_to_url)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Vídeo + Áudio", "full")
        self.mode_combo.addItem("Somente Áudio", "audio")
        self.mode_combo.addItem("Somente Vídeo", "video_only")
        self.format_combo = QComboBox()
        self.mode_combo.currentIndexChanged.connect(self._update_format_combo)
        self._update_format_combo(0)
        download_btn = QPushButton("Baixar")
        download_btn.setObjectName("Primary")
        download_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        download_btn.clicked.connect(self._start_download)
        row.addWidget(self.btn_back)
        row.addWidget(self.url_edit, 1)
        row.addWidget(go_btn)
        row.addWidget(self.mode_combo)
        row.addWidget(self.format_combo)
        row.addWidget(download_btn)
        top_layout.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.status = QLabel("Pronto")
        self.status.setObjectName("Muted")
        top_layout.addWidget(self.progress)
        top_layout.addWidget(self.status)
        layout.addWidget(top)

        if QWebEngineView:
            self.web = QWebEngineView()
            back_action = self.web.pageAction(QWebEnginePage.WebAction.Back)
            if back_action is not None:
                self.btn_back.clicked.connect(back_action.trigger)
                back_action.changed.connect(lambda: self.btn_back.setEnabled(back_action.isEnabled()))
                self.btn_back.setEnabled(back_action.isEnabled())
            self.web.setUrl(QUrl("https://m.youtube.com"))
            self.web.urlChanged.connect(lambda url: self.url_edit.setText(url.toString()))
            layout.addWidget(self.web, 1)
        else:
            fallback = QFrame()
            fallback.setObjectName("Card")
            fb_layout = QVBoxLayout(fallback)
            fb_title = QLabel("PyQt6-WebEngine não está instalado")
            fb_title.setObjectName("SectionTitle")
            fb_text = QLabel("O navegador interno precisa do pacote PyQt6-WebEngine. Ainda é possível colar a URL manualmente no campo acima.")
            fb_text.setObjectName("Muted")
            fb_text.setWordWrap(True)
            fb_layout.addWidget(fb_title)
            fb_layout.addWidget(fb_text)
            layout.addWidget(fallback, 1)
        return page

    def _downloads_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        header_row = QHBoxLayout()
        title = QLabel("Arquivos baixados")
        title.setObjectName("SectionTitle")
        refresh = QPushButton("Atualizar")
        refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        refresh.clicked.connect(self._load_downloads)
        open_folder = QPushButton("Abrir Pasta")
        open_folder.setObjectName("Primary")
        open_folder.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        open_folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.download_dir))))
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(refresh)
        header_row.addWidget(open_folder)
        card_layout.addLayout(header_row)
        self.download_list = QListWidget()
        self.download_list.itemDoubleClicked.connect(self._open_selected_file)
        card_layout.addWidget(self.download_list, 1)
        layout.addWidget(card, 1)
        return page

    def _settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        title = QLabel("Configurações")
        title.setObjectName("SectionTitle")
        self.folder_label = QLabel(str(self.download_dir))
        self.folder_label.setObjectName("Muted")
        choose = QPushButton("Escolher pasta de downloads")
        choose.setObjectName("Primary")
        choose.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        choose.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        choose.clicked.connect(self._choose_folder)
        card_layout.addWidget(title)
        card_layout.addWidget(QLabel("Pasta atual:"))
        card_layout.addWidget(self.folder_label)
        card_layout.addSpacing(12)
        card_layout.addWidget(choose)
        card_layout.addStretch(1)
        layout.addWidget(card, 1)
        return page

    def _go_to_url(self) -> None:
        text = self.url_edit.text().strip()
        if not text:
            return
        if not text.startswith(("http://", "https://")):
            text = "https://" + text
        if hasattr(self, "web"):
            self.web.setUrl(QUrl(text))
        self.url_edit.setText(text)

    def _start_download(self) -> None:
        url = self.url_edit.text().strip()
        if not url.startswith(("http://", "https://")):
            self._show_message(QMessageBox.Icon.Warning, "URL inválida", "Cole ou abra uma URL válida antes de baixar.")
            return
        if self._thread and self._thread.isRunning():
            self._show_message(QMessageBox.Icon.Information, "Download em andamento", "Aguarde o download atual terminar.")
            return
        if self._save_dialog is not None:
            self._save_dialog.raise_()
            self._save_dialog.activateWindow()
            return
        output_fmt = self.format_combo.currentData()
        # Captura a solicitação antes de abrir o seletor. O usuário pode
        # continuar navegando ou mudar as opções enquanto escolhe o destino.
        request = DownloadRequest(
            url=url,
            mode=self.mode_combo.currentData(),
            output_dir=self.download_dir,
            output_format=output_fmt,
        )
        dialog = QFileDialog(self)
        # O seletor nativo do Windows interrompe os timers do Qt. show()
        # mantém o loop principal e o navegador ativos, sem um exec() aninhado.
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setWindowTitle("Salvar arquivo como")
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setNameFilter(f"*.{output_fmt}")
        dialog.setDefaultSuffix(output_fmt)
        dialog.setDirectory(str(self.download_dir))
        dialog.selectFile(f"download.{output_fmt}")
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.fileSelected.connect(lambda filename: self._download_selected_file(filename, request))
        dialog.finished.connect(self._clear_save_dialog)
        self._save_dialog = dialog
        dialog.show()

    @pyqtSlot(int)
    def _clear_save_dialog(self, result: int) -> None:
        self._save_dialog = None

    def _download_selected_file(self, filename: str, request: DownloadRequest) -> None:
        save_path = Path(filename)
        request.output_dir = save_path.parent
        request.output_filename = save_path.stem
        self._thread = QThread()
        self._worker = DownloadWorker(request)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress, Qt.ConnectionType.QueuedConnection)
        self._worker.finished.connect(self._on_finished, Qt.ConnectionType.QueuedConnection)
        self._worker.failed.connect(self._on_failed, Qt.ConnectionType.QueuedConnection)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker)
        self.progress.setValue(0)
        self.status.setText("Iniciando...")
        self._thread.start()

    @pyqtSlot()
    def _clear_worker(self) -> None:
        self._thread = None
        self._worker = None

    @pyqtSlot(int, str)
    def _on_progress(self, value: int, text: str) -> None:
        self.progress.setValue(value)
        self.status.setText(text)

    @pyqtSlot(str, str)
    def _on_finished(self, file_path: str, title: str) -> None:
        self.progress.setValue(100)
        self.status.setText(f"Concluído: {Path(file_path).name}")
        self._load_downloads()
        mode = self._worker.request.mode if self._worker else "full"
        if mode == "audio":
            kind = "Áudio"
        elif mode == "video_only":
            kind = "Vídeo"
        else:
            kind = "Vídeo + Áudio"
        dlg = QDialog(self)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dlg.setWindowModality(Qt.WindowModality.NonModal)
        dlg.setWindowTitle("Download concluído")
        dlg.setFixedWidth(380)
        dlg.setStyleSheet("QDialog { background: #0D1024; }")
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(28, 28, 28, 20)
        layout.setSpacing(20)
        lbl = QLabel(f"Arquivo de <b>{kind}</b> baixado com sucesso.")
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)
        ok_btn = QPushButton("Ok")
        ok_btn.setFixedHeight(38)
        ok_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        ok_btn.setMinimumWidth(100)
        ok_btn.setStyleSheet(
            "QPushButton { background-color: #22a55b; color: #fff; border: none;"
            " border-radius: 6px; font-size: 14px; font-weight: bold; padding: 0 24px; }"
            "QPushButton:hover { background-color: #1e9451; }"
            "QPushButton:pressed { background-color: #197a44; }"
        )
        ok_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        ok_btn.clicked.connect(dlg.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(ok_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        dlg.show()

    def _show_message(self, icon: QMessageBox.Icon, title: str, message: str) -> None:
        dialog = QMessageBox(icon, title, message, QMessageBox.StandardButton.Ok, self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.show()

    @pyqtSlot(str)
    def _on_failed(self, message: str) -> None:
        self.status.setText("Falha no download")
        self._show_message(QMessageBox.Icon.Critical, "Erro no download", message)

    def _load_downloads(self) -> None:
        if not hasattr(self, "download_list"):
            return
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.download_list.clear()
        files = [p for p in self.download_dir.iterdir() if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            item = QListWidgetItem("Nenhum arquivo baixado ainda.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.download_list.addItem(item)
            return
        for path in files:
            size_mb = path.stat().st_size / (1024 * 1024)
            item = QListWidgetItem(f"{path.name}\n{size_mb:.1f} MB • duplo clique para abrir")
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.download_list.addItem(item)

    def _open_selected_file(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Escolha a pasta de downloads", str(self.download_dir))
        if folder:
            self.download_dir = Path(folder)
            self._settings.setValue("download_dir", str(self.download_dir))
            self._settings.sync()
            self.folder_label.setText(str(self.download_dir))
            self._load_downloads()
