"""Settings dialog."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ..config import Config
from ..models import BEST_FORMAT, FORMAT_PRESETS


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("设置")
        self.resize(520, 360)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        form = QFormLayout()

        # Download folder
        dlg_row = QHBoxLayout()
        self.dir_edit = QLineEdit(self.config.get("download_dir"))
        self.dir_btn = QPushButton("浏览…")
        self.dir_btn.clicked.connect(self._pick_dir)
        dlg_row.addWidget(self.dir_edit, 1)
        dlg_row.addWidget(self.dir_btn)
        form.addRow("下载目录:", dlg_row)

        # ffmpeg directory
        ff_row = QHBoxLayout()
        self.ff_edit = QLineEdit(self.config.get("ffmpeg_dir"))
        self.ff_edit.setPlaceholderText("留空则使用系统 PATH 中的 ffmpeg")
        self.ff_btn = QPushButton("浏览…")
        self.ff_btn.clicked.connect(self._pick_ff)
        ff_row.addWidget(self.ff_edit, 1)
        ff_row.addWidget(self.ff_btn)
        form.addRow("ffmpeg 目录:", ff_row)

        # Max concurrent
        self.concurrent = QSpinBox()
        self.concurrent.setRange(1, 8)
        self.concurrent.setValue(int(self.config.get("max_concurrent", 3)))
        form.addRow("最大同时下载数:", self.concurrent)

        # Default format
        self.default_fmt = QComboBox()
        for label, value in FORMAT_PRESETS:
            self.default_fmt.addItem(label, value)
        cur = self.config.get("default_format", BEST_FORMAT)
        idx = self.default_fmt.findData(cur)
        if idx >= 0:
            self.default_fmt.setCurrentIndex(idx)
        form.addRow("默认画质:", self.default_fmt)

        # Browser server
        self.server_chk = QCheckBox("启用浏览器扩展「发送到 Downie」")
        self.server_chk.setChecked(bool(self.config.get("browser_server_enabled", True)))
        self.port = QSpinBox()
        self.port.setRange(1024, 65535)
        self.port.setValue(int(self.config.get("browser_server_port", 7654)))
        form.addRow(self.server_chk)
        form.addRow("监听端口:", self.port)

        # Age verification / login
        self.cookies_mode = QComboBox()
        self.cookies_mode.addItem("不使用", "none")
        self.cookies_mode.addItem("从浏览器导入 cookies", "browser")
        self.cookies_mode.addItem("使用 cookies.txt 文件", "file")
        cur_mode = self.config.get("cookies_mode", "none")
        mi = self.cookies_mode.findData(cur_mode)
        if mi >= 0:
            self.cookies_mode.setCurrentIndex(mi)
        self.cookies_mode.currentIndexChanged.connect(self._on_cookies_mode)
        form.addRow("年龄验证 / 登录:", self.cookies_mode)

        self.cookies_browser = QComboBox()
        for b in ("chrome", "firefox", "edge", "brave", "opera"):
            self.cookies_browser.addItem(b)
        bi = self.cookies_browser.findText(self.config.get("cookies_browser", "chrome"))
        if bi >= 0:
            self.cookies_browser.setCurrentIndex(bi)
        form.addRow("浏览器:", self.cookies_browser)

        cf_row = QHBoxLayout()
        self.cookies_file = QLineEdit(self.config.get("cookies_file", ""))
        self.cookies_file.setPlaceholderText("cookies.txt 路径（模式选「文件」时生效）")
        self.cookies_file_btn = QPushButton("浏览…")
        self.cookies_file_btn.clicked.connect(self._pick_cookies)
        cf_row.addWidget(self.cookies_file, 1)
        cf_row.addWidget(self.cookies_file_btn)
        form.addRow("cookies 文件:", cf_row)

        self._on_cookies_mode()

        root.addLayout(form)
        root.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ------------------------------------------------------------------ #
    def _pick_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择下载目录", self.dir_edit.text())
        if d:
            self.dir_edit.setText(d)

    def _pick_ff(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "选择 ffmpeg 所在目录", self.ff_edit.text()
        )
        if d:
            self.ff_edit.setText(d)

    def _pick_cookies(self) -> None:
        f, _ = QFileDialog.getOpenFileName(
            self, "选择 cookies.txt", self.cookies_file.text(),
            "Text files (*.txt);;All files (*.*)",
        )
        if f:
            self.cookies_file.setText(f)

    def _on_cookies_mode(self) -> None:
        mode = self.cookies_mode.currentData()
        self.cookies_browser.setEnabled(mode == "browser")
        self.cookies_file.setEnabled(mode == "file")
        self.cookies_file_btn.setEnabled(mode == "file")

    def _save(self) -> None:
        self.config.update(
            {
                "download_dir": self.dir_edit.text(),
                "ffmpeg_dir": self.ff_edit.text(),
                "max_concurrent": self.concurrent.value(),
                "default_format": self.default_fmt.currentData(),
                "browser_server_enabled": self.server_chk.isChecked(),
                "browser_server_port": self.port.value(),
                "cookies_mode": self.cookies_mode.currentData(),
                "cookies_browser": self.cookies_browser.currentText(),
                "cookies_file": self.cookies_file.text(),
            }
        )
        self.accept()
