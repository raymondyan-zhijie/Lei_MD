# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
