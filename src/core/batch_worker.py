"""批量并行转换（）。
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

import threading
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

# BatchWorker 状态机（）
# 0=IDLE（未启动）  1=RUNNING  2=CANCELLED  3=FINISHED（自然完成）
STATE_IDLE = 0
STATE_RUNNING = 1
STATE_CANCELLED = 2
STATE_FINISHED = 3

class _ConvertRunnable(QRunnable):
    """单文件转换 task。Signal 通过 helper QObject 派回主线程。"""

    class _Signals(QObject):
        item_finished = Signal(str, str)   # path, markdown
        item_failed = Signal(str, object)  # path, ConversionError
        item_done = Signal()               # 计数（成功/失败都算 done）

    def __init__(self, converter: Any, file_path: str) -> None:
        super().__init__()
        # 保留原始 converter 引用，run() 入口才 clone_for_thread()
        # 出来一个带独立 MarkItDown 引擎的实例。lazy clone 避免一次性 N 个实例
        # 全部预构造（如果 batch 在派发阶段就被 cancel()，N 个 clone 浪费）。
        self._source_converter = converter
        self._converter: Any = None  # lazy-cloned in run()
        self._file_path = file_path
        self.signals = _ConvertRunnable._Signals()
        # ：用 threading.Event 保证跨线程内存可见性
        # 之前 self._cancelled: bool 在 worker 线程 run() 和主线程 cancel()
        # 之间无 happens-before 关系，bool 写在 Py3 上不是原子的。
        # Event.set()/is_set() 是线程安全的，set 后所有线程的 is_set() 立刻返回 True。
        # 默认 unset：只有 cancel() 显式 set() 后 run() 才提前 return。
        self._cancel_event = threading.Event()
    def cancel(self) -> None:
        self._cancel_event.set()

    def run(self) -> None:
        if self._cancel_event.is_set():
            # cancel 在 start 之前被设
            return
        # 每个 runnable 持有独立 MarkItDown 引擎。
        # 兼容没有 clone_for_thread 的替身 converter（_StubConverter / 测试 mock / 纯函数）——
        # 这种情况下退化使用原 converter，与行为一致（单线程用同一个实例）。
        if self._converter is None:
            clone = getattr(self._source_converter, "clone_for_thread", None)
            if callable(clone):
                self._converter = clone()
            else:
                self._converter = self._source_converter
        # 兼容测试 mock：converter 可以是 (a) instance with .convert() 方法
        # (b) callable 顶层函数。MarkItDownConverter 走 (a)；
        # 测试 stub/lambda 走 (b)。旧测试套用 lambda 作 converter，
        # 不能要求它们改成有 .convert() 方法的对象。
        converter_obj = self._converter
        try:
            if hasattr(converter_obj, "convert") and callable(converter_obj.convert):
                md = converter_obj.convert(self._file_path)
            else:
                md = converter_obj(self._file_path)
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
        # ：状态机，start() 二次调用守卫用
        self._state: int = STATE_IDLE
        # 留的 _finalize_emitted，在 __init__ 显式置位
        # 避免 cancel() 路径用 getattr 兜底（状态更清晰）
        self._finalize_emitted: bool = False

    def start(self) -> None:
        """派发所有任务（异步，分批让 cancel 能介入）。"""
        # ：start() 二次调用守卫
        # 二次 start() 之前会让 _idx 复位、emit 假 progress 并双倍 dispatch。
        # 只有 IDLE 状态才允许进入 RUNNING。
        if self._state != STATE_IDLE:
            return
        self._state = STATE_RUNNING
        self._idx = 0
        # 启动 0 进度
        self.progress.emit(0, self._total)
        # 初次派发
        self._dispatch_next()

    def _dispatch_next(self) -> None:
        """派发一个任务（受 cancel 约束）。"""
        # ：_dispatch_next() 也加状态守卫
        # IDLE: 还没 start()（不应该被调，_on_item_done 不会触发）
        # CANCELLED / FINISHED: 不再派新任务
        if self._state != STATE_RUNNING:
            return
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

    def wait_finished(self, timeout_ms: int = 2000) -> bool:
        """等所有已派发 runnable 真正回收（公开 API，替代外部直接访问 _pool）。

        v0.4.1 P0 S3：原本 main_window.closeEvent 注释里写
        ``bw._pool.waitForDone(2000)``——访问私有属性，破坏封装。
        现暴露 public 方法 + 单元测试覆盖。

        Args:
            timeout_ms: 最大等待毫秒（默认 2000，UI 关闭场景够用）。

        Returns:
            True = 所有 runnable 都在超时内结束；False = 仍有残留。
        """
        # 拷贝到本地变量避免 self._pool 突然被 GC 回收（极小概率）
        pool = self._pool
        return pool.waitForDone(int(timeout_ms))

    def cancel(self) -> None:
        """协作式取消：不再 dispatch 新任务，已跑的继续。

        注：finished 只在所有路径（包括未跑的）都"结算"后发。
        这里把剩余路径的 done_count 补齐，让 finished 触发。
        说明：cancel() 允许在 IDLE 或 RUNNING 调用，
        已处于 CANCELLED/FINISHED 时是 no-op（不重复进入 finalize 路径）。
        """
        # ：状态守卫
        # 二次 cancel 进来直接 return，避免双重 finalize emit。
        if self._state not in (STATE_IDLE, STATE_RUNNING):
            return
        self._state = STATE_CANCELLED
        # ：cancel finalize 路径内部对 _done_count 的赋值
        # 已经在 mutex 内（下方 self._done_count = self._total），读 _done_count
        # 仅在 progress.emit 用，emit 是主线程排队的，happens-after 自然成立。
        self._mutex.lock()
        self._cancelled = True
        for t in self._dispatched:
            t.cancel()  # ：threading.Event.set() 是原子的
        # 标记 finalize 一次完成，避免与 _on_item_done 双重 finished emit
        self._finalize_emitted = getattr(self, "_finalize_emitted", False)
        already_finalized = self._finalize_emitted
        if not already_finalized:
            self._done_count = self._total
        self._mutex.unlock()
        # 把剩余未 dispatch 的算作"已 done"（按 cancelled），让 finished 触发
        # 在主线程用 QTimer.singleShot(0) 避免重入
        from PySide6.QtCore import QTimer
        def _finalize():
            if getattr(self, "_finalize_emitted", False):
                return
            self._mutex.lock()
            self._finalize_emitted = True
            # 审计（复审 #5）：cancel 路径也释放
            # _dispatched 强引用。cancel 后已 dispatch 的 _ConvertRunnable
            # 仍会跑完（协作式），但 cancel() 已经 set 了 threading.Event，
            # 它们的 run() 会 early return。等所有 runnable 真正回收后，
            # 清 _dispatched 让 GC 回收 _Signals QObject。
            self._dispatched.clear()
            self._mutex.unlock()
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
        # ：done_count 增量 + finished 判定必须原子化
        # Qt queued-slot 让本槽在主线程跑（AutoConnection → Queued），
        # 但 cancel() 可能在主线程并发，锁是显式契约。
        self._mutex.lock()
        if getattr(self, "_finalize_emitted", False):
            # cancel 路径已经 finalize 过，不再重复
            self._mutex.unlock()
            return
        if self._done_count < self._total:
            self._done_count += 1
            self.progress.emit(self._done_count, self._total)
        reached_total = self._done_count >= self._total
        self._mutex.unlock()
        # 派发下一个（如果还有且未取消）
        self._dispatch_next()
        if reached_total:
            self._mutex.lock()
            if getattr(self, "_finalize_emitted", False):
                self._mutex.unlock()
                return
            self._finalize_emitted = True
            # ：自然完成 → 置 FINISHED
            # cancel 路径也会走 _finalize 逻辑（cancel 自己把 _state 改成 CANCELLED），
            # 所以这里只在原状态是 RUNNING 时才覆写为 FINISHED。
            if self._state == STATE_RUNNING:
                self._state = STATE_FINISHED
            # 审计（复审 #5）：释放 _dispatched 持有的
            # _ConvertRunnable 强引用。finalize 检查通过后所有 runnable
            # 都已回收（pool 已 waitForDone + runnable.run() 退出），清
            # 列表让 GC 回收 _ConvertRunnable + 内嵌的 _Signals QObject。
            self._dispatched.clear()
            self._mutex.unlock()
            # 等所有 runnable 真正结束再发 finished（用 QTimer.singleShot 0 让事件循环跑一拍）
            QTimer.singleShot(0, self.finished.emit)
