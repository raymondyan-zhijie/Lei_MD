"""Tests filling remaining audit coverage gaps (P3 stage 2.2)."""
from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QCoreApplication, QEventLoop, QThread, QTimer
from PySide6.QtWidgets import QApplication

from src.core.batch_worker import BatchWorker
from src.core.history import HistoryManager
from src.ui import i18n
from src.ui.i18n import Translator, set_locale, tr


# ============ BatchWorker 并发压测 ============


def test_batch_worker_concurrent_increments_no_lost_updates(qtbot):
    """P3 gap: BatchWorker._done_count increment is mutex-protected under load."""
    counter_lock = threading.Lock()
    counter = {"calls": 0}

    def _convert(p):
        with counter_lock:
            counter["calls"] += 1
        time.sleep(0.01)  # 模拟真实 IO
        return f"# {p}"

    paths = [f"/tmp/file_{i}.txt" for i in range(20)]
    bw = BatchWorker(_convert, paths, concurrency=4)
    progress_seen = []
    bw.progress.connect(lambda d, t: progress_seen.append((d, t)))
    finished_seen = []
    bw.finished.connect(lambda: finished_seen.append(1))
    bw.start()

    qtbot.waitUntil(lambda: len(finished_seen) >= 1, timeout=10000)
    # 让事件循环跑一拍
    loop = QEventLoop()
    QTimer.singleShot(100, loop.quit)
    loop.exec()

    final_done = progress_seen[-1][0] if progress_seen else 0
    assert final_done == 20, f"expected final done=20, got {final_done}; lost updates in lock?"

    # done 序列应包含 1..20 每个值（无丢更新）。start 还会先发 0/total。
    dones = set(d for d, t in progress_seen)
    expected = set(range(1, 21))  # 1..20
    missing = expected - dones
    assert not missing, f"missing done values: {sorted(missing)}; lost updates in lock?"
    assert counter["calls"] == 20, f"converter called {counter['calls']} times, expected 20"


# ============ set_locale 翻译实际生效 ============


def test_set_locale_zh_cn_translations_actually_apply():
    """P3 gap: set_locale('zh_CN') actually loads zh_CN.json and tr() returns Chinese."""
    set_locale("zh_CN")
    # 关键 UI 翻译应该中文
    assert tr("menu.file") == "文件"
    assert tr("settings.title") == "设置"
    assert tr("history.title") == "历史记录"
    # 未知 key fallback
    assert tr("nonexistent.key") == "nonexistent.key"
    # 复位
    set_locale("en")


def test_set_locale_en_falls_back_to_keys():
    """P3 gap: set_locale('en') returns keys (no en.json bundled, fallback to key)."""
    set_locale("en")
    assert tr("menu.file") == "menu.file"
    assert tr("settings.title") == "settings.title"
