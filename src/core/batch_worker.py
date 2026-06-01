"""批量并行转换（Task 2.2）。

按 03 §Task 2.2：
- QThreadPool 跑 N 个 QRunnable，并发度可配（默认从 ConfigManager.batch_concurrency 读 4）
- progress(int done, int total) 每完成一个 emit
- item_finished(path, md) / item_failed(path, err) 单条 signal
- finished() 所有完成时 emit
- cancel() 协作式：不再 dispatch 新任务，已跑的不强杀

设计：
- BatchWorker 本身是 QObject 容器（不是 QThread，本身不跑）
- 用 QThreadPool.start(QRunnable) 派发
- 每个 _ConvertRunnable 跑一次 converter.convert()，结果用 signal 回到主线程
- _done_count 用 QMutex 保护（Qt queued slot 保证在主线程跑，但 cancel 时序需要锁）
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    QMutex,
    QObject,
    QRunnable,
    QThreadPool,
    QTimer,
    Signal,
    Slot,
)


class _ConvertRunnable(QRunnable):
    """单文件转换 task。Signal 通过 helper QObject 派回主线程。"""

    class _Signals(QObject):
        item_finished = Signal(str, str)   # path, markdown
        item_failed = Signal(str, object)  # path, ConversionError
        item_done = Signal()               # 计数（成功/失败都算 done）

    def __init__(self, converter: Any, file_path: str) -> None:
        super().__init__()
        self._converter = converter
        self._file_path = file_path
        self.signals = _ConvertRunnable._Signals()
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        if self._cancelled:
            # cancel 在 start 之前被设
            return
        try:
            md = self._converter.convert(self._file_path)
            self.signals.item_finished.emit(self._file_path, md)
        except Exception as e:
            from src.core.errors import ConversionError, ErrorCode
            if isinstance(e, ConversionError):
                self.signals.item_failed.emit(self._file_path, e)
            else:
                ce = ConversionError(
                    ErrorCode.E_INTERNAL_001,
                    filename=str(self._file_path),
                    cause=e,
                )
                self.signals.item_failed.emit(self._file_path, ce)
        finally:
            self.signals.item_done.emit()


class BatchWorker(QObject):
    """批量并行转换管理器。

    Args:
        converter: 任何带 .convert(path) -> str 方法的对象。
        file_paths: 待转换路径列表。
        concurrency: 并发度（默认 4，可从 ConfigManager.batch_concurrency 读）。
    """

    progress = Signal(int, int)         # done, total
    item_finished = Signal(str, str)    # path, markdown
    item_failed = Signal(str, object)   # path, ConversionError
    finished = Signal()                 # 全部完成

    def __init__(
        self,
        converter: Any,
        file_paths: list[str],
        concurrency: int = 4,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._converter = converter
        self._paths = list(file_paths)
        self._concurrency = max(1, int(concurrency))
        self._total = len(self._paths)
        self._done_count = 0
        self._cancelled = False
        self._mutex = QMutex()
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(self._concurrency)
        # 跟踪已派发 runnable（cancel 时设 cancelled）
        self._dispatched: list[_ConvertRunnable] = []

    def start(self) -> None:
        """派发所有任务（异步，分批让 cancel 能介入）。"""
        self._idx = 0
        # 启动 0 进度
        self.progress.emit(0, self._total)
        # 初次派发
        self._dispatch_next()

    def _dispatch_next(self) -> None:
        """派发一个任务（受 cancel 约束）。"""
        self._mutex.lock()
        if self._cancelled or self._idx >= self._total:
            self._mutex.unlock()
            return
        path = self._paths[self._idx]
        self._idx += 1
        self._mutex.unlock()

        task = _ConvertRunnable(self._converter, path)
        task.signals.item_finished.connect(self._on_item_finished)
        task.signals.item_failed.connect(self._on_item_failed)
        # item_done 内部：每完成一个，尝试再派发下一个
        task.signals.item_done.connect(self._on_item_done)
        self._dispatched.append(task)
        self._pool.start(task)

    def cancel(self) -> None:
        """协作式取消：不再 dispatch 新任务，已跑的继续。

        注：finished 只在所有路径（包括未跑的）都"结算"后发。
        这里把剩余路径的 done_count 补齐，让 finished 触发。
        """
        self._mutex.lock()
        self._cancelled = True
        for t in self._dispatched:
            t.cancel()
        self._mutex.unlock()
        # 把剩余未 dispatch 的算作"已 done"（按 cancelled），让 finished 触发
        # 在主线程用 QTimer.singleShot(0) 避免重入
        from PySide6.QtCore import QTimer
        def _finalize():
            if self._done_count < self._total:
                self._done_count = self._total
                self.progress.emit(self._done_count, self._total)
                self.finished.emit()
        QTimer.singleShot(0, _finalize)

    @Slot(str, str)
    def _on_item_finished(self, path: str, md: str) -> None:
        self.item_finished.emit(path, md)

    @Slot(str, object)
    def _on_item_failed(self, path: str, err: object) -> None:
        self.item_failed.emit(path, err)

    @Slot()
    def _on_item_done(self) -> None:
        self._done_count += 1
        self.progress.emit(self._done_count, self._total)
        # 派发下一个（如果还有且未取消）
        self._dispatch_next()
        if self._done_count >= self._total:
            # 等所有 runnable 真正结束再发 finished（用 QTimer.singleShot 0 让事件循环跑一拍）
            QTimer.singleShot(0, self.finished.emit)
