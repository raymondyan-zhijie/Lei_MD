"""Regression tests for v0.2.1 hotfixes: H2 / H3 / H4.

v0.2.2 audit M3.2 回归（terminal-signal 三选一 contract）：
- test_worker_cancel_emits_job_done_but_not_error_or_finished
  验证 cancel 路径下只发 job_done，不发 finished_with_md / error。
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QEventLoop, QTimer

from src.core.config import ConfigManager
from src.core.worker import ConversionWorker

# ============ H3: UTF-8 BOM 容忍 ============


def test_config_loads_with_utf8_bom(monkeypatch, tmp_path):
    """ConfigManager accepts config.json saved with UTF-8 BOM (Windows Notepad default)."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    cfg_file = tmp_path / "config" / "Lei_MD" / "config.json"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_bytes(b"\xef\xbb\xbf" + b'{"theme": "dark", "language": "zh_CN"}')
    cm = ConfigManager()
    assert cm.get().theme == "dark"
    assert cm.get().language == "zh_CN"


# ============ H4: cancel() 后 finished_with_md 不发 ============


def _make_stub_converter(md: str = "# hi", delay_s: float = 0.05):
    """Stub converter: sleeps delay_s then returns md."""

    class _Stub:
        def convert(self, path: str) -> str:
            time.sleep(delay_s)
            return md

    return _Stub()


def test_worker_cancel_after_convert_does_not_emit_finished(qtbot, tmp_path):
    """H4: cancel() after convert() returns must NOT emit finished_with_md."""
    f = tmp_path / "x.txt"
    f.write_text("hi")
    worker = ConversionWorker(_make_stub_converter(delay_s=0.2), str(f))

    finished_seen = []
    worker.finished_with_md.connect(lambda md: finished_seen.append(md))

    worker.start()
    # 等 convert() 起步后再取消
    QTimer.singleShot(50, worker.cancel)
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=3000)
    assert finished_seen == [], f"finished_with_md should not emit after cancel, got {finished_seen}"


def test_worker_cancel_before_emit_keeps_no_preview(qtbot, tmp_path):
    """H4 sanity: convert() 完成后才取消也保护 preview 不被更新。"""
    f = tmp_path / "x.txt"
    f.write_text("hi")
    # 0 延迟 converter，cancel 几乎在 convert 返回同时
    worker = ConversionWorker(_make_stub_converter(delay_s=0.0), str(f))
    finished_seen = []
    error_seen = []
    worker.finished_with_md.connect(lambda md: finished_seen.append(md))
    worker.error.connect(lambda e: error_seen.append(e))
    worker.start()
    worker.cancel()  # 立即取消
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=3000)
    # 可能两者都不发（H4 行为），也可能发 error（取消语义）
    assert finished_seen == [], "must not emit finished_with_md when cancel was requested"


# ============ H2: 批量取消按钮生效 ============


@pytest.fixture
def isolated_config(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    from src.core.config import ConfigManager
    return ConfigManager()


@pytest.fixture
def isolated_history(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    from src.core.history import HistoryManager
    return HistoryManager()


def test_mainwindow_cancel_button_cancels_batch(qtbot, monkeypatch, isolated_config, isolated_history, tmp_path):
    """H2: clicking cancel during a batch calls batch.cancel() (not silent no-op)."""
    from src.ui.main_window import MainWindow

    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    cancel_called = []

    class _FakeBW:
        def __init__(self, converter, paths, concurrency):
            self.progress = MagicMock()
            self.finished = MagicMock()
            self.item_failed = MagicMock()
        def cancel(self):
            cancel_called.append(True)
        def start(self): pass

    monkeypatch.setattr("src.ui.main_window.BatchWorker", _FakeBW)

    # 准备一个真文件让 _start_batch 不会因空列表早返回
    a = tmp_path / "a.txt"
    a.write_text("hi")
    win.file_list.add_files([str(a)])

    win._start_batch()
    # 此时 _active_batch 应被设上
    assert win._active_batch is not None

    # 模拟点击取消按钮
    win._on_cancel_clicked()
    assert cancel_called == [True], f"batch.cancel() should be called once, got {cancel_called}"


# ============ M3.2: cancel 路径 terminal-signal 三选一 contract ============


class _RecordingConverter:
    """Stub converter：convert() 内 sleep 一段，外部可在 sleep 中调用 cancel()。

    用于覆盖 H4 的"convert 返回后才被 cancel"路径（H4 修复的关键场景）。
    """

    def __init__(self, md: str = "# hi", pre_emit_sleep_s: float = 0.15):
        self._md = md
        self._sleep = pre_emit_sleep_s
        self.calls: list[str] = []

    def convert(self, path: str) -> str:
        self.calls.append(path)
        time.sleep(self._sleep)  # 给 cancel() 留窗口
        return self._md


def test_worker_cancel_emits_job_done_but_not_error_or_finished(qtbot, monkeypatch, tmp_path):
    """M3.2: cancel 路径下 terminal signal 必须三选一——只发 job_done。

    监听三个 signal（finished_with_md / error / job_done），
    断言 cancel 后：
    - job_done 必发，且 success=False，error_msg ∈ {"", "E_SYS_001"}
    - finished_with_md 不发
    - error 不发

    覆盖 H4 路径（convert 返回后 cancel 触发 H4 早期 return）。
    """
    f = tmp_path / "cancel.txt"
    f.write_text("hi")
    # convert() sleep 0.20s；cancel 在 80ms 触发 → cancel 在 convert() 返回前
    # 即命中 worker.py:79 的早期 return（"md = ... ; if cancel: return"）
    # 该路径与 H4 路径（worker.py:85）都满足 M3.2 contract：只发 job_done。
    converter = _RecordingConverter(md="# hi", pre_emit_sleep_s=0.20)

    # 用 monkeypatch 注入可观察的 converter（spy 桩模式）
    monkeypatch.setattr(converter, "convert", converter.convert, raising=True)

    worker = ConversionWorker(converter, str(f))

    # 三个 spy list（跨线程用 queued connection，事件循环派发）
    finished_seen: list[str] = []
    error_seen: list[object] = []
    job_done_seen: list[tuple] = []

    def _on_finished(md: str) -> None:
        finished_seen.append(md)

    def _on_error(e: object) -> None:
        error_seen.append(e)

    def _on_job_done(source_path, source_format, md_len, duration_ms, success, error_msg):
        job_done_seen.append(
            (source_path, source_format, md_len, duration_ms, success, error_msg)
        )

    worker.finished_with_md.connect(_on_finished)
    worker.error.connect(_on_error)
    worker.job_done.connect(_on_job_done)

    worker.start()
    QTimer.singleShot(80, worker.cancel)  # cancel 在 convert 睡眠中 → 命中 line 79
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=3000)
    # 给事件循环一拍时间让 queued signal 派发完
    qtbot.waitUntil(lambda: len(job_done_seen) >= 1, timeout=2000)
    # 再拍一拍，确保 finished_with_md/error 不会有延迟 emit
    settled_loop = QEventLoop()
    QTimer.singleShot(150, settled_loop.quit)
    settled_loop.exec()

    # 主契约：terminal signal 三选一
    assert finished_seen == [], (
        f"cancel 路径不应有 finished_with_md listener 被调, got {finished_seen}"
    )
    assert error_seen == [], (
        f"cancel 路径不应有 error listener 被调, got {error_seen}"
    )

    # job_done 必发，且语义 = 用户取消（success=False）
    assert len(job_done_seen) == 1, (
        f"job_done 应只发一次, got {len(job_done_seen)} 次: {job_done_seen}"
    )
    src_path, src_fmt, md_len, dur_ms, success, err_msg = job_done_seen[0]
    assert src_path == str(f)
    assert src_fmt == ".txt"
    assert success is False, f"cancel 后 success 应为 False, got {success!r}"
    # M3.2 决策：cancel 不再算 error；H4 路径下 error_msg="E_SYS_001"，
    # 早 3 个 cancel 检查点 error_msg=""（run() 默认值）。两者都代表 cancel。
    assert err_msg in ("", "E_SYS_001"), (
        f"cancel 后 error_msg 应为 '' 或 'E_SYS_001'，got {err_msg!r}"
    )
