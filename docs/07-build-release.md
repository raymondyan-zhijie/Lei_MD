# 07 - Build & Release Guide

> 🌐 **Language**: **中文** | [English](07-build-release.en.md)

把 Lei_MD 打成 Windows 可执行文件（和 NSIS 安装包）的完整指南。

---

## 0. 你在做什么

Lei_MD 是一个 Python + PySide6 桌面应用。普通用户**不**想装 Python、装依赖、配 venv——他们想要**双击 .exe**。所以我们要：

```
Python source → PyInstaller → Lei_MD-0.4.1.exe (onefile, ~40 MB)
                                ↓
                              NSIS  (可选)
                                ↓
                       Lei_MD-0.4.1-Setup.exe (安装向导, ~30 MB)
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

## 7. 进阶：CI 自动 build

`.github/workflows/build-windows.yml`（**v0.5.0 计划**）：

```yaml
name: build-windows
on:
  push:
    tags: ['v*.*.*']
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install pyinstaller
      - run: pyinstaller Lei_MD.spec
      - uses: actions/upload-artifact@v4
        with:
          name: Lei_MD-windows
          path: dist/Lei_MD-${{ github.ref_name }}.exe
      - uses: softprops/action-gh-release@v2  # 自动 attach 到 release
        with:
          files: dist/Lei_MD-${{ github.ref_name }}.exe
```

**当前 v0.4.1 状态**：手动 build。CI build 是 v0.5.0 任务（避免吃 Actions minutes）。

---

## 8. 参考

- PyInstaller 6.x docs: https://pyinstaller.org/en/v6.6.0/
- NSIS docs: https://nsis.sourceforge.io/Docs/
- MarkItDown: https://github.com/microsoft/markitdown
- Lei_MD: https://github.com/raymondyan-zhijie/Lei_MD

---

**更新于 v0.4.1**（2026-06-02）
