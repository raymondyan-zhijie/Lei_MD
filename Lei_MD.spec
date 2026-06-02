# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Lei_MD.

Build a single-file Windows executable that bundles:
- src/ package (Python source)
- src/resources/ (locale JSON, icons)
- PySide6 Qt runtime
- markitdown[all] + transitive deps (pdf, docx, xlsx, pptx, image, ...)

Output: dist/Lei_MD-0.4.1.exe (~30-60 MB onefile)

Build:
    pyinstaller Lei_MD.spec
or
    pwsh scripts/build-windows.ps1  # recommended (handles venv + cleanup)

For the v0.4.1 release, the executable is uploaded to:
    https://github.com/raymondyan-zhijie/Lei_MD/releases/tag/v0.4.1
"""

from pathlib import Path
import sys

# ──────────────────────────────────────────────────────────────────────
# Project metadata (kept in sync with pyproject.toml + src/__init__.py)
# ──────────────────────────────────────────────────────────────────────
APP_NAME = "Lei_MD"
APP_VERSION = "0.4.1"
ENTRY = "src/main.py"
ICON = "src/resources/icons/app.ico"  # see "Icon note" below

# Icon note: v0.4.1 ships without an .ico; PyInstaller will fall back to
# the system default exe icon. To add a custom icon:
#   1. Drop a 256x256 .ico at src/resources/icons/app.ico
#   2. Uncomment the `icon=` line in the EXE() block below
#   3. Add `('src/resources/icons/app.ico', 'resources/icons')` to datas

# ──────────────────────────────────────────────────────────────────────
# Hidden imports (modules PyInstaller can't auto-detect)
# ──────────────────────────────────────────────────────────────────────
hiddenimports = [
    # MarkItDown: dynamic converter registration via entry_points.
    # PyInstaller's static analysis misses these — list the main ones.
    "markitdown",
    "markitdown.converters",
    "markitdown.converters._pdf_converter",          # pdfminer-backed
    "markitdown.converters._docx_converter",         # mammoth-backed
    "markitdown.converters._xlsx_converter",         # openpyxl-backed
    "markitdown.converters._pptx_converter",         # python-pptx-backed
    "markitdown.converters._html_converter",         # bs4-backed
    "markitdown.converters._image_converter",        # PIL-backed
    "markitdown.converters._audio_converter",        # pydub-backed (optional, but
                                                     # markitdown[all] pulls it in)
    "markitdown.converters._epub_converter",
    "markitdown.converters._outlook_converter",
    "markitdown.converters._zip_converter",
    # youtube-dl / yt-dlp backend for src/core/youtube.py
    "yt_dlp",
    "yt_dlp.extractor",
    # PySide6 plugins that are dynamically loaded
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtXml",
    "PySide6.QtNetwork",
    "PySide6.QtPrintSupport",
    # darkdetect fallback (theme detection)
    "darkdetect",
]

# ──────────────────────────────────────────────────────────────────────
# Data files bundled into the exe (accessed via sys._MEIPASS at runtime)
# ──────────────────────────────────────────────────────────────────────
datas = [
    # (source, dest-dir-in-bundle)
    ("src/resources/locales", "resources/locales"),
    ("src/resources/icons",   "resources/icons"),
    # README / LICENSE displayed in About box (optional)
    # ("README.md",    "."),
    # ("LICENSE",      "."),
]

# ──────────────────────────────────────────────────────────────────────
# Excluded modules (slim down the bundle; reduce false positives)
# ──────────────────────────────────────────────────────────────────────
excludes = [
    "tkinter",        # we use PySide6, not tk
    "matplotlib",     # not used
    "numpy.tests",
    "pandas.tests",
    "scipy",
    "pytest",
    "pytestqt",
    # Trim some large unused stdlib bits
    "xml.dom.minidom",
    "unittest",
    "pydoc",
]

# ──────────────────────────────────────────────────────────────────────
# Build the Analysis
# ──────────────────────────────────────────────────────────────────────
a = Analysis(
    [ENTRY],
    pathex=[str(Path(".").resolve())],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    # No `win_no_prefer_redirects` / `win_private_assemblies` here —
    # PyInstaller 6.x defaults are correct for PySide6.
    noarchive=False,
)

pyz = PYZ(a.pure)

# ──────────────────────────────────────────────────────────────────────
# Single-file EXE
# ──────────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f"{APP_NAME}-{APP_VERSION}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,            # compress with UPX if available (saves ~10 MB)
    upx_exclude=[],
    runtime_tmpdir=None, # default = user's %APPDATA% (recommended)
    console=False,       # GUI app, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,    # current arch (x86_64 for windows-latest)
    codesign_identity=None,        # v0.4.x: no signing (SmartScreen will warn)
    entitlements_file=None,
    # icon=ICON,  # uncomment when app.ico exists
)

# Note: OneDir vs OneFile
# - We use OneFile (above) for v0.4.1 because the user wants a single
#   ``Lei_MD-0.4.1.exe`` they can copy to any Windows machine.
# - For a faster startup, switch to COLLECT() + EXE() (OneDir) — the
#   build script `scripts/build-windows.ps1` supports both via a flag.
