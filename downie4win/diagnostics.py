"""Environment checks and the optional end-to-end download self-test.

The dialog lives in ``ui.diagnostics_dialog`` so this module contains no
widget code and can also be used from the command line.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import urllib.request

import yt_dlp
from PySide6.QtCore import QThread, Signal


def check_yt_dlp() -> dict:
    try:
        return {"ok": True, "detail": f"yt-dlp {yt_dlp.version.__version__}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": str(exc)}


def check_ffmpeg(ffmpeg_dir: str = "") -> dict:
    candidates = []
    if ffmpeg_dir:
        candidates.append(os.path.join(ffmpeg_dir, "ffmpeg.exe"))
        candidates.append(os.path.join(ffmpeg_dir, "ffmpeg"))
    path_in_env = shutil.which("ffmpeg")
    if path_in_env:
        candidates.append(path_in_env)
    for candidate in candidates:
        if os.path.isfile(candidate):
            try:
                out = subprocess.run(
                    [candidate, "-version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                first = out.stdout.splitlines()[0] if out.stdout else "ffmpeg"
                return {"ok": True, "detail": f"{first}  ({candidate})"}
            except Exception:  # noqa: BLE001
                return {"ok": True, "detail": f"已找到 ffmpeg: {candidate}"}
    return {"ok": False, "detail": "未找到 ffmpeg（音视频合并/转码必需）"}


def check_network() -> dict:
    try:
        with urllib.request.urlopen("https://pypi.org", timeout=8):
            pass
        return {"ok": True, "detail": "网络可达"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": str(exc)}


def run_all(ffmpeg_dir: str = "") -> list[tuple[str, dict]]:
    return [
        ("yt-dlp", check_yt_dlp()),
        ("ffmpeg", check_ffmpeg(ffmpeg_dir)),
        ("网络", check_network()),
    ]


class QuickDownloadTest(QThread):
    done = Signal(bool, str)

    def __init__(self, ffmpeg_dir: str = "", parent=None):
        super().__init__(parent)
        self.ffmpeg_dir = ffmpeg_dir

    def run(self) -> None:
        tmp = tempfile.mkdtemp(prefix="downiewin_selftest_")
        try:
            opts = {
                "outtmpl": os.path.join(tmp, "selftest.%(ext)s"),
                "format": "best[height<=144]/best[filesize<3M]/bestaudio",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "retries": 2,
                "ffmpeg_location": self.ffmpeg_dir or None,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download(["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])
            self.done.emit(True, f"测试下载成功，文件已保存到：{tmp}")
        except Exception as exc:  # noqa: BLE001
            self.done.emit(False, f"{type(exc).__name__}: {exc}"[:400])


def missing_components(ffmpeg_dir: str = "") -> list[str]:
    """Return human-readable list of missing critical components."""
    return [
        f"{name}: {result['detail']}"
        for name, result in run_all(ffmpeg_dir)
        if not result["ok"]
    ]


if __name__ == "__main__":
    for name, result in run_all():
        print(f"[{'OK' if result['ok'] else 'FAIL'}] {name}: {result['detail']}")
