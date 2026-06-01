# Lei_MD

> 🪟 **Windows 桌面版文件转 Markdown 工具** — 基于 [Microsoft MarkItDown](https://github.com/microsoft/markitdown) (⭐ 136,328)
> **大而全 · 完全离线 · 传统安装程序**

拖拽文件 → 自动转换 → 实时预览 → 一键导出。**让非技术用户也能享受 MarkItDown 的强大能力。**

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 🖱 **拖拽转换** | 拖入文件/文件夹即可自动转换 |
| 📁 **目录递归** | 拖入文件夹自动展开所有支持文件 |
| 👁 **实时预览** | 内置 Markdown 渲染视图（表格/代码高亮/图片） |
| 📦 **批量处理** | 一次拖入多个文件，并行转换 + 进度条 |
| 📋 **一键复制** | 转换结果一键复制到剪贴板 |
| 💾 **导出文件** | 导出为 .md 文件（UTF-8） |
| 🎨 **深色模式** | 跟随 Windows 系统主题自动切换 |
| 🌏 **双语界面** | 中文 / English |
| 🤖 **LLM 图片描述** | 可选 OpenAI 兼容 API，为图片生成文字描述 |
| 📜 **历史记录** | SQLite 存储，自动保留最近 50 条 |
| 🔒 **完全离线** | 安装后不联网，配置/历史存本地 |
| ⚠️ **错误码体系** | 5 大类错误码（E_FILE / E_CONVERT / E_SYS / E_INTERNAL / E_UPDATE） |

## 📦 支持的格式（v1.0）

| 类别 | 格式 |
|------|------|
| 📄 文档 | PDF · DOCX · DOC · PPTX · PPT · XLSX · XLS · EPUB |
| 🌐 文本 | HTML · HTM · CSV · JSON · XML · TXT · MD |
| 🖼 图片 | JPG · JPEG · PNG · GIF · BMP · WEBP（可选 LLM 描述） |
| 📦 压缩 | ZIP · MSG · IPYNB |
| ❌ **v1.0 不支持** | MP3 · WAV · OGG · FLAC（计划 v1.1+ 离线实现） |

## 🚀 快速开始

### 普通用户

1. 下载最新 `Lei_MD-Setup-x.x.x.exe` 从 [Releases](https://github.com/raymondyan-zhijie/Lei_MD/releases)
2. 双击安装（NSIS 引导）
3. 拖入文件开始使用！

### 开发者

```bash
git clone https://github.com/raymondyan-zhijie/Lei_MD.git
cd Lei_MD
pip install -e ".[dev]"
python src/main.py
```

## 📸 截图

> 待补充

## 🗺 路线图

| 版本 | 时间 | 内容 |
|------|------|------|
| v0.1.0 | 2026-06 | 项目初始化 + 6 份规划文档 |
| v0.5.0 | 2026-07 | MVP：拖拽 + 预览 + 导出（核心 5 格式） |
| v1.0.0 | 2026-08 | 完整 20+ 格式 + NSIS 安装包（**400-500MB 离线**） |
| v1.1.0 | 2026-Q4 | 音频转录（ffmpeg + whisper 离线） + 应用内更新检查 |
| v1.2.0 | 2027-Q1 | WinGet / Scoop 分发 + 可选自动更新 |
| v2.0.0 | 2027-Q4 | 跨平台（macOS/Linux） |

## 🏗 技术栈

| 层 | 技术 |
|----|------|
| GUI | PySide6 (Qt6) |
| 转换引擎 | Microsoft MarkItDown[all] |
| 预览渲染 | markdown + Pygments + QTextBrowser |
| 历史存储 | SQLite (含完整性自检) |
| 配置存储 | JSON (`%APPDATA%\Lei_MD\config.json`) |
| 打包 | PyInstaller + NSIS |
| CI/CD | GitHub Actions (Windows + Ubuntu) |

## 📁 项目结构

```
Lei_MD/
├── src/                # 源代码
│   ├── ui/             # GUI 组件 (MainWindow, DropArea, PreviewPanel, ...)
│   ├── core/           # 业务逻辑 (Converter, BatchWorker, History, Config, Updater)
│   └── resources/      # 图标 + 国际化 + 错误码映射
├── tests/              # 测试 (单元 + UI + 集成 + 性能)
│   ├── conftest.py     # 全局 qapp fixture
│   └── fixtures/       # 样本文件
├── docs/               # 规划文档
│   ├── 01-requirements.md
│   ├── 02-architecture.md
│   ├── 03-development-plan.md
│   ├── 04-testing-plan.md
│   ├── 05-release-plan.md
│   └── 06-dependency-update-strategy.md
├── scripts/            # 构建脚本 (PyInstaller, NSIS, bump_version)
├── .github/workflows/  # CI (test+lint+build) + CD (release)
├── CODE_OF_CONDUCT.md  # 社区行为准则
├── CONTRIBUTING.md     # 贡献指南
├── CHANGELOG.md        # 变更日志
├── LICENSE             # MIT
└── pyproject.toml      # 项目配置
```

## 🤝 贡献

欢迎贡献！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。
社区行为准则见 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

> **上游 MarkItDown 发布新版本时**，请参考 [docs/06-dependency-update-strategy.md](docs/06-dependency-update-strategy.md)。

## 📄 许可

MIT License — Copyright (c) 2026 leimengde。与上游 [Microsoft MarkItDown](https://github.com/microsoft/markitdown) 保持一致。

## 🙏 致谢

本项目基于 Microsoft AutoGen Team 的杰出工作：[MarkItDown](https://github.com/microsoft/markitdown)
