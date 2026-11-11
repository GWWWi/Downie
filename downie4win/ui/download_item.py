"""Per-download list row widget."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DownloadItemWidget(QWidget):
    """A single row in the download list showing thumbnail, title, progress
    and controls. The buttons emit signals that the main window wires up."""

    request_pause = Signal()
    request_resume = Signal()
    request_cancel = Signal()
    request_retry = Signal()

    def __init__(self, title: str, subtitle: str, thumbnail_url: str = "", parent=None):
        super().__init__(parent)
        self._build_ui(title, subtitle, thumbnail_url)

    def _build_ui(self, title, subtitle, thumbnail_url):
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        # Thumbnail
        self.thumb = QLabel()
        self.thumb.setFixedSize(96, 54)
        self.thumb.setStyleSheet("QLabel{background:#e9edf2;border-radius:6px;}")
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setText("🎞")
        root.addWidget(self.thumb)

        if thumbnail_url:
            self._fetch_thumb(thumbnail_url)

        # Middle: title + subtitle + progress + status
        mid = QVBoxLayout()
        mid.setSpacing(4)
        self.title_lbl = QLabel(title or "（未知标题）")
        self.title_lbl.setStyleSheet("font-weight:600;")
        self.title_lbl.setWordWrap(True)
        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setStyleSheet("color:#6b7280;font-size:11px;")
        self.sub_lbl.setWordWrap(True)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFixedHeight(14)

        self.status_lbl = QLabel("等待中…")
        self.status_lbl.setStyleSheet("color:#6b7280;font-size:11px;")

        mid.addWidget(self.title_lbl)
        mid.addWidget(self.sub_lbl)
        mid.addWidget(self.bar)
        mid.addWidget(self.status_lbl)
        root.addLayout(mid, 1)

        # Right: control buttons
        ctrl = QVBoxLayout()
        ctrl.setSpacing(4)
        self.btn_pause = QPushButton("暂停")
        self.btn_retry = QPushButton("重试")
        self.btn_cancel = QPushButton("取消")
        for b in (self.btn_pause, self.btn_retry, self.btn_cancel):
            b.setFixedWidth(72)
            b.setFixedHeight(26)
        self.btn_retry.setVisible(False)
        self.btn_pause.clicked.connect(self.request_pause)
        self.btn_retry.clicked.connect(self.request_retry)
        self.btn_cancel.clicked.connect(self.request_cancel)
        ctrl.addWidget(self.btn_pause)
        ctrl.addWidget(self.btn_retry)
        ctrl.addWidget(self.btn_cancel)
        root.addLayout(ctrl)

    # ------------------------------------------------------------------ #
    def _fetch_thumb(self, url: str) -> None:
        self._nam = QNetworkAccessManager()
        self._nam.finished.connect(self._on_thumb)
        self._nam.get(QNetworkRequest(QUrl(url)))

    def _on_thumb(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll().data()
            pix = QPixmap()
            if pix.loadFromData(data):
                self.thumb.setPixmap(
                    pix.scaled(
                        self.thumb.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
        reply.deleteLater()

    # ------------------------------------------------------------------ #
    def set_progress(self, percent: int, speed: str, eta: str, filename: str) -> None:
        if percent > 0:
            self.bar.setRange(0, 100)
            self.bar.setValue(percent)
        else:
            self.bar.setRange(0, 0)  # busy / indeterminate
        self.status_lbl.setText(f"{percent}%  •  {speed}  •  ETA {eta}")

    def set_status(self, text: str) -> None:
        self.status_lbl.setText(text)

    def set_busy(self) -> None:
        self.bar.setRange(0, 0)

    def mark_queued(self) -> None:
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.status_lbl.setText("等待中…")
        self.btn_retry.setText("重试")
        self.btn_retry.setVisible(False)
        self.btn_pause.setVisible(True)
        self.btn_cancel.setVisible(True)

    def mark_success(self, path: str) -> None:
        self.bar.setRange(0, 100)
        self.bar.setValue(100)
        self.status_lbl.setText(f"完成  •  {os.path.basename(path)}")
        self.btn_pause.setVisible(False)
        self.btn_cancel.setVisible(False)
        self.btn_retry.setVisible(False)

    def mark_error(self, msg: str) -> None:
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.status_lbl.setText(f"失败  •  {msg}")
        self.btn_pause.setVisible(False)
        self.btn_retry.setVisible(True)
        self.btn_cancel.setVisible(True)

    def mark_cancelled(self) -> None:
        self.status_lbl.setText("已取消")
        self.btn_pause.setVisible(False)
        self.btn_retry.setVisible(True)

    def mark_paused(self) -> None:
        self.status_lbl.setText("已暂停")
        self.btn_pause.setVisible(False)
        self.btn_retry.setVisible(True)
        self.btn_retry.setText("继续")
        self.btn_cancel.setVisible(True)
