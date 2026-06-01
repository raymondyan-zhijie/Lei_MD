"""PreviewPanel Markdown 预览（Task 1.5）。

按 03 §Task 1.5：
- 用 QTextBrowser（零依赖、轻量、纯文本 OK）
- v1.0 不引入 QWebEngine（400MB+ 体积增量大）
- API: set_markdown(str) / clear() / is_empty() / toPlainText() / toHtml()
- set_markdown 用 setMarkdown() (PySide6 6.4+)
- 非法字符（NUL 等）通过清洗兜底

设计：
- 单组件，可嵌入 MainWindow 的右侧预览区
- is_empty() 由内部 _last_md 状态决定（set_markdown / clear 改它）
"""
from __future__ import annotations

from PySide6.QtWidgets import QTextBrowser


class PreviewPanel(QTextBrowser):
    """Markdown 预览面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_md: str = ""
        self.setOpenExternalLinks(True)
        # 禁止编辑（只读）
        self.setReadOnly(True)

    def set_markdown(self, markdown: str) -> None:
        """设置并渲染 Markdown。

        清洗策略：
        - 过滤 NUL 字节（QTextBrowser 在某些平台会因 NUL 抛错）
        - 保留其他字符
        """
        cleaned = markdown.replace("\x00", "")
        self._last_md = cleaned
        try:
            self.setMarkdown(cleaned)
        except Exception:
            # 极端输入兜底：当 setMarkdown 抛错（PySide6 6.9 已知极少场景），
            # 降级到 setPlainText 让用户至少看到内容
            self.setPlainText(cleaned)

    def clear(self) -> None:
        """清空预览。"""
        self._last_md = ""
        super().clear()

    def is_empty(self) -> bool:
        """是否为空。"""
        return not self._last_md
