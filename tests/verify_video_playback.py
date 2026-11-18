"""Teste integrado opcional: python tests/verify_video_playback.py.

Usa o WebEngine real e as configurações da aplicação, sem alterar a política
de reprodução. Gera um vídeo local e acompanha seus quadros até o fim.
"""
import functools
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "windows" if os.name == "nt" else "offscreen")

import imageio_ffmpeg
from PyQt6.QtCore import QRect, QSettings, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QDialog, QLineEdit, QMessageBox
from src.dvaStudio.ui import main_window


class LocalBrowser(QWebEngineView):
    def setUrl(self, url):
        pass  # A página inicial externa é substituída pela página local do teste.


class VideoHandler(http.server.SimpleHTTPRequestHandler):
    video_requests = 0
    lock = threading.Lock()

    def log_message(self, *args):
        pass

    def copyfile(self, source, target):
        slow = False
        if self.path.split("?")[0] == "/video.webm":
            with self.lock:
                type(self).video_requests += 1
                slow = type(self).video_requests > 1
        try:
            while chunk := source.read(2048):
                target.write(chunk)
                target.flush()
                if slow:
                    time.sleep(0.025)
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    def pump(seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.005)

    def wait_for(predicate, timeout=20):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            pump(0.01)
        assert predicate(), "Tempo esgotado na verificação do vídeo"

    def javascript(view, script):
        result = []
        view.page().runJavaScript(script, result.append)
        wait_for(lambda: bool(result), 5)
        return result[0]

    samples = []

    def sample(view, phase):
        state = javascript(view, """({time:player.currentTime, duration:player.duration,
            paused:player.paused, ended:player.ended, ready:player.readyState,
            frames:player.getVideoPlaybackQuality().totalVideoFrames,
            hidden:document.hidden, origin:performance.timeOrigin,
            rect:{x:player.getBoundingClientRect().x,y:player.getBoundingClientRect().y,
                width:player.clientWidth,height:player.clientHeight},
            error:player.error && player.error.message, playError:window.playError,
            events:window.mediaEvents})""")
        state["phase"] = phase
        rect = state["rect"]
        frame = view.grab(QRect(int(rect["x"]), int(rect["y"]),
                               int(rect["width"]), int(rect["height"]))).toImage()
        colors = {frame.pixelColor(x * frame.width() // 10, y * frame.height() // 10).rgb()
                  for x in range(1, 10) for y in range(1, 10)}
        state["visible_colors"] = len(colors)
        assert len(colors) > 5, f"O vídeo ficou sem imagem: {state}"
        samples.append(state)
        return state

    with tempfile.TemporaryDirectory(dir=ROOT / "build", prefix="video-test-") as tmp:
        folder = Path(tmp).resolve()
        subprocess.run([
            imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-f", "lavfi", "-i",
            "testsrc2=size=160x90:rate=10:duration=14", "-f", "lavfi", "-i",
            "anullsrc=r=48000:cl=stereo", "-shortest", "-c:v", "libvpx", "-deadline",
            "realtime", "-cpu-used", "8", "-b:v", "150k", "-c:a", "libopus", "-b:a", "32k",
            "-y", str(folder / "video.webm"),
        ], capture_output=True, check=True)
        (folder / "player.html").write_text("""<!doctype html><title>Vídeo de teste</title>
            <video id="player" autoplay controls src="/video.webm" width="640"></video>
            <script>window.mediaEvents=[];
            for(const event of ['play','pause','ended','waiting','stalled','error']) {
                player.addEventListener(event,()=>mediaEvents.push({event,time:player.currentTime}));
            }
            player.play().catch(e=>window.playError=String(e));</script>""", encoding="utf-8")
        config = folder / "DVAStudio"
        config.mkdir()
        settings = QSettings(str(config / "settings.ini"), QSettings.Format.IniFormat)
        settings.setValue("download_dir", str(folder / "downloads"))
        settings.sync()
        server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(VideoHandler, directory=str(folder)))
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        with patch.dict(os.environ, {"APPDATA": str(folder), "LOCALAPPDATA": str(folder)}), \
                patch.object(main_window, "QWebEngineView", LocalBrowser), \
                patch.object(main_window.MainWindow, "showMaximized"):
            window = main_window.MainWindow()
            window.show()
            view = window.web
            loaded = []
            view.loadFinished.connect(loaded.append)
            try:
                url = QUrl(f"http://127.0.0.1:{server.server_port}/player.html")
                view.load(url)
                wait_for(lambda: bool(loaded))
                assert loaded[-1]
                pump(1)
                initial = sample(view, "before")
                assert not initial["paused"] and initial["frames"] > 0, initial
                origin = initial["origin"]

                window.mode_combo.setCurrentIndex(1)
                window._start_download()
                assert window._save_dialog is not None
                for _ in range(4):
                    pump(0.25)
                    state = sample(view, "choosing")
                    assert not state["paused"] and not state["hidden"], state
                destination = folder / "downloads" / "video-audio.mp3"
                window._save_dialog.findChild(QLineEdit, "fileNameEdit").setText(str(destination))
                window._save_dialog.accept()
                deadline = time.monotonic() + 30
                while window._thread is not None and time.monotonic() < deadline:
                    pump(0.15)
                    state = sample(view, "downloading")
                    assert not state["paused"] or state["ended"], state
                    assert state["origin"] == origin and not state["error"], state
                assert window._thread is None
                assert destination.is_file(), [d.text() for d in window.findChildren(QMessageBox)]
                assert len(loaded) == 1, "A página foi recarregada durante o download"
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    pump(0.2)
                    state = sample(view, "after")
                    if state["ended"]:
                        break
                    assert not state["paused"] and not state["hidden"], state
                assert state["ended"] and state["time"] >= state["duration"] - 0.1, state
                assert state["frames"] > initial["frames"] + 50, state
                assert all(s["origin"] == origin for s in samples)

                # Uma pausa explícita deve continuar sendo respeitada pelo app.
                javascript(view, "player.currentTime=0;player.play();true")
                pump(0.3)
                javascript(view, "player.pause();true")
                paused = sample(view, "manual-pause")
                window._on_finished(str(destination), "Vídeo de teste")
                pump(0.4)
                still_paused = sample(view, "manual-pause-after-notification")
                assert still_paused["paused"] and abs(still_paused["time"] - paused["time"]) < 0.1
                result = {"ok": True, "initial": initial, "natural_end": state,
                          "manual_pause_respected": True, "samples": samples}
                (ROOT / "build" / "video-playback-report.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                print(json.dumps({"ok": True, "duration": state["duration"], "frames": state["frames"],
                                  "samples": len(samples), "manual_pause_respected": True}), flush=True)
            finally:
                if window._thread is not None:
                    wait_for(lambda: window._thread is None, 30)
                window._stop_metadata_workers()
                for dialog in window.findChildren(QDialog):
                    dialog.close()
                view.stop()
                window.close()
                app.processEvents()
                server.shutdown()
                server.server_close()
                server_thread.join()


if __name__ == "__main__":
    main()
