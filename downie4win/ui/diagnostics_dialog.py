"""Environment diagnostics dialog; checks live in ``downie4win.diagnostics``."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from ..diagnostics import QuickDownloadTest, run_all


def _tag(ok: bool) -> str:
    return "🟢" if ok else "🔴"


class DiagnosticsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("环境诊断")
        self.resize(520, 360)
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        form = QFormLayout()
        self.lbl_yt = QLabel()
        self.lbl_ff = QLabel()
        self.lbl_net = QLabel()
        form.addRow("yt-dlp:", self.lbl_yt)
        form.addRow("ffmpeg:", self.lbl_ff)
        form.addRow("网络:", self.lbl_net)
        root.addLayout(form)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        root.addWidget(self.log)

        btn_row = QHBoxLayout()
        self.test_btn = QPushButton("运行极速下载测试（验证合并）")
        self.test_btn.clicked.connect(self._run_test)
        self.refresh_btn = QPushButton("重新检查")
        self.refresh_btn.clicked.connect(self._refresh)
        btn_row.addWidget(self.test_btn)
        btn_row.addWidget(self.refresh_btn)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _refresh(self) -> None:
        results = run_all(self.config.effective_ffmpeg_dir())
        labels = {
            "yt-dlp": self.lbl_yt,
            "ffmpeg": self.lbl_ff,
            "网络": self.lbl_net,
        }
        for name, result in results:
            labels[name].setText(f"{_tag(result['ok'])} {result['detail']}")
        missing = [(name, result) for name, result in results if not result["ok"]]
        if missing:
            details = "\n  - ".join(
                f"{name}: {result['detail']}" for name, result in missing
            )
            self.log.appendPlainText("⚠️ 以下问题可能影响下载：\n  - " + details)
        else:
            self.log.appendPlainText("✅ 核心依赖就绪。")

    def _run_test(self) -> None:
        self.test_btn.setEnabled(False)
        self.log.appendPlainText("… 正在进行极速下载测试（时长约数秒）…")
        self._tester = QuickDownloadTest(self.config.effective_ffmpeg_dir(), self)
        self._tester.done.connect(self._on_test_done)
        self._tester.start()

    def _on_test_done(self, ok: bool, message: str) -> None:
        self.test_btn.setEnabled(True)
        self.log.appendPlainText(("✅ " if ok else "❌ ") + message)
