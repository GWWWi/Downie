"""One-click build script for DownieWin.

Run it (double-click build.bat on Windows, or `python build.py`) and it will:
  1. create a local .venv if missing,
  2. install requirements + pyinstaller,
  3. download ffmpeg into ./bin (unless SKIP_FFMPEG=1),
  4. run PyInstaller using build.spec,
  5. leave the standalone exe at dist/DownieWin/DownieWin.exe

No need to remember the pyinstaller command ever again.
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(ROOT, ".venv")
PY = (
    os.path.join(VENV, "Scripts", "python.exe")
    if os.name == "nt"
    else os.path.join(VENV, "bin", "python")
)


def run(cmd) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd)


def main() -> int:
    # 1. virtualenv
    if not os.path.exists(PY):
        run([sys.executable, "-m", "venv", VENV])

    # 2. dependencies
    run([PY, "-m", "pip", "install", "-U", "pip"])
    run([PY, "-m", "pip", "install", "-r", os.path.join(ROOT, "requirements.txt")])
    run([PY, "-m", "pip", "install", "pyinstaller"])

    # 3. ffmpeg (optional, skip with SKIP_FFMPEG=1 for a faster build/test)
    if os.environ.get("SKIP_FFMPEG") != "1" and not os.path.exists(
        os.path.join(ROOT, "bin", "ffmpeg.exe")
    ):
        try:
            run([PY, os.path.join(ROOT, "get_ffmpeg.py")])
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] ffmpeg 下载失败（可稍后手动放入 bin/）：{exc}")

    # 4. build
    run(
        [
            PY,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            os.path.join(ROOT, "build.spec"),
        ]
    )

    exe = os.path.join(ROOT, "dist", "DownieWin", "DownieWin.exe")
    print("\n构建完成 🎉")
    print("可执行文件：", exe if os.path.exists(exe) else "(未找到，请检查上方输出)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
