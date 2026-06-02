"""历史记录面板测试（Task 2.3）。

按 03 §Task 2.3 + HistoryManager API：
- HistoryPanel(QWidget) 构造时注入 HistoryManager + Converter
- 表格列：文件名 / 格式 / 长度 / 耗时 / 成功/失败 / 时间
- refresh() 重新从 HistoryManager.list() 拉数据
- 搜索框（QLineEdit）按 source_path 实时过滤
- 双击行 → file_selected(path) signal（不直接重转，让 MainWindow 处理）
"""
from __future__ import annotations

import pytest


@pytest.fixture
def isolated_data_home(monkeypatch, tmp_path):
    """XDG_DATA_HOME → tmp。"""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.delenv("APPDATA", raising=False)
    return tmp_path


@pytest.fixture
def history_with_entries(isolated_data_home, qtbot):
    """HistoryManager 预填 3 条样本。"""
    from src.core.history import HistoryManager
    hm = HistoryManager(max_entries=20)
    hm.request_add(source_path="/tmp/a.pdf", fmt=".pdf", md_len=100, duration_ms=50, success=True)
    hm.request_add(source_path="/tmp/b.docx", fmt=".docx", md_len=200, duration_ms=80, success=True)
    hm.request_add(source_path="/tmp/c.pdf", fmt=".pdf", md_len=0, duration_ms=20, success=False, error="E_CONVERT_002")
    qtbot.waitUntil(lambda: len(hm.list(limit=20)) >= 3, timeout=3000)
    yield hm
    hm.close()


# ----------- 构造载入 -----------

def test_history_panel_loads_entries(qtbot, history_with_entries):
    """构造时表格含 3 行。"""
    from src.ui.history_panel import HistoryPanel
    panel = HistoryPanel(history_with_entries)
    qtbot.addWidget(panel)
    assert panel.row_count() == 3


# ----------- refresh -----------

def test_history_panel_refresh_picks_up_new_entries(qtbot, history_with_entries):
    """新增 1 条 → refresh() → 4 行。"""
    from src.ui.history_panel import HistoryPanel
    panel = HistoryPanel(history_with_entries)
    qtbot.addWidget(panel)
    assert panel.row_count() == 3

    history_with_entries.request_add(
        source_path="/tmp/d.html", fmt=".html", md_len=50, duration_ms=10, success=True,
    )
    # refresh 由用户操作触发，不自动
    panel.refresh()
    assert panel.row_count() == 4


# ----------- 搜索过滤 -----------

def test_history_panel_search_filters_by_path(qtbot, history_with_entries):
    """搜索 'pdf' → 2 行（a.pdf + c.pdf）。"""
    from src.ui.history_panel import HistoryPanel
    panel = HistoryPanel(history_with_entries)
    qtbot.addWidget(panel)
    assert panel.row_count() == 3

    panel.search_edit.setText("pdf")
    assert panel.row_count() == 2

    panel.search_edit.setText("docx")
    assert panel.row_count() == 1

    panel.search_edit.setText("")  # 清空 → 全显
    assert panel.row_count() == 3


# ----------- 双击选行 -----------

def test_history_panel_double_click_emits_signal(qtbot, history_with_entries):
    """双击第一行 → file_selected(path) signal 触发。"""
    from src.ui.history_panel import HistoryPanel
    panel = HistoryPanel(history_with_entries)
    qtbot.addWidget(panel)
    captured = []
    panel.file_selected.connect(lambda p: captured.append(p))

    # 选第 0 行 + 触发 activated signal
    panel.table_widget.selectRow(0)
    # 用 itemDoubleClicked 信号模拟双击
    idx = panel.table_widget.model().index(0, 0)
    panel.table_widget.doubleClicked.emit(idx)
    qtbot.waitUntil(lambda: bool(captured), timeout=1000)
    assert captured[0] in ("/tmp/a.pdf", "/tmp/b.docx", "/tmp/c.pdf")


# ----------- 失败显示 -----------

def test_history_panel_marks_failed_entries(qtbot, history_with_entries):
    """失败条目（success=False）有视觉标记。"""
    from src.ui.history_panel import HistoryPanel
    panel = HistoryPanel(history_with_entries)
    qtbot.addWidget(panel)
    # 找 success 列 = False 的行（这里有 c.pdf 是失败）
    found_failed = False
    for row in range(panel.row_count()):
        # status 列在第 4 列
        item = panel.table_widget.item(row, 4)
        if item and "失败" in item.text():
            found_failed = True
            break
    assert found_failed, "应有失败标记的行"
