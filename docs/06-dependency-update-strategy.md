# Lei_MD 依赖更新策略

> **品牌：** leimengde  
> **版本：** 规划期快照（实际依赖见 [pyproject.toml](../pyproject.toml)） | **日期：** 2026-06-01  
> **范围：** 首次发布（v1.0.0）之后的版本演进与上游依赖管理  
>  
> 本文档为**项目初始规划期**的原始快照。v0.3.0 实际依赖版本与策略见 [IMPLEMENTATION_VS_PLAN.md](IMPLEMENTATION_VS_PLAN.md)。

> **SSOT 索引**：本文档是以下主题的**权威定义**：
> - §3 markitdown 上游更新策略
> - §4 底层库更新策略
> - §5 SemVer 发布规则
> - §7 失败恢复机制

---

## 1. 概述

Lei_MD 是 Microsoft MarkItDown 的 GUI 封装。**它不是孤岛**——它依赖一个**关键上游**（MarkItDown）和 **7+ 底层库**（PySide6、PyMuPDF、python-docx 等）。任何一个更新都可能 break 本项目。

本文档定义：
1. 上游 MarkItDown 更新的跟进策略
2. 底层库更新的处理流程
3. Lei_MD 自身的 SemVer 发布规则
4. 用户的更新渠道
5. 更新失败的恢复机制

---

## 2. 依赖层级

```
┌─────────────────────────────────────────┐
│  Lei_MD v1.0.0                           │   ← 我们
├─────────────────────────────────────────┤
│  markitdown[all] v0.1.x                  │   ← 关键上游（1 个）
├─────────────────────────────────────────┤
│  PySide6 / markdown / Pygments /        │   ← 底层库（7+ 个）
│  PyMuPDF / python-docx / python-pptx /  │
│  openpyxl / magika / pydub / ...        │
├─────────────────────────────────────────┤
│  Python 3.10 / 3.11 / 3.12 / 3.13       │   ← 运行时
└─────────────────────────────────────────┘
```

**更新频率（粗略）**：
- MarkItDown：每月 1-2 次 minor
- PySide6：每季度 minor
- 底层库：每周都有 PR 涌入（Dependabot 必触发）

---

## 3. 上游 MarkItDown 更新策略

### 3.1 版本锁定规则

`pyproject.toml` 当前约束：
```toml
"markitdown[all]>=0.1.0,<0.2.0"
```

- **`<0.2.0` 上限**：在 v0.2.0 发布前**不主动放开**。
- **Dependabot** 自动开 PR（`versioning-strategy: increase within bounds`）
- 当 `markitdown v0.2.0` 发布 → Dependabot **不会**自动升级（因越界） → 人工 review

### 3.2 评估周期（markitdown minor 发布时）

| 步骤 | 动作 | 时间 |
|------|------|------|
| 1 | 看 release notes（breaking changes?） | 1 天 |
| 2 | 本地 `pip install markitdown==0.2.0` + 跑测试 | 半天 |
| 3 | 跑样本文件转换（PDF/Word/Excel/PPT/HTML 各 1 个） | 半天 |
| 4 | 检查 `MarkItDown.convert()` 签名是否变化 | 1 小时 |
| 5 | 改 `pyproject.toml` 上限 + 更新代码 | 1 天 |
| 6a | 无 breaking → 开 PR "deps: bump markitdown to 0.2.x" | 半天 |
| 6b | 有 breaking → 开 PR "feat!: migrate to markitdown 0.2 API" + **Lei_MD minor bump** | 1-2 天 |

### 3.3 应急处理（markitdown 发严重 bug）

如果上游发了 `0.1.5` 修复严重 bug：
- **不等待周一**，手动当天发 PR
- PR title：`hotfix(deps): bump markitdown to 0.1.5 for CVE-xxx`
- 走 hotfix 分支 → 合 main → 立即 patch release（0.1.5.1）

---

## 4. 底层库更新策略

### 4.1 自动 vs 手动

| 库 | 类型 | 策略 |
|----|------|------|
| PySide6 | GUI 核心 | **手动**，major 延后 1 个 minor 周期 |
| PyMuPDF / pdfminer | PDF 解析 | Dependabot 自动（patch + minor） |
| python-docx | Word 解析 | Dependabot 自动 |
| python-pptx | PPT 解析 | Dependabot 自动 |
| openpyxl | Excel 解析 | Dependabot 自动 |
| magika | 格式检测 | Dependabot 自动 |
| markdown | Markdown 渲染 | Dependabot 自动 |
| Pygments | 代码高亮 | Dependabot 自动 |

### 4.2 Dependabot 配置

`.github/dependabot.yml`：
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
    groups:
      minor-and-patch:
        patterns: ["*"]
        update-types: ["minor", "patch"]
    labels:
      - "dependencies"
    commit-message:
      prefix: "deps"
    # PySide6 例外，单独开 PR 不合组
    ignore:
      - dependency-name: "PySide6"
        update-types: ["minor", "major"]
```

### 4.3 PR 合并规则

| PR 类型 | 合并方式 |
|---------|----------|
| Dependabot patch 自动 PR | **CI 通过即合**（auto-merge enabled） |
| Dependabot minor 自动 PR | 人工 review + 本地烟测（启动 app + 转 1 文件） |
| Dependabot major PR | 人工评估，通常延后 |
| PySide6 minor | 单独评估，CI 必须跑全平台 + 全样本 |

### 4.4 CI 烟测（自动跑）

`pytest -m smoke`：
- 启动 app
- 转换 1 个 .txt
- 转换 1 个 .pdf
- 转换 1 个 .docx
- 验证历史写入 SQLite

**这是 PR 合并的硬门槛**——任一失败则 PR 不可合。

---

## 5. Lei_MD 自身 SemVer 发布规则

### 5.1 版本号约定

```
v MAJOR . MINOR . PATCH
  ↑        ↑        ↑
  重大      新功能    Bug 修复
  不兼容
```

### 5.2 触发条件

| 改动 | 版本 bump | 示例 |
|------|-----------|------|
| Bug 修复、性能优化、文档更新 | **PATCH** (0.0.X) | v1.0.0 → v1.0.1 |
| 新增 P1 功能、markitdown 0.1.x → 0.1.y (patch) | **PATCH** (0.0.X) | v1.0.0 → v1.0.1 |
| 新增 P2 进阶功能、底层库 minor 升级、markitdown 0.1.x → 0.2.0 (minor) | **MINOR** (0.X.0) | v1.0.0 → v1.1.0 |
| GUI 重写、配置文件 schema 不兼容、markitdown 0.x → 1.0 | **MAJOR** (X.0.0) | v1.x.x → v2.0.0 |

### 5.3 自动化

`.github/workflows/release.yml`：
- 监听 `v*` tag
- 跑全测试
- PyInstaller + NSIS 打包
- 创建 GitHub Release（自动生成 notes）

**手动打 tag**（不在 CI 自动）：
```bash
git tag -a v1.0.1 -m "hotfix: 修复 X"
git push origin v1.0.1
```

---

## 6. 用户侧更新

### 6.1 三种渠道

| 渠道 | 适用 | 频率 |
|------|------|------|
| **应用内「检查更新」** | 已安装用户 | 用户主动点击 |
| **GitHub Releases RSS** | 关注者 | 每次发布 |
| **GitHub Watch → Releases only** | 开发者 | 邮件通知 |

### 6.2 应用内「检查更新」实现

```python
# src/core/updater.py
import urllib.request
import json
from packaging import version

GITHUB_API = "https://api.github.com/repos/raymondyan-zhijie/Lei_MD/releases/latest"
CURRENT = "1.0.0"

def check_update() -> dict | None:
    """返回新版本信息，或 None 表示无更新。"""
    try:
        with urllib.request.urlopen(GITHUB_API, timeout=5) as resp:
            data = json.loads(resp.read())
        latest_tag = data["tag_name"].lstrip("v")
        if version.parse(latest_tag) > version.parse(CURRENT):
            return {
                "version": latest_tag,
                "url": data["html_url"],
                "notes": data["body"],
            }
    except Exception as e:
        log_error("E_UPDATE_001", e)  # 不阻塞用户使用
    return None
```

**UI 弹窗**：
```
┌─────────────────────────────┐
│  发现新版本 v1.1.0           │
│                              │
│  [完整更新说明]               │
│                              │
│  [访问下载]  [稍后]  [忽略]   │
└─────────────────────────────┘
```

### 6.3 不做自动更新（**故意**）

- 离线产品哲学：用户掌控升级时机
- 避免后台偷偷下载大文件
- NSIS 安装包要求用户明确操作

---

## 7. 失败恢复

### 7.1 用户更新失败

| 场景 | 行为 | 错误码 |
|------|------|--------|
| 无网络 | "检查更新失败，请稍后重试" | `E_UPDATE_001` |
| GitHub API 限流 | "服务繁忙，请稍后重试" | `E_UPDATE_002` |
| 下载中断 | 显示已下载百分比 + 断点续传按钮 | `E_UPDATE_003` |
| Checksum 不匹配 | 拒绝安装，提示重新下载 | `E_UPDATE_004` |
| 磁盘满 | 提示清理磁盘 | `E_UPDATE_005` |
| 旧版→新版不兼容 schema | NSIS 卸载旧版 + 安装新版（**不迁移配置**） | (NSIS 处理) |

### 7.2 应用内 SQLite 损坏
启动时检测 → 备份 `.bak` → 重建（详见 [02-architecture.md §6.4](02-architecture.md)）

### 7.3 应用内 config 损坏
启动时检测 → 备份 `.bak` → 重置默认（同上 [02 §6.4](02-architecture.md)）

### 7.4 更新到一半断电

NSIS 安装器**原子性**保证：
- 安装脚本执行要么全成要么全败
- 不存在"装了一半"的状态

---

## 8. 监控与告警（v1.1+ 路线图）

| 指标 | 来源 | 告警 |
|------|------|------|
| Crash rate | Sentry / 自建 crash 报告 | >1% 触发告警 |
| 更新失败率 | 应用内 `E_UPDATE_*` 上报 | >5% 触发告警 |
| MarkItDown 上游 release | GitHub Watch | 收到通知后人工评估 |

**v1.0 不上监控**——日活不到阈值无意义。

---

## 9. 长期路线图（更新视角）

```
v1.0.0  2026 Q3   MVP 首发，无更新机制（手动下载）
v1.1.0  2026 Q4   加入「检查更新」+ markitdown 0.1.x 自动跟随
v1.2.0  2027 Q1   WinGet/Scoop 分发 + 自动更新（可选）
v2.0.0  2027 Q4   跨平台（macOS/Linux）+ 平台特定打包
```

---

## 10. 参考

- [Dependabot 配置文档](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file)
- [Semantic Versioning 2.0.0](https://semver.org/)
- [PyInstaller + NSIS 打包实践](https://nsis.sourceforge.io/Download)
- [Microsoft MarkItDown releases](https://github.com/microsoft/markitdown/releases)
