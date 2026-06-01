# MarkItDown-GUI

> 🪟 **Windows 桌面版文件转 Markdown 工具** — 基于 Microsoft MarkItDown (⭐136K+)

拖拽文件 → 自动转换 → 预览 → 导出。让非技术用户也能享受 MarkItDown 的强大能力。

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 🖱 **拖拽转换** | 拖入文件即可转换，支持 PDF/Word/Excel/PPT/HTML/EPUB/图片/音频/ZIP 等 20+ 格式 |
| 👁 **实时预览** | 内置 Markdown 渲染视图，表格、代码高亮完美呈现 |
| 📦 **批量处理** | 一次拖入多个文件，并行转换带进度条 |
| 📋 **一键复制** | 转换结果一键复制到剪贴板 |
| 💾 **导出文件** | 导出为 .md 文件 (UTF-8) |
| 🎨 **深色模式** | 跟随 Windows 系统主题自动切换 |
| 🌏 **中文界面** | 完整的中文 UI |
| 🤖 **LLM 图片描述** | 可选集成 OpenAI API，为图片生成文字描述 |
| 📜 **历史记录** | 自动保存转换历史，随时回看 |

## 🚀 快速开始

### 普通用户

1. 下载最新 `MarkItDown-GUI-Setup-x.x.x.exe` 从 [Releases](https://github.com/raymondyan/markitdown-gui/releases)
2. 双击安装
3. 拖入文件开始使用！

### 开发者

```bash
git clone https://github.com/raymondyan/markitdown-gui.git
cd markitdown-gui
pip install -e ".[dev]"
python src/main.py
```

## 📸 截图

> 待补充

## 🗺 路线图

- [x] 文件拖拽转换（MVP）
- [x] Markdown 预览
- [x] 批量转换
- [x] 深色模式
- [x] 中文界面
- [ ] LLM 图片描述增强
- [ ] YouTube 链接转换
- [ ] 插件生态
- [ ] WinGet / Scoop 分发
- [ ] 跨平台支持 (macOS/Linux)

## 🏗 技术栈

| 层 | 技术 |
|----|------|
| GUI | PySide6 (Qt6) |
| 转换引擎 | Microsoft MarkItDown |
| 预览渲染 | markdown + Pygments |
| 历史存储 | SQLite |
| 打包 | PyInstaller + NSIS |

## 📁 项目结构

```
markitdown-gui/
├── src/                # 源代码
│   ├── ui/             # GUI 组件
│   └── core/           # 业务逻辑
├── tests/              # 测试
├── docs/               # 文档
│   ├── 01-requirements.md
│   ├── 02-architecture.md
│   ├── 03-development-plan.md
│   ├── 04-testing-plan.md
│   └── 05-release-plan.md
├── scripts/            # 构建脚本
└── .github/            # CI/CD
```

## 🤝 贡献

欢迎贡献！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 许可

MIT License — 与上游 [Microsoft MarkItDown](https://github.com/microsoft/markitdown) 保持一致。

## 🙏 致谢

本项目基于 Microsoft AutoGen Team 的杰出工作：[MarkItDown](https://github.com/microsoft/markitdown)
