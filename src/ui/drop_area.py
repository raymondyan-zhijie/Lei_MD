"""拖拽区域组件（Task 1.2）。

职责：
- 提供"拖入文件到这里"的视觉提示
- 接受系统文件拖拽
- 过滤支持的扩展名（v1.0 不支持音频，详见 01 F9a）
- 目录拖入时递归展开所有支持文件
- emit `files_dropped(list[str])` Signal 通知 MainWindow

设计：
- 继承 QLabel（最轻量，自带富文本 + 拖拽事件）
- setAcceptDrops(True) + 重写 dragEnterEvent / dropEvent
- 支持的扩展名以**类常量**暴露，便于 Task 4.x 测试断言
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QLabel


# v1.0 支持的扩展名（与 01 §3.1 F2 + 02 §1.1 + 03 §Task 1.3 SUPPORTED 一致）
# v1.0 不支持音频：.wav / .mp3 / .ogg / .flac（详见 01 F9a，v1.1+ 离线实现）
SUPPORTED_EXTENSIONS: set[str] = {
    # 文档
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".ppt", ".doc",
    ".epub", ".rtf", ".odt", ".ods", ".odp",
    # 网页
    ".html", ".htm", ".xml",
    # 图片
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    # 数据
    ".csv", ".json", ".tsv", ".xlsx",
    # 压缩
    ".zip",
    # 文本
    ".txt", ".md", ".rst", ".log",
}


class DropArea(QLabel):
    """拖拽区域。"""

    # 拖入有效文件后 emit（参数：绝对路径列表，已过滤 + 目录已递归）
    files_dropped = Signal(list)

    DEFAULT_PLACEHOLDER = (
        "拖拽文件到此处开始转换\n\n"
        "支持 PDF · Word · Excel · PPT · HTML · EPUB · 图片 · ZIP 等\n"
        "（音频 MP3/WAV 暂不支持 — 详见 v1.1+ 路线图）"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        self.setText(self.DEFAULT_PLACEHOLDER)
        # 视觉风格（dashed border + 半透明背景），由 QSS 注入
        self.setObjectName("DropArea")
        self.setProperty("cssClass", "drop-area")

    # -------- 公开 API --------

    def placeholder_text(self) -> str:
        """返回占位提示文本（测试可见）。"""
        return self.text()

    @staticmethod
    def supported_extensions() -> set[str]:
        """返回支持的扩展名集合（测试可见）。"""
        return SUPPORTED_EXTENSIONS

    # -------- Qt 事件 --------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """拖入时若含文件 URL 则接受。"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragEnterEvent) -> None:
        """拖动过程中持续接受（让 drop 事件能触发）。"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """放下时：收集所有支持文件路径，递归展开目录。"""
        if not event.mimeData().hasUrls():
            event.ignore()
            return

        paths: list[str] = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if not local:
                continue
            p = Path(local)
            if p.is_dir():
                # 递归展开目录中所有支持文件
                for child in p.rglob("*"):
                    if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS:
                        paths.append(str(child.resolve()))
            elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                paths.append(str(p.resolve()))
            # 其他情况（不存在的路径/不支持的格式）静默忽略

        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            # 拖入了但全部不被支持 → 拒绝
            event.ignore()
