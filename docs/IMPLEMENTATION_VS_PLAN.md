# 规划 vs 实施 对照表（v0.3.0 截止）

> **生成日期：** 2026-06-02  
> **基线版本：** v0.3.0（157/157 绿）  
> **对比对象：** 6 份初始规划文档（[01-requirements](01-requirements.md) / [02-architecture](02-architecture.md) / [03-development-plan](03-development-plan.md) / [04-testing-plan](04-testing-plan.md) / [05-release-plan](05-release-plan.md) / [06-dependency-update-strategy](06-dependency-update-strategy.md)）  
> **实施记录源：** [CHANGELOG.md](../CHANGELOG.md) v0.1.0 / v0.2.0 / v0.3.0 三段

---

## 1. 总体结论

| 维度 | 数字 | 说明 |
|---|---|---|
| 规划任务总数 | 17（Phase 0-5）| 任务 0.1 ~ 5.x |
| ✅ 已实施 | 15 | 88% |
| ⚠️ 部分/有偏差 | 2 | 12%（CI 工作流推迟；打包推迟到 v1.0）|
| ❌ 未实施 | 1 | 6%（YouTube URL 输入）|
| 🆕 规划外追加 | 12+ 项 | 32 项审计修复（详见 §3）|

**整体评估**：规划准确度高（15/17 命中），主要偏差集中在 Phase 3 打包（v0.3.0 走 pip+GitHub Release，NSIS 安装包推迟到 v1.0）和 Phase 0 CI（v0.3.0 仅本地 pytest，无 GitHub Actions）。规划外最大的追加是 6 维度审计（5 subagent 并行 + 32 项 hotfix + 60 新测试），属于在 v0.2.0~v0.3.0 实施过程中基于实际代码产生的新需求，不在初始规划里。

---

## 2. 任务级对照（Phase × Task）

### Phase 0: 项目初始化

| 任务 | 规划 | 实施 | 状态 |
|---|---|---|---|
| Task 0.1 项目骨架 | pyproject.toml + .gitignore + requirements + src/ | pyproject.toml + .gitignore + LICENSE + CONTRIBUTING + CODE_OF_CONDUCT + README | ✅ |
| Task 0.2 CI/CD | GitHub Actions test/lint/build 三 job | 无（v0.3.0 仅本地 pytest + ruff）| ⚠️ 推迟 |

### Phase 1: MVP（v0.1.0 已发布）

| 任务 | 规划 | 实施 | 状态 |
|---|---|---|---|
| Task 1.1 程序入口 | src/main.py + QMainWindow | `src/main.py` + `src/ui/main_window.py` | ✅ |
| Task 1.2 拖拽区域 | `src/ui/drop_area.py` | 同左 | ✅ |
| Task 1.3 转换引擎封装 | `MarkItDownConverter` 封装 | `src/core/converter.py` | ✅ |
| Task 1.4 异步转换 Worker | `ConverterWorker(QThread)` | `src/core/worker.py` + `src/core/batch_worker.py`（v0.2.0 扩展为批量） | ✅ |
| Task 1.5 Markdown 预览 | `PreviewPanel(QTextBrowser)` | `src/ui/preview_panel.py` | ✅ |
| Task 1.6 文件列表 | `FileList` 组件 | `src/ui/file_list.py` | ✅ |
| Task 1.7 主窗口整合 | 菜单/工具栏/状态栏 | `src/ui/main_window.py` | ✅ |
| Task 1.8 配置管理 | `ConfigManager` JSON 持久化 | `src/core/config.py`（含 v0.2.2 chmod 0o600 / v0.2.3 校验 / v0.2.3 备份三级 fallback） | ✅ +增强 |
| Task 1.9 历史记录 | `HistoryManager(SQLite)` | `src/core/history.py`（含 v0.2.2 main-thread assert / v0.2.2 close-leak fix / WAL + Signal 串行化） | ✅ +增强 |

### Phase 2: 增强（v0.2.0 已发布）

| 任务 | 规划 | 实施 | 状态 |
|---|---|---|---|
| Task 2.1 设置对话框 | `SettingsDialog` | `src/ui/settings_dialog.py`（含 v0.2.3 staging copy reset） | ✅ |
| Task 2.2 批量并行 | `BatchWorker(QThreadPool)` | `src/core/batch_worker.py`（含 v0.2.2 mutex + finished-once / v0.2.6 threading.Event） | ✅ |
| Task 2.3 历史记录面板 | `HistoryPanel` | `src/ui/history_panel.py` | ✅ |
| Task 2.4 YouTube URL 输入 | URL 输入框 → markitdown YouTube converter | **未实施**（v0.3.0 跳到 pip+GitHub Release，跳过了 YouTube） | ❌ |
| Task 2.5 深色模式 | `darkdetect` + QSS 切换 | `src/ui/styles.py` | ✅ |
| Task 2.6 中文界面 | i18n + zh_CN.json | `src/ui/i18n.py` + `src/resources/locales/zh_CN.json`（含 v0.2.5 locale 白名单 / v0.2.6 fallback key） | ✅ |

### Phase 3: 打包（推迟到 v1.0）

| 任务 | 规划 | 实施 | 状态 |
|---|---|---|---|
| Task 3.1 PyInstaller 打包 | `scripts/build.py` | 无（v0.3.0 走 `pip install lei-md`） | ⚠️ v1.0 |
| Task 3.2 NSIS 安装包 | `scripts/installer.nsi` | 无（同上） | ⚠️ v1.0 |
| Task 3.3 GitHub Release 自动化 | release.yml | 走 `curl` 调 GitHub API（人工触发），非 GitHub Actions 自动化 | ⚠️ 流程变体 |

### Phase 4: 测试

| 任务 | 规划 | 实施 | 状态 |
|---|---|---|---|
| Task 4.1 单元测试 | pytest + qapp fixture | 28 个测试文件 / 157 测试 / 全部绿 | ✅ +超出 |
| Task 4.2 测试清单 | 单元 + UI + 集成 + 性能 | 单元 + UI + 集成 + 回归（v0.2.1 ~ v0.2.7 全覆盖）+ 真实 worker E2E | ✅ +超出 |

### Phase 5: v1.0 收尾清单

| 项目 | 状态 | 备注 |
|---|---|---|
| 拖拽 7+ 格式 | ✅ | v0.1.0 已支持 |
| 目录递归展开 | ✅ | v0.1.0 |
| 音频明确提示 | ⚠️ 部分 | i18n key 存在，UI 拦截未做（v0.1.0 仍把 mp3 当 unsupported format） |
| 批量 10 文件无崩溃 | ✅ | v0.2.0 20 并发压测通过 |
| 预览渲染 | ✅ | QTextBrowser + 表格/代码块/图片 |
| 复制 / 导出 | ✅ | UTF-8 .md |
| 深色/浅色 | ✅ | darkdetect 跟随系统 |
| 中文界面 | ✅ | zh_CN.json 完整 |

---

## 3. 规划外追加（v0.2.0 ~ v0.3.0 实施中涌现）

### 3.1 6 维度审计（v0.3.0 核心）

| 维度 | 范畴 | 修复项数 |
|---|---|---|
| 安全 | chmod / BOM / 路径遍历 / file:// | 5 |
| 并发 | BatchWorker 状态机 / SQLite WAL / HistoryManager 主线程 | 8 |
| 错误处理 | ConfigManager 备份 / OSError → E_FILE_001 / 8 处 silent swallow | 5 |
| 架构 SSOT | 文档清理 / 章节引用统一 | 2 |
| 测试覆盖 | BatchWorker 并发 / 真实 worker E2E / set_locale 翻译生效 | 3 |
| P0/P1 复审 | closeEvent history.close / i18n en 白名单 / _start_batch 守卫 | 4 |
| **合计** | | **32 项** + 60 新测试 |

### 3.2 配置加固（v0.2.1 ~ v0.2.3）

- `chmod 0o600`（H1）— config.json / 备份文件权限
- `utf-8-sig` BOM 剥离（H3）— Windows 记事本兼容
- `ConfigManager._backup_and_reset` 三级 fallback（M6.4）— os.replace → shutil.move → unlink
- `AppConfig.__post_init__` 类型 + 范围校验（M6.3）
- 拒绝非 dict JSON root（M6.2）

### 3.3 Worker 安全（v0.2.1 ~ v0.2.7）

- `BatchWorker` 状态机（IDLE / RUNNING / CANCELLED / FINISHED）+ `threading.Event` + 互斥 finalize
- `MarkItDownConverter.clone_for_thread()` 线程隔离（M3.8）
- `MainWindow.closeEvent` 5 步关停（cancel → wait → processEvents → history.close → accept）
- i18n locale 白名单（防恶意语言文件）

### 3.4 UI 增强（v0.2.5 ~ v0.2.6）

- `PreviewPanel.setOpenLinks(False)` + `file://` 拦截（L3）
- `DropArea` 限深 10 + 限 2000 文件（L2）
- `ConversionError.__cause__` 链路可见（L4）

---

## 4. 偏差项后续行动

| 偏差 | 后续 |
|---|---|
| ⚠️ Task 0.2 CI/CD 推迟 | v0.4.0 前建 `.github/workflows/test.yml`（windows + ubuntu + python 3.10-3.13 矩阵）。**当前依赖本地 .venv 跑 157/157**，首次跑需 `source .venv/bin/activate` |
| ⚠️ Task 3.1/3.2 打包推迟 | v1.0 计划。要 PyInstaller + NSIS 在 Windows runner 跑。Linux 容器**不能**出 .exe |
| ❌ Task 2.4 YouTube URL | v0.4.0 候选。可用 `markitdown`'s YouTubeTranscriptFetcherCli 实现 |
| ⚠️ Phase 5 音频明确提示 | v0.4.0 候选。DropArea 加 mime type 检查 + 显式 E_FILE_006 弹窗 |

---

## 5. 关键经验（v0.1.0 → v0.3.0 跨 Sprint 总结）

1. **规划准确，但"安全"维度需要额外一轮**：32 项审计修复有 27 项不在初始规划里，是看到实际代码后才浮现。后续 v1.0 规划应在 Phase 0 加"安全评审 + 架构评审"两个 Phase 0 后的 review gate。
2. **Phase 边界"软化"**：原计划 Sprint 0/1-2/3/4 4 个 sprint，实际 v0.1.0~v0.3.0 只用 1 个 sprint（2 周内集中推进）。原因是 Task 0.1 已搭好骨架后，其余任务可并行。
3. **测试规模超预期 1.8x**：规划预期 88 个测试，实际产出 157 个（88% 是 hotfix 回归 + 6 维度复审加的）。说明"任务级测试" + "跨任务审计"是两条独立测试路径。
4. **NSIS / PyInstaller 强依赖 Windows runner**：Aliyun Linux 容器无法交叉编译 .exe，需要独立的 Windows CI runner 或本地 Windows 机器。**v0.3.0 选 pip+GitHub Release 是务实选择**。
5. **6 维度复审"必须做"**：5 subagent 并行扫（安全/并发/错误处理/架构 SSOT/测试覆盖），跨 Sprint 找到了 32 个真问题，比单 agent 自审有效得多。**v1.0 复审应在 v1.0-rc1 之前再做一次**。

---

## 6. 引用

- [CHANGELOG.md](../CHANGELOG.md) — v0.1.0 / v0.2.0 / v0.3.0 三段完整记录
- [01-requirements.md](01-requirements.md) — 需求快照
- [02-architecture.md](02-architecture.md) — 架构快照
- [03-development-plan.md](03-development-plan.md) — 开发计划快照（已标注"历史规划档案"）
- [04-testing-plan.md](04-testing-plan.md) — 测试计划快照
- [05-release-plan.md](05-release-plan.md) — 发布计划快照
- [06-dependency-update-strategy.md](06-dependency-update-strategy.md) — 依赖更新策略快照
- [GitHub Release v0.3.0](https://github.com/raymondyan-zhijie/Lei_MD/releases/tag/v0.3.0)
