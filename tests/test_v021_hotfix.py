"""Regression tests for v0.2.1 hotfixes: H2 / H3 / H4."""
from __future__ import annotations

import time
from pathlib import Path
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
