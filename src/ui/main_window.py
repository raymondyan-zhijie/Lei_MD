"""MainWindow 主窗口组装（ + 异步升级）。+ changelog：
- 顶层 QMainWindow
- 中心区：左 DropArea + 中 FileList + 右 PreviewPanel（QSplitter 三栏）
- 信号连接：DropArea.files_dropped → FileList.add_files → 异步转换 → PreviewPanel.set_markdown
- 状态栏显示"已添加 N 个文件"
- 窗口标题含 "Lei_MD" 升级（异步转换 + 进度 + 取消）：
- 注入 converter（默认 MarkItDownConverter，测试可换 Stub）
- 选文件 → 启 ConversionWorker（QThread），不阻塞 UI
- status bar 加 QProgressBar（0~100，转换中可见，结束隐藏）
- status bar 加"取消"按钮（转换中可见，按下 worker.cancel()）
- finished_with_md / error → preview 更新 + progress/cancel 隐藏
- 选新文件前自动 cancel 上一个 worker
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.core.batch_worker import BatchWorker
from src.core.config import ConfigManager
from src.core.converter import MarkItDownConverter
from src.core.history import HistoryManager
from src.core.worker import ConversionWorker, YouTubeFetchWorker
from src.ui.drop_area import DropArea
from src.ui.file_list import FileList
from src.ui.i18n import set_locale
from src.ui.i18n import tr as _tr
from src.ui.preview_panel import PreviewPanel
from src.ui.styles import apply_theme

# closeEvent 路径下会等 worker 2000ms，超时要 log.warning。
_log = logging.getLogger(__name__)


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
        # 注入 history（，默认 None 兼容.x）
        self._history = history
        # 注入 config（，默认 None 时新建内存默认）
        self._config = config_manager if config_manager is not None else ConfigManager()

        # 应用主题（）
        try:
            apply_theme(self._config.get().theme)
        except Exception:  # noqa: BLE001
            _log.warning(
                "MainWindow.__init__: apply_theme(%r) failed, fallback to 'system'",
                self._config.get().theme,
                exc_info=True,
            )
            apply_theme("system")

        # 应用 i18n（）
        try:
            set_locale(self._config.get().language)
        except Exception:  # noqa: BLE001
            _log.warning(
                "MainWindow.__init__: set_locale(%r) failed, fallback to 'en'",
                self._config.get().language,
                exc_info=True,
            )
            set_locale("en")

        # 菜单栏（）
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
        # v0.4.2 P1 M4：YouTube URL 输入框 + 抓取按钮（放在 DropArea 上方）
        self.yt_url_edit = QLineEdit()
        self.yt_url_edit.setPlaceholderText(_tr("youtube.url.placeholder"))
        self.yt_url_edit.setClearButtonEnabled(True)
        self.yt_fetch_button = QPushButton(_tr("youtube.fetch"))
        self.yt_fetch_button.clicked.connect(self._on_youtube_fetch)
        yt_row = QHBoxLayout()
        yt_row.addWidget(self.yt_url_edit, 1)
        yt_row.addWidget(self.yt_fetch_button)
        left_layout.addLayout(yt_row)
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
        # v0.4.0 Task C：音频被拒时弹 E_FILE_006 模态
        self.drop_area.audio_rejected.connect(self._on_audio_rejected)
        self.file_list.file_selected.connect(self._on_file_selected)

        # 当前活跃 worker
        self._active_worker: ConversionWorker | None = None
        # ：批量转换时取消按钮要能取消 batch
        self._active_batch: BatchWorker | None = None
        # v0.4.3 P0.5: 累计 batch 中已完成的 (path -> markdown) 映射。
        # BatchWorker 自身只发 item_finished(path, md) signal，finished 时不携带结果，
        # 所以 MainWindow 必须自己累积，否则成功的 markdown 全丢（之前用户必须靠
        # _on_single_finished-like 路径但批量没接入）。
        self._batch_results: dict[str, str] = {}
        # v0.4.2 P1 M4：YouTube 抓取 worker（一次只能跑一个）
        self._active_youtube: YouTubeFetchWorker | None = None

    # -------- slots --------

    def _on_files_dropped(self, paths: list[str]) -> None:
        self.file_list.add_files(paths)
        n = self.file_list.count()
        self.status.showMessage(f"已添加 {n} 个文件")

        # P0.4: 接入 auto_convert 配置。
        # - 关闭：仅加入列表，不启动转换（与配置项行为对齐）。
        # - 单文件：自动转（同时选中该文件 → 触发 _on_file_selected）。
        # - 多文件：仅加入列表（不自动批量）。批量触发由用户点击"批量转换"按钮
        #   或菜单走 _on_batch_clicked()，与"非拖入"路径保持一致。
        auto = bool(self._config.get().auto_convert)
        if not auto or not paths:
            return
        if len(paths) == 1:
            # 单文件自动转：先选中再触发 _on_file_selected。
            self.file_list.select_path(paths[0])
        # 多文件：留待用户主动触发批量任务。

    def _on_audio_rejected(self, audio_paths: list[str]) -> None:
        """v0.4.0 Task C：音频被 E_FILE_006 拦截，弹模态告知用户。"""
        from PySide6.QtWidgets import QMessageBox

        # 只显示前 5 个文件名，避免弹窗过宽
        sample = "\n".join(Path(p).name for p in audio_paths[:5])
        more = f"\n... 还有 {len(audio_paths) - 5} 个" if len(audio_paths) > 5 else ""
        from src.core.errors import ERROR_MESSAGES, ErrorCode

        detail = (
            f"以下音频文件不在 v1.0 支持范围：\n\n{sample}{more}\n\n"
            f"错误码：{ErrorCode.E_FILE_006.value}\n"
            f"说明：{ERROR_MESSAGES[ErrorCode.E_FILE_006]['zh_CN']}"
        )
        QMessageBox.warning(
            self,
            "音频转录暂不支持",
            detail,
            QMessageBox.Ok,
        )
        _log.info("MainWindow rejected %d audio file(s) with E_FILE_006", len(audio_paths))

    def _on_copy_clicked(self) -> None:
        """v0.4.1 P0 M1：把当前预览的 Markdown 复制到系统剪贴板。"""
        from PySide6.QtWidgets import QMessageBox

        if self.preview_panel.is_empty():
            QMessageBox.information(
                self, "复制 Markdown", "预览区为空，请先选中文件完成转换。"
            )
            return
        if self.preview_panel.copy_to_clipboard():
            n = len(self.preview_panel._last_md)  # noqa: SLF001
            self.status.showMessage(f"已复制 {n} 字符到剪贴板", 3000)
        else:
            QMessageBox.warning(
                self, "复制失败", "剪贴板不可用，请重试或检查系统权限。"
            )

    def _on_export_clicked(self) -> None:
        """v0.4.1 P0 M2：把当前预览的 Markdown 导出为 .md 文件。

        v0.4.4+ P0 改造：若 ``output_dir=custom`` 且 ``custom_output_dir``
        存在可写，用它作 QFileDialog 初始目录（而不是 home）。写盘失败用
        ``E_SYS_002`` 错误码提示，而不是临时字符串。
        """
        from src.core.errors import ERROR_MESSAGES, ErrorCode

        if self.preview_panel.is_empty():
            QMessageBox.information(
                self, "导出 .md", "预览区为空，请先选中文件完成转换。"
            )
            return
        # 默认文件名：取当前选中文件的 stem
        selected = self.file_list.selected_paths()
        if selected:
            default_name = Path(selected[0]).stem + ".md"
        else:
            default_name = "output.md"
        # v0.4.4+: 配置的 custom_output_dir 作为 dialog 初始目录
        out_dir = self._resolve_output_dir()
        if out_dir is not None:
            initial = str(out_dir / default_name)
        else:
            initial = default_name
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 Markdown",
            initial,
            "Markdown 文件 (*.md);;所有文件 (*.*)",
        )
        if not path:
            return  # 用户取消
        try:
            Path(path).write_text(
                self.preview_panel._last_md,  # noqa: SLF001
                encoding="utf-8",
            )
        except OSError as e:
            _log.warning("MainWindow._on_export_clicked: write %s failed: %s", path, e)
            # v0.4.4+ P0: 用 E_SYS_002 错误码，不是临时字符串。
            # 用 .get() 兜底以防 ERROR_MESSAGES 没登记（理论不会，
            # 但比 KeyError 安全）。
            msg = ERROR_MESSAGES.get(ErrorCode.E_SYS_002, {}).get(
                "zh_CN", f"输出路径不可写：{path}"
            )
            QMessageBox.warning(
                self,
                "导出失败",
                f"{msg}\n路径：{path}\n{e}",
            )
            return
        self.status.showMessage(f"已导出到 {path}", 5000)

    def _resolve_output_dir(self) -> Path | None:
        """v0.4.4+ P0: 解析 ``output_dir=custom`` 配置成实际可写 Path。

        返回：
          - ``Path``：配置指向的目录存在 + 可写
          - ``None``：output_dir != "custom"，或 custom_output_dir 为空 /
            不存在 / 不可写（已弹 QMessageBox 警告用户）

        调用方在拿到 ``None`` 时退回到"原行为"（弹 dialog / 不自动导出）。
        """
        import os

        from src.core.errors import ERROR_MESSAGES, ErrorCode

        cfg = self._config.get()
        if cfg.output_dir != "custom":
            return None
        if not cfg.custom_output_dir.strip():
            return None
        p = Path(cfg.custom_output_dir).expanduser()
        if not p.exists() or not p.is_dir():
            msg = ERROR_MESSAGES.get(ErrorCode.E_SYS_002, {}).get(
                "zh_CN", f"输出路径不存在：{p}"
            )
            QMessageBox.warning(
                self,
                "输出目录无效",
                f"{msg}\n路径：{p}",
            )
            return None
        if not os.access(p, os.W_OK):
            msg = ERROR_MESSAGES.get(ErrorCode.E_SYS_002, {}).get(
                "zh_CN", f"输出路径不可写：{p}"
            )
            QMessageBox.warning(
                self,
                "输出目录不可写",
                f"{msg}\n路径：{p}",
            )
            return None
        return p

    def _on_youtube_fetch(self) -> None:
        """v0.4.2 P1 M4：用户点"抓取"按钮 → 启动 YouTubeFetchWorker。

        流程：
        1) 校验 URL（白名单格式 / extract_video_id 非空）
        2) 启动 YouTubeFetchWorker（QThread 异步）
        3) 禁用输入框 + 按钮，显示进度条 indeterminate
        4) finished → PreviewPanel.set_markdown
        5) error → 状态栏 + QMessageBox.warning
        6) 任何分支都要 deleteLater 释放 worker
        """
        from PySide6.QtWidgets import QMessageBox

        from src.core.youtube import extract_video_id

        url = self.yt_url_edit.text().strip()
        if not url:
            QMessageBox.information(self, "YouTube 抓取", "请先粘贴一个 YouTube URL")
            return
        if extract_video_id(url) is None:
            QMessageBox.warning(
                self, "YouTube 抓取", f"不是有效的 YouTube URL：\n{url}"
            )
            return
        # 防二次点击
        if self._active_youtube is not None and self._active_youtube.isRunning():
            self.status.showMessage("已有 YouTube 抓取在进行中…", 3000)
            return

        # 禁用 UI + 显示进度
        self.yt_url_edit.setEnabled(False)
        self.yt_fetch_button.setEnabled(False)
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.setVisible(True)
        self.status.showMessage(f"正在抓取字幕：{url}")

        worker = YouTubeFetchWorker(url, timeout=30)
        self._active_youtube = worker
        worker.finished.connect(self._on_youtube_finished)
        worker.error.connect(self._on_youtube_error)
        # finished 或 error 都要 cleanup（避免两条路径都漏 deleteLater）
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        worker.start()

    def _on_youtube_finished(self, markdown: str) -> None:
        """v0.4.2 P1 M4：YouTube 抓取成功 → 写入 PreviewPanel。"""
        self.preview_panel.set_markdown(markdown)
        self.status.showMessage(
            f"YouTube 字幕已抓取（{len(markdown)} 字符）", 5000
        )
        # 恢复 UI
        self._reset_youtube_ui()

    def _on_youtube_error(self, code: str) -> None:
        """v0.4.2 P1 M4：YouTube 抓取失败 → 弹模态。"""
        from PySide6.QtWidgets import QMessageBox

        from src.core.errors import ERROR_MESSAGES, ErrorCode

        try:
            ec = ErrorCode(code)
            msg = ERROR_MESSAGES.get(ec, {}).get("zh_CN", f"抓取失败：{code}")
        except ValueError:
            msg = f"抓取失败：{code}"

        self.status.showMessage(f"YouTube 抓取失败：{code}", 5000)
        QMessageBox.warning(self, "YouTube 抓取失败", f"{msg}\n\n错误码：{code}")
        self._reset_youtube_ui()

    def _reset_youtube_ui(self) -> None:
        """v0.4.2 P1 M4：恢复 YouTube 输入框 + 按钮 + 进度条。"""
        self.yt_url_edit.setEnabled(True)
        self.yt_fetch_button.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        self._active_youtube = None

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
        # job_done 携带元信息 → history.request_add
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
        """ ：Worker 完成时携带元信息，转发给 HistoryManager。"""
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
        # ：先看 batch（最后启动的活动），再看 single worker
        if self._active_batch is not None:
            self._active_batch.cancel()
            self.status.showMessage("已取消批量转换")
        elif self._active_worker is not None:
            self._active_worker.cancel()
            self.status.showMessage("已取消")
        else:
            return  # 没活动，点了也不该有副作用
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)

    def _cleanup_worker(self, worker: ConversionWorker) -> None:
        if self._active_worker is worker:
            self._active_worker = None
        # QThread 必须显式 deleteLater()，
        # 否则 force-terminate 时 Qt 会报
        # "QThread: Destroyed while thread is still running"。
        # deleteLater 会在事件循环下一拍把 QObject 子树释放掉。
        worker.deleteLater()

    # -------- 生命周期（  / ）--------

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt event override)
        """窗口关闭：协作式停掉 batch / worker，避免 QThread 被 force-terminate。

        顺序（按 spec）：
          1) _active_batch?.cancel()   — BatchWorker.cancel() 把状态置 CANCELLED
             并在事件循环下一拍 emit finished。
          2) _active_worker?.cancel()   — QThread.cancel_event.set()，run() 跑
             到检查点会自然 return。
          3) worker.wait(2000)          — 最多 2s 等 QThread 真正退出。
          4) bw.wait_finished(2000)     — 最多 2s 等 BatchWorker 内部 QThreadPool
             排空已派发的 _ConvertRunnable（v0.4.1 P0 S3：改用 public API，
             替代原本直接访问 bw._pool 的私有属性）。
          5) accept event               — 无论 wait 是否超时都 accept，避免用户卡死。
             超时只 log.warning（属于"异常路径"）。

        引用清理：closeEvent 路径下 _active_batch 可能还没被 _on_batch_finished
        清掉（cancel 触发的 finalize 用了 QTimer.singleShot(0, ...)），手动置 None
        避免 dangling pointer。
        """
        # 1) batch 取消（None-safe）
        if self._active_batch is not None:
            try:
                self._active_batch.cancel()
            except RuntimeError:  # bw 已 deleteLater()，被 PyQt 哨兵抛出
                _log.warning(
                    "MainWindow.closeEvent: BatchWorker.cancel() RuntimeError "
                    "(deleteLater)",
                    exc_info=True,
                )
                pass

        # 2) worker 取消（None-safe）
        if self._active_worker is not None:
            try:
                self._active_worker.cancel()
            except RuntimeError:  # 同上
                _log.warning(
                    "MainWindow.closeEvent: ConversionWorker.cancel() RuntimeError "
                    "(deleteLater)",
                    exc_info=True,
                )
                pass

        # 3) 等 QThread 真正结束（最多 2s）
        if self._active_worker is not None:
            if not self._active_worker.wait(2000):
                _log.warning(
                    "MainWindow.closeEvent: ConversionWorker 2000ms 内未退出，"
                    "将强制 accept event 避免卡死用户"
                )

        # 4) 等 BatchWorker 的 QThreadPool 排空（最多 2s）
        # （v0.4.1 P0 S3）：改用 public BatchWorker.wait_finished()，
        # 不再访问 _pool 私有属性。
        if self._active_batch is not None:
            try:
                if not self._active_batch.wait_finished(2000):
                    _log.warning(
                        "MainWindow.closeEvent: BatchWorker 2000ms 内未排空，"
                        "将强制 accept event 避免卡死用户"
                    )
            except RuntimeError:  # bw 已 deleteLater()，被 PyQt 哨兵抛出
                _log.warning(
                    "MainWindow.closeEvent: BatchWorker.wait_finished() RuntimeError "
                    "(deleteLater)",
                    exc_info=True,
                )
            # closeEvent 路径下 _on_batch_finished 还没跑（cancel 触发的
            # finalize 走 QTimer.singleShot(0)），手动清引用避免 dangling。
            self._active_batch = None

        # 5) 让主线程事件循环消化掉所有 queued job_done / finished signal
        # （worker 退出前 emit 的信号走 QueuedConnection，必须在 history.close()
        # 前处理完，否则 _on_add 会用已 close 的 _conn 报 ProgrammingError）。
        QApplication.processEvents()

        # 6) 关闭 SQLite 连接（WAL checkpoint + 释放文件锁）。
        # （复审 #1）：之前 close() 从未被调用，
        # 每次退出都遗留 -wal/-shm 侧车文件 + 文件描述符直到 GC。
        if self._history is not None:
            try:
                self._history.close()
            except Exception:  # noqa: BLE001
                _log.warning("MainWindow.closeEvent: HistoryManager.close() failed", exc_info=True)

        # 7) 无论 wait 是否超时，都 accept event（spec 异常路径语义）
        event.accept()

    # -------- 菜单栏（）--------

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
        toolbar.addSeparator()
        # v0.4.1 P0 M1：实现 README 声称的"一键复制 Markdown"
        self._act_copy = toolbar.addAction("复制 Markdown")
        self._act_copy.triggered.connect(self._on_copy_clicked)
        # v0.4.1 P0 M2：实现 README 声称的"导出为 .md 文件"
        self._act_export = toolbar.addAction("导出 .md...")
        self._act_export.triggered.connect(self._on_export_clicked)

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
                _log.warning(
                    "MainWindow._open_settings_dialog: apply_theme(%r) failed",
                    self._config.get().theme,
                    exc_info=True,
                )
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
            (
                "Lei_MD\n\n基于 MarkItDown 的桌面 GUI 工具\n\n"
                "仓库: github.com/raymondyan-zhijie/Lei_MD"
            ),
        )

    # -------- 批量转换（）--------

    def _start_batch(self) -> None:
        """用 ConfigManager.batch_concurrency 启动 BatchWorker。

        审计（）：运行中守卫 —— 二次点击"全部转换"会
        覆盖 ``self._active_batch`` 引用，旧 bw 的 progress/failed signal 仍
        连到旧 slot（lambda 闭包捕获旧 bw，但 progress slot 走 ``self._on_batch_progress``），
        导致状态条上 done 计数被新 / 旧 batch 的 progress 信号交织刷新，看起来
        像 "interleaved progress"。

        修复：入口先 ``self._active_batch.cancel()``，把旧 batch 协作式终止
        （不再派新任务、finalize 路径正常走完），再启动新 batch。状态栏提示
        用户"已取消上一次批量"。
        """
        # ：运行中守卫 —— 先 cancel 旧 batch，避免引用覆盖 + 信号交织
        if self._active_batch is not None:
            self._active_batch.cancel()
            self.status.showMessage("已取消上一次批量")

        paths = self.file_list.all_paths()
        if not paths:
            self.status.showMessage("文件列表为空")
            return
        concurrency = max(1, int(self._config.get().batch_concurrency))
        # P0.5: 上一次 batch 的累积映射清空 —— 否则上轮成功的 md 会污染下一轮。
        self._batch_results.clear()
        bw = BatchWorker(self._converter, paths, concurrency=concurrency)
        bw.progress.connect(self._on_batch_progress)
        bw.item_finished.connect(self._on_batch_item_finished)
        # finished 结束后要把 BatchWorker deleteLater()，
        # 否则下一次 _start_batch 持有的旧 bw 还活着（内存泄漏 / dangling）。
        # 通过 lambda 透传 bw 引用，slot 内部用完即弃。
        bw.finished.connect(lambda b=bw: self._on_batch_finished(b))
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

    def _on_batch_finished(self, bw: BatchWorker) -> None:
        self.status.showMessage("批量转换完成")
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
        if self._active_batch is bw:
            self._active_batch = None
        # P0.5: batch 生命周期结束，累积映射也清空，避免下次 _start_batch 重复
        # clear()（防呆） + 释放短时 markdown 内存。失败条目由 BatchWorker 内部
        # 计数，MainWindow 不再单独追踪。
        self._batch_results.clear()
        # BatchWorker 是 QObject 树根，必须 deleteLater()，
        # 否则它内部的 QThreadPool + 已派发的 _ConvertRunnable 不会被回收。
        bw.deleteLater()

    @Slot(str, str)
    def _on_batch_item_finished(self, path: str, md: str) -> None:
        # P0.5: 成功条目落地。Markdown 写到 history（用 Path 后缀推 source_format），
        # 同时缓存到 _batch_results 备用。
        # v0.4.4+ P0: 如果 output_dir=custom + 目录可写，自动写一份同名 .md 到该
        # 目录（旁路 dialog）。这是专家建议的"批量转换应优先使用配置目录"。
        # 配置无效时不报错（已 _resolve_output_dir 弹过 QMessageBox 一次），
        # 只跳过自动导出，行为退回到"只写 history + 缓存"。
        out_dir = self._resolve_output_dir()
        if out_dir is not None:
            try:
                target = out_dir / (Path(path).stem + ".md")
                target.write_text(md, encoding="utf-8")
            except OSError as exc:
                # 写盘失败也不能让 batch 崩，只记 status
                self.status.showMessage(
                    f"导出失败：{target} - {exc}", 5000
                )
        try:
            fmt = Path(path).suffix.lstrip(".").lower() or "unknown"
        except Exception:
            fmt = "unknown"
        try:
            self._history.request_add(
                source_path=path,
                fmt=fmt,
                md_len=len(md),
                duration_ms=0,  # batch 不再细分每条耗时（BatchWorker 不发）
                success=True,
                error="",
            )
        except Exception as exc:  # 历史写入失败不能影响 batch 主流程
            self.status.showMessage(f"历史记录失败：{exc}")
        self._batch_results[path] = md

    def _on_batch_item_failed(self, path: str, err: str) -> None:
        # 当前简单记到状态栏；计划加入错误汇总面板
        self.status.showMessage(f"失败：{Path(path).name} - {err}")
