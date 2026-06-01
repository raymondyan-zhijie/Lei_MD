"""MainWindow 主窗口组装（Task 1.7）。

按 03 §Task 1.7：
- 顶层 QMainWindow
- 中心区：左 DropArea + 中 FileList + 右 PreviewPanel（QSplitter 三栏）
- 信号连接：DropArea.files_dropped → FileList.add_files → 异步转换 → PreviewPanel.set_markdown
- 状态栏显示"已添加 N 个文件"
- 窗口标题含 "Lei_MD"

MVP 范围：
- 同步转换（v0.1.0 简化版，Task 1.4 Worker 留给 v0.1.1 集成）
- 转换走 ConversionWorker（异步），本次组装并连信号
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QStatusBar,
    QWidget,
    QVBoxLayout,
)

from src.core.worker import ConversionWorker
from src.ui.drop_area import DropArea
from src.ui.file_list import FileList
from src.ui.preview_panel import PreviewPanel


class MainWindow(QMainWindow):
    """Lei_MD 主窗口。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lei_MD — MarkItDown GUI")
        self.resize(1100, 720)

        # 三个子组件
        self.drop_area = DropArea()
        self.file_list = FileList()
        self.preview_panel = PreviewPanel()

        # 布局：QSplitter 三栏（可拖拽调比例）
        splitter = QSplitter(Qt.Orientation.Horizontal)
        # DropArea 单独一个垂直容器（带标题空白）
        left_wrap = QWidget()
        left_layout = QVBoxLayout(left_wrap)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.drop_area)
        splitter.addWidget(left_wrap)
        splitter.addWidget(self.file_list)
        splitter.addWidget(self.preview_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 2)
        splitter.setSizes([280, 320, 500])

        self.setCentralWidget(splitter)

        # 状态栏
        self.status: QStatusBar = self.statusBar()
        self.status.showMessage("拖入文件开始转换")

        # 信号连接
        self.drop_area.files_dropped.connect(self._on_files_dropped)
        self.file_list.file_selected.connect(self._on_file_selected)

        # 当前活跃的 worker（保留引用，避免 GC 导致线程被销毁）
        self._active_worker: ConversionWorker | None = None

    # -------- slots --------

    def _on_files_dropped(self, paths: list[str]) -> None:
        self.file_list.add_files(paths)
        n = self.file_list.count()
        self.status.showMessage(f"已添加 {n} 个文件")

    def _on_file_selected(self, path: str) -> None:
        # 启动 Worker 异步转换
        # v0.1.0: 用同步 Converter 简化，Worker 留 v0.1.1
        from src.core.converter import MarkItDownConverter

        converter = MarkItDownConverter()
        # 简化：先同步跑，看到内容后切异步
        try:
            md = converter.convert(path)
            self.preview_panel.set_markdown(md)
            self.status.showMessage(f"已转换：{path}")
        except Exception as e:
            self.preview_panel.set_markdown(f"> ⚠️ {e}")
            self.status.showMessage(f"转换失败：{path}")
