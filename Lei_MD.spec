"""PyInstaller spec for Lei_MD.

Build a single-file Windows executable that bundles:
- src/ package (Python source)
- src/resources/ (locale JSON, icons)
- PySide6 Qt runtime
- markitdown[all] + transitive deps (pdf, docx, xlsx, pptx, image, ...)

Output: dist/Lei_MD-<version>.exe (~30-60 MB onefile)

Build:
    pyinstaller Lei_MD.spec
or
    pwsh scripts/build-windows.ps1  # recommended (handles venv + cleanup)
"""

from pathlib import Path

import tomllib

import magika  # v0.4.9: locate the on-disk `magika/models/` directory for datas bundle

# ──────────────────────────────────────────────────────────────────────
# Project metadata — version is read from pyproject.toml (single source
# of truth). The build script does the same so the two stay in lockstep.
# ──────────────────────────────────────────────────────────────────────
APP_NAME = "Lei_MD"
# SPECPATH is a global that PyInstaller injects when executing the spec
# (absolute path to the spec file's directory). It is the only reliable
# location reference inside a spec — `__file__` is NOT defined here
# (PyInstaller 6.20+ strict mode raises NameError on `__file__`).
_PYPROJECT = Path(SPECPATH) / "pyproject.toml"
APP_VERSION = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
ENTRY = "src/main.py"
# ICON is intentionally unset in v0.4.5 — no .ico file ships yet (see
# spec "Icon note" comment below). PyInstaller will fall back to the
# system default exe icon. To add a custom icon:
#   1. Drop a 256x256 .ico at src/resources/icons/app.ico
#   2. Uncomment the `icon=` line in the EXE() block below
#   3. Add `('src/resources/icons', 'resources/icons')` to datas AND
#      create the directory with a .gitkeep so the source path exists.

# ──────────────────────────────────────────────────────────────────────
# Hidden imports (modules PyInstaller can't auto-detect)
# ──────────────────────────────────────────────────────────────────────
hiddenimports = [
    # MarkItDown: dynamic converter registration via entry_points.
    # PyInstaller's static analysis misses these — list every installed
    # converter. Verified against markitdown v0.1.x (the .dist-info on
    # the build venv). Earlier v0.4.3-era spec named `_outlook_converter`
    # (WRONG: it was renamed to `_outlook_msg_converter` in markitdown
    # 0.1+) and `yt_dlp.extractor` (WRONG: markitdown dropped yt-dlp in
    # 0.1+; it now uses `youtube_transcript_api` — see `_youtube_converter`).
    "markitdown",
    "markitdown.converters",
    "markitdown.converters._audio_converter",
    "markitdown.converters._bing_serp_converter",
    "markitdown.converters._csv_converter",
    "markitdown.converters._cu_converter",
    "markitdown.converters._doc_intel_converter",
    "markitdown.converters._docx_converter",
    "markitdown.converters._epub_converter",
    "markitdown.converters._exiftool",
    "markitdown.converters._html_converter",
    "markitdown.converters._image_converter",
    "markitdown.converters._ipynb_converter",
    "markitdown.converters._llm_caption",
    "markitdown.converters._markdownify",
    "markitdown.converters._outlook_msg_converter",
    "markitdown.converters._pdf_converter",
    "markitdown.converters._plain_text_converter",
    "markitdown.converters._pptx_converter",
    "markitdown.converters._rss_converter",
    "markitdown.converters._transcribe_audio",
    "markitdown.converters._wikipedia_converter",
    "markitdown.converters._xlsx_converter",
    "markitdown.converters._youtube_converter",
    "markitdown.converters._zip_converter",
    # YouTube transcript fetcher (replaces the long-removed yt-dlp backend)
    "youtube_transcript_api",
    # PySide6 plugins that are dynamically loaded
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtXml",
    "PySide6.QtNetwork",
    "PySide6.QtPrintSupport",
    # darkdetect fallback (theme detection)
    "darkdetect",
    # v0.4.8: defusedxml submodules — PyInstaller's static analysis does
    # NOT follow the wrapper → stdlib re-export chain in defusedxml
    # submodules, so they can be silently absent from the bundle even
    # though `import defusedxml` works. Listing every submodule ensures
    # each `from xml.dom.X import ...` line at module top of each
    # defusedxml/*.py is satisfied at runtime.
    "defusedxml",
    "defusedxml.minidom",
    "defusedxml.ElementTree",
    "defusedxml.sax",
    "defusedxml.pulldom",
    "defusedxml.expatbuilder",
    "defusedxml.expatreader",
    "defusedxml.common",
    "defusedxml.xmlrpc",
    "defusedxml.cElementTree",
]

# ──────────────────────────────────────────────────────────────────────
# Data files bundled into the exe (accessed via sys._MEIPASS at runtime)
# ──────────────────────────────────────────────────────────────────────
datas = [
    # (source, dest-dir-in-bundle)
    ("src/resources/locales", "resources/locales"),
    # v0.4.9: magika ships its ML model directory at
    # `<site-packages>/magika/models/standard_v3_3/` (~3.2 MB). PyInstaller's
    # hook for magika does NOT bundle this directory — at runtime magika
    # raises `MagikaError: model dir not found at
    # <sys._MEIPASS>/magika/models/standard_v3_3` the first time it
    # initialises (i.e. on the first file conversion). Markitdown's
    # _pdf_converter / _docx_converter / _pptx_converter / _xlsx_converter
    # all import magika for content-type detection, so EVERY conversion
    # fails. Pin the path explicitly via `Path(magika.__file__).parent`
    # so the spec stays correct across dev-venv and CI locations.
    (
        str(Path(magika.__file__).parent / "models"),
        "magika/models",
    ),
    # NOTE: src/resources/icons intentionally NOT bundled yet — no
    # .ico file ships in v0.4.5. See ICON comment above for the steps
    # to enable it (and remember to create the dir + .gitkeep first).
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
    # NOTE: do NOT exclude `xml.dom.minidom` or `xml.etree.*` — the
    # defusedxml package re-exports from these stdlib modules at
    # runtime (e.g. `defusedxml.minidom` does `from xml.dom.minidom
    # import *`). Markitdown's `_rss_converter` and `_html_converter`
    # import defusedxml, so excluding the stdlib aliases would crash
    # the bundled exe with `ModuleNotFoundError: No module named
    # 'xml.dom.minidom'`. Defusedxml exists specifically to wrap
    # these (with XXE protection), so we want them present.
    # Same logic applies to `unittest` (used by test discovery hooks
    # in some libs) and `pydoc` (used by IDE integrations). Stdlib
    # submodules are NOT safe to exclude. See skill
    # `windows-desktop-build-pipeline`/references/pyinstaller-spec-pitfalls.md
    # §11 for the full rule + detection script.
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
    codesign_identity=None,        # no signing in v0.4.x (SmartScreen will warn)
    entitlements_file=None,
    # icon=ICON,  # uncomment when app.ico exists
)

# Note: OneDir vs OneFile
# - We use OneFile (above) because the user wants a single
#   ``Lei_MD-<version>.exe`` they can copy to any Windows machine.
# - For a faster startup, switch to COLLECT() + EXE() (OneDir) — the
#   build script `scripts/build-windows.ps1` supports both via a flag.
