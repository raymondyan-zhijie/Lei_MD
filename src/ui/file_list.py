"""FileList 已添加文件列表（v0.4.1 P0 S1：依赖从 src.ui.drop_area 改到 src.core.supported）。
- QListWidget 包装
- add_files(paths)：过滤不支持扩展名（core.supported.SUPPORTED_EXTENSIONS）+ 去重
- clear() / count() / selected_paths()
- item 双击 / 选中触发 file_selected(str) signal
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from src.core.supported import SUPPORTED_EXTENSIONS  # v0.4.1 P0 S1


class FileList(QListWidget):
    """已添加文件列表。"""

    # 选中行变化时发（path 或 None）
    file_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        # 内部状态：path -> row
        self._paths: set[str] = set()
        self.currentItemChanged.connect(self._on_current_changed)

    def add_files(self, paths) -> None:
        """批量加文件。

        过滤规则：
        - 路径不在 SUPPORTED_EXTENSIONS 的跳过
        - 已存在的跳过（按 abs path）
        """
        added = 0
        for raw in paths:
            p = Path(raw)
            # 不存在或不是文件 → 跳过
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            abs_path = str(p.resolve())
            if abs_path in self._paths:
                continue
            self._paths.add(abs_path)
            item = QListWidgetItem(p.name)
            item.setData(Qt.ItemDataRole.UserRole, abs_path)
            item.setToolTip(abs_path)
            self.addItem(item)
            added += 1
        return None  # 显式返回 None

    def clear(self) -> None:
        """清空列表。"""
        self._paths.clear()
        super().clear()

    def all_paths(self) -> list[str]:
        """返回所有加入过的 abs path 列表（去重保序）。"""
        out: list[str] = []
        seen: set[str] = set()
        for i in range(self.count()):
            item = self.item(i)
            p = item.data(Qt.ItemDataRole.UserRole)
            if p and p not in seen:
                seen.add(p)
                out.append(p)
        return out

    def selected_paths(self) -> list[str]:
        """当前选中行对应的 abs path 列表。"""
        out: list[str] = []
        for item in self.selectedItems():
            p = item.data(Qt.ItemDataRole.UserRole)
            if p:
                out.append(p)
        return out

    def select_path(self, path: str) -> bool:
        """按 abs path 选中一行（精确匹配）。

        Returns True if a matching row was found and set as the current
        item (which then triggers the file_selected signal). False if the
        path is not in the list.
        """
        for i in range(self.count()):
            item = self.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == path:
                self.setCurrentItem(item)
                return True
        return False

    def _on_current_changed(self, current, _previous) -> None:
        if current is None:
            return
        path = current.data(Qt.ItemDataRole.UserRole)
        if path:
            self.file_selected.emit(path)
