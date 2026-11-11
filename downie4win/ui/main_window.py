"""Main application window and presentation of download task state."""
from __future__ import annotations

import os

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QToolBar,
    QWidget,
)

from .. import __app_name__, __version__
from ..browser_server import BrowserServer
from ..config import Config
from ..download_manager import DownloadManager
from ..models import AUDIO_FORMAT, BEST_FORMAT, DownloadRequest, DownloadTask, TaskState
from .add_dialog import AddDialog
from .diagnostics_dialog import DiagnosticsDialog
from .download_item import DownloadItemWidget
from .settings_dialog import SettingsDialog


def _make_icon() -> QIcon:
    """Generate a simple tray/app icon at runtime (no binary asset needed)."""
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setBrush(QColor("#e11d48"))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(4, 4, 56, 56, 14, 14)
    p.setBrush(QColor("white"))
    p.drawRoundedRect(22, 20, 12, 24, 3, 3)   # play triangle-ish
    p.drawPolygon(
        [pix.rect().topLeft(), pix.rect().topRight(), pix.rect().bottomLeft()]
    )
    p.end()
    return QIcon(pix)


class MainWindow(QMainWindow):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.manager = DownloadManager(config, self)
        self._rows: dict[
            DownloadTask, tuple[QListWidgetItem, DownloadItemWidget]
        ] = {}
        self.manager.task_added.connect(self._add_task_row)
        self.manager.task_removed.connect(self._remove_task_row)
        self.manager.task_progress.connect(self._on_task_progress)
        self.manager.task_status.connect(self._on_task_status)
        self.manager.task_state_changed.connect(self._on_task_state)
        self.manager.task_finished.connect(self._on_task_finished)

        self.setWindowTitle(f"{__app_name__} {__version__}")
        self.resize(820, 560)
        self.setWindowIcon(_make_icon())

        self._build_ui()
        self._build_tray()

        # Browser "send to" server
        self._server = None
        if self.config.get("browser_server_enabled", True):
            self._start_server()

        # One-shot startup environment check (warns if ffmpeg etc. missing)
        QTimer.singleShot(600, self._auto_check)

    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(18, 18))
        self.addToolBar(toolbar)

        self.act_add = QAction("＋ 添加", self)
        self.act_add.triggered.connect(self.on_add)
        self.act_settings = QAction("⚙ 设置", self)
        self.act_settings.triggered.connect(self.on_settings)
        self.act_start_all = QAction("▶ 开始全部", self)
        self.act_start_all.triggered.connect(self.on_start_all)
        self.act_clear = QAction("🗑 清除已完成", self)
        self.act_clear.triggered.connect(self.on_clear_finished)
        self.act_open = QAction("📁 打开下载目录", self)
        self.act_open.triggered.connect(self.on_open_folder)

        for a in (
            self.act_add,
            self.act_start_all,
            self.act_clear,
            self.act_open,
            self.act_settings,
        ):
            toolbar.addAction(a)

        # Menu bar
        menubar = self.menuBar()
        help_menu = menubar.addMenu("帮助")
        diag_act = QAction("环境诊断…", self)
        diag_act.triggered.connect(self.on_diagnostics)
        help_menu.addAction(diag_act)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.setCentralWidget(self.list_widget)

        hint = QWidget()
        hb = QHBoxLayout(hint)
        self.hint_lbl = QPushButton(
            "把视频链接粘贴到这里，或点击「＋ 添加」。也可以安装浏览器扩展一键发送链接。"
        )
        self.hint_lbl.setFlat(True)
        self.hint_lbl.setStyleSheet("color:#9ca3af;")
        self.hint_lbl.clicked.connect(self.on_add)
        hb.addStretch(1)
        hb.addWidget(self.hint_lbl)
        hb.addStretch(1)
        self._hint = hint
        self._show_hint(True)

    def _show_hint(self, show: bool) -> None:
        if show and self.list_widget.count() == 0:
            item = QListWidgetItem(self.list_widget)
            item.setFlags(Qt.NoItemFlags)
            self.list_widget.setItemWidget(item, self._hint)
            item.setSizeHint(self._hint.sizeHint())
        elif not show and self.list_widget.count() == 1 and self.list_widget.item(0).flags() == Qt.NoItemFlags:
            self.list_widget.takeItem(0)

    # ------------------------------------------------------------------ #
    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(_make_icon())
        menu = QMenu(self)
        show_act = QAction("显示窗口", self)
        show_act.triggered.connect(self.showNormal)
        quit_act = QAction("退出", self)
        quit_act.triggered.connect(self._quit_app)
        menu.addAction(show_act)
        menu.addSeparator()
        menu.addAction(quit_act)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self.showNormal() if reason == QSystemTrayIcon.DoubleClick else None
        )
        self.tray.show()

    # ------------------------------------------------------------------ #
    def _start_server(self) -> None:
        self._server = BrowserServer(self.config.get("browser_server_port", 7654))
        if self._server.start():
            self._server.url_received.connect(self.on_url_from_browser)
        else:
            self._server = None

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def on_add(self) -> None:
        clip = QApplication.clipboard().text().strip()
        dlg = AddDialog(self, last_url=clip if clip.startswith("http") else "")
        if dlg.exec() == QDialog.Accepted:
            opts = dlg.result_options()
            self.add_download(opts, interactive=True)

    def on_settings(self) -> None:
        dlg = SettingsDialog(self.config, self)
        if dlg.exec() == QDialog.Accepted:
            # Restart server if port/setting changed.
            if self._server:
                self._server.stop()
                self._server = None
            if self.config.get("browser_server_enabled", True):
                self._start_server()

    def on_diagnostics(self) -> None:
        DiagnosticsDialog(self.config, self).exec()

    def _auto_check(self) -> None:
        from ..diagnostics import missing_components

        miss = missing_components(self.config.effective_ffmpeg_dir())
        if miss:
            QMessageBox.warning(
                self,
                "环境检查",
                "启动检查发现问题：\n\n"
                + "\n".join("• " + m for m in miss)
                + "\n\n可在「帮助 ▸ 环境诊断」查看详情，或在「设置」里指定 ffmpeg。",
            )

    def on_start_all(self) -> None:
        self.manager.start_all()

    def on_clear_finished(self) -> None:
        self.manager.clear_finished()

    def on_open_folder(self) -> None:
        path = self.config.get("download_dir")
        if not path or not os.path.isdir(path):
            return
        if os.name == "nt":
            os.startfile(path)
        else:
            # 不要用 os.system 拼命令：路径里出现双引号就会变成命令注入。
            import subprocess
            subprocess.Popen(["xdg-open", path])

    def on_url_from_browser(self, url: str) -> None:
        if not url:
            return
        default_format = self.config.get("default_format", BEST_FORMAT)
        self.add_download(
            DownloadRequest(
                url=url,
                format=default_format,
                audio_only=default_format == AUDIO_FORMAT,
            ),
            interactive=False,
        )
        try:
            if self.tray.isVisible():
                self.tray.showMessage(
                    __app_name__,
                    f"已添加下载：{url[:60]}",
                    QSystemTrayIcon.Information,
                    2000,
                )
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # DownloadManager signal adapters: this class only renders task state.
    # ------------------------------------------------------------------ #
    def add_download(
        self, options: DownloadRequest | dict, interactive: bool = True
    ) -> DownloadTask:
        request = (
            options
            if isinstance(options, DownloadRequest)
            else DownloadRequest.from_options(options)
        )
        return self.manager.add(request)

    def _add_task_row(self, task: DownloadTask) -> None:
        self._show_hint(False)
        info = task.request.info
        title = info.get("title") or task.url
        subtitle = info.get("uploader") or info.get("webpage_url") or task.url
        widget = DownloadItemWidget(title, subtitle, info.get("thumbnail", ""))
        item = QListWidgetItem()
        item.setSizeHint(widget.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)
        self._rows[task] = (item, widget)

        widget.request_pause.connect(lambda task=task: self.manager.pause(task))
        widget.request_cancel.connect(lambda task=task: self.manager.cancel(task))
        widget.request_retry.connect(lambda task=task: self.manager.retry(task))

    def _remove_task_row(self, task: DownloadTask) -> None:
        row_data = self._rows.pop(task, None)
        if row_data is not None:
            item, _widget = row_data
            row = self.list_widget.row(item)
            if row >= 0:
                self.list_widget.takeItem(row)
        if not self.manager.tasks:
            self._show_hint(True)

    def _row_widget(self, task: DownloadTask) -> DownloadItemWidget | None:
        row_data = self._rows.get(task)
        return row_data[1] if row_data is not None else None

    def _on_task_progress(
        self,
        task: DownloadTask,
        percent: int,
        speed: str,
        eta: str,
        filename: str,
    ) -> None:
        widget = self._row_widget(task)
        if widget is not None:
            widget.set_progress(percent, speed, eta, filename)

    def _on_task_status(self, task: DownloadTask, text: str) -> None:
        widget = self._row_widget(task)
        if widget is not None:
            widget.set_status(text)

    def _on_task_state(self, task: DownloadTask) -> None:
        widget = self._row_widget(task)
        if widget is None:
            return
        if task.state == TaskState.QUEUED:
            widget.mark_queued()
        elif task.state == TaskState.PAUSED:
            widget.mark_paused()

    def _on_task_finished(
        self, task: DownloadTask, success: bool, message: str
    ) -> None:
        widget = self._row_widget(task)
        if widget is None:
            return
        if success:
            widget.mark_success(message)
        elif task.state == TaskState.CANCELLED:
            widget.mark_cancelled()
        else:
            lower = message.lower()
            login_required = any(
                marker in lower
                for marker in ("age", "confirm your age", "sign in", "login")
            )
            widget.mark_error(
                "年龄受限 / 需登录：请在「设置」里配置浏览器 cookies"
                if login_required
                else message
            )

    # ------------------------------------------------------------------ #
    def closeEvent(self, event) -> None:
        # 托盘不可用的环境（部分 Linux / 远程桌面）必须允许正常关闭，否则
        # 窗口关不掉、任务也不取消，只能杀进程。
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self._shutdown()
            event.accept()
            return
        event.ignore()
        self.hide()
        self.tray.showMessage(
            __app_name__,
            "已最小化到系统托盘，点击托盘图标可重新打开。",
            QSystemTrayIcon.Information,
            2000,
        )

    def _shutdown(self) -> None:
        """Stop services and workers before the application exits."""
        if self._server is not None:
            self._server.stop()
            self._server = None
        self.manager.shutdown()

    def _quit_app(self) -> None:
        self._shutdown()
        QApplication.instance().quit()
