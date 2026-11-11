# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec to build a standalone DownieWin.exe on Windows.

Build:
    pyinstaller build.spec
The resulting executable lands in dist/DownieWin/DownieWin.exe and bundles
yt-dlp + PySide6. Drop ffmpeg.exe next to the .exe (or run get_ffmpeg.py first
and it will be collected automatically from bin/). At runtime the app
auto-detects a bundled ffmpeg.exe sitting next to the executable, so the
standalone exe needs no ffmpeg on PATH and no manual config.
"""
import os

block_cipher = None

HERE = globals().get("SPECPATH") or os.getcwd()
bin_dir = os.path.join(HERE, "bin")

binaries = []
if os.path.isdir(bin_dir):
    for root, _d, files in os.walk(bin_dir):
        for f in files:
            if f.lower() in ("ffmpeg.exe", "ffprobe.exe"):
                binaries.append((os.path.join(root, f), "."))

a = Analysis(
    # Entry is the project-root launcher (absolute import `from downie4win...`).
    # Using downie4win/__main__.py directly fails when frozen because its
    # first line is a relative import with no parent package at the top level.
    [os.path.join(HERE, "main.py")],
    pathex=[HERE],
    binaries=binaries,
    datas=[],
    hiddenimports=[
        "yt_dlp",
        "yt_dlp.extractor",
        "PySide6",
        "PySide6.QtNetwork",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="DownieWin",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=None,
)
