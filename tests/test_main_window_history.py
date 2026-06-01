"""MainWindow 接入 HistoryManager 测试（Task 1.9 集成）。"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


class _StubConverter:
    def __init__(self, *, sleep=0.02, fail=False):
        self.sleep = sleep
        self.fail = fail
        self.calls = []

    def convert(self, path: str) -> str:
        self.calls.append(path)
        import time
        if self.sleep:
            time.sleep(self.sleep)
        if self.fail:
            from src.core.errors import ConversionError, ErrorCode
            raise ConversionError(ErrorCode.E_CONVERT_002, filename=Path(path).name)
        return f"# {Path(path).name}\n\nok"


@pytest.fixture
def main_window_with_history(qtbot, tmp_path, monkeypatch):
    """MainWindow 注入 StubConverter + HistoryManager（tmp 路径）。"""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from src.ui.main_window import MainWindow
    from src.core.history import HistoryManager
    hm = HistoryManager(max_entries=10)
    stub = _StubConverter(sleep=0.02)
    w = MainWindow(converter=stub, history=hm)
    qtbot.addWidget(w)
    yield w, hm, stub
    hm.close()


@pytest.fixture
def main_window_with_history_fail(qtbot, tmp_path, monkeypatch):
    """MainWindow 注入 fail=True StubConverter + HistoryManager。"""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from src.ui.main_window import MainWindow
    from src.core.history import HistoryManager
    hm = HistoryManager(max_entries=10)
    stub = _StubConverter(sleep=0.02, fail=True)
    w = MainWindow(converter=stub, history=hm)
    qtbot.addWidget(w)
    yield w, hm, stub
    hm.close()


def test_mainwindow_records_history_on_success(main_window_with_history, qtbot, tmp_path):
    """成功转换 → history 有 1 条 success=True。"""
    w, hm, _stub = main_window_with_history
    p = tmp_path / "doc.pdf"
    p.write_text("dummy")
    w._on_file_selected(str(p))
    qtbot.waitUntil(lambda: len(hm.list(limit=10)) >= 1, timeout=3000)
    rows = hm.list(limit=10)
    assert len(rows) == 1
    assert rows[0].source_path == str(p)
    assert rows[0].source_format == ".pdf"
    assert bool(rows[0].success) is True
    assert rows[0].markdown_length > 0
    assert rows[0].duration_ms >= 0


def test_mainwindow_records_history_on_failure(main_window_with_history_fail, qtbot, tmp_path):
    """失败转换 → history 有 1 条 success=False + error_msg。"""
    w, hm, _stub = main_window_with_history_fail
    p = tmp_path / "bad.pdf"
    p.write_text("dummy")
    w._on_file_selected(str(p))
    qtbot.waitUntil(lambda: len(hm.list(limit=10)) >= 1, timeout=3000)
    rows = hm.list(limit=10)
    assert len(rows) == 1
    assert bool(rows[0].success) is False
    assert "E_CONVERT_002" in rows[0].error_msg


def test_mainwindow_no_history_if_not_injected(qtbot, tmp_path):
    """未注入 history → 转换仍能完成（graceful），不抛。"""
    from src.ui.main_window import MainWindow
    stub = _StubConverter()
    w = MainWindow(converter=stub, history=None)
    qtbot.addWidget(w)
    p = tmp_path / "a.pdf"
    p.write_text("dummy")
    w._on_file_selected(str(p))
    qtbot.waitUntil(lambda: not w.preview_panel.is_empty(), timeout=3000)
    assert "a.pdf" in w.preview_panel.toPlainText()
