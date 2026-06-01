"""MainWindow 主窗口组装（Task 1.7 + v0.1.1 异步升级）。

按 03 §Task 1.7 + v0.1.1 changelog：
- 顶层 QMainWindow
- 中心区：左 DropArea + 中 FileList + 右 PreviewPanel（QSplitter 三栏）
- 信号连接：DropArea.files_dropped → FileList.add_files → 异步转换 → PreviewPanel.set_markdown
- 状态栏显示"已添加 N 个文件"
- 窗口标题含 "Lei_MD"

v0.1.1 升级（异步转换 + 进度 + 取消）：
- 注入 converter（默认 MarkItDownConverter，测试可换 Stub）
- 选文件 → 启 ConversionWorker（QThread），不阻塞 UI
- status bar 加 QProgressBar（0~100，转换中可见，结束隐藏）
- status bar 加"取消"按钮（转换中可见，按下 worker.cancel()）
- finished_with_md / error → preview 更新 + progress/cancel 隐藏
- 选新文件前自动 cancel 上一个 worker
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QWidget,
    QVBoxLayout,
)

from src.core.batch_worker import BatchWorker
from src.core.config import ConfigManager
from src.core.converter import MarkItDownConverter
from src.core.history import HistoryManager
from src.core.worker import ConversionWorker
from src.ui.drop_area import DropArea
from src.ui.file_list import FileList
from src.ui.i18n import set_locale
from src.ui.preview_panel import PreviewPanel
from src.ui.styles import apply_theme


class MainWindow(QMainWindow):
    """Lei_MD 主窗口。"""

    def __init__(
        self,
        parent=None,
        *,
        converter: object | None = None,
        history: HistoryManager | None = None,
        config_manager: ConfigManager | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Lei_MD — MarkItDown GUI")
        self.resize(1100, 720)

        # 注入 converter（默认真实 markitdown）
        self._converter = converter if converter is not None else MarkItDownConverter()
        # 注入 history（v0.2.0，默认 None 兼容 v0.1.x）
        self._history = history
        # 注入 config（v0.2.0 Sprint 3，默认 None 时新建内存默认）
        self._config = config_manager if config_manager is not None else ConfigManager()

        # 应用主题（v0.2.0 Sprint 3 Task 2.5）
        try:
            apply_theme(self._config.get().theme)
        except Exception:  # noqa: BLE001
            apply_theme("system")

        # 应用 i18n（v0.2.0 Sprint 3 Task 2.6）
        try:
            set_locale(self._config.get().language)
        except Exception:  # noqa: BLE001
            set_locale("en")

        # 菜单栏（v0.2.0 Sprint 3）
        self._build_menus()

        # 三个子组件
        self.drop_area = DropArea()
        self.file_list = FileList()
        self.preview_panel = PreviewPanel()

        # 布局：QSplitter 三栏（可拖拽调比例）
        splitter = QSplitter(Qt.Orientation.Horizontal)
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

        # 状态栏 + 进度条 + 取消按钮
        self.status: QStatusBar = self.statusBar()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(180)
        self.status.addPermanentWidget(self.progress_bar)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setVisible(False)
        self.cancel_button.setFixedHeight(self.progress_bar.sizeHint().height())
        self.status.addPermanentWidget(self.cancel_button)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)

        self.status.showMessage("拖入文件开始转换")

        # 信号连接
        self.drop_area.files_dropped.connect(self._on_files_dropped)
        self.file_list.file_selected.connect(self._on_file_selected)

        # 当前活跃 worker
        self._active_worker: ConversionWorker | None = None

    # -------- slots --------

    def _on_files_dropped(self, paths: list[str]) -> None:
        self.file_list.add_files(paths)
        n = self.file_list.count()
        self.status.showMessage(f"已添加 {n} 个文件")

    def _on_file_selected(self, path: str) -> None:
        # 取消上一个 worker（如果有）
        if self._active_worker is not None and self._active_worker.isRunning():
            self._active_worker.cancel()
            # 不等结束，新 worker start() 会让它自然退出

        # 启动新 worker
        self.preview_panel.clear()  # 清旧内容
        self.status.showMessage(f"转换中：{path}")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.cancel_button.setVisible(True)

        worker = ConversionWorker(self._converter, path)
        worker.progress.connect(self._on_worker_progress)
        worker.finished_with_md.connect(self._on_worker_finished)
        worker.error.connect(self._on_worker_error)
        # v0.2.0：job_done 携带元信息 → history.request_add
        if self._history is not None:
            worker.job_done.connect(self._on_job_done)
        # 线程结束自动清引用
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self._active_worker = worker
        worker.start()

    def _on_worker_progress(self, pct: int) -> None:
        self.progress_bar.setValue(pct)

    def _on_worker_finished(self, markdown: str) -> None:
        self.preview_panel.set_markdown(markdown)
        self.status.showMessage("转换完成")
        # progress/cancel 隐藏延后到 worker.finished（线程级信号）
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)

    def _on_worker_error(self, err: object) -> None:
        # err 是 ConversionError
        self.preview_panel.set_markdown(f"> ⚠️ {err}")
        self.status.showMessage("转换失败")
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)

    def _on_job_done(
        self,
        source_path: str,
        source_format: str,
        md_len: int,
        duration_ms: int,
        success: bool,
        error_msg: str,
    ) -> None:
        """v0.2.0：Worker 完成时携带元信息，转发给 HistoryManager。"""
        if self._history is None:
            return
        self._history.request_add(
            source_path=source_path,
            fmt=source_format,
            md_len=md_len,
            duration_ms=duration_ms,
            success=success,
            error=error_msg,
        )

    def _on_cancel_clicked(self) -> None:
        if self._active_worker is not None:
            self._active_worker.cancel()
            self.status.showMessage("已取消")
            self.progress_bar.setVisible(False)
            self.cancel_button.setVisible(False)

    def _cleanup_worker(self, worker: ConversionWorker) -> None:
        if self._active_worker is worker:
            self._active_worker = None

    # -------- 菜单栏（v0.2.0 Sprint 3 集成）--------

    def _build_menus(self) -> None:
        """构建菜单栏：文件 / 视图 / 帮助。"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        act_settings = file_menu.addAction("设置(&S)...")
        act_settings.triggered.connect(self._open_settings_dialog)
        file_menu.addSeparator()
        act_exit = file_menu.addAction("退出(&X)")
        act_exit.triggered.connect(self.close)

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")
        self._act_history = view_menu.addAction("历史记录(&H)...")
        self._act_history.triggered.connect(self._open_history_panel)

        # 工具栏：批量转换按钮
        toolbar = self.addToolBar("主工具栏")
        toolbar.setObjectName("MainToolbar")
        self._act_batch = toolbar.addAction("全部转换")
        self._act_batch.triggered.connect(self._start_batch)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        act_about = help_menu.addAction("关于 Lei_MD(&A)...")
        act_about.triggered.connect(self._show_about)

    def _open_settings_dialog(self) -> None:
        """打开设置对话框，关闭后持久化并应用主题。"""
        from src.ui.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self._config, parent=self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            try:
                apply_theme(self._config.get().theme)
            except Exception:  # noqa: BLE001
                pass

    def _open_history_panel(self) -> None:
        """打开历史记录对话框（模态只读视图）。"""
        from src.ui.history_panel import HistoryPanel

        if self._history is None:
            self.status.showMessage("历史功能未启用")
            return
        dlg = HistoryPanel(self._history, parent=self)
        dlg.setWindowTitle("历史记录")
        dlg.resize(800, 500)
        dlg.show()  # 非模态，可与主窗口并存

    def _show_about(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "关于 Lei_MD",
            "Lei_MD v0.2.0\n\n基于 MarkItDown 的桌面 GUI 工具\n\n仓库: github.com/raymondyan-zhijie/Lei_MD",
        )

    # -------- 批量转换（v0.2.0 Sprint 3 集成）--------

    def _start_batch(self) -> None:
        """用 ConfigManager.batch_concurrency 启动 BatchWorker。"""
        paths = self.file_list.all_paths()
        if not paths:
            self.status.showMessage("文件列表为空")
            return
        concurrency = max(1, int(self._config.get().batch_concurrency))
        bw = BatchWorker(self._converter, paths, concurrency=concurrency)
        bw.progress.connect(self._on_batch_progress)
        bw.finished.connect(self._on_batch_finished)
        bw.item_failed.connect(self._on_batch_item_failed)
        self._active_batch = bw
        bw.start()
        self.status.showMessage(f"批量转换 0/{len(paths)}")
        self.progress_bar.setVisible(True)
        self.cancel_button.setVisible(True)

    def _on_batch_progress(self, done: int, total: int) -> None:
        self.status.showMessage(f"批量转换 {done}/{total}")
        pct = int(done * 100 / max(total, 1))
        self.progress_bar.setValue(pct)

    def _on_batch_finished(self) -> None:
        self.status.showMessage("批量转换完成")
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
        self._active_batch = None

    def _on_batch_item_failed(self, path: str, err: str) -> None:
        # 当前简单记到状态栏；v0.3 计划加入错误汇总面板
        self.status.showMessage(f"失败：{Path(path).name} - {err}")
