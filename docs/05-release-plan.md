# Lei_MD 发布与维护计划

> 🌐 **Language**: **中文** | [English](05-release-plan.en.md)

> **品牌：** leimengde  
> **版本：** 规划期快照（实际发布见 [CHANGELOG](../CHANGELOG.md)） | **日期：** 2026-06-01  
>  
> 本文档为**项目初始规划期**的原始快照。v0.3.0 已发布（pip + GitHub Release），实际发布流程见 [IMPLEMENTATION_VS_PLAN.md](IMPLEMENTATION_VS_PLAN.md)。

> **SSOT 索引**：本文档是以下主题的**权威定义**：
> - §1 版本策略与里程碑
> - §3 交付物形态（NSIS 安装包大小、下载渠道）
>
> 上游依赖更新流程详见 [06-dependency-update-strategy.md](06-dependency-update-strategy.md)。
> 构建与打包流程详见 [07-build-release.md](07-build-release.md)。

---

## 1. 版本策略

采用 **SemVer (MAJOR.MINOR.PATCH)**：

| 版本号 | 变更类型 | 示例 |
|--------|----------|------|
| MAJOR (X.0.0) | 不兼容的 API 变更 | UI 重写、文件格式不兼容 |
| MINOR (0.X.0) | 向后兼容的新功能 | 新增格式支持、新面板 |
| PATCH (0.0.X) | 向后兼容的缺陷修复 | Bug 修复、性能优化 |

### 里程碑

> **总时间预估**（MVP）: 4-6 周（保守估算，详见 [03-development-plan.md](03-development-plan.md)）

```
v0.1.0  ← MVP: 拖拽转换 + 预览 + 导出                          （已发布，详见 CHANGELOG）
v0.2.0  ← 增强: 设置/批量/LLM/深色/中文/历史/YouTube            （已发布，详见 CHANGELOG）
v0.3.0  ← 审计/P0-P3 hotfix/6 维度复审/文档清理                  （已发布，157/157 绿，2026-06-02）
v1.0.0  ← 正式: 打包/NSIS 安装包/用户文档/第一正式版             （规划中）
v1.x.0  ← 持续迭代                                              （每月）
```

> **版本对应实施记录**：见 [CHANGELOG.md](../CHANGELOG.md) 与 [IMPLEMENTATION_VS_PLAN.md](IMPLEMENTATION_VS_PLAN.md)。

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

```python
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
#    - PyInstaller 打包 Lei_MD.exe
#    - NSIS 生成 Lei_MD-Setup-x.x.x.exe
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
            dist/Lei_MD.exe
            dist/Lei_MD-Setup-*.exe
          generate_release_notes: true
```

## 3. 交付物

### 3.1 三种交付形态（**大而全离线**）

| 形态 | 目标用户 | 大小（预估） |
|------|----------|------------|
| **NSIS 标准安装包** | 普通用户、企业部署 | 400-500MB（包含全部 20+ 格式依赖） |
| **便携版 zip** | 进阶用户、U 盘携带 | 同上，解压即用 |
| **pip 包** | 开发者自用 | 仅源码 + 依赖声明 |

> **v1.0 不提供按格式分拆安装**（MarkItDown 上游不分模块化，按需安装需要 fork 上游，列入 v2.0+ 路线图）

### 3.2 下载渠道

| 渠道 | 说明 |
|------|------|
| **GitHub Releases** | 主渠道，自动发布（`https://github.com/raymondyan-zhijie/Lei_MD/releases`） |
| **应用内「检查更新」** | 启动时调 `https://api.github.com/repos/raymondyan-zhijie/Lei_MD/releases/latest` 提示用户 |
| **官网** (未来) | `lei-md.leimengde.net` |
| **WinGet** (未来) | `winget install leimengde.Lei_MD` |
| **Scoop** (未来) | `scoop install lei-md` |

## 4. 用户文档

### 4.1 README.md 结构

```markdown
# Lei_MD

> 🪟 Windows 桌面版文件转 Markdown 工具 — 基于 Microsoft MarkItDown，**大而全 + 离线运行 + 传统安装**

## 快速开始
下载 Setup.exe → 安装 → 拖入文件 → 获得 Markdown

## 功能
- 🖱 拖拽转换：支持 PDF/Word/Excel/PPT/HTML/EPUB/图片/CSV/JSON/XML/ZIP 等
- 📁 目录拖拽：自动递归展开所有支持文件
- 👁 实时预览：Markdown 渲染视图（表格、代码块、图片）
- 📋 一键复制到剪贴板 / 导出 .md 文件
- 🎨 深色模式
- 🌏 中英文界面
- 🔒 本地优先运行（YouTube 字幕获取等少数功能需联网；日常使用不传数据）

## 不支持的格式（v1.0）
- 音频（MP3/WAV/OGG/FLAC）— 详见 [01-requirements.md F9a](01-requirements.md)

## 安装
1. 下载 `Lei_MD-Setup-x.x.x.exe`
2. 双击安装（NSIS 引导）
3. 开始使用

## 开发
见 `docs/` 目录（6 份规划文档）

## 反馈
- Issues: https://github.com/raymondyan-zhijie/Lei_MD/issues
- Email: 联系 leimengde
```

### 4.2 用户手册

```markdown
# Lei_MD 用户手册

## 基本操作
1. 打开 Lei_MD
2. 拖拽文件到窗口（或点击选择文件 / 拖入整个文件夹）
3. 点击「开始转换」
4. 预览 Markdown 结果
5. 点击「导出 .md」保存文件

## 批量转换
拖入多个文件或整个文件夹，点击「开始转换」即可批量处理。
文件夹会自动递归展开所有支持格式的文件。
转换过程显示进度条，每个文件完成后立即预览。

## 错误处理
所有错误均以**错误码**显示（例：`E_FILE_001`），
详细信息悬停可见，详细 traceback 在 `%APPDATA%\Lei_MD\logs\`。
遇到问题可在 GitHub Issues 搜索错误码。

## 设置 LLM 图片描述（v1.0.0+）
进入「设置」→ 填入 OpenAI 兼容 API Key → 选择模型
转换 PPT 和图片时会自动调用 LLM 生成描述文字。
（API Key 存储在 `%APPDATA%\Lei_MD\config.json`，不联网传输）

## 快捷键
| 快捷键 | 功能 |
|--------|------|
| Ctrl+O | 选择文件 |
| Ctrl+C | 复制 Markdown |
| Ctrl+S | 导出 .md |
| Ctrl+Q | 退出 |

## 数据存储位置
- 配置：`%APPDATA%\Lei_MD\config.json`
- 历史：`%APPDATA%\Lei_MD\history.db`
- 日志：`%APPDATA%\Lei_MD\logs\`
- 备份：`%APPDATA%\Lei_MD\*.bak`（自动生成，损坏恢复用）
```

## 5. 维护计划

### 5.1 上游依赖更新

> 完整的上游更新策略（markitdown / PySide6 / 底层库 / SemVer / 失败恢复）见 [docs/06-dependency-update-strategy.md](06-dependency-update-strategy.md)。本节为快速参考摘要。

| 依赖 | 检查频率 | 策略 | 详见 |
|------|----------|------|------|
| markitdown | 每周 | Dependabot PR | 06 §3 |
| PySide6 | 每月 | 手动评估 | 06 §4.1 |
| Python | 每季度 | 新增版本 CI 矩阵 | 06 §4 |
| 底层库（PyMuPDF/python-docx 等） | 每周 | Dependabot `group` | 06 §4.2 |

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
2026 Q3 — v1.0.0  稳定版发布（**未代码签名**，接受 SmartScreen 警告，README 提供「如何继续安装」说明）
2026 Q4 — v1.1.0  LLM 集成增强、自定义转换模板、**评估 EV 代码签名证书**（消除 SmartScreen 警告）
2027 Q1 — v1.2.0  WinGet/Scoop 分发、自动更新
2027 Q2 — v1.3.0  插件生态、用户自定义转换脚本
2027 Q4 — v2.0.0  跨平台 (macOS/Linux) 支持
```

**Code Signing 决策记录**：
- v1.0：**不签名**。Windows SmartScreen 会弹「未知发布者」警告，README 在「安装」章节提供「仍要安装」操作说明
- v1.1+：评估自签名 vs EV 证书成本与流程（EV 证书 ~$300-500/年，签发后 SmartScreen 立即信任；自签名仅企业内部分发有效）
- 详见 [02 §5.3 STRIDE Spoofing 威胁评估](02-architecture.md)

## 6. 社区与贡献

### 6.1 贡献指南

```markdown
# 贡献指南 (CONTRIBUTING.md)

## 开发环境
git clone https://github.com/raymondyan-zhijie/Lei_MD.git
cd Lei_MD
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
- deps: 上游依赖升级

## PR 流程
1. Fork 仓库
2. 创建功能分支（feat/xxx 或 fix/xxx）
3. 写测试 → 实现 → 确保本地通过
4. 提交 PR，描述变更
5. CI 自动运行测试（lint + pytest + build）
6. 维护者 Review 后合并

## 上游更新特别说明
当 `markitdown` 上游发布新版本时，请参考 `docs/06-dependency-update-strategy.md`，
不要直接修改 `pyproject.toml` 的版本上限。
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

## [1.0.0] - 2026-XX-XX

### Added
- 文件拖拽转换 (PDF/Word/Excel/PPT/HTML/EPUB/图片/CSV/JSON/XML/ZIP)
- 目录递归展开
- Markdown 实时预览
- 批量转换 + 进度条
- 一键复制到剪贴板
- 导出 .md 文件
- 深色/浅色主题切换
- 中英文界面 + 错误信息国际化
- 5 大类错误码体系（E_FILE / E_CONVERT / E_SYS / E_INTERNAL / E_UPDATE）
- SQLite 历史记录 + 启动时完整性检查
- 配置文件损坏自动备份恢复

### Fixed
- 大文件 (>50MB) 转换时内存泄漏修复
- 拖入目录时不再误传目录路径给 MarkItDown
- ConverterWorker 复用 converter 实例（性能优化）

### Not in v1.0 (planned v1.1+)
- 音频转录 (MP3/WAV) — 详见 [01-requirements.md F9a](01-requirements.md)
- YouTube URL 输入

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

Copyright (c) 2026 leimengde

Permission is hereby granted, free of charge, to any person obtaining a copy...
```
