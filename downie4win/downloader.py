"""yt-dlp wrapper with Qt signals for progress reporting.

Each download runs in its own QThread (DownloadWorker) so the UI never
blocks. Cancellation is achieved by raising yt_dlp.utils.DownloadCancelled
from the progress hook; "pause" is implemented as cancel-and-keep-partial
so a follow-up run resumes the .part file for HTTP sources.
"""
from __future__ import annotations

import os

import yt_dlp
from PySide6.QtCore import QThread, Signal

from .models import DownloadRequest


def format_size(n) -> str:
    if not n:
        return "?"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def format_speed(speed) -> str:
    if not speed:
        return "--"
    return f"{format_size(speed)}/s"


def format_eta(eta) -> str:
    if eta is None:
        return "--"
    eta = int(eta)
    h, rem = divmod(eta, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def fetch_info(url: str) -> tuple[dict, list[dict]]:
    """Return (info_dict, formats) for a URL without downloading."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "simulate": True,
        "skip_download": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    formats = info.get("formats", []) if info else []
    return info or {}, formats


def build_ydl_opts(
    out_dir: str,
    file_template: str,
    format_str: str,
    audio_only: bool,
    ffmpeg_dir: str,
    progress_hook,
    cookies: dict | None = None,
) -> dict:
    postprocessors = []
    if audio_only:
        postprocessors.append(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        )
        postprocessors.append({"key": "FFmpegMetadata"})
    else:
        # Merge best video+audio when they come as separate streams.
        postprocessors.append({"key": "FFmpegMerger"})

    opts = {
        "outtmpl": os.path.join(out_dir, file_template),
        "ffmpeg_location": ffmpeg_dir or None,
        "progress_hooks": [progress_hook],
        "postprocessors": postprocessors,
        "format": "bestaudio" if audio_only else format_str,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "ignoreerrors": False,
        "concurrent_fragment_downloads": 4,
        "retries": 3,
        "fragment_retries": 3,
    }
    # Age verification / login: pass the authenticated session to yt-dlp so
    # age-restricted videos can be downloaded.
    if cookies:
        mode = cookies.get("mode", "none")
        if mode == "browser":
            opts["cookiesfrombrowser"] = (cookies.get("browser") or "chrome",)
        elif mode == "file" and cookies.get("file"):
            opts["cookiefile"] = cookies["file"]
    return opts


class DownloadWorker(QThread):
    """Runs a single yt-dlp download in a background thread."""

    progress = Signal(int, str, str, str)   # percent, speed, eta, filename
    status = Signal(str)                     # human status text
    finished = Signal(bool, str)             # success, message/path

    def __init__(
        self,
        request: DownloadRequest,
        out_dir: str,
        file_template: str,
        ffmpeg_dir: str,
        cookies: dict | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.request = request
        self.out_dir = out_dir
        self.file_template = file_template
        self.ffmpeg_dir = ffmpeg_dir
        self.cookies = cookies
        self._cancel = False
        self.final_file: str = ""

    # ------------------------------------------------------------------ #
    def cancel(self) -> None:
        self._cancel = True

    def _hook(self, d: dict) -> None:
        if self._cancel:
            raise yt_dlp.utils.DownloadCancelled()

        status = d.get("status")
        if status == "downloading":
            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            percent = int(downloaded / total * 100) if total else 0
            self.progress.emit(
                percent,
                format_speed(d.get("speed")),
                format_eta(d.get("eta")),
                os.path.basename(d.get("filename", "")),
            )
        elif status == "finished":
            self.final_file = d.get("filename", "")
            self.status.emit("下载完成，正在合并 / 处理…")
            self.progress.emit(100, "--", "--", os.path.basename(self.final_file))
        elif status == "error":
            self.status.emit("下载出错")

    # ------------------------------------------------------------------ #
    def run(self) -> None:
        try:
            opts = build_ydl_opts(
                self.out_dir,
                self.file_template,
                self.request.format,
                self.request.audio_only,
                self.ffmpeg_dir,
                self._hook,
                self.cookies,
            )
            self.status.emit("开始下载…")
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.request.url])
            if self._cancel:
                self.finished.emit(False, "已取消")
                return
            self.finished.emit(True, self.final_file or "完成")
        except yt_dlp.utils.DownloadCancelled:
            self.finished.emit(False, "已取消")
        except yt_dlp.utils.YoutubeDLError as exc:
            self.finished.emit(False, f"yt-dlp 错误: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.finished.emit(False, f"错误: {exc}")
