"""Integration tests for BatchWorker wired into MainWindow."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.core.batch_worker import BatchWorker
from src.core.config import ConfigManager
from src.core.history import HistoryManager
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


def test_mainwindow_has_batch_action(isolated_config, isolated_history, qtbot):
    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    assert hasattr(win, "_act_batch")
    assert win._act_batch.text() != ""


def test_start_batch_uses_config_concurrency(isolated_config, isolated_history, qtbot, monkeypatch, tmp_path):
    """start_batch creates BatchWorker with config.batch_concurrency."""
    isolated_config.update(batch_concurrency=7)
    win = MainWindow(config_manager=isolated_config, history=isolated_history)

    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("hi")
    b.write_text("bye")

    captured = []

    class _FakeBW:
        def __init__(self, converter, paths, concurrency):
            captured.append(concurrency)
            self.progress = MagicMock()
            self.finished = MagicMock()
            self.item_finished = MagicMock()
            self.item_failed = MagicMock()
        def start(self): pass
        def cancel(self): pass

    monkeypatch.setattr("src.ui.main_window.BatchWorker", _FakeBW)
    win.file_list.add_files([str(a), str(b)])
    win._start_batch()
    assert captured == [7]


def test_start_batch_emits_progress_to_status(isolated_config, isolated_history, qtbot, monkeypatch):
    """BatchWorker.progress signal updates status bar."""
    win = MainWindow(config_manager=isolated_config, history=isolated_history)

    bw = BatchWorker(MagicMock(), ["/tmp/a.txt"], concurrency=1)
    win._active_batch = bw
    # 直接触发 progress signal
    win._on_batch_progress(1, 1)
    assert "1" in win.status.currentMessage()
