"""v0.4.3 P0.5：批量成功条目落地到 history + _batch_results 缓存。

R1.5 — 测试 ``MainWindow._on_batch_item_finished`` slot。
- 不依赖 BatchWorker（避免真实 MarkItDown / QThreadPool 跨线程）
- 直接 emit signal 模拟 _start_batch 后 BatchWorker 触发的 item_finished
- 用 tmp ``XDG_DATA_HOME`` 隔离 history DB
"""
from __future__ import annotations

import pytest


class _StubConverter:
    """占位 MainWindow 的 converter（slot 实际不调它，但 MainWindow.__init__
    会用其真实 MarkItDownConverter 默认值——这里显式注入一个轻量 stub。"""

    def convert(self, path: str) -> str:  # pragma: no cover - 不会走到
        return f"# stub for {path}\n"


@pytest.fixture
def main_window_with_history(qtbot, tmp_path, monkeypatch):
    """注入 StubConverter + tmp DB 的 HistoryManager。"""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from src.core.history import HistoryManager
    from src.ui.main_window import MainWindow

    hm = HistoryManager(max_entries=20)
    w = MainWindow(converter=_StubConverter(), history=hm)
    qtbot.addWidget(w)
    yield w, hm
    hm.close()


def test_batch_item_finished_writes_history(main_window_with_history, tmp_path):
    """emit item_finished(path, md) → history 出现一行 success=True。"""
    w, hm = main_window_with_history
    p = tmp_path / "report.pdf"
    p.write_text("dummy")

    md = "# Hello\n\nSome converted content.\n"
    # 直接 emit，绕过 BatchWorker
    w._on_batch_item_finished(str(p), md)

    rows = hm.list(limit=10)
    matched = [r for r in rows if r.source_path == str(p)]
    assert len(matched) == 1, f"Expected 1 history row for {p}, got {len(matched)}"
    row = matched[0]
    assert row.success == 1  # SQLite 存 INTEGER (0/1)，不是 bool
    assert row.markdown_length == len(md)
    assert row.source_format == "pdf"
    # _batch_results 缓存也填充
    assert w._batch_results[str(p)] == md


def test_batch_finished_clears_results_map(main_window_with_history, tmp_path):
    """_on_batch_finished 把 _batch_results 清空，防止下一轮污染。"""
    w, _hm = main_window_with_history
    p1 = tmp_path / "a.md"
    p1.write_text("a")
    p2 = tmp_path / "b.md"
    p2.write_text("b")

    w._on_batch_item_finished(str(p1), "# a")
    w._on_batch_item_finished(str(p2), "# b")
    assert len(w._batch_results) == 2

    # 模拟 batch 结束。用 QObject 子类占位（_on_batch_finished 会调
    # bw.deleteLater()，需要 QObject 基类）。_active_batch is bw 检查要求
    # 是同一个对象引用。
    from PySide6.QtCore import QObject

    class _FakeBW(QObject):
        pass

    fake_bw = _FakeBW()
    w._active_batch = fake_bw
    w._on_batch_finished(fake_bw)
    assert w._batch_results == {}
