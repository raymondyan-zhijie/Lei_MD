# MarkItDown-GUI 发布与维护计划

> **版本：** v0.1.0 | **日期：** 2026-06-01

---

## 1. 版本策略

采用 **SemVer (MAJOR.MINOR.PATCH)**：

| 版本号 | 变更类型 | 示例 |
|--------|----------|------|
| MAJOR (X.0.0) | 不兼容的 API 变更 | UI 重写、文件格式不兼容 |
| MINOR (0.X.0) | 向后兼容的新功能 | 新增格式支持、新面板 |
| PATCH (0.0.X) | 向后兼容的缺陷修复 | Bug 修复、性能优化 |

### 里程碑

```
v0.1.0  ← MVP: 拖拽转换 + 预览 + 导出         (Sprint 1-2, 2 周)
v0.2.0  ← 批量/设置/LLM/深色/中文              (Sprint 3, 1 周)
v0.3.0  ← 历史面板/YouTube/插件                (Sprint 4, 1 周)
v1.0.0  ← 打包/安装包/文档/第一正式版          (Sprint 5, 1 周)
v1.x.0  ← 持续迭代                             (每月)
```

## 2. 发布流程

### 2.1 发布前检查清单

```markdown
- [ ] 所有 P0/P1 测试通过
- [ ] ruff lint 零错误
- [ ] 在干净 Windows 10/11 虚拟机验证 .exe 可运行
- [ ] NSIS 安装包安装/卸载正常
- [ ] README.md 更新到最新版本号
- [ ] CHANGELOG.md 记录所有变更
- [ ] Git tag 打上对应版本号
```

### 2.2 发布步骤

```bash
# 1. 更新版本号
python scripts/bump_version.py 1.0.0

# 2. 提交并打 tag
git add .
git commit -m "release: v1.0.0"
git tag -a v1.0.0 -m "v1.0.0: First stable release"

# 3. 推送 tag（触发 GitHub Actions release.yml）
git push origin main --tags

# 4. GitHub Actions 自动：
#    - 运行全部测试
#    - PyInstaller 打包
#    - NSIS 生成安装包
#    - 创建 GitHub Release 并上传资产
```

### 2.3 自动发布流水线

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ['v*']

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - name: Install deps
        run: |
          pip install -e ".[all]"
          pip install pyinstaller
      - name: Build EXE
        run: python scripts/build.py
      - name: Build NSIS installer
        uses: joncloud/makensis-action@v4
        with:
          script-file: scripts/installer.nsi
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            dist/MarkItDown-GUI.exe
            dist/MarkItDown-GUI-Setup-*.exe
          generate_release_notes: true
```

## 3. 交付物

### 3.1 三种交付形态

| 形态 | 目标用户 | 大小 |
|------|----------|------|
| **便携版 .exe** | 进阶用户、U 盘携带 | ~80MB (单文件) |
| **NSIS 安装包** | 普通用户、企业部署 | ~90MB |
| **zip 压缩包** | 便携 + 可选依赖 | ~80MB |

### 3.2 下载渠道

| 渠道 | 说明 |
|------|------|
| **GitHub Releases** | 主渠道，自动发布 |
| **官网** (未来) | markitdown-gui.leimengde.net |
| **WinGet** (未来) | `winget install markitdown-gui` |
| **Scoop** (未来) | `scoop install markitdown-gui` |

## 4. 用户文档

### 4.1 README.md 结构

```markdown
# MarkItDown-GUI

> 🪟 Windows 桌面版文件转 Markdown 工具 — 基于 Microsoft MarkItDown

## 快速开始
下载 .exe → 拖入文件 → 获得 Markdown

## 功能
- 🖱 拖拽转换：支持 PDF/Word/Excel/PPT/HTML 等 20+ 格式
- 👁 实时预览：Markdown 渲染视图
- 📋 一键复制/导出
- 🎨 深色模式
- 🌏 中文界面

## 安装
1. 下载 MarkItDown-GUI-Setup-x.x.x.exe
2. 双击安装
3. 开始使用

## 开发
见 docs/ 目录
```

### 4.2 用户手册

```markdown
# MarkItDown-GUI 用户手册

## 基本操作
1. 打开 MarkItDown-GUI
2. 拖拽文件到窗口（或点击选择文件）
3. 点击「开始转换」
4. 预览 Markdown 结果
5. 点击「导出 .md」保存文件

## 批量转换
拖入多个文件，点击「开始转换」即可批量处理。
转换过程显示进度条，每个文件完成后立即预览。

## 设置 LLM 图片描述
进入「设置」→ 填入 OpenAI API Key → 选择模型
转换 PPT 和图片时会自动调用 LLM 生成描述文字。

## 快捷键
| 快捷键 | 功能 |
|--------|------|
| Ctrl+O | 选择文件 |
| Ctrl+C | 复制 Markdown |
| Ctrl+S | 导出 .md |
| Ctrl+Q | 退出 |
```

## 5. 维护计划

### 5.1 上游依赖更新

| 依赖 | 检查频率 | 策略 |
|------|----------|------|
| markitdown | 每周 | 自动 Dependabot PR |
| PySide6 | 每月 | 手动评估兼容性 |
| Python | 每季度 | 新增版本 CI 矩阵 |

### 5.2 日常维护任务

| 任务 | 频率 | 负责人 |
|------|------|--------|
| 依赖安全扫描 | 每周 (Dependabot) | 自动 |
| Issue 分类/回复 | 每周 | 维护者 |
| 社区 PR Review | 按需 | 维护者 |
| 新格式支持 (上游新增) | 按需 | 维护者 |
| 性能回归测试 | 每个版本发布前 | CI |

### 5.3 长期路线图

```
2026 Q3 — v1.0.0  稳定版发布
2026 Q4 — v1.1.0  LLM 集成增强、自定义转换模板
2027 Q1 — v1.2.0  WinGet/Scoop 分发、自动更新
2027 Q2 — v1.3.0  插件生态、用户自定义转换脚本
2027 Q4 — v2.0.0  跨平台 (macOS/Linux) 支持
```

## 6. 社区与贡献

### 6.1 贡献指南

```markdown
# 贡献指南 (CONTRIBUTING.md)

## 开发环境
git clone https://github.com/<user>/markitdown-gui.git
cd markitdown-gui
pip install -e ".[dev]"

## 代码风格
- 遵循 PEP 8
- ruff 自动格式化
- 类型注解必须

## 提交规范
- feat: 新功能
- fix: 缺陷修复
- docs: 文档更新
- style: 代码格式
- refactor: 重构
- test: 测试
- chore: 构建/工具

## PR 流程
1. Fork 仓库
2. 创建功能分支
3. 写测试 → 实现 → 确保通过
4. 提交 PR，描述变更
5. CI 自动运行测试
6. 维护者 Review 后合并
```

### 6.2 问题反馈模板

```yaml
name: Bug Report
description: 报告缺陷
body:
  - type: input
    attributes:
      label: 版本号
      placeholder: "v1.0.0"
  - type: input
    attributes:
      label: Windows 版本
      placeholder: "Windows 11 23H2"
  - type: textarea
    attributes:
      label: 复现步骤
  - type: textarea
    attributes:
      label: 期望行为
  - type: textarea
    attributes:
      label: 截图/日志
```

## 7. CHANGELOG 模板

```markdown
# Changelog

## [1.0.0] - 2026-07-15

### Added
- 文件拖拽转换 (PDF/Word/Excel/PPT/HTML/EPUB/图片/音频/ZIP)
- Markdown 实时预览
- 批量转换 + 进度条
- 一键复制到剪贴板
- 导出 .md 文件
- 深色/浅色主题切换
- 中英文界面

### Fixed
- 大文件 (>50MB) 转换时内存泄漏修复

## [0.1.0] - 2026-06-30

### Added
- 项目初始化
- 基本窗口骨架
- 拖拽区域组件
- 转换引擎封装
```

## 8. 许可证

本项目采用 **MIT License**，与上游 [Microsoft MarkItDown](https://github.com/microsoft/markitdown) 保持一致。

```
MIT License

Copyright (c) 2026 Raymond Yan

Permission is hereby granted, free of charge, to any person obtaining a copy...
```
