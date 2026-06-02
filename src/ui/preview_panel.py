"""PreviewPanel Markdown 预览（）。
- 用 QTextBrowser（零依赖、轻量、纯文本 OK）
- 不引入 QWebEngine（400MB+ 体积增量大）
- API: set_markdown(str) / clear() / is_empty() / toPlainText() / toHtml()
- set_markdown 用 setMarkdown() (PySide6 6.4+)
- 非法字符（NUL 等）通过清洗兜底

设计：
- 单组件，可嵌入 MainWindow 的右侧预览区
- is_empty() 由内部 _last_md 状态决定（set_markdown / clear 改它）
"""
from __future__ import annotations

import logging

from PySide6.QtWidgets import QTextBrowser

_log = logging.getLogger(__name__)

class PreviewPanel(QTextBrowser):
    """Markdown 预览面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_md: str = ""
        # P3 ) 关闭外链跳转：之前 setOpenExternalLinks(True) 会
        # 让 <a href="file:///..."> 真的打开本地文件，存在被恶意 md 触达任意文件的
        # 风险。改为 setOpenLinks(False)：用户仍可复制链接，但点击不触发导航。
        self.setOpenExternalLinks(False)
        self.setOpenLinks(False)
        # 重写 setSource 拒绝 file:// —— 任何绕过 Qt link 机制的导航（键盘 /
        # QDesktopServices）也会被这里兜住。
        self.setSource = self._safe_set_source  # type: ignore[method-assign]
        # 禁止编辑（只读）
        self.setReadOnly(True)

    def _safe_set_source(self, name) -> None:
        """ P3 audit 拒绝 file:// / 任意本地路径导航。

        走 setSource 的来源：
        - QTextBrowser 点击 <a href="..."> 时（被 setOpenLinks(False) 拦住）
        - 直接 setSource(...) 调用
        - loadResource(QTextDocument.ImageResource, ...) 不走 setSource

        仅放过 http(s) / 空 / 非本地 scheme。
        """
        try:
            from PySide6.QtCore import QUrl  # local import to avoid module-level dep
            if isinstance(name, QUrl):
                url = name
            else:
                url = QUrl(str(name))
            scheme = url.scheme().lower()
            if scheme in ("file", ""):
                _log.warning(
                    "PreviewPanel blocked link to %s (scheme=%r)", url.toString(), scheme,
                )
                return
            # 其余（http/https/mailto/...）让基类正常处理
            super().setSource(url)
        except Exception:  # noqa: BLE001
            _log.warning("PreviewPanel._safe_set_source failed", exc_info=True)

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
            _log.warning(
                "PreviewPanel.setMarkdown failed; falling back to setPlainText",
                exc_info=True,
            )
            self.setPlainText(cleaned)

    def clear(self) -> None:
        """清空预览。"""
        self._last_md = ""
        super().clear()

    def is_empty(self) -> bool:
        """是否为空。"""
        return not self._last_md
