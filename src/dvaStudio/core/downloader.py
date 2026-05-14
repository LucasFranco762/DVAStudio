from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


def _get_ffmpeg_dir() -> str:
    """Retorna um diretório com um executável chamado exatamente 'ffmpeg.exe',
    requisito do yt-dlp para reconhecer o binário."""
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


@dataclass
class DownloadRequest:
    url: str
    mode: str
    output_dir: Path
    output_format: str = "mp4"
    output_filename: str | None = None


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
        try:
            import yt_dlp

            ffmpeg_dir = _get_ffmpeg_dir()

            self.request.output_dir.mkdir(parents=True, exist_ok=True)
            if self.request.output_filename:
                output_template = str(self.request.output_dir / f"{self.request.output_filename}.%(ext)s")
            else:
                output_template = str(self.request.output_dir / "%(title).180s [%(id)s].%(ext)s")
            merge_fmt = self.request.output_format if self.request.mode != "audio" else None
            options = {
                "format": self._format_selector(),
                "outtmpl": output_template,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
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
            self.progress.emit(100, "Concluído")
            self.finished.emit(file_path, title)
        except Exception as exc:
            self.failed.emit(str(exc))
