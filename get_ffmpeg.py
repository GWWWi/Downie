"""Download a static ffmpeg build for Windows into ./bin and point the
app config at it. Run:  python get_ffmpeg.py
"""
from __future__ import annotations

import os
import sys
import zipfile

try:
    import urllib.request
except ImportError:
    urllib = None  # type: ignore

# Stable "essentials" build (matches what yt-dlp docs recommend on Windows).
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
TARGET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")


def _download(url: str, dest: str) -> None:
    print(f"下载 ffmpeg: {url}")
    urllib.request.urlretrieve(url, dest)  # nosec - trusted static URL


def main() -> int:
    os.makedirs(TARGET_DIR, exist_ok=True)
    zip_path = os.path.join(TARGET_DIR, "ffmpeg.zip")

    try:
        _download(FFMPEG_URL, zip_path)
    except Exception as exc:  # noqa: BLE001
        print(f"下载失败: {exc}")
        print("请手动从 https://www.gyan.dev/ffmpeg/builds/ 下载并解压 ffmpeg.exe 到 bin/ 目录。")
        return 1

    print("解压中…")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(TARGET_DIR)
    os.remove(zip_path)

    # Locate ffmpeg.exe inside the extracted folder.
    ffmpeg_exe = None
    for root, _dirs, files in os.walk(TARGET_DIR):
        if "ffmpeg.exe" in files:
            ffmpeg_exe = os.path.join(root, "ffmpeg.exe")
            break

    if not ffmpeg_exe:
        print("未找到 ffmpeg.exe，解压可能不完整。")
        return 1

    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    print(f"ffmpeg 已安装到: {ffmpeg_dir}")

    # Persist into the app config.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from downie4win.config import Config

        cfg = Config()
        cfg.set("ffmpeg_dir", ffmpeg_dir)
        print("已写入配置 ffmpeg_dir。")
    except Exception as exc:  # noqa: BLE001
        print(f"（跳过写入配置：{exc}）请手动在设置中指定 ffmpeg 目录：{ffmpeg_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
