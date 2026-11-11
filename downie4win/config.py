"""Configuration management for DownieWin.

Settings are stored as JSON under the OS config location so they survive
restarts. Sensible defaults are applied on first run.
"""
from __future__ import annotations

import json
import os
import sys

from PySide6.QtCore import QStandardPaths

from .models import BEST_FORMAT

DEFAULT_SETTINGS: dict = {
    "download_dir": "",
    "ffmpeg_dir": "",
    "max_concurrent": 3,
    "default_format": BEST_FORMAT,   # best video + best audio, merged
    "audio_only": False,
    "browser_server_enabled": True,
    "browser_server_port": 7654,
    "theme": "light",
    "file_template": "%(title)s [%(id)s].%(ext)s",
    # Age verification / login (for age-restricted videos)
    "cookies_mode": "none",          # none | browser | file
    "cookies_browser": "chrome",     # chrome | firefox | edge | brave | opera
    "cookies_file": "",              # path to cookies.txt (when mode == file)
}


class Config:
    """Thin wrapper around a JSON settings file."""

    def __init__(self) -> None:
        self.path = self._config_path()
        self.data: dict = dict(DEFAULT_SETTINGS)
        self.load()
        if not self.data.get("download_dir"):
            self.data["download_dir"] = (
                QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
                or os.path.expanduser("~/Downloads")
            )
        os.makedirs(self.data["download_dir"], exist_ok=True)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _config_path() -> str:
        base = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
        os.makedirs(base, exist_ok=True)
        folder = os.path.join(base, "DownieWin")
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, "config.json")

    def load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                self.data.update(data)
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            # 配置损坏时不要静默丢弃：把原文件改名备份，否则下一次 save()
            # 就会用默认值永久覆盖用户原来的设置。
            backup = self.path + ".corrupt"
            try:
                os.replace(self.path, backup)
            except OSError:
                backup = "(备份失败)"
            print(f"[config] 配置文件损坏（{exc}），已备份到 {backup}，本次使用默认配置")
        except OSError as exc:
            print(f"[config] 读取配置失败：{exc}，本次使用默认配置")

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        # 原子写：先写临时文件并落盘，再 replace。直接 open(...,"w") 在断电 /
        # 杀软拦截时会留下半截 JSON，下次启动就变成“配置全丢”。
        tmp_path = self.path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, self.path)

    # ------------------------------------------------------------------ #
    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value) -> None:
        self.data[key] = value
        self.save()

    def update(self, mapping: dict) -> None:
        self.data.update(mapping)
        self.save()

    # ------------------------------------------------------------------ #
    def effective_ffmpeg_dir(self) -> str:
        """Resolve the ffmpeg directory actually used at runtime.

        Priority:
          1. User-configured ``ffmpeg_dir`` (if it exists and contains ffmpeg).
          2. A ``ffmpeg.exe`` sitting next to the running executable — this is
             what the PyInstaller one-folder build relies on, because
             ``build.spec`` bundles ``ffmpeg.exe`` into the same folder as
             ``DownieWin.exe``.
          3. Otherwise fall back to the configured value (possibly empty, which
             lets yt-dlp use whatever ffmpeg is on the system PATH).
        """
        configured = (self.data.get("ffmpeg_dir") or "").strip()
        if configured and os.path.isfile(os.path.join(configured, "ffmpeg.exe")):
            return configured
        # Bundled next to the executable (frozen build / portable layout).
        exe_dir = os.path.dirname(sys.executable)
        if os.path.isfile(os.path.join(exe_dir, "ffmpeg.exe")):
            return exe_dir
        return configured
