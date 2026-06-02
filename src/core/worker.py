"""异步转换 Worker（）。
- QThread 子类，后台调 Converter.convert()，避免阻塞主线程
- signals: started, progress(int 0~100), finished(str markdown),
  error(ConversionError), job_done(...)
- 异常不崩线程，全部转 error signal
- cancel() 可中断（设 cancel_event，run() 中检查）

设计：
- 接受任意有 .convert(path) -> str 的对象（鸭子类型），便于 mock/Stub
- 进度在 60% / 90% / 100% 报告（markitdown 不暴露原生进度条，模拟）
- 不在 Worker 里捕获 traceback（日志交给 caller，UI 显示错误码即可）

Terminal signal 语义：
- `job_done` 是**唯一**的 terminal signal，每次 run() 都发（成功/异常/取消）
- `finished_with_md`：仅成功时发（cancel 路径不发）
- `error`：仅真实转换异常时发（cancel 不发，走 job_done(success=False)）
- 消费者（如 HistoryManager._on_job_done）应以 job_done 为权威事实源

"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal

from src.core.errors import ConversionError, ErrorCode  # v0.4.2 P1 C1：顶层导入


class ConversionWorker(QThread):
    """单文件转换后台线程。

    Args:
        converter: 任何带 .convert(path) -> str 方法的对象。
            生产用 MarkItDownConverter，测试用 _StubConverter。
        file_path: 待转换文件的绝对路径。
    """

    # signal 声明
    progress = Signal(int)              # 0~100
    finished_with_md = Signal(str)      # 成功：返回 markdown 文本
    error = Signal(object)              # 失败：返回 ConversionError
    # ：转换完成时携带元信息（路径/格式/长度/耗时/成功/错误）
    # HistoryManager 通过这个 signal 异步写 SQLite
    job_done = Signal(str, str, int, int, bool, str)
    # args: source_path, source_format, markdown_length, duration_ms, success, error_msg

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
        start = time.time()
        path = Path(self._file_path)
        source_format = path.suffix.lower() if path.suffix else ""
        duration_ms = 0
        success = False
        error_msg = ""
        md = ""

        try:
            self.progress.emit(0)

            if self._cancel_event.is_set():
                return

            # markitdown 没有原生进度回调，模拟三个检查点
            self.progress.emit(60)
            if self._cancel_event.is_set():
                return

            md = self._converter.convert(self._file_path)

            if self._cancel_event.is_set():
                return

            self.progress.emit(90)
            self.progress.emit(100)
            # ：emit 成品前再检查一次取消，避免 UI 显示"已取消"但 preview 是满的
            if self._cancel_event.is_set():
                error_msg = "E_SYS_001"  # 用户取消
                return
            self.finished_with_md.emit(md)
            success = True
        except Exception as e:
            # 已是 ConversionError 直接转发；其他异常包装
            if isinstance(e, ConversionError):
                error_msg = str(e.code)
                self.error.emit(e)
            else:
                ce = ConversionError(
                    ErrorCode.E_INTERNAL_001,
                    filename=str(self._file_path),
                    cause=e,
                )
                error_msg = str(ce.code)
                self.error.emit(ce)
        finally:
            # 不管成功/失败/cancel 都发 job_done（cancel 也记，但 success=False）
            duration_ms = int((time.time() - start) * 1000)
            self.job_done.emit(
                self._file_path,
                source_format,
                len(md),
                duration_ms,
                success,
                error_msg,
            )


class YouTubeFetchWorker(QThread):
    """v0.4.2 P1 M4：YouTube 字幕抓取异步 Worker（避免阻塞 UI）。

    复用 ConversionWorker 的 cancel / job_done 模式：
    - cancel() 设 cancel_event（fetch_youtube_transcript 内部不检查，因为
      yt-dlp 抓取是阻塞调用；cancel 主要用于 UI 防呆——禁用按钮 + 状态栏提示）
    - finished(markdown) 成功时 emit
    - error(YouTubeFetchError) 失败时 emit（用户可见）
    """

    finished = Signal(str)  # 成功：返回 markdown
    error = Signal(str)    # 失败：返回错误码（"E_CONVERT_001" 等）+ 消息

    def __init__(self, url: str, *, timeout: int = 30, parent=None):
        super().__init__(parent)
        self._url = url
        self._timeout = timeout
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """请求取消（UI 按钮立即禁用；fetch 本身是阻塞的）。"""
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def run(self) -> None:
        """线程主循环。"""
        from src.core.youtube import (
            YouTubeFetchError,
            extract_video_id,
            fetch_youtube_transcript,
        )

        if self._cancel_event.is_set():
            return
        # 二次校验 URL（避免 UI 在 worker start 之后又改了输入框）
        if extract_video_id(self._url) is None:
            self.error.emit("E_CONVERT_005")
            return
        try:
            md = fetch_youtube_transcript(self._url, timeout=self._timeout)
        except YouTubeFetchError as e:
            # e.code 是字符串形式的 ErrorCode（"E_CONVERT_001" 等）
            self.error.emit(e.code)
            return
        except Exception:
            # 兜底：未知异常 → E_INTERNAL_001
            self.error.emit("E_INTERNAL_001")
            return
        if self._cancel_event.is_set():
            return
        self.finished.emit(md)
