from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


def _get_ffmpeg_dir() -> str:
    """Retorna um diretório com um executável chamado exatamente 'ffmpeg.exe',
    requisito do yt-dlp para reconhecer o binário."""
    if getattr(sys, "frozen", False):
        runtime = Path(sys._MEIPASS) / "runtime"
        if not (runtime / "ffmpeg.exe").is_file():
            raise RuntimeError("FFmpeg não encontrado. Copie a pasta completa do aplicativo.")
        return str(runtime)

    import imageio_ffmpeg

    src = Path(imageio_ffmpeg.get_ffmpeg_exe())
    cache_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "DVAStudio" / "bin"
    cache_dir.mkdir(parents=True, exist_ok=True)
    dst = cache_dir / "ffmpeg.exe"
    if not dst.exists():
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
    return str(cache_dir)


def _get_js_runtimes() -> dict:
    if getattr(sys, "frozen", False):
        node = Path(sys._MEIPASS) / "runtime" / "node.exe"
        if not node.is_file():
            raise RuntimeError("Node.js não encontrado. Copie a pasta completa do aplicativo.")
        return {"node": {"path": str(node)}}
    return {"deno": {}, "node": {}}


@dataclass
class DownloadRequest:
    url: str
    mode: str
    output_dir: Path
    output_format: str = "mp4"
    output_filename: str | None = None


class _DownloadLogger:
    """Preserva avisos do yt-dlp para o diagnóstico na interface sem console."""

    def __init__(self) -> None:
        self.warnings: list[str] = []

    def debug(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)
            self.warnings = self.warnings[-3:]

    def error(self, message: str) -> None:
        # O erro também será recebido pela exceção de extract_info.
        pass


class DownloadWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str, str)
    failed = pyqtSignal(str)

    def __init__(self, request: DownloadRequest):
        super().__init__()
        self.request = request
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def _hook(self, data: dict) -> None:
        if self._cancelled:
            raise RuntimeError("Download cancelado pelo usuário.")
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            percent = int(downloaded * 100 / total) if total else 0
            speed = data.get("_speed_str", "").strip()
            eta = data.get("_eta_str", "").strip()
            label = f"Baixando... {speed}  ETA {eta}".strip()
            self.progress.emit(max(0, min(100, percent)), label)
        elif status == "finished":
            self.progress.emit(98, "Finalizando arquivo...")

    def _format_selector(self) -> str:
        if self.request.mode == "audio":
            return "bestaudio/best"
        if self.request.mode == "video_only":
            return "bestvideo[acodec=none]/bestvideo"
        return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

    def _postprocessors(self) -> list[dict]:
        if self.request.mode == "audio":
            return [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": self.request.output_format,
                "preferredquality": "192",
            }]
        return []

    @pyqtSlot()
    def run(self) -> None:
        logger = _DownloadLogger()
        try:
            import yt_dlp

            ffmpeg_dir = _get_ffmpeg_dir()

            self.request.output_dir.mkdir(parents=True, exist_ok=True)
            if self.request.output_filename:
                filename = self.request.output_filename.replace("%", "%%")
                output_template = str(self.request.output_dir).replace("%", "%%") + os.sep + f"{filename}.%(ext)s"
            else:
                output_template = str(self.request.output_dir).replace("%", "%%") + os.sep + "%(title).180s [%(id)s].%(ext)s"
            merge_fmt = self.request.output_format if self.request.mode != "audio" else None
            options = {
                "format": self._format_selector(),
                "outtmpl": output_template,
                "noplaylist": True,
                "quiet": True,
                "logger": logger,
                "noprogress": True,
                # yt-dlp habilita apenas Deno por padrão. Aceita também Node
                # quando instalado, necessário para os desafios do YouTube.
                "js_runtimes": _get_js_runtimes(),
                "progress_hooks": [self._hook],
                "postprocessors": self._postprocessors(),
                "ffmpeg_location": ffmpeg_dir,
            }
            if merge_fmt:
                options["merge_output_format"] = merge_fmt
            self.progress.emit(2, "Preparando download...")
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(self.request.url, download=True)
                title = info.get("title", "") if info else ""
                file_path = ydl.prepare_filename(info)
                ext = self.request.output_format
                file_path = str(Path(file_path).with_suffix(f".{ext}"))
                if not Path(file_path).is_file():
                    raise RuntimeError(f"O arquivo final não foi encontrado: {file_path}")
            self.progress.emit(100, "Concluído")
            self.finished.emit(file_path, title)
        except Exception as exc:
            message = str(exc)
            if logger.warnings:
                message += "\n\nAvisos do download:\n" + "\n".join(logger.warnings)
            self.failed.emit(message)
