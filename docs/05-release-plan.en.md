# Lei_MD Release & Maintenance Plan

> 🌐 **Language**: [中文](05-release-plan.md) | **English**

> **Brand:** leimengde
> **Version:** Planning snapshot (see [CHANGELOG](../../CHANGELOG.md) for actual releases) | **Date:** 2026-06-01
>
> v0.4.0 has been released (pip + GitHub Release). The actual release flow is in [IMPLEMENTATION_VS_PLAN.md](IMPLEMENTATION_VS_PLAN.md).

> **SSOT index**: This document is the **authoritative definition** of:
> - §1 Version strategy & milestones
> - §3 Deliverable forms (NSIS installer size, download channels)
>
> Upstream dependency update flow: see [06-dependency-update-strategy.md](06-dependency-update-strategy.md).

---

## 1. Version Strategy

Adopt **SemVer (MAJOR.MINOR.PATCH)**:

| Version | Change type | Examples |
|--------|----------|------|
| MAJOR (X.0.0) | Incompatible API change | UI rewrite, incompatible file format |
| MINOR (0.X.0) | Backward-compatible new feature | New format support, new panel |
| PATCH (0.0.X) | Backward-compatible bug fix | Bug fix, performance optimization |

### Milestones

> **Total time estimate** (MVP): 4-6 weeks (conservative, see [03-development-plan.md](03-development-plan.md))

```
0.1.0  ← MVP: drag-convert + preview + export                          (Released, see CHANGELOG)
0.2.0  ← Enhanced: settings / batch / LLM / dark / Chinese / history / YouTube  (Released, see CHANGELOG)
0.3.0  ← Audit / P0-P3 hotfix / 6-dim review / docs cleanup              (Released, 157/157 green, 2026-06-02)
0.4.0  ← CI workflow (8 matrix) + YouTube URL + audio E_FILE_006 explicit rejection (Released, 205/205 green, 2026-06-02)
1.0.0  ← Formal: packaging / NSIS installer / user docs / first stable release (Planned)
1.x.0  ← Continuous iteration                                            (Monthly)
```

> **Version-to-implementation mapping**: see [CHANGELOG.md](../../CHANGELOG.md) and [IMPLEMENTATION_VS_PLAN.md](IMPLEMENTATION_VS_PLAN.md).

## 2. Release Process

### 2.1 Pre-release checklist

```markdown
- [ ] All P0/P1 tests pass
- [ ] ruff lint has zero errors
- [ ] On a clean Windows 10/11 VM, verify .exe runs (planned for v1.0)
- [ ] NSIS installer installs / uninstalls normally (planned for v1.0)
- [ ] README.md updated to the latest version
- [ ] CHANGELOG.md records all changes
- [ ] Git tag has the corresponding version
```

### 2.2 Release steps (v0.4.0 actual flow)

```bash
# 1. Update version number
# Edit pyproject.toml: version = "X.Y.Z"

# 2. Commit and tag
git add pyproject.toml CHANGELOG.md
git commit -m "release: v0.X.Y"
git tag -a v0.X.Y -m "v0.X.Y: <summary>"

# 3. Push (with tag)
git push origin main --follow-tags

# 4. GitHub Release: create via API
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     https://api.github.com/repos/raymondyan-zhijie/Lei_MD/releases \
     -d @release.json   # body: tag_name, name, body (markdown)
```

### 2.3 Automated release pipeline (planned for v1.0)

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

## 3. Deliverables

### 3.1 Three delivery forms (**comprehensive offline**)

| Form | Target user | Size (estimate) |
|------|----------|------------|
| **NSIS standard installer** | Regular users, enterprise deployment | 400-500MB (includes all 20+ format deps) |
| **Portable zip** | Power users, U-disk carry | Same as above, unzip-and-use |
| **pip package** | Developer self-use | Source only + dependency declaration |

> **v1.0 will not provide format-split installers** (MarkItDown upstream is not modular; format-on-demand requires forking upstream, listed in v2.0+ roadmap)

### 3.2 Download channels

| Channel | Description |
|------|------|
| **GitHub Releases** | Main channel, auto-publish (`https://github.com/raymondyan-zhijie/Lei_MD/releases`) |
| **In-app "Check for Updates"** | On launch, calls `https://api.github.com/repos/raymondyan-zhijie/Lei_MD/releases/latest` to prompt the user |
| **Official site** (future) | `lei-md.leimengde.net` |
| **WinGet** (future) | `winget install leimengde.Lei_MD` |
| **Scoop** (future) | `scoop install lei-md` |

> v0.4.0 actual state: only GitHub Releases is live (`https://github.com/raymondyan-zhijie/Lei_MD/releases/tag/v0.4.0` is the latest). pip install is via `pip install lei-md==0.4.0` (no PyPI publication yet, only git+https install).

## 4. User Documentation

### 4.1 README.md structure

```markdown
# Lei_MD

> 🪟 Windows desktop file-to-Markdown tool — based on Microsoft MarkItDown, **all-in-one + offline + traditional install**

## Quick Start
Download Setup.exe → install → drop a file → get Markdown

## Features
- 🖱 Drag-and-drop conversion: supports PDF / Word / Excel / PPT / HTML / EPUB / images / CSV / JSON / XML / ZIP
- 📁 Directory drag-and-drop: auto-recursively expand all supported files
- 👁 Live preview: Markdown rendering view (tables, code blocks, images)
- 📋 One-click copy to clipboard / export .md file
- 🎨 Dark mode
- 🌏 Chinese & English UI
- 🔒 Fully offline, no network, no data upload

## Unsupported formats (v1.0)
- Audio (MP3 / WAV / OGG / FLAC) — see [01-requirements.md F9a](01-requirements.md)

## Installation
1. Download `Lei_MD-Setup-x.x.x.exe`
2. Double-click to install (NSIS wizard)
3. Start using

## Development
See `docs/` directory (6 planning docs)

## Feedback
- Issues: https://github.com/raymondyan-zhijie/Lei_MD/issues
- Email: contact leimengde
```

### 4.2 User Manual

```markdown
# Lei_MD User Manual

## Basic operation
1. Open Lei_MD
2. Drag a file into the window (or click to select / drop a folder)
3. Click "Start Convert"
4. Preview the Markdown result
5. Click "Export .md" to save the file

## Batch conversion
Drop multiple files or a folder, click "Start Convert" for batch processing.
Folders auto-recurse to expand all supported formats.
A progress bar shows during conversion; each file previews as soon as it finishes.

## Error handling
All errors display an **error code** (e.g. `E_FILE_001`).
Detailed info is visible on hover; full traceback is in `%APPDATA%\Lei_MD\logs\`.
Search error codes in GitHub Issues when you hit problems.

## Setting up LLM image description (v1.0.0+)
Go to "Settings" → fill in the OpenAI-compatible API Key → select model.
When converting PPT and images, LLM is auto-called to generate description text.
(The API Key is stored at `%APPDATA%\Lei_MD\config.json`, no network transmission)

## Shortcuts
| Shortcut | Function |
|--------|------|
| Ctrl+O | Select files |
| Ctrl+C | Copy Markdown |
| Ctrl+S | Export .md |
| Ctrl+Q | Quit |

## Data storage location
- Config: `%APPDATA%\Lei_MD\config.json`
- History: `%APPDATA%\Lei_MD\history.db`
- Logs: `%APPDATA%\Lei_MD\logs\`
- Backup: `%APPDATA%\Lei_MD\*.bak` (auto-generated, for corruption recovery)
```

## 5. Maintenance Plan

### 5.1 Upstream dependency updates

> The full upstream update strategy (markitdown / PySide6 / underlying libs / SemVer / failure recovery) is in [docs/06-dependency-update-strategy.md](06-dependency-update-strategy.md). This section is a quick-reference summary.

| Dependency | Check frequency | Strategy | Details |
|------|----------|------|------|
| markitdown | Weekly | Dependabot PR | 06 §3 |
| PySide6 | Monthly | Manual evaluation | 06 §4.1 |
| Python | Quarterly | New version CI matrix | 06 §4 |
| Underlying libs (PyMuPDF/python-docx etc.) | Weekly | Dependabot `group` | 06 §4.2 |

### 5.2 Routine maintenance tasks

| Task | Frequency | Owner |
|------|------|------|
| Dependency security scan | Weekly (Dependabot) | Automated |
| Issue triage / reply | Weekly | Maintainer |
| Community PR review | As needed | Maintainer |
| New format support (upstream additions) | As needed | Maintainer |
| Performance regression test | Before each release | CI |

### 5.3 Long-term roadmap

```
2026 Q3 — v1.0.0  Stable release (**not code-signed**, SmartScreen warning accepted, README provides "How to proceed with installation" notes)
2026 Q4 — v1.1.0  LLM integration enhancements, custom conversion templates, **evaluate EV code signing certificate** (to eliminate SmartScreen warnings)
2027 Q1 — v1.2.0  WinGet / Scoop distribution, auto-update
2027 Q2 — v1.3.0  Plugin ecosystem, user-defined conversion scripts
2027 Q4 — v2.0.0  Cross-platform (macOS / Linux) support
```

**Code signing decision log**:
- v1.0: **Not signed**. Windows SmartScreen will show "Unknown publisher" warning; README "Installation" section provides "Install anyway" instructions.
- v1.1+: Evaluate self-signed vs EV certificate cost & process (EV cert ~$300-500/year, issued → SmartScreen trusts immediately; self-signed only valid for enterprise internal distribution).
- See [02 §5.3 STRIDE Spoofing threat assessment](02-architecture.md)

## 6. Community & Contribution

### 6.1 Contribution guide

```markdown
# Contribution guide (CONTRIBUTING.md)

## Dev environment
git clone https://github.com/raymondyan-zhijie/Lei_MD.git
cd Lei_MD
pip install -e ".[dev]"

## Code style
- Follow PEP 8
- ruff auto-formatting
- Type annotations required

## Commit convention
- feat: new feature
- fix: bug fix
- docs: documentation update
- style: code formatting
- refactor: refactor
- test: test
- chore: build/tooling
- deps: upstream dependency upgrade

## PR flow
1. Fork the repository
2. Create a feature branch (feat/xxx or fix/xxx)
3. Write tests → implement → ensure local tests pass
4. Submit PR with change description
5. CI auto-runs tests (lint + pytest + build)
6. Maintainer review and merge

## Upstream update notes
When upstream `markitdown` releases a new version, see `docs/06-dependency-update-strategy.md`;
do not directly modify the version cap in `pyproject.toml`.
```

### 6.2 Issue feedback template

```yaml
name: Bug Report
description: Report a bug
body:
  - type: input
    attributes:
      label: Version
      placeholder: "v0.4.0"
  - type: input
    attributes:
      label: Windows version
      placeholder: "Windows 11 23H2"
  - type: textarea
    attributes:
      label: Reproduction steps
  - type: textarea
    attributes:
      label: Expected behavior
  - type: textarea
    attributes:
      label: Screenshot / log
```

## 7. CHANGELOG template

```markdown
# Changelog

## [X.Y.Z] - YYYY-MM-DD

### Added
- File drag-and-drop conversion (PDF/Word/Excel/PPT/HTML/EPUB/Images/CSV/JSON/XML/ZIP)
- Directory recursion
- Markdown live preview
- Batch conversion + progress bar
- One-click copy to clipboard
- Export .md file
- Dark / light theme switching
- Chinese & English UI + error message i18n
- 5-category error code system (E_FILE / E_CONVERT / E_SYS / E_INTERNAL / E_UPDATE)
- SQLite history + startup integrity check
- Config file corruption auto-backup recovery

### Fixed
- Large file (>50MB) memory leak during conversion
- No longer mis-passes directory path to MarkItDown when dropping folders
- ConverterWorker reuses converter instance (performance optimization)

### Not in v1.0 (planned for v1.1+)
- Audio transcription (MP3/WAV) — see [01-requirements.md F9a](01-requirements.md)
- YouTube URL input

## [0.1.0] - 2026-06-30
### Added
- Project init
- Basic window skeleton
- Drag-and-drop area component
- Conversion engine wrapper
```

## 8. License

This project is under the **MIT License**, consistent with upstream [Microsoft MarkItDown](https://github.com/microsoft/markitdown).

```
MIT License

Copyright (c) 2026 leimengde

Permission is hereby granted, free of charge, to any person obtaining a copy...
```
