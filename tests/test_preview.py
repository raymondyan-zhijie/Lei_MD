"""PreviewPanel Markdown 渲染测试（Task 1.5）。

按 03 §Task 1.5：4 个测试。
- QTextBrowser（轻量、零依赖、纯文本 OK）
- set_markdown(str) / clear() / is_empty()
- 渲染异常时降级显示原文 + 警告条
"""
from __future__ import annotations

import pytest


@pytest.fixture
def app(qtbot):
    """qtbot 自带 QApplication，无需手动建。"""
    return qtbot


def test_preview_starts_empty(qtbot):
    """初始：is_empty() == True，控件存在。"""
    from src.ui.preview_panel import PreviewPanel
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    assert panel.is_empty() is True


def test_preview_set_markdown_displays_content(qtbot):
    """set_markdown 后：is_empty() == False，toPlainText() 包含原文。"""
    from src.ui.preview_panel import PreviewPanel
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    md = "# Hello\n\nWorld"
    panel.set_markdown(md)
    assert panel.is_empty() is False
    # QTextBrowser 自动渲染 markdown 源码到 toPlainText（不一定完全等同输入）
    # 但至少要包含标题文字
    assert "Hello" in panel.toPlainText() or "Hello" in panel.toHtml()
    assert "World" in panel.toPlainText() or "World" in panel.toHtml()


def test_preview_clear_resets(qtbot):
    """clear() 后：is_empty() == True。"""
    from src.ui.preview_panel import PreviewPanel
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    panel.set_markdown("something")
    assert panel.is_empty() is False
    panel.clear()
    assert panel.is_empty() is True


def test_preview_handles_invalid_markdown_gracefully(qtbot):
    """非法输入：set_markdown 仍接受（QTextBrowser 不抛），is_empty() == False。"""
    from src.ui.preview_panel import PreviewPanel
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    # 含 NUL 字节等极端情况也不应崩
    panel.set_markdown("\x00\x01\x02 ???")
    # 不崩即可
    assert panel.is_empty() is False
