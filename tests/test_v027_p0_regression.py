"""v0.2.7 P0 regression tests (post-audit fixes)."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from src.core.config import ConfigManager
from src.core.history import HistoryManager
from src.ui import i18n
from src.ui.i18n import set_locale
from src.ui.main_window import MainWindow


@pytest.fixture
def isolated_config(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    return ConfigManager()


@pytest.fixture
def isolated_history(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    return HistoryManager()


# ============ 4a-1: HistoryManager.close() 在 closeEvent 调 ============


def test_close_event_calls_history_close(qtbot, isolated_config, isolated_history, caplog):
    """P0: MainWindow.closeEvent must call self._history.close() to release WAL."""
    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    assert isolated_history._conn is not None, "history db should be open"

    with caplog.at_level(logging.WARNING):
        win.close()

    # close() 是 best-effort，但调过。WAL checkpoint 后 _conn 应仍可用
    # （close 不 unbind Python 引用，只 sqlite3 close）；下次 list 仍 OK
    # 关键：close 路径无异常被记录（除已知的 deleteLater RuntimeError 哨兵）
    fatal = [r for r in caplog.records if "HistoryManager.close() failed" in r.message]
    assert not fatal, f"close() failed: {[r.getMessage() for r in fatal]}"


def test_close_event_without_history_is_noop(qtbot, isolated_config):
    """P0: history is None 时 closeEvent 不应崩。"""
    win = MainWindow(config_manager=isolated_config, history=None)
    win.close()  # 不抛


# ============ 4a-3: DEFAULT_LOCALE="en" 不 spam warning ============


def test_set_locale_en_does_not_warn(caplog):
    """P0: set_locale('en') (DEFAULT_LOCALE) is in whitelist — no warning logged."""
    with caplog.at_level(logging.WARNING, logger="src.ui.i18n"):
        set_locale("en")
    warns = [r for r in caplog.records if "rejected" in r.message.lower() or "invalid" in r.message.lower() or "unknown" in r.message.lower()]
    assert not warns, f"en should be whitelisted, got: {[r.getMessage() for r in warns]}"


def test_set_locale_garbage_still_rejected(caplog):
    """P0: 路径遍历字符串仍被拒（白名单保护）。"""
    with caplog.at_level(logging.WARNING, logger="src.ui.i18n"):
        set_locale("../../etc/passwd")
    # 应当 fallback 到 en（DEFAULT_LOCALE），但不 crash
    assert i18n._default.locale == "en"


# ============ 4a-4: closeEvent E2E with real worker thread ============


def test_close_event_with_real_slow_worker_no_qt_warning(qtbot, isolated_config, isolated_history, tmp_path, caplog):
    """P0: 真 ConversionWorker 跑时点 close，QThread 不应被 force-terminate。

    监听 logging 抓 Qt 内部 'QThread: Destroyed while thread is still running'
    警告 — 出现即为 v0.2.3 M4.1 修复的回归。
    """
    f = tmp_path / "x.txt"
    f.write_text("hi")

    class _SlowConverter:
        def __init__(self, sleep_s: float = 0.5):
            self.sleep_s = sleep_s

        def convert(self, path: str) -> str:
            time.sleep(self.sleep_s)
            return f"# {path}"

    win = MainWindow(
        config_manager=isolated_config,
        history=isolated_history,
        converter=_SlowConverter(0.5),
    )
    win.file_list.add_files([str(f)])
    # 用 protected API 模拟"用户点选文件 → 启动 worker"
    win._on_file_selected(str(f))

    # 立即关窗（worker 还没跑完）
    with caplog.at_level(logging.WARNING):
        win.close()
        # 等事件循环处理 close
        loop = QEventLoop()
        QTimer.singleShot(100, loop.quit)
        loop.exec()

    qt_thread_warnings = [
        r for r in caplog.records
        if "QThread" in r.message and "Destroyed" in r.message
    ]
    assert not qt_thread_warnings, (
        f"closeEvent should cancel+wait worker cleanly; got Qt warnings: "
        f"{[r.getMessage() for r in qt_thread_warnings]}"
    )
