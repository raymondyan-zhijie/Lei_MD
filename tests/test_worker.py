"""Worker 异步转换线程测试（Task 1.4）。

按 03 §Task 1.4：5 个测试。
- QThread 子类，后台调 Converter.convert
- signals: started, progress(int), finished(str), error(ConversionError)
- 异常不崩线程，转成 error signal
- cancel() 后线程退出

TDD：先写红灯（mock 还没实现），再补代码。
"""
from __future__ import annotations

import time
from pathlib import Path

from src.core.errors import ConversionError, ErrorCode


class _StubConverter:
    """测试用 Converter 替身：避免真 markitdown 依赖。"""

    def __init__(self, *, sleep: float = 0.0, fail: bool = False, fail_code: ErrorCode = ErrorCode.E_CONVERT_002):
        self.sleep = sleep
        self.fail = fail
        self.fail_code = fail_code
        self.calls: list[str] = []

    def convert(self, file_path: str) -> str:
        self.calls.append(file_path)
        if self.sleep:
            time.sleep(self.sleep)
        if self.fail:
            raise ConversionError(self.fail_code, filename=Path(file_path).name)
        return f"# {Path(file_path).name}\n\nok"


def _wait_for_signal(signal, timeout: float = 2.0) -> bool:
    """阻塞等一个 PySide signal。"""
    from PySide6.QtCore import QEventLoop, QTimer
    loop = QEventLoop()
    received = []

    def _on_emit(*args):
        received.append(args)
        loop.quit()

    signal.connect(_on_emit)
    QTimer.singleShot(int(timeout * 1000), loop.quit)
    loop.exec()
    signal.disconnect(_on_emit)
    return bool(received)


def test_worker_emits_finished_with_markdown(qtbot):
    """正常路径：worker.finished(markdown) 触发。"""
    from src.core.worker import ConversionWorker

    stub = _StubConverter()
    worker = ConversionWorker(stub, "/tmp/a.pdf")  # type: ignore[arg-type]
    worker.start()
    qtbot.waitSignal(worker.finished_with_md, timeout=3000)
    qtbot.waitUntil(lambda: len(stub.calls) == 1, timeout=3000)
    assert stub.calls == ["/tmp/a.pdf"]


def test_worker_emits_error_on_conversion_error(qtbot):
    """转换异常：worker.error(ConversionError) 触发，线程不崩。"""
    from src.core.worker import ConversionWorker

    stub = _StubConverter(fail=True, fail_code=ErrorCode.E_CONVERT_002)
    worker = ConversionWorker(stub, "/tmp/bad.pdf")  # type: ignore[arg-type]
    captured = []
    worker.error.connect(lambda e: captured.append(e))
    worker.start()
    qtbot.waitUntil(lambda: bool(captured), timeout=3000)
    assert isinstance(captured[0], ConversionError)
    assert captured[0].code == ErrorCode.E_CONVERT_002


def test_worker_emits_progress(qtbot):
    """进度信号：worker.progress(0..100)。"""
    from src.core.worker import ConversionWorker

    stub = _StubConverter(sleep=0.05)
    worker = ConversionWorker(stub, "/tmp/slow.pdf")  # type: ignore[arg-type]
    progress_values: list[int] = []
    # AutoConnection（默认）= 跨线程时 queued，qtbot.waitSignal 已含事件循环派发
    worker.progress.connect(lambda pct: progress_values.append(pct))
    worker.start()
    qtbot.waitSignal(worker.finished_with_md, timeout=3000)
    # 等所有 queued signal 派发完
    qtbot.waitUntil(lambda: 100 in progress_values, timeout=2000)
    assert progress_values, "应至少收到一个 progress 事件"
    assert all(0 <= p <= 100 for p in progress_values)
    assert progress_values[-1] == 100


def test_worker_cancel_stops_thread(qtbot):
    """取消：worker.cancel() 后线程退出，未触发 finished。"""
    from src.core.worker import ConversionWorker

    stub = _StubConverter(sleep=0.5)  # 长任务
    worker = ConversionWorker(stub, "/tmp/long.pdf")  # type: ignore[arg-type]
    finished_seen: list[str] = []
    worker.finished_with_md.connect(lambda s: finished_seen.append(s))
    worker.start()
    worker.cancel()
    # 取消后等线程结束
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=3000)
    assert finished_seen == [], "取消后不应触发 finished"


def test_worker_is_qthread_subclass():
    """Worker 必须是 QThread 子类（PySide6 标准）。"""
    from PySide6.QtCore import QThread

    from src.core.worker import ConversionWorker

    assert issubclass(ConversionWorker, QThread)
