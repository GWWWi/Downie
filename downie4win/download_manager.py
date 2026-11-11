"""Download queue, concurrency control, and worker lifetime management.

This module deliberately has no widget imports. The main window observes
signals and renders task state; all state transitions live here.
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from .config import Config
from .downloader import DownloadWorker
from .models import DownloadRequest, DownloadTask, TaskState


class DownloadManager(QObject):
    """Own download tasks and serialize every queue state transition."""

    task_added = Signal(object)
    task_removed = Signal(object)
    task_progress = Signal(object, int, str, str, str)
    task_status = Signal(object, str)
    task_state_changed = Signal(object)
    task_finished = Signal(object, bool, str)

    def __init__(
        self,
        config: Config,
        parent: QObject | None = None,
        *,
        worker_factory: Callable[..., DownloadWorker] = DownloadWorker,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self._worker_factory = worker_factory
        self._tasks: list[DownloadTask] = []
        # A paused task may still have a thread winding down, so active count
        # must be based on real workers rather than the visible task state.
        self._running: dict[DownloadTask, DownloadWorker] = {}
        # Keep removed-but-running QThreads alive until they actually exit.
        self._retired: list[DownloadWorker] = []

    @property
    def tasks(self) -> tuple[DownloadTask, ...]:
        return tuple(self._tasks)

    @property
    def active_count(self) -> int:
        return len(self._running)

    def add(self, request: DownloadRequest) -> DownloadTask:
        task = DownloadTask(request)
        self._tasks.append(task)
        self.task_added.emit(task)
        self._make_worker(task)
        self._schedule()
        return task

    def start_all(self) -> None:
        restartable = {
            TaskState.QUEUED,
            TaskState.ERROR,
            TaskState.CANCELLED,
            TaskState.PAUSED,
        }
        for task in self.tasks:
            if task.state in restartable:
                self._relaunch(task)
        self._schedule()

    def clear_finished(self) -> None:
        removable = {TaskState.DONE, TaskState.ERROR, TaskState.CANCELLED}
        for task in self.tasks:
            if task.state in removable:
                self._remove_task(task)

    def pause(self, task: DownloadTask) -> None:
        if task.state != TaskState.ACTIVE or task not in self._running:
            return
        worker = task.worker
        if worker is None:
            return
        task.pause_requested = True
        worker.cancel()
        self._set_state(task, TaskState.PAUSED)

    def retry(self, task: DownloadTask) -> None:
        if task in self._running:
            return
        self._relaunch(task)
        self._schedule()

    def cancel(self, task: DownloadTask) -> None:
        if task.state == TaskState.ACTIVE:
            task.remove_on_finish = True
            task.pause_requested = False
            if task.worker is not None:
                task.worker.cancel()
            self.task_status.emit(task, "正在取消…")
        else:
            self._remove_task(task)

    def shutdown(self) -> None:
        """Cancel workers and briefly wait, avoiding orphan ffmpeg processes."""
        running = list(self._running.values())
        for worker in running:
            worker.cancel()
        running.extend(self._retired)
        for worker in running:
            if worker.isRunning():
                worker.wait(3000)

    def _cookies(self) -> dict[str, str]:
        return {
            "mode": self.config.get("cookies_mode", "none"),
            "browser": self.config.get("cookies_browser", "chrome"),
            "file": self.config.get("cookies_file", ""),
        }

    def _make_worker(self, task: DownloadTask) -> DownloadWorker:
        worker = self._worker_factory(
            task.request,
            self.config.get("download_dir"),
            self.config.get("file_template"),
            self.config.effective_ffmpeg_dir(),
            self._cookies(),
        )
        worker.progress.connect(
            lambda percent, speed, eta, filename, task=task: self.task_progress.emit(
                task, percent, speed, eta, filename
            )
        )
        worker.status.connect(
            lambda text, task=task: self.task_status.emit(task, text)
        )
        worker.finished.connect(
            lambda success, message, task=task, worker=worker: self._on_finished(
                task, worker, success, message
            )
        )
        task.worker = worker
        return worker

    def _set_state(self, task: DownloadTask, state: TaskState) -> None:
        if task.state == state:
            return
        task.state = state
        self.task_state_changed.emit(task)

    def _launch(self, task: DownloadTask) -> None:
        if task.state != TaskState.QUEUED or task in self._running:
            return
        worker = task.worker
        if worker is None:
            worker = self._make_worker(task)
        if worker.isRunning():
            return
        self._running[task] = worker
        self._set_state(task, TaskState.ACTIVE)
        self.task_status.emit(task, "开始下载…")
        worker.start()

    def _schedule(self) -> None:
        limit = max(1, int(self.config.get("max_concurrent", 3)))
        for task in self.tasks:
            if self.active_count >= limit:
                break
            if task.state == TaskState.QUEUED:
                self._launch(task)

    def _on_finished(
        self,
        task: DownloadTask,
        worker: DownloadWorker,
        success: bool,
        message: str,
    ) -> None:
        if self._running.get(task) is worker:
            del self._running[task]
        if task not in self._tasks or task.worker is not worker:
            self._schedule()
            return

        if task.remove_on_finish:
            task.remove_on_finish = False
            task.pause_requested = False
            self._remove_task(task)
            self._schedule()
            return

        if task.pause_requested:
            task.pause_requested = False
            self._set_state(task, TaskState.PAUSED)
            self._schedule()
            return

        if success:
            self._set_state(task, TaskState.DONE)
        elif message == "已取消":
            self._set_state(task, TaskState.CANCELLED)
        else:
            self._set_state(task, TaskState.ERROR)
        self.task_finished.emit(task, success, message)
        self._schedule()

    def _relaunch(self, task: DownloadTask) -> None:
        if task in self._running:
            return
        old_worker = task.worker
        if old_worker is not None and old_worker.isRunning():
            return
        task.pause_requested = False
        task.remove_on_finish = False
        self._make_worker(task)
        self._set_state(task, TaskState.QUEUED)

    def _remove_task(self, task: DownloadTask) -> None:
        if task not in self._tasks:
            return
        worker = task.worker
        if worker is not None and worker.isRunning():
            task.remove_on_finish = True
            task.pause_requested = False
            worker.cancel()
            self._retire(worker)
            task.worker = None
        elif worker is not None:
            worker.wait(200)

        self._tasks.remove(task)
        self.task_removed.emit(task)

    def _retire(self, worker: DownloadWorker) -> None:
        if worker in self._retired:
            return
        self._retired.append(worker)
        QTimer.singleShot(200, self._reap_retired)

    def _reap_retired(self) -> None:
        still_running: list[DownloadWorker] = []
        for worker in self._retired:
            if worker.isRunning():
                still_running.append(worker)
            else:
                worker.wait(0)
        self._retired = still_running
        if self._retired:
            QTimer.singleShot(200, self._reap_retired)
