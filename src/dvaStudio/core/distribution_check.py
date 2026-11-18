"""Verificação interna do pacote gerado, sem acessar sites externos."""
from __future__ import annotations

import functools
import http.server
import json
import subprocess
import sys
import tempfile
import threading
import wave
from pathlib import Path


def verify_distribution(report: Path) -> int:
    result = {"ok": False, "stage": "imports"}

    def checkpoint(stage: str) -> None:
        result["stage"] = stage
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    checkpoint("imports")
    try:
        from PyQt6.QtCore import QEventLoop, QTimer
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        import yt_dlp.version
        import yt_dlp_ejs
        from .downloader import DownloadRequest, DownloadWorker, _get_ffmpeg_dir, _get_js_runtimes

        if not getattr(sys, "frozen", False):
            raise RuntimeError("Esta verificação deve executar dentro do aplicativo compilado.")
        root = Path(sys._MEIPASS)
        for name in ("Icone.png", "Icone.ico"):
            if not (root / name).is_file():
                raise RuntimeError(f"Ícone não incluído: {name}")
        checkpoint("Qt WebEngine")
        # QtWebEngine no Windows precisa do nome do programa em argv[0].
        app = QApplication(sys.argv[:1])
        view = QWebEngineView()
        loop = QEventLoop()
        loaded = []
        view.loadFinished.connect(lambda ok: (loaded.append(ok), loop.quit()))
        QTimer.singleShot(15000, loop.quit)
        view.setHtml("<html><body>Verificação DVA Studio</body></html>")
        loop.exec()
        if not loaded or not loaded[0]:
            raise RuntimeError("O navegador integrado não carregou o conteúdo de teste.")
        checkpoint("Node.js e MP3")
        node = _get_js_runtimes()["node"]["path"]
        node_version = subprocess.run([node, "--version"], capture_output=True, text=True, check=True).stdout.strip()
        ffmpeg = str(Path(_get_ffmpeg_dir()) / "ffmpeg.exe")

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        with tempfile.TemporaryDirectory(dir=report.parent) as tmp:
            folder = Path(tmp)
            with wave.open(str(folder / "source.wav"), "wb") as audio:
                audio.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
                audio.writeframes(b"\x00\x00" * 2000)
            server = http.server.ThreadingHTTPServer(
                ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(folder)),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                worker = DownloadWorker(DownloadRequest(
                    f"http://127.0.0.1:{server.server_port}/source.wav", "audio", folder, "mp3", "validacao",
                ))
                paths, errors = [], []
                worker.finished.connect(lambda path, title: paths.append(path))
                worker.failed.connect(errors.append)
                worker.run()
                if errors or not paths:
                    raise RuntimeError(f"Falha no teste MP3: {errors}")
                subprocess.run([ffmpeg, "-v", "error", "-i", paths[0], "-f", "null", "-"], capture_output=True, check=True)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
        view.close()
        app.quit()
        result.update(ok=True, stage="concluído", yt_dlp=yt_dlp.version.__version__, node=node_version,
                      webengine=True, mp3=True, icons=True)
    except Exception as exc:
        result["error"] = str(exc)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if result["ok"] else 1
