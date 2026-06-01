"""异步转换 Worker（Task 1.4）。

按 03 §Task 1.4：
- QThread 子类，后台调 Converter.convert()，避免阻塞主线程
- signals: started, progress(int 0~100), finished(str markdown), error(ConversionError)
- 异常不崩线程，全部转 error signal
- cancel() 可中断（设 cancel_event，run() 中检查）

设计：
- 接受任意有 .convert(path) -> str 的对象（鸭子类型），便于 mock/Stub
- 进度在 60% / 90% / 100% 报告（markitdown 不暴露原生进度条，模拟）
- 不在 Worker 里捕获 traceback（日志交给 caller，UI 显示错误码即可）
"""
from __future__ import annotations

import threading
from typing import Any

from PySide6.QtCore import QThread, Signal


class ConversionWorker(QThread):
    """单文件转换后台线程。

    Args:
        converter: 任何带 .convert(path) -> str 方法的对象。
            生产用 MarkItDownConverter，测试用 _StubConverter。
        file_path: 待转换文件的绝对路径。
    """

    # signal 声明
    progress = Signal(int)          # 0~100
    finished_with_md = Signal(str)  # 成功：返回 markdown 文本
    error = Signal(object)          # 失败：返回 ConversionError

    def __init__(self, converter: Any, file_path: str, parent=None):
        super().__init__(parent)
        self._converter = converter
        self._file_path = file_path
        # 用 threading.Event 而非 QThread.requestInterruption（更易测）
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """请求取消。不强制终止线程，但 run() 会在检查点退出。"""
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def run(self) -> None:
        """线程主循环。"""
        try:
            self.progress.emit(0)

            if self._cancel_event.is_set():
                return

            # markitdown 没有原生进度回调，模拟三个检查点
            self.progress.emit(60)
            if self._cancel_event.is_set():
                return

            markdown = self._converter.convert(self._file_path)

            if self._cancel_event.is_set():
                return

            self.progress.emit(90)
            self.progress.emit(100)
            self.finished_with_md.emit(markdown)
        except Exception as e:
            # 已是 ConversionError 直接转发；其他异常包装
            from src.core.errors import ConversionError, ErrorCode
            if isinstance(e, ConversionError):
                self.error.emit(e)
            else:
                self.error.emit(
                    ConversionError(
                        ErrorCode.E_INTERNAL_001,
                        filename=str(self._file_path),
                        cause=e,
                    )
                )
