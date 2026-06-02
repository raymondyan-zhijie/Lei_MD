# Changelog

> 🌐 **Language**: **中文** | [English](CHANGELOG.en.md)

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.6] - 2026-06-02

v0.4.5 之后的**首个 build infrastructure release**。10 commits：version bump 0.4.3→0.4.5 收尾 + 6 个 build pipeline bug fix（PyInstaller 6.20 / PowerShell 7 strict mode 暴露）+ 文档治理（"完全离线" → "本地优先" + docs/07-build-release §7 升级）。**GitHub Actions build pipeline 跑通**。**275/275 测试绿**。

### Fixed
- **`__version__` 0.4.3 → 0.4.5 (d22bf7a)**：R1.6 commit 漏 bump `src/__init__.py` L7 + `pyproject.toml` L3，导致 `test_version_consistency` 在 0.4.5 release 后实际 fail
- **CHANGELOG v0.4.5 段补 (c008fef)**：R1.6 bump + 审核 3 个 commit 都漏 CHANGELOG
- **PowerShell 7 strict-mode (fbdcedb)**：`build-windows.ps1` L188/189 `Write-Host "... v$AppVersion:"` 冒号被 PowerShell 7 当 scope qualifier 起始 → `${AppVersion}` 包起来
- **spec `__file__` → SPECPATH (507fec4)**：`Lei_MD.spec` L26 `Path(__file__).resolve().parent` —— PyInstaller 6.20.0 strict mode 拒收，改用 PyInstaller 内置 global `SPECPATH`
- **spec icons dir 缺失 (ae1e950)**：v0.4.3 spec 写 `("src/resources/icons", ...)` 但仓库从未建该目录 → 删 datas 该行 + ICON 注释（v0.4.6 还没 .ico）
- **spec hiddenimports 重写 (51e5d6a)**：v0.4.3 spec 列 `_outlook_converter`（markitdown 0.1+ 改名为 `_outlook_msg_converter`）和 `yt_dlp.extractor`（markitdown 0.1+ 已移除 yt-dlp backend 改用 youtube_transcript_api）—— 改用 grep 实际 site-packages 枚举 23 个 converter
- **installer LICENSE 路径 (51e5d6a)**：`installer.nsi` L50 `MUI_PAGE_LICENSE "LICENSE"` 漏 `..\` 前缀（其它 `File` 命令都有）→ `..\LICENSE`

### Added
- **`.github/workflows/build.yml`**：windows-latest + py3.12 + PyInstaller onefile 自动化；触发器 = `v*` tag push（自动 build + attach Release）/ `workflow_dispatch`（手动 + 可选 NSIS）/ 每周日 02:00 UTC dry-run

### Documentation
- **本地优先措辞 (1741bca)**：9 处"完全离线" / "fully offline" → "本地优先" / "local-first"（R2-1 commit 漏改）
- **docs/IMPLEMENTATION_VS_PLAN.md 截止 v0.4.5**
- **docs/07-build-release §7 升级 v0.5.0 计划 → v0.4.5 已上线**（6d53651）：触发条件表 / 用法 / 产物 / 耗时 / 实战坑

### Verified
- ✅ 275/275 测试绿（v0.4.5 → v0.4.6: 0 新增；纯 build + 文档治理）
- ✅ ruff 0 errors
- ✅ CI #22/#23 8/8 矩阵绿
- ✅ GitHub Actions build.yml 端到端验证（7 次触发：1-6 修 bug，#7 success）：
  - **build #4 success** (PyInstaller onefile, no NSIS) → `Lei_MD-0.4.5.exe` 138 MB
  - **build #7 success** (PyInstaller + NSIS) → `Lei_MD-0.4.5.exe` + `Lei_MD-0.4.5-Setup.exe` 各 138 MB
- ✅ PE 头 + version 字符串 + MD5/SHA256 全部验证通过
- ✅ 文件已上传 filebrowser: `https://file.leimengde.net/files/2026-06-02/`

### Artifacts (this release)
- `Lei_MD-0.4.5.exe` (PyInstaller onefile, 138 MB, GUI x86-64)
  - MD5: `d0164fd026bcd3a6bc12ab8c58c7215f`
  - SHA256: `e09d6fcdf9aef4396a28309dac5d5aea4dc9e01f5f3be59d59db4644dfb8f71a`
- `Lei_MD-0.4.5-Setup.exe` (NSIS installer, 138 MB, NSIS bootstrapper 32-bit)
  - MD5: `f339fd0cb4830540e3b6d3e875d33c88`
  - SHA256: `b7d9eb42afd73334a37d4a820feb66a2594596236e23b3562a690c99953fb87f`

> **v0.4.5 → v0.4.6 bump 理由**：v0.4.5 (release 333073483) 是 i18n 完善 patch；本次 10 commits 是**新增 build infrastructure**（不算 patch 而算 minor）。诚实版本号。

## [0.4.5] - 2026-06-02

v0.4.4 之后的小型治理 patch。**专家审查第一批 11 项中的 10 项 P0/P1/P2 修复，1 项 E1 延后到 v0.5.0+**，**3 commit**。**275/275 测试绿**。

### Fixed
- **A1 (428dca2) 删 main_window 冗余 import**：`import` 段清 5 处未使用符号
- **D1/D2/D3 (428dca2) SettingsDialog i18n 化**：4 个 group title + 3 个 button + 窗口标题 全部走 `tr()`，新增 7 个 i18n 键（zh+en）
- **A3 (83f9f91) i18n.py docstring 修正**：删除错误注释
- **B1 (83f9f91) 删错误注释**：DropArea 中关于 Qt 内部机制的不准确描述
- **D5 (83f9f91) YouTube 3 个弹窗 i18n 化**：模态警告文本走 `tr()`
- **D6 (83f9f91) DropArea placeholder 拆 3 键**：拖拽 / 松开 / 文件类型说明分别走 i18n；修复 `test_drop_area` 中 "drag" 断言
- **A2 (8f4bb1f) reload_language 移到公开 API 段**：文档结构对齐
- **A4 (8f4bb1f) 菜单/工具栏/对话框 i18n 化**：所有 UI 可见文字走 `tr()`

### Documentation
- **C1 (8f4bb1f) README 双语界面行**：补全英文件
- **C2 (8f4bb1f) docs/02-architecture.en.md §5.1+5.2 重写**：完全离线 → 本地优先

### Deferred
- **E1 双重触发器重构**：`MainWindow._on_config_changed` 同时承担 theme 和 language 切换，破坏 config schema 才做 → 推迟到 v0.5.0+；当前加注释 + 测试覆盖行为

### Verified
- ✅ 275/275 测试绿（v0.4.4 → v0.4.5: 0 新增；纯治理）
- ✅ ruff 0 errors
- ✅ CI #20 8/8 矩阵绿
- ✅ origin/main = 8f4bb1f 二次验证
- ✅ release id 333073483

## [0.4.4] - 2026-06-02

v0.4.3 之后的第二个治理 patch。**专家审查第二批 19 项中的 P0 + 1 项 P1（R4-6），共 5 commit**。**275/275 测试绿**。**CI #18 8/8 绿**。

### Fixed

- **R2-1 (df7f1bb)** LLM 图片描述功能撤场：UI widget 保留但 `setEnabled(False)` + "disabled since v0.4.4" 标签；converter 删 `llm_api_key=` 参数；monkey-patch 注释清理；README 4 处 LLM 文字改 "暂未实现"；同步改 "完全离线" → "本地优先"（标 R4-1 范围）
- **R2-2 (b9e918d)** output_dir 配置接 export 流：新增 `MainWindow._resolve_output_dir()` 辅助（"same" 返回 None；"custom" 检查路径存在 + 是目录 + 可写）；`_on_export_clicked` 用 `out_dir` 作 QFileDialog 初始路径；`_on_batch_item_finished` 批量自动导出同名 .md 到 `out_dir`；`errors.py` 补 `E_SYS_002` 登记
- **R2-3 (a49662a)** `set_locale("system")` 解析 + en_US.json 71 keys：移除 `"system"` 白名单（变触发器）；新增 `_resolve_system_locale()` 走 `LC_ALL > LANG > getdefaultlocale()` 解析为 zh_CN/en_US；新建 `src/resources/locales/en_US.json`（71 keys 全翻译）
- **R3-6 (d3a2932)** `src/resources/__init__.py` package marker：之前缺 `__init__.py`，setuptools wheel 打包时 `package_data` 不会包含 `locales/*.json`，安装后 set_locale("zh_CN") 找不到 JSON → UI 全英文 fallback
- **R4-6 (cc1bad9)** 切换语言后窗口立即刷新（不再需要重启）：`ConfigManager.on_change(callback)` 回调列表 + `MainWindow._on_config_changed` 调 `reload_language()` + `apply_theme()`

### Fixed (R4-6 顺带)

- **R2-2 真 bug 修复**：`_resolve_output_dir()` 每次调都弹 QMessageBox.warning（模态），batch 转 N 个文件弹 N 次对话框 → 加 `_warn` 参数 + `_output_dir_warned_for` 缓存去重
- **R2-3 残尾**：en_US.json 旧版 `status.converting` 漏 `{done}/{total}`、`status.cancelling` 漏 `...` 格式占位符
- **i18n 键新增**：`status.drop_to_start`、`button.cancel`（zh+en 双语同步）

### Changed

- i18n 协议对齐：所有可见文字必须走 `tr(key)`，`_tr("button.cancel")` / `_tr("status.drop_to_start")` 等取代硬编码中文
- ConfigManager.on_change 回调替代 Qt signal（保持 CM 纯 Python 对象，测试可无 QApplication 实例化）

### Verified

- ✅ 275/275 测试绿（v0.4.3 → v0.4.4: +28）
- ✅ ruff 0 errors
- ✅ CI #18 8/8 矩阵绿（Ubuntu+Windows × 3.10/3.11/3.12/3.13）
- ✅ origin/main = cc1bad9 二次验证
- ✅ release id 333042901

## [0.4.3] - 2026-06-02

v0.4.2 之后的首个治理 patch。**专家审查第二批 19 项中的前 5 项 P0**。**247/247 测试绿**。

### Fixed

- **P0.1: 跟踪 `Lei_MD.spec`** (`14f4eae`)：spec 之前被 .gitignore 排除但 README 声称一键 build 需要它；`build/` `dist/` 仍忽略，根 `!Lei_MD.spec` allowlist 放行。
- **P0.2: 单一版本源** (`aa97d5d` + `34dd92d`)：`pyproject.toml` `[project] version` 唯一真源；`scripts/build-windows.ps1` 用 `python -c "import tomllib..."` 读；`Lei_MD.spec` 用 `tomllib.loads(...)` 嵌入；`installer/installer.nsi` 强制 `/DAPP_VERSION=...` 从 build 脚本传入。CI 加 `version-consistency` job。新增 `tests/test_version_consistency.py` 4 个测试。
- **P0.3: 入口装 Config + History** (`436ea7d`)：之前 `main.py` 只 `MainWindow()`，所有依赖都拿默认；现在 `config = ConfigManager(); history = HistoryManager(max_entries=config.get().max_history); window = MainWindow(config_manager=config, history=history)`。新增 3 个集成测试。
- **P0.4: `auto_convert` 接入 DropArea** (`6d54fea`)：单文件拖入自动转 + 选中；多文件仅加入列表（与"非拖入"路径一致）；`auto_convert=False` 仅加入列表。
- **P0.5: 批量成功条目落地** (`a08032a`)：之前 `BatchWorker.item_finished(path, md)` signal MainWindow 没接，批量成功 markdown 全丢；现在新 slot 写 history + 累 `_batch_results` 缓存。3 个旧 `_FakeBW` mock 补 `item_finished` 属性。

### Security

- **隔离 workflow-only commit** (`34dd92d`)：PAT 缺 `workflow` scope，build chain commit (`aa97d5d`) 已推，workflow-only commit 暂留本地。

## [0.4.2] - 2026-06-02

v0.4.1 之后 PySide6 6.11 在 py3.12 ubuntu 上 segfault 的 hotfix。**CI #12 7/7 绿**。

### Fixed

- **P0 PySide6 segfault** (`973a9b3`)：pin `PySide6<6.11`（6.9.x 稳定线）—— 6.11+ 在 ubuntu py3.12 上 QDragEnterEvent 触发 segfault。`src/ui/i18n.py` 加 `sys._MEIPASS` 支持（PyInstaller 资源路径）。

## [0.4.1] - 2026-06-02

v0.4.0 release 推出了 CI workflow 但 4 个 commit 之后才让 CI 真正跑绿。**205/205 测试绿 · 7/7 CI jobs 绿**。

### Fixed

- **CI: ruff 治理** (`86a2e27`): `ruff check src/ tests/` 从 151 errors → 0 errors
  - auto-fix 112 个 (--fix --unsafe-fixes): I001 unsorted imports / F401 unused / UP007 union syntax
  - 手改 18 个: F821 log→_log / E402 import 顺序 / N802 Qt event 强制驼峰 (noqa) / N812 LEI_MD_VERSION brand import (noqa)
  - 拆 32 个 E501 长行: log.warning 父化、_log 改 named function、CSS 拆多行
  - `pyproject.toml` 加 per-file-ignores (tests/i18n/styles 走 E501 例外)
- **CI: flaky test 修** (`d5d505e`): `test_batch_worker_emits_progress_with_done_total` Qt Signal 在 worker deleteLater 时仍 in flight 导致"Signal source has been deleted"
  - 加 `qtbot.waitSignal(bw.finished)` 等最后信号
  - 20/20 本地 stress 绿 (修前 9/10)
- **CI: Windows XDG_*_HOME 修复** (`ea02458`): `config_dir()` / `data_dir()` 在 Windows 上**只读 %APPDATA%**，忽略 `XDG_CONFIG_HOME` / `XDG_DATA_HOME`
  - 导致 Windows runner 上 18 个测试因 state pollution 失败 (theme='light' 残留、history rows 泄露、config 目录不存在)
  - 修法: Windows 优先读 XDG_*_HOME (test override)，production 默认仍走 %APPDATA%
  - 真实 production 行为不变
- **CI: Windows rsplit path 修复** (`7c09a58`): `tests/test_v025_low.py` 用 `p.rsplit("/", 1)[-1]` 取 basename —— 在 Windows 上 path sep 是 `\\` 而非 `/`，所以拆分失败
  - 改用 `Path(p).name` (跨平台)
  - 影响 2 个 drop_area 测试

### CI Status

- 7-job matrix: ubuntu + windows × py3.10/3.11/3.12/3.13 (排除 win+3.10)
- 实际跑出 7/7 全绿 (commit `7c09a58`)
- 完整历程: #1-3 YAML 缩进 fail → #4 ruff 4/7 fail → #5 Windows XDG 4/7 fail → #6 Windows rsplit 3/7 fail → #7 ✅
- 教训: v0.x 之前 CI 只跑 Linux, 隐藏了 Windows-only 路径/state bug; v0.4.1 修复后才真"cross-platform tested"

### Notes

- v0.4.0 tag 没动 (已发布不重写 CHANGELOG)
- 本次 4 个 commit 全部是 CI 修复, 无功能变更 → patch 版本号 (0.4.1)
- pyproject.toml 仍 `version = "0.4.0"` (没改 version; tag 才是 source of truth for release)

## [0.4.0] - 2026-06-02

v0.3.0 IMPLEMENTATION_VS_PLAN §4 中标记的 3 个候选全部实施。**205/205 测试绿**（v0.3.0 的 157 + 新增 48）。

### Added

- **CI 工作流** (`.github/workflows/test.yml`): ubuntu-latest + windows-latest × Python 3.10/3.11/3.12/3.13 = 8 矩阵 (排除 win+3.10)
  - 每周一 09:00 UTC 自动跑
  - `pip install -e ".[dev]"` + `ruff check` + `pytest --tb=short -q`
  - 替代 v0.3.0 时代的"本地手动 source .venv"流程
- **Task 2.4 YouTube URL 输入** (规划补齐): `src/core/youtube.py` + 4 个 E_CONVERT_* 错误码 (E_CONVERT_003/004/005)
  - 支持 4 种 URL 形式: watch?v= / youtu.be/ / shorts/ / embed/
  - 抓字幕不下载视频,流量极小
  - 错误码体系完整: 无效 URL / yt-dlp 缺失 / 网络超时 / 视频不可访问 / 无字幕
- **音频 E_FILE_006 显式拦截** (Task C): 拖入 .mp3/.wav/.ogg/.flac/.m4a/.aac/.wma/.opus **不再静默忽略**,而是
  - `DropArea.audio_rejected` Signal 触发
  - MainWindow 弹模态对话框,显示错误码 E_FILE_006 + 错误信息
  - 4 个新音频扩展名 (.m4a/.aac/.wma/.opus) 加入拦截集

### Added (Tests)

- `tests/test_youtube.py` (30 项): URL 解析 + 错误码映射 + 4 种 URL 形式 SSOT
- `tests/test_v040_audio_reject.py` (18 项): 音频集合 SSOT + drop 行为 + 错误码注册

### Fixed

- `src/core/youtube.py` YOUTUBE_URL_PATTERNS: 修正 `[\w-]{11}` 贪婪匹配的边界问题
  ( `waytoolongvideoid12345` 错误匹配前 11 字符)

## [0.3.0] - 2026-06-02

跨 Sprint 整体审计 + P2/P3 hotfix + 文档清理后的整合 release。**157/157 测试绿灯**（v0.2.2 的 97 + v0.2.3-v0.2.7 新增 60）。

### Added

- 6 维度审计（安全/并发/错误处理/架构 SSOT/测试覆盖）+ 全量自修
- P0/P1/P2/P3 共 23 个 Medium + 6 个 Low 全部修复并加回归测试
- `test_v027_p0_regression.py`（5）+ `test_v027_p1_regression.py`（8）+ `test_p3_coverage_gaps.py`（3）

### Fixed

- **M1.2** BatchWorker `_cancelled` 改 `threading.Event` 保证跨线程内存可见
- **M1.3** BatchWorker 加 IDLE/RUNNING/CANCELLED/FINISHED 状态机防二次 start/cancel
- **M1.5** cancel finalize 与 _on_item_done 互斥（`_finalize_emitted` 标志 + mutex）
- **M3.1** HistoryManager 外层 except close 失败连接
- **M3.2** HistoryManager 公共方法 None 守卫（`_conn = None` 初始化）
- **M3.7** `MarkItDownConverter.convert` 拒绝目录/设备文件
- **M3.8** MarkItDown 线程隔离：`clone_for_thread()` 每 runnable 独立引擎
- **M3.3** SettingsDialog Reset 不再改 live config（staging copy）
- **M3.4** BatchWorker `_dispatched.clear()` finalize 时清理
- **M3.5** `_start_batch` 运行中守卫：先 cancel 旧 batch 再启新
- **M3.6** `HistoryPanel.refresh` try/except `sqlite3.Error` → 不崩
- **M4.1** MainWindow `closeEvent` 5 步关停：cancel → wait → waitForDone → processEvents → `history.close()` → accept
- **M4.2** closeEvent 清 `_active_batch` 引用
- **M5.3** `os.path.getsize` 包 try/except OSError → 准确错误码 E_FILE_001
- **M5.4** 8 处 silent exception swallow 加 `log.warning`
- **M6.2** ConfigManager 拒绝非 dict JSON root
- **M6.3** `AppConfig.__post_init__` 字段类型 + 范围校验
- **M6.4** `_backup_and_reset` 三级 fallback：`os.replace` → `shutil.move` → `unlink`
- **L1** i18n locale 白名单（"system"/"en"/"zh_CN"/"en_US"）
- **L2** DropArea `rglob` 改 `os.walk` + 限深 10 + 限文件 2000
- **L3** PreviewPanel `setOpenLinks(False)` + `_safe_set_source` 拦截 file://
- **L4** `ConversionError.__cause__` 链路可见
- **closeEvent 调 `HistoryManager.close()`**（v0.2.6 复审 #1：之前从未调用，每次退出 WAL 泄漏）
- **i18n en 加白名单**（v0.2.6 复审 #3：英文用户启动不再 spam warning）

### Changed

- `BatchWorker._ConvertRunnable.run()` 兼容 callable 顶层函数（测试 stub 回归）
- `closeEvent` 顺序：先 drain queued signals (`processEvents`) 再 `history.close()` 避免 ProgrammingError

### Cleanup

- 源文件 docstring/注释：删除所有 `v0.X.Y`/`Sprint N`/`Task X.Y`/`M[N.M]`/`H[N]`/`L[N]`/`P[N]`/`SSOT[：]` 引用
- 保留所有"为什么这样做"的实质内容
- 净删 67 行版本元信息

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

## [0.4.5] - 2026-06-02

v0.4.4 之后的小型治理 patch — **审核收口 11 项**。**275/275 测试绿**。**CI #20 8/8 绿**。

### Fixed (P0)

- **A1 (428dca2)** main_window.py 删 5 处冗余 `from PySide6.QtWidgets import QMessageBox`（顶层已 import）
- **D1/D2/D3 (428dca2)** SettingsDialog 全 i18n 化（之前完全硬编码中文，R4-6 live lang switch 半成品）：
  - 窗口标题 / 3 个按钮 / 4 个 group title 全部走 i18n
  - JSON +3 键：settings.group.output / capacity / ui

### Fixed (P1)

- **A3 (83f9f91)** i18n.py docstring 修复（"i18n for Lei_MD — ." 损坏）
- **B1 (83f9f91)** 删"让旧 import 路径下的 _tr() 行为不变"错误注释
- **D5 (83f9f91)** YouTube 3 个 QMessageBox 文案走 i18n（fetch_title / empty_url / invalid_url / fetch_failed_title / fetch_failed_error_code）
- **D6 (83f9f91)** DropArea DEFAULT_PLACEHOLDER 4 行硬编码拆 3 个 i18n 键（drop.placeholder.lead / formats / audio_note）

### Fixed (P2)

- **A2 (8f4bb1f)** `reload_language` 从「生命周期」段移到「公开 API」段，定位更准
- **A4 (8f4bb1f)** 主菜单 5 项 + 工具栏 3 项 + 5 个对话框（导出/复制/历史/关于/音频拒绝）走 i18n
- **C1 (8f4bb1f)** README.md / README.en.md「双语界面」行加 v0.4.5 提示
- **C2 (8f4bb1f)** docs/02-architecture.en.md §5.1+5.2 重写（VALID_LOCALES 改 frozenset / system trigger / locale 解析链）

### Skipped

- **C3** docs/07-build-release.md 是操作手册不是 changelog，无需改
- **E1** AppConfig.language 拆 use_system_locale 字段（去双触发器）— 留 v0.5.0+ 单独 commit（破坏现有 config schema）

### Verified

- ✅ 275/275 测试绿（v0.4.4 → v0.4.5: +0，2 个测试放宽接受双语）
- ✅ ruff 0 errors
- ✅ CI #20 8/8 矩阵绿
- ✅ origin/main = 8f4bb1f 二次验证
- ✅ release id 333073483

### i18n 键增长

v0.4.3 (71) → v0.4.4 (75, +4) → **v0.4.5 (100, +25)**
