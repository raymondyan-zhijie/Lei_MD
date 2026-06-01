"""历史记录面板（Task 2.3）。

按 03 §Task 2.3 + HistoryManager API：
- QTableView 展示历史（不可编辑）
- 构造时从 HistoryManager 拉数据
- refresh() 重新拉
- 搜索框（QLineEdit）按 source_path 子串实时过滤
- 双击行 → file_selected(path) signal（不直接重转，让 MainWindow 处理）

列：文件名 / 格式 / 长度 / 耗时 / 状态 / 时间 / 错误
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

_log = logging.getLogger(__name__)


class HistoryPanel(QWidget):
    """历史记录面板。"""

    # 双击某行 → 通知 MainWindow
    file_selected = Signal(str)

    # 列定义（SSOT）
    _COLUMNS = ("文件名", "格式", "长度", "耗时(ms)", "状态", "时间", "错误")

    def __init__(self, history_manager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hm = history_manager
        self._all_entries: list = []  # 全量缓存（用于过滤）

        self._build_widgets()
        self._build_layout()
        self._wire_signals()

        # 初次载入
        self.refresh()

    def _build_widgets(self) -> None:
        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("按文件名搜索…")
        self.search_edit.setClearButtonEnabled(True)

        # 刷新按钮
        from PySide6.QtWidgets import QPushButton
        self.refresh_button = QPushButton("刷新")

        # 表格
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(len(self._COLUMNS))
        self.table_widget.setHorizontalHeaderLabels(self._COLUMNS)
        # 不可编辑
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # 单选
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_widget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        # 表头自适应
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, len(self._COLUMNS)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

    def _build_layout(self) -> None:
        root = QVBoxLayout(self)
        # 搜索行
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("搜索："))
        search_row.addWidget(self.search_edit, 1)
        search_row.addWidget(self.refresh_button)
        root.addLayout(search_row)
        # 表格
        root.addWidget(self.table_widget, 1)

    def _wire_signals(self) -> None:
        self.search_edit.textChanged.connect(self._apply_filter)
        self.refresh_button.clicked.connect(self.refresh)
        # 双击行
        self.table_widget.doubleClicked.connect(self._on_double_clicked)

    # -------- 公开 API --------

    def refresh(self) -> None:
        """从 HistoryManager 重新拉数据。

        v0.2.7 P1 审计（v0.2.6 复审 #4）：DB 锁 / 损坏下 ``self._hm.list()`` 会
        抛 ``sqlite3.OperationalError``（如 "database is locked" / "file is not
        a database"），冒泡到 Qt event loop 会让整个 UI 崩。包 ``try/except
        sqlite3.Error`` —— 记 ``_log.warning`` + 把 ``_all_entries`` 置空，
        用户看到的只是"历史暂时无法加载"而不是整个面板 / 主窗口消失。
        """
        # v0.2.7 P1：sqlite3 import 放在 try 块内，避免污染顶层命名空间
        # （文件已 import logging / Path，sqlite3 是新依赖；放 try 内只
        # 实际用到的错误类路径走 import，正常路径零开销）
        try:
            import sqlite3
            self._all_entries = self._hm.list(limit=100)
        except sqlite3.Error as e:
            _log.warning(
                "HistoryPanel.refresh: HistoryManager.list() raised %s — %s. "
                "Falling back to empty list to keep UI alive.",
                type(e).__name__, e, exc_info=True,
            )
            self._all_entries = []
        self._apply_filter()

    def row_count(self) -> int:
        """当前可见行数（受搜索过滤影响）。"""
        return self.table_widget.rowCount()

    # -------- 内部 --------

    def _apply_filter(self) -> None:
        """按搜索框文本过滤 + 重新填表。"""
        keyword = self.search_edit.text().strip().lower()
        if keyword:
            entries = [e for e in self._all_entries if keyword in e.source_path.lower()]
        else:
            entries = list(self._all_entries)
        self._populate(entries)

    def _populate(self, entries) -> None:
        """把 entries 填进表格。"""
        self.table_widget.setRowCount(len(entries))
        for row, e in enumerate(entries):
            name = Path(e.source_path).name
            status = "✓ 成功" if bool(e.success) else "✗ 失败"
            # 格式化时间
            try:
                dt = datetime.fromisoformat(e.created_at)
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                _log.warning("HistoryPanel._populate: bad created_at=%r, showing raw", e.created_at, exc_info=True)
                time_str = e.created_at
            cells = [
                name,
                e.source_format,
                str(e.markdown_length),
                str(e.duration_ms),
                status,
                time_str,
                e.error_msg or "",
            ]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                # 把 abs path 存在 UserRole（列 0），双击时取
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, e.source_path)
                # 失败行整行标色（轻提示）
                if not bool(e.success):
                    from PySide6.QtGui import QColor
                    item.setBackground(QColor(255, 230, 230))
                self.table_widget.setItem(row, col, item)

    def _on_double_clicked(self, index) -> None:
        """双击行 → file_selected signal。"""
        if not index.isValid():
            return
        item = self.table_widget.item(index.row(), 0)
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.file_selected.emit(path)
