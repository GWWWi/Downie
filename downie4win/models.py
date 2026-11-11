"""Domain models shared by the UI and download services."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

BEST_FORMAT = "bv*+ba/b"
AUDIO_FORMAT = "__audio__"
FORMAT_PRESETS: tuple[tuple[str, str], ...] = (
    ("最佳画质（自动合并音视频）", BEST_FORMAT),
    ("仅音频（MP3）", AUDIO_FORMAT),
    ("720p", "best[height<=720]"),
    ("480p", "best[height<=480]"),
    ("360p", "best[height<=360]"),
)


@dataclass(frozen=True, slots=True)
class DownloadRequest:
    """Immutable user choices needed to create one download."""

    url: str
    format: str = BEST_FORMAT
    audio_only: bool = False
    info: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_options(cls, options: Mapping[str, Any]) -> "DownloadRequest":
        """Convert legacy dialog/browser option mappings to a typed request."""
        return cls(
            url=str(options["url"]).strip(),
            format=str(options.get("format") or BEST_FORMAT),
            audio_only=bool(options.get("audio_only", False)),
            info=dict(options.get("info") or {}),
        )


class TaskState(str, Enum):
    QUEUED = "queued"
    ACTIVE = "active"
    PAUSED = "paused"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass(eq=False, slots=True)
class DownloadTask:
    """Runtime state for a queue entry; identity is stable across retries."""

    request: DownloadRequest
    state: TaskState = TaskState.QUEUED
    worker: Any = field(default=None, repr=False)
    remove_on_finish: bool = False
    pause_requested: bool = False

    @property
    def url(self) -> str:
        return self.request.url
