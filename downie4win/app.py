"""Application bootstrap."""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox


def _ensure_yt_dlp() -> bool:
    try:
        import yt_dlp  # noqa: F401
        return True
    except ImportError:
        return False


def main() -> int:
    # HiDPI aware (Windows).
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("DownieWin")
    app.setApplicationDisplayName("DownieWin")

    if not _ensure_yt_dlp():
        QMessageBox.critical(
            None,
            "缺少依赖",
            "未检测到 yt-dlp。请先运行：\n\n  pip install -r requirements.txt\n\n"
            "然后重新启动本程序。",
        )
        return 1

    # Import application modules after the dependency check so a missing
    # yt-dlp produces the friendly error above instead of an import traceback.
    from .config import Config
    from .ui.main_window import MainWindow

    config = Config()
    window = MainWindow(config)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
