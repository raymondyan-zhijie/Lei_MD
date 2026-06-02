# 07 - Build & Release Guide

> 🌐 **Language**: [中文](07-build-release.md) | **English**

Complete guide to building Lei_MD as a Windows executable (and optional NSIS installer).

---

## 0. What you're doing

Lei_MD is a Python + PySide6 desktop app. End users don't want to install Python, set up venv, manage deps — they want to **double-click a .exe**. So we build:

```
Python source → PyInstaller → Lei_MD-0.4.1.exe (onefile, ~40 MB)
                                ↓
                              NSIS  (optional)
                                ↓
                       Lei_MD-0.4.1-Setup.exe (installer wizard, ~30 MB)
```

**What users get is the `.exe` (double-click to run) or `Setup.exe` (double-click to install into Program Files).**

---

## 1. Prerequisites (Windows 11 machine)

| Tool | Purpose | Verify |
|---|---|---|
| **Windows 10/11** | OS | — |
| **Python 3.10-3.13** | build | `python --version` |
| **Git** | clone source | `git --version` |
| **NSIS 3.x** *(optional)* | build installer | `makensis --version` |
| **UPX** *(optional)* | compress .exe | `upx --version` (PyInstaller auto-detects) |
| **7-Zip** *(optional)* | inspect artifacts | 7z |

**You don't need**: Visual Studio, MSVC, Qt SDK — PyInstaller 6.x ships with PySide6 wheels.

### Install Python (if you don't have it)
1. https://www.python.org/downloads/windows/
2. **Important**: check "Add Python to PATH"
3. Pick 3.10 / 3.11 / 3.12 / 3.13 (v0.4.1's matrix tested all 4)

### Install NSIS (optional, only for Setup.exe)
1. https://nsis.sourceforge.io/Download
2. Install to `C:\Program Files (x86)\NSIS\`
3. `makensis` will be auto-added to PATH

---

## 2. Build in one command

```powershell
# In PowerShell
cd C:\path\to\Lei_MD   # repo root
git checkout v0.4.1
pwsh scripts/build-windows.ps1
```

**Output**:
```
==> Build complete!
    Executable:   C:\path\to\Lei_MD\dist\Lei_MD-0.4.1.exe
```

With NSIS installer:
```powershell
pwsh scripts/build-windows.ps1 -WithInstaller
```

Produces `installer\Lei_MD-0.4.1-Setup.exe` (additional artifact).

**Time**:
- First run: 5-10 minutes (creates venv, installs pyinstaller, pulls markitdown[all] wheels)
- Subsequent (incremental): 1-3 minutes

**Artifact size** (onefile mode):
- `Lei_MD-0.4.1.exe` ~40 MB (PySide6 6.9 + markitdown[all] is the heavy part)
- `Lei_MD-0.4.1-Setup.exe` ~30 MB (NSIS itself ~1 MB, exe same as above)

---

## 3. Manual build (step-by-step)

```powershell
# 1. Create build venv
python -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1

# 2. Install dependencies
pip install -U pip
pip install -e ".[dev]"
pip install pyinstaller

# 3. Run PyInstaller (spec is at repo root)
pyinstaller Lei_MD.spec

# 4. Output: dist\Lei_MD-0.4.1.exe
```

---

## 4. Upload to GitHub Release

### Option A: Drag-and-drop in browser (easiest)

1. Open https://github.com/raymondyan-zhijie/Lei_MD/releases/tag/v0.4.1
2. Click **Edit release**
3. Drag `Lei_MD-0.4.1.exe` (and optional `Setup.exe`) into the **Attach binaries** area
4. Click **Update release**

### Option B: `gh` CLI (if you have GitHub CLI)

```powershell
gh release upload v0.4.1 `
  dist\Lei_MD-0.4.1.exe `
  installer\Lei_MD-0.4.1-Setup.exe `
  --clobber
```

### Option C: Let Hermes upload

Send `dist\Lei_MD-0.4.1.exe` to Hermes (WeChat / filebrowser / Telegram), and Hermes will POST it to GitHub's `upload_url` endpoint.

---

## 5. Troubleshooting

### 5.1 `ModuleNotFoundError: No module named 'markitdown'`

PyInstaller's `Analysis` missed `markitdown`. Reason: markitdown dynamically registers converters via `entry_points`, so static analysis doesn't see them.

**Fix**: add to `Lei_MD.spec`'s `hiddenimports`:
```python
"markitdown.converters._pdf_converter",
"markitdown.converters._docx_converter",
# ... etc
```
(spec already lists all of them; if you still see a missing one, add it by name from the error.)

### 5.2 Runtime `FileNotFoundError: resources/locales/zh_CN.json`

PyInstaller bundled the resources but the runtime can't find the path.

**Fix**: spec's `datas` must be correct:
```python
datas = [("src/resources/locales", "resources/locales")]
```

And the code should resolve via `sys._MEIPASS`:
```python
import sys
from pathlib import Path
resource_dir = Path(sys._MEIPASS) / "resources"  # frozen mode
if not hasattr(sys, "_MEIPASS"):
    resource_dir = Path(__file__).parent.parent / "src" / "resources"
```

**v0.4.1 check**: `src/ui/i18n.py`'s `_LOCALES_DIR` does the dual-mode resolution (added in v0.4.1).

### 5.3 "Failed to load Qt platform plugin windows" on launch

PySide6 missing a plugin.

**Fix**: spec's `hiddenimports` includes:
```python
"PySide6.QtSvg",
"PySide6.QtSvgWidgets",
"PySide6.QtXml",
"PySide6.QtNetwork",
"PySide6.QtPrintSupport",
```
(spec has these.)

### 5.4 "Microsoft Defender SmartScreen blocked an unrecognized app"

PyInstaller exe is **unsigned**, so SmartScreen warns by default.

**v0.4.x**: accept the warning; tell users "More info → Run anyway".

**Future v1.0+**: consider
- SignPath Foundation's free OSS code signing certificate
- Or buy Sectigo / DigiCert (~$70-200/year)
- CI auto-sign + submit SmartScreen reputation

### 5.5 exe takes 5-10s to show window

Onefile mode: extracts to `%APPDATA%` then runs.

**Optimization**: switch to OneDir (spec uses `COLLECT()` + `EXE()`), startup < 1s, but users get a folder.

**v0.4.1 current**: Onefile (single file = easier distribution).

### 5.6 markitdown[all] won't install

Some optional deps (like `pydub` needs ffmpeg) can fail.

**Workaround**: `pip install markitdown[all] --no-deps` then install the working subset manually.

### 5.7 NSIS says "License file not found: LICENSE"

v0.4.1 repo doesn't have a `LICENSE` file.

**Fix**: first `git add LICENSE` (MIT content), or comment out `!insertmacro MUI_PAGE_LICENSE "LICENSE"` in `installer.nsi`.

---

## 6. Post-upload verification

On a separate Windows machine (or sandbox):
```powershell
Invoke-WebRequest `
  -Uri "https://github.com/raymondyan-zhijie/Lei_MD/releases/download/v0.4.1/Lei_MD-0.4.1.exe" `
  -OutFile "Lei_MD.exe"

.\Lei_MD.exe
# 1. Program should launch
# 2. Drag a PDF in → should convert to markdown
# 3. About box should show "0.4.1"
# 4. Close → reopen → history should be preserved
```

---

## 7. CI auto-build (enabled in v0.4.5+)

`.github/workflows/build.yml` (enabled v0.4.5):

**Triggers**:
| Trigger | Behavior |
|---|---|
| Push `v*` tag | Auto-build → attach artifact to matching GitHub Release |
| `workflow_dispatch` (manual) | Build + Actions UI can opt into NSIS |
| Weekly Sunday 02:00 UTC | dry-run (catches spec/dep rot, zero-cost) |

**Jobs** (1 windows job):
- `build-windows` — windows-latest × py3.12 (PyInstaller + PySide6 6.7-6.10 stable line)
- Steps: checkout → setup-python → [optional] `choco install nsis` → `pwsh scripts/build-windows.ps1` → `actions/upload-artifact@v4` → [tag only] `gh release upload`

**Usage**:
```powershell
# Trigger from GitHub Actions UI
gh workflow run build.yml -f with_installer=false
# Or with NSIS:
gh workflow run build.yml -f with_installer=true
```

**Artifacts**:
- Every run produces `lei-md-windows-3.12` artifact (dist/*.exe + installer/*.exe), retained 14 days
- On tag push the .exe is **auto-attached** to the matching GitHub Release

**Duration**:
- First run: ~8-12 minutes (windows-latest cold start + venv deps + PyInstaller onefile)
- Subsequent: ~5-8 minutes (pip cache hits)

**Known pitfalls** (v0.4.5 in-the-wild):
- PowerShell 7 strict mode fails to parse `$AppVersion:` (colon) — must wrap in `${AppVersion}` (build-windows.ps1 L188/189)
- NSIS installer job requires explicit `choco install nsis` (windows-latest runner has no makensis by default)

**v0.4.5+ status**: ✅ enabled. Pushing a `v*` tag auto-builds + attaches the .exe to the release. Day-to-day PR/merge runs only `test.yml`, no impact on build minutes.

---

## 8. References

- PyInstaller 6.x docs: https://pyinstaller.org/en/v6.6.0/
- NSIS docs: https://nsis.sourceforge.io/Docs/
- MarkItDown: https://github.com/microsoft/markitdown
- Lei_MD: https://github.com/raymondyan-zhijie/Lei_MD

---

**Updated for v0.4.1** (2026-06-02)
