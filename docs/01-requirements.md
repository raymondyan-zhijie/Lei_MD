# MarkItDown-GUI 需求文档

> **项目名称：** MarkItDown-GUI  
> **版本：** v0.1.0  
> **日期：** 2026-06-01  
> **作者：** Raymond Yan  

---

## 1. 项目背景

[Microsoft MarkItDown](https://github.com/microsoft/markitdown)（⭐136K+ stars）是一个优秀的 Python 文件转 Markdown 工具，支持 PDF、Word、Excel、PowerPoint、HTML、EPUB、图片（OCR）、音频（转录）、YouTube 等 20+ 种格式。然而它仅有命令行接口，对 Windows 普通用户不够友好。

本项目旨在为 MarkItDown 构建一个 **Windows 原生图形界面**，让非技术用户也能轻松拖拽文件完成转换。

## 2. 用户画像

| 角色 | 需求 | 痛点 |
|------|------|------|
| 学生/研究者 | 把论文 PDF、课程 PPT 转 Markdown 整理笔记 | 命令行不会用 |
| 内容创作者 | 把 Word/网页文章转 Markdown 发布 | 来回切换工具繁琐 |
| 办公人员 | 批量转换 Excel/Word 文档为文本 | 格式丢失、步骤多 |
| 开发者 | 快速预览文件 Markdown 输出 | CLI 不直观 |

## 3. 功能需求

### 3.1 核心功能（MVP — v1.0）

| 编号 | 功能 | 优先级 | 描述 |
|------|------|--------|------|
| F1 | 文件拖拽转换 | P0 | 拖拽单个或多个文件到窗口，自动识别格式并转换 |
| F2 | 格式支持列表 | P0 | 支持 MarkItDown 所有内置格式（PDF/Word/Excel/PPT/HTML/EPUB/图片/音频/CSV/JSON/XML/ZIP） |
| F3 | 转换结果预览 | P0 | 内置 Markdown 实时预览窗口，支持渲染视图 |
| F4 | 一键复制/导出 | P0 | 复制 Markdown 原文到剪贴板、导出为 .md 文件 |
| F5 | 批量转换 | P1 | 多文件并行/顺序批量转换，进度条显示 |
| F6 | 输出目录选择 | P1 | 用户可指定输出目录，默认同源文件目录 |
| F7 | 历史记录 | P1 | 保留最近 50 条转换记录，支持回看 |

### 3.2 进阶功能（v1.1+）

| 编号 | 功能 | 优先级 | 描述 |
|------|------|--------|------|
| F8 | LLM 图片描述 | P2 | 集成 OpenAI 兼容 API，对图片/PPT 中的图片生成描述 |
| F9 | YouTube 链接转换 | P2 | 输入 YouTube URL，获取字幕转 Markdown |
| F10 | 插件支持 | P2 | 支持 MarkItDown 第三方插件 |
| F11 | 导入/导出配置 | P2 | 用户可保存/加载转换配置预设 |
| F12 | 深色模式 | P2 | 支持 Windows 深色/浅色主题切换 |

### 3.3 非功能需求

| 编号 | 需求 | 指标 |
|------|------|------|
| NF1 | 性能 | 单文件 <5MB 转换在 3 秒内完成 |
| NF2 | 兼容性 | Windows 10/11，Python 3.10+ |
| NF3 | 安装包大小 | 便携版 <100MB，安装版 <200MB |
| NF4 | 内存占用 | 空闲 <100MB，转换中 <500MB |
| NF5 | 国际化 | 支持中/英文界面切换 |

## 4. 约束条件

- **依赖 MarkItDown 库**：核心转换能力由上游库提供，本项目只做 GUI 封装
- **必须兼容 Windows**：考虑使用 PyInstaller 打包为独立 .exe
- **遵循 MIT 许可**：与上游 MarkItDown 保持一致
- **Python 生态**：GUI 框架限定 Python 生态（降低维护成本）
