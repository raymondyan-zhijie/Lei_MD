# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.2] - 2026-06-01

Sprint 3 跨 Sprint 整体审计后的 P1 hotfix。**97/97 测试绿灯**（v0.2.1 的 92 + 新增 5 回归测试）。

### Fixed

- **H1** `ConfigManager.save()` 写完不收紧权限 → LLM API key 同机可读 (`src/core/config.py:122-145`)
  - 修复：`save()` + 备份复位后都 `os.chmod(0o600)`；Windows/FAT32/只读盘容错
  - 影响：POSIX 系统上 config.json 现在仅当前用户可读写（多用户机器/备份工具/恶意软件读不到 key）
  - 长期：v0.3+ 计划用 `keyring` 替换（Windows Credential Manager / macOS Keychain / Secret Service）
- **H5** `BatchWorker._done_count += 1` 丢更新 + cancel/自然完成 finished 双发 (`src/core/batch_worker.py:160-200`)
  - 修复：增量在 QMutex 锁内，新增 `_finalize_emitted` 标志使 `finished` 单发（cancel finalize 与 _on_item_done 互斥）
  - 影响：批量转换中途取消 + 最后一个任务完成并发时 finished 不再发 2 次
- **H6** `HistoryManager.check_same_thread=False` 仅靠注释保证主线程唯一 (`src/core/history.py:106-120, 198-242`)
  - 修复：新增 `_assert_main_thread()`，在 `_on_add` / `list` / `_trim` / `close` 入口 assert
  - 影响：从 worker 线程误调任何公共方法立即 `RuntimeError`（之前会导致 sqlite3 死锁/段错误）
  - QCoreApplication 未启动时（CLI/测试）跳过
- **H9** i18n 字符串与代码不一致：`zh_CN.json` 写"200MB"但 `errors.py:60` 是"500MB" (`src/resources/locales/zh_CN.json:58`)
  - 修复：i18n 改为"500MB"
  - 影响：用户看到的中文错误信息与实际限制一致

### Added

- `tests/test_v022_hotfix.py` — 5 个回归测试覆盖 H1/H5/H6/H9

## [0.2.1] - 2026-06-01

Sprint 3 跨 Sprint 整体审计后的 P0 安全/正确性 hotfix。**92/92 测试绿灯**（v0.2.0 的 88 + 新增 4 回归测试）。

### Fixed

- **H2** 批量模式下取消按钮是 silent no-op (`src/ui/main_window.py:197-202`)
  - 修复：`_on_cancel_clicked` 先检查 `_active_batch`，再 fallback 到 `_active_worker`；`__init__` 声明 `self._active_batch = None`
  - 影响：用户在批量转换中途点"取消"现在能真停，旧行为是 UI 撒了谎
- **H4** 单文件 worker 在 `cancel()` 之后仍 `emit(finished_with_md)` (`src/core/worker.py:82-89`)
  - 修复：在 `emit(md)` 前再 check 一次 `self._cancel_event.is_set()`，被取消则不 emit（job_done 仍发，error_msg = "E_SYS_001"）
  - 影响：UI 不再出现"已取消"状态但 preview 已渲染满的矛盾
- **H3** `ConfigManager` 拒收 UTF-8 BOM (`src/core/config.py:88`)
  - 修复：encoding 从 `"utf-8"` 改为 `"utf-8-sig"`，自动剥离 BOM
  - 影响：Windows 记事本默认存 BOM 的 config.json 现在能正常加载，不再被误判损坏而 reset

### Added

- `tests/test_v021_hotfix.py` — 4 个回归测试覆盖 H2/H3/H4

## [0.2.0] - 2026-06-01

Sprint 3 完成（Task 2.1 ~ 2.6 + MainWindow 集成）。**88/88 测试绿灯**（v0.2.0-rc1 的 58 + 新增 30）。

### Added

- **SettingsDialog** (`src/ui/settings_dialog.py`, Task 2.1)
  - 模态对话框，注入 ConfigManager 读写
  - 5/5 测试：构造载入 / accept 持久化 / cancel 不改 / 字段类型映射 / reset_to_defaults
- **BatchWorker** (`src/core/batch_worker.py`, Task 2.2)
  - QThreadPool + QRunnable 批量并行转换
  - signals: `progress(done, total)` / `finished()` / `item_failed(path, err)`
  - cancel() 立即发 finished，剩余路径标记 cancelled
  - 单文件失败不影响其他（错误汇总通过 `item_failed`）
- **HistoryPanel** (`src/ui/history_panel.py`, Task 2.3)
  - 表格视图：时间/源文件/输出文件/状态
  - 搜索框按 source_path 子串过滤
  - 双击行触发 `file_selected(path)` signal（MainWindow 接住走 worker）
- **深色模式** (`src/ui/styles.py`, Task 2.5)
  - `darkdetect` 检测系统主题
  - `apply_theme('dark'|'light'|'system')` 切换 QPalette + QSS
  - `ThemeManager` 监听系统变更，外部回调通知
- **中文界面** (`src/ui/i18n.py` + `src/resources/locales/zh_CN.json`, Task 2.6)
  - `Translator` 类 + 模块级默认 + `tr(key)` helper
  - `set_locale('zh_CN'|'en')` 加载对应 JSON；缺失键 fallback 到 key 本身
  - 53 条 zh_CN 翻译（菜单/状态/设置/历史/错误码）

### Changed

- **MainWindow 集成** (`src/ui/main_window.py`)
  - 新增 `config_manager: ConfigManager | None` 注入
  - 启动时 `apply_theme(config.theme)` + `set_locale(config.language)`
  - 菜单栏：文件（设置/退出） / 视图（历史记录） / 帮助（关于）
  - 工具栏"全部转换" 按钮 → 启动 BatchWorker 用 `config.batch_concurrency`
  - 设置变更后自动 apply_theme
  - 历史面板作为非模态对话框从"视图 > 历史记录"打开
- **FileList** (`src/ui/file_list.py`)
  - 新增 `all_paths() -> list[str]`，批量转换用

### Test Coverage

新增 30 个测试（73 → 88/88）：
- test_settings_dialog.py: 5
- test_batch_worker.py: 5
- test_history_panel.py: 5
- test_styles.py: 3
- test_i18n.py: 4
- test_mainwindow_integration.py: 3
- test_batch_integration.py: 3
- test_i18n_integration.py: 2

## [0.2.0-rc1] - 2026-06-01

Sprint 2 完成（Task 1.8 + Task 1.9）。**58/58 测试绿灯**（v0.1.1 的 44 + 新增 14）。

### Added

- **配置文件管理** (`src/core/config.py`, Task 1.8)
  - `AppConfig` dataclass：output_dir / custom_output_dir / auto_convert / max_history=50 / language="system" / theme="system" / batch_concurrency=4 / llm_api_base / llm_api_key / llm_model="gpt-4o"
  - `ConfigManager` 跨平台：Windows %APPDATA%\\Lei_MD\\config.json，Linux/macOS ~/.config/Lei_MD/config.json
  - 损坏自动备份 .json.bak + 复位（E_INTERNAL_003）
  - 未知字段静默忽略（forward-compat）
  - `update(**kwargs)` 即写盘
- **历史记录** (`src/core/history.py`, Task 1.9)
  - SQLite 持久化，schema 含 source_path / source_format / markdown_length / duration_ms / success / error_msg / created_at
  - **WAL + Signal 串行化并发模型**（02 §3.3.1）：PRAGMA journal_mode=WAL + busy_timeout=5000 + synchronous=NORMAL
  - `request_add()` emit `add_requested(dict)` Signal → 主线程槽 `_on_add` 实际写
  - 容量 trim：保留 max_entries=50
  - **崩溃恢复**：启动 PRAGMA integrity_check，损坏 → 备份 .db.bak.<ts> + 重建（E_INTERNAL_002）
  - `close()` 调 `PRAGMA wal_checkpoint(TRUNCATE)`
- **Worker 元信息 signal** (`src/core/worker.py`)
  - 新增 `job_done = Signal(str, str, int, int, bool, str)`：source_path / source_format / md_len / duration_ms / success / error_msg
  - 通过 `try/finally` 块保证成功/失败/取消三种路径都发
- **MainWindow 集成** (`src/ui/main_window.py`)
  - `MainWindow(converter=..., history=...)` 新增 history kwarg（向后兼容）
  - 转换完成自动写历史
- **测试 14 个新增**
  - `tests/test_config.py` 5 个：默认 / 持久化 / 损坏备份 / 未知字段忽略 / 目录创建
  - `tests/test_history.py` 6 个：增删查 / 排序 / trim / 失败 / 跨线程 / 损坏恢复
  - `tests/test_main_window_history.py` 3 个：成功记录 / 失败记录 / 未注入 graceful

### Changed

- **API**：`MainWindow.__init__()` 新增可选 kwarg `history`（默认 None，v0.1.x 调用方式不破）
- **API**：`ConversionWorker.job_done` 新 signal（向后兼容，旧 signal 不变）
- 实现：`_config_dir()` / `data_dir()` 改为每次调用重新读 env（测试 monkeypatch 友好）

## [0.1.1] - 2026-06-01

Worker 异步转换接入 MainWindow。**44/44 测试绿灯**（v0.1.0 的 36 + 新增 8）。

### Added
- **MainWindow 异步转换升级** (`src/ui/main_window.py`)
  - 选文件 → 启 ConversionWorker（QThread）后台转换，主线程不阻塞
  - status bar 永久添加 QProgressBar（0~100，转换中实时更新）
  - status bar 永久添加「取消」按钮（按下 worker.cancel() 协作中断）
  - 切换文件自动 cancel 上一个 worker，避免并发
- **Converter 依赖注入** — `MainWindow(converter=...)` 测试可换 Stub
- **新测试** `tests/test_main_window_v011.py`（8 个用例）
  - progress_bar / cancel_button 初始隐藏
  - converter 注入生效
  - 选文件 → 异步 → preview 显示
  - 进度条 0→100 实时更新
  - 取消按钮中断 worker
  - 错误时 preview 显示中文错误信息
  - 切换文件 cancel 上一个

### Changed
- **API breaking**：`MainWindow.__init__()` 增加可选 kwarg `converter`。向后兼容（默认仍用真 MarkItDownConverter）
- MainWindow 不再 import 同步 converter 调用路径（性能 + UX 改进）

## [0.1.0] - 2026-06-01

首个可运行的 MVP。Sprint 1（Task 1.1-1.7）全部完成，36/36 测试绿灯。

### Added
- **核心转换引擎** (`src/core/converter.py`)
  - 包装 Microsoft MarkItDown，单实例化复用引擎
  - 前置校验：文件存在、非空、<500MB
  - 异常翻译：MarkItDown 抛异常 → ConversionError（E_CONVERT_001 密码保护 / E_CONVERT_002 损坏）
- **错误码体系** (`src/core/errors.py`) — SSOT 实现 5 大类 16 错误码
  - E_FILE_001~006（文件级：不存在/空/超大/路径遍历/不支持格式/音频暂不支持）
  - E_CONVERT_001~002（转换级：密码保护/损坏）
  - E_SYS_001~003 / E_INTERNAL_001~003 / E_UPDATE_001~002
  - 双语错误信息（zh_CN / en_US），不向用户暴露 Python traceback
- **异步 Worker** (`src/core/worker.py`) — QThread 子类
  - signals: `progress(int)`, `finished_with_md(str)`, `error(ConversionError)`
  - `cancel()` 协作式中断
- **UI 组件**（`src/ui/`）
  - `drop_area.py`：拖拽接收 + 目录递归 + 扩展名过滤（SSOT 集合）
  - `file_list.py`：已添加文件列表 + 去重 + 扩展名过滤 + 选中信号
  - `preview_panel.py`：QTextBrowser Markdown 预览 + NUL 清洗兜底
  - `main_window.py`：三栏 QSplitter 组装（DropArea / FileList / PreviewPanel）+ 状态栏
- **入口** (`src/main.py` + `src/app.py`) — `QApplication` 初始化 + MainWindow 启动
- **打包配置** (`pyproject.toml`)
  - pip 包名 `lei-md`（[project] name）+ Python 导入名 `src.*`（`[tool.setuptools] packages`）
  - `[project.scripts] lei-md = "src.main:main"`
  - 依赖钉版本（PySide6 6.9.x、markitdown 0.1.x）+ Python 3.10~3.13
- **测试**：36/36 绿
  - 单元 + 集成：TDD 风格（先 test 后 code）
  - `pytest-qt` 跑 PySide6 offscreen 模式（Linux 容器无显示器）
  - Stub Converter 隔离 markitdown 真实依赖

### Known Limitations（v0.1.0 范围外，留待后续 Sprint）
- 音频转录（MP3/WAV）不支持 → v1.1+ 离线 ffmpeg + whisper tiny
- 批量转换仍走同步，Worker 已写好留 v0.1.1 接入 MainWindow
- 设置面板 / 历史记录 / i18n 切换 / 主题 → Sprint 2+
- QWebEngine 增强预览 → 仅在用户启用 v1.0 高级预览时拉取（+400MB 体积）

## [Unreleased] - Pre-Sprint 1（项目初始化与文档）

### Added
- 项目初始化：文档驱动的完整规划
  - 需求文档 (`docs/01-requirements.md`)
  - 架构设计文档 (`docs/02-architecture.md`)
  - 开发计划 (`docs/03-development-plan.md`)，含 15 个具体任务
  - 测试计划 (`docs/04-testing-plan.md`)
  - 发布与维护计划 (`docs/05-release-plan.md`)
  - 依赖更新策略 (`docs/06-dependency-update-strategy.md`)
- 项目骨架: `pyproject.toml`, `.gitignore`, `LICENSE`, `README.md`, `CONTRIBUTING.md`
- 社区准则: `CODE_OF_CONDUCT.md` (Contributor Covenant v2.0)
- 错误处理设计：5 大类错误码体系（E_FILE/E_CONVERT/E_SYS/E_INTERNAL/E_UPDATE）
- 配置路径：统一到 `%APPDATA%\Lei_MD\`（Windows）+ `~/.config/Lei_MD/`（v2.0+ 跨平台）
- 离线 + 大而全 + 传统安装包路线（400-500MB 单安装包）
- 应用内「检查更新」+ GitHub Releases 主渠道
- SemVer + Dependabot 自动依赖更新策略
