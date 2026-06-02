# 07 - Build & Release Guide

> 🌐 **Language**: **中文** | [English](07-build-release.en.md)

把 Lei_MD 打成 Windows 可执行文件（和 NSIS 安装包）的完整指南。

---

## 0. 你在做什么

Lei_MD 是一个 Python + PySide6 桌面应用。普通用户**不**想装 Python、装依赖、配 venv——他们想要**双击 .exe**。所以我们要：

```
Python source → PyInstaller → Lei_MD-0.4.7.exe (onefile, ~139 MB)
                                ↓
                              NSIS  (可选)
                                ↓
                       Lei_MD-0.4.7-Setup.exe (安装向导, ~150 MB)
```

**用户拿到的就是 `.exe`（双击跑）或 `Setup.exe`（双击安装到 Program Files）**。

---

## 1. 前置条件（Windows 11 机器）

| 工具 | 用途 | 验证 |
|---|---|---|
| **Windows 10/11** | OS | — |
| **Python 3.10-3.13** | build | `python --version` |
| **Git** | 拉源码 | `git --version` |
| **NSIS 3.x** *(可选)* | 打安装包 | `makensis --version` |
| **UPX** *(可选)* | 压缩 .exe | `upx --version`（PyInstaller 自动检测）|
| **7-Zip** *(可选)* | 看产物 | 7z |

**不需要**：Visual Studio、MSVC、Qt SDK——PyInstaller 6.x 自带 PySide6 wheels。

### 安装 Python（如果还没）
1. https://www.python.org/downloads/windows/
2. **关键**：勾选 "Add Python to PATH"
3. 选 3.10 / 3.11 / 3.12 / 3.13 之一（v0.4.1 矩阵 4 个都过）

### 安装 NSIS（可选，要做 Setup.exe 的话）
1. https://nsis.sourceforge.io/Download
2. 装到 `C:\Program Files (x86)\NSIS\`
3. `makensis` 自动在 PATH 里

---

## 2. 一行命令 build

```powershell
# 在 PowerShell 里
cd C:\path\to\Lei_MD   # 仓库根目录
git checkout v0.4.1
pwsh scripts/build-windows.ps1
```

**跑完**会输出：
```
==> Build complete!
    Executable:   C:\path\to\Lei_MD\dist\Lei_MD-0.4.1.exe
```

带 NSIS 安装包：
```powershell
pwsh scripts/build-windows.ps1 -WithInstaller
```

跑出来 `installer\Lei_MD-0.4.1-Setup.exe`（额外产物）。

**耗时**：
- 首次：5-10 分钟（装 venv + pip install pyinstaller + markitdown 拉一堆 wheels）
- 之后（incremental）：1-3 分钟

**产物大小**（onefile 模式）：
- `Lei_MD-0.4.1.exe` ~40 MB（PySide6 6.9 + markitdown[all] = 重量大头）
- `Lei_MD-0.4.1-Setup.exe` ~30 MB（NSIS 自身 ~1 MB，exe 同上）

---

## 3. 手工 build（如果你想拆开看每步）

```powershell
# 1. 建 build venv
python -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1

# 2. 装依赖
pip install -U pip
pip install -e ".[dev]"
pip install pyinstaller

# 3. 跑 PyInstaller（spec 在仓库根）
pyinstaller Lei_MD.spec

# 4. 产 dist\Lei_MD-0.4.1.exe
```

---

## 4. 怎么上传到 GitHub Release

### 选项 A: 浏览器拖拽（最简单）

1. 打开 https://github.com/raymondyan-zhijie/Lei_MD/releases/tag/v0.4.1
2. 点 **Edit release**
3. **Attach binaries** 区拖入 `Lei_MD-0.4.1.exe`（和可选 `Setup.exe`）
4. 点 **Update release**

### 选项 B: `gh` CLI（如果你装了 GitHub CLI）

```powershell
gh release upload v0.4.1 `
  dist\Lei_MD-0.4.1.exe `
  installer\Lei_MD-0.4.1-Setup.exe `
  --clobber
```

### 选项 C: 让 Hermes 帮你传

把 `dist\Lei_MD-0.4.1.exe` 传给 Hermes（微信 / filebrowser / Telegram），Hermes 用 GitHub API 上传到 release 的 `upload_url` 端点。

---

## 5. 故障排查

### 5.1 `ModuleNotFoundError: No module named 'markitdown'`

PyInstaller 的 `Analysis` 漏了 `markitdown`。原因：markitdown 用 `entry_points` 动态注册 converter，static analysis 看不到。

**修法**：`Lei_MD.spec` 的 `hiddenimports` 加：
```python
"markitdown.converters._pdf_converter",
"markitdown.converters._docx_converter",
# ... 等等
```
（spec 里已经全列了；如果还报，照报错名加。）

### 5.2 运行时 `FileNotFoundError: resources/locales/zh_CN.json`

PyInstaller 打了 resources 但运行时找不到路径。

**修法**：spec 里的 `datas` 要写对：
```python
datas = [("src/resources/locales", "resources/locales")]
```
然后代码读：
```python
import sys
from pathlib import Path
resource_dir = Path(sys._MEIPASS) / "resources"  # frozen 模式
# 或开发模式：
if not hasattr(sys, "_MEIPASS"):
    resource_dir = Path(__file__).parent.parent / "src" / "resources"
```

**v0.4.1 检查清单**：`src/ui/i18n.py` 的 `_LOCALES_DIR` 是不是用 `sys._MEIPASS` 解析的？

### 5.3 启动后弹 "Failed to load Qt platform plugin windows"

PySide6 缺 plugin。

**修法**：spec 的 `hiddenimports` 加：
```python
"PySide6.QtSvg",
"PySide6.QtSvgWidgets",
"PySide6.QtXml",
"PySide6.QtNetwork",
"PySide6.QtPrintSupport",
```
（spec 已加。）

### 5.4 报 "Microsoft Defender SmartScreen 阻止了未知应用启动"

PyInstaller exe **未签名**，SmartScreen 默认警告。

**当前 v0.4.x**：接受这个警告，给用户说明"更多信息 → 仍要运行"。

**未来 v1.0+**：考虑
- 申请 SignPath 基金会的免费 OSS 代码签名证书
- 或购买 Sectigo / DigiCert 证书（~$70-200/年）
- CI 自动 sign + 提交 SmartScreen 信誉

### 5.5 exe 启动 5-10 秒才出窗口

Onefile 模式特性：解压到 `%APPDATA%` 再跑。

**优化**：改成 OneDir 模式（spec 切到 `COLLECT()` + `EXE()`），启动 < 1 秒，但用户拿到的是文件夹。

**当前 v0.4.1**：Onefile（单文件方便分发）。

### 5.6 markitdown[all] 装不上

某些 optional 依赖（如 `pydub` 需要 ffmpeg）可能装失败。

**workaround**：先 `pip install markitdown[all] --no-deps`，再手动装跑得起来的子集。

### 5.7 NSIS 报 "License file not found: LICENSE"

v0.4.1 仓库没有 `LICENSE` 文件。

**修法**：先 `git add LICENSE`（MIT 内容），或在 `installer.nsi` 里把 `!insertmacro MUI_PAGE_LICENSE "LICENSE"` 注释掉。

---

## 6. 上传后怎么验证 release

```powershell
# 在另一台 Windows 机器（或 sandbox）
Invoke-WebRequest `
  -Uri "https://github.com/raymondyan-zhijie/Lei_MD/releases/download/v0.4.1/Lei_MD-0.4.1.exe" `
  -OutFile "Lei_MD.exe"

.\Lei_MD.exe
# 1. 程序应该弹出
# 2. 拖一个 PDF 进去 → 应该转 markdown
# 3. About box 应该显示版本 "0.4.1"
# 4. 关闭 → 重新打开 → history 应该保留
```

---

## 7. CI 自动 build（v0.4.5+ 已上线）

`.github/workflows/build.yml`（v0.4.5 启用）：

**触发条件**：
| 触发器 | 行为 |
|---|---|
| 推送 `v*` tag | 自动跑 → 产物上传到对应 GitHub Release |
| `workflow_dispatch`（手动）| 跑 + 在 Actions UI 可选 NSIS |
| 每周日 02:00 UTC | dry-run（catch spec/dep rot，零成本） |

**Jobs**（1 个 windows job）：
- `build-windows` — windows-latest × py3.12（PyInstaller + PySide6 6.7-6.10 稳定线）
- 步骤：checkout → setup-python → [可选] `choco install nsis` → `pwsh scripts/build-windows.ps1` → `actions/upload-artifact@v4` → [tag only] `gh release upload`

**用法**：
```powershell
# 在 GitHub Actions UI 手动触发
gh workflow run build.yml -f with_installer=false
# 或带 NSIS：
gh workflow run build.yml -f with_installer=true
```

**产物**：
- 每次 run 产 `lei-md-windows-3.12` artifact（dist/*.exe + installer/*.exe），保留 14 天
- tag push 时**自动 attach** 到对应 GitHub Release

**耗时**：
- 首次：~8-12 分钟（windows-latest runner cold start + venv 装依赖 + PyInstaller onefile）
- 后续：~5-8 分钟（pip cache 命中）

**已知坑**（v0.4.5-v0.4.7 实战）：
- PowerShell 7 strict-mode 解析 `$AppVersion:`（冒号）会失败 — 必须在 `${AppVersion}` 包起来（build-windows.ps1 L188/189）
- NSIS 安装包 job 需要显式 `choco install nsis`（windows-latest runner 默认不带）；choco 装后**不**自动刷新 PowerShell `$env:PATH`，需 `Get-ItemProperty 'HKLM:\SOFTWARE\WOW6432Node\NSIS'` + 手动 prepend `Program Files (x86)\NSIS`（build.yml NSIS step 已加）
- tag push ≠ 创建 release（GitHub Actions 行为）：必须 `Ensure GitHub Release exists` step 用 `gh release view $tag` 预检 + `$LASTEXITCODE` 判断（**不要**用 `Select-String -NotMatch 'already exists'` 字符串过滤 — HTTP 422 错误信息不含这串文字，会 fail）
- PyInstaller spec `excludes` **禁忌**：不列 stdlib 子模块。defusedxml 链 re-export 8 个 `xml.dom/etree/sax` 子模块，exclude 1 个 → 运行时崩 `ModuleNotFoundError: No module named 'xml.dom.minidom'`，崩溃点远离 exclude 行（main_window → converter → markitdown → _rss_converter → defusedxml.minidom L10）。excludes 只列第三方叶子包（matplotlib/scipy/pytest），不动 stdlib。详细 + 检测脚本：`scripts/audit_excludes.py`（在 windows-desktop-build-pipeline skill）
- PyInstaller spec `__file__` **陷阱**：PyInstaller 6.20+ strict mode 编译 spec 时没有 `__file__` global → NameError。必须用 PyInstaller 注入的 `SPECPATH` 替代

**v0.4.7 E2E 自动化验证**（2026-06-02）：`git tag v0.4.7 && git push origin v0.4.7 --force` → 自动 build #11 (5 min) → Ensure Release step print "already exists — skipping create" → `gh release upload --clobber` → 0 人工。Release v0.4.7 id `333196237` + asset 145.5 MB。

**当前 v0.4.5+ 状态**：✅ 启用。tag 推 v* 自动 build + attach Release；日常 PR/merge 只跑 `test.yml`，不影响 build minutes。

---

## 8. 参考

- PyInstaller 6.x docs: https://pyinstaller.org/en/v6.6.0/
- NSIS docs: https://nsis.sourceforge.io/Docs/
- MarkItDown: https://github.com/microsoft/markitdown
- Lei_MD: https://github.com/raymondyan-zhijie/Lei_MD

---

**更新于 v0.4.7**（2026-06-02）
