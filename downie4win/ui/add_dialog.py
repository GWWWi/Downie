"""Add-URL dialog: paste a link, pick quality, enqueue the download."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
)

from ..downloader import fetch_info, format_size
from ..models import AUDIO_FORMAT, BEST_FORMAT, FORMAT_PRESETS, DownloadRequest


class _FormatFetcher(QThread):
    done = Signal(object, object)   # info, formats
    error = Signal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self) -> None:
        try:
            info, formats = fetch_info(self.url)
            self.done.emit(info, formats)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


def _fmt_label(f: dict) -> str:
    vid = f.get("vcodec", "none")
    aud = f.get("acodec", "none")
    res = f.get("resolution") or f.get("height")
    note = f.get("format_note", "")
    ext = f.get("ext", "")
    parts = [str(res) if res else "音频" if aud != "none" else "?"]
    if note:
        parts.append(note)
    if ext:
        parts.append(ext)
    if vid != "none" and aud != "none":
        parts.append("音视频")
    elif aud != "none":
        parts.append("仅音频")
    else:
        parts.append("仅视频")
    size = f.get("filesize") or f.get("filesize_approx")
    if size:
        parts.append(format_size(size))
    return f"{f.get('format_id')}: " + " · ".join(parts)


class AddDialog(QDialog):
    """Returns the chosen options via `result_options()` after accept()."""

    def __init__(self, parent=None, last_url: str = ""):
        super().__init__(parent)
        self.setWindowTitle("添加下载")
        self.resize(520, 320)
        self.info = None
        self.formats = []
        self._build_ui(last_url)

    def _build_ui(self, last_url: str) -> None:
        root = QVBoxLayout(self)

        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("链接:"))
        self.url_edit = QLineEdit(last_url)
        self.url_edit.setPlaceholderText("粘贴视频链接，例如 https://www.youtube.com/watch?v=...")
        url_row.addWidget(self.url_edit, 1)
        root.addLayout(url_row)

        self.fetch_btn = QLabel('<a href="fetch">获取可用画质</a>')
        self.fetch_btn.setOpenExternalLinks(False)
        self.fetch_btn.linkActivated.connect(self._fetch)
        self.url_edit.returnPressed.connect(self._fetch)
        root.addWidget(self.fetch_btn)

        self.fetch_bar = QProgressBar()
        self.fetch_bar.setRange(0, 0)
        self.fetch_bar.setVisible(False)
        root.addWidget(self.fetch_bar)

        form = QFormLayout()
        self.format_combo = QComboBox()
        for label, value in FORMAT_PRESETS:
            self.format_combo.addItem(label, value)
        form.addRow("画质 / 格式:", self.format_combo)

        self.audio_chk = QCheckBox("下载完成后转换为 MP3")
        form.addRow(self.audio_chk)
        root.addLayout(form)

        self.meta_lbl = QLabel("")
        self.meta_lbl.setWordWrap(True)
        self.meta_lbl.setStyleSheet("color:#6b7280;font-size:11px;")
        root.addWidget(self.meta_lbl)

        root.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._buttons = buttons

    # ------------------------------------------------------------------ #
    def _fetch(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            return
        self.fetch_bar.setVisible(True)
        self.meta_lbl.setText("正在获取信息…")
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self._fetcher = _FormatFetcher(url, self)
        self._fetcher.done.connect(self._on_formats)
        self._fetcher.error.connect(self._on_error)
        self._fetcher.start()

    def _on_formats(self, info, formats) -> None:
        self.info = info
        self.formats = formats
        self.fetch_bar.setVisible(False)
        title = info.get("title", "?")
        dur = info.get("duration")
        self.meta_lbl.setText(
            f"标题: {title}"
            + (f"  •  时长 {int(dur)}s" if dur else "")
            + f"  •  {len(formats)} 种格式"
        )
        # Populate per-format choices (keep the smart presets at top).
        for f in formats:
            self.format_combo.addItem(_fmt_label(f), f.get("format_id"))
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

    def _on_error(self, msg: str) -> None:
        self.fetch_bar.setVisible(False)
        self.meta_lbl.setText(f"获取失败: {msg}")

    # ------------------------------------------------------------------ #
    def result_options(self) -> DownloadRequest:
        data = self.format_combo.currentData()
        audio_only = self.audio_chk.isChecked() or data == AUDIO_FORMAT
        if data == AUDIO_FORMAT:
            fmt = "bestaudio"
        else:
            fmt = data or BEST_FORMAT
        return DownloadRequest(
            url=self.url_edit.text().strip(),
            format=fmt,
            audio_only=audio_only,
            info=self.info or {},
        )
