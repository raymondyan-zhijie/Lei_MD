# Lei_MD

> 🪟 **Windows desktop file-to-Markdown tool** — based on [Microsoft MarkItDown](https://github.com/microsoft/markitdown) (⭐ 136,328)
> **All-in-one · Fully offline · Traditional installer**

> 🌐 **Language**: [中文](README.md) | **English**

Drag a file → auto-convert → live preview → one-click export. **Let non-technical users enjoy the power of MarkItDown.**

## ✨ Features

| Feature | Description |
|------|------|
| 🖱 **Drag & drop conversion** | Drop files/folders to auto-convert |
| 📁 **Directory recursion** | Drop a folder to auto-expand all supported files |
| 👁 **Live preview** | Built-in Markdown rendering view (tables / code highlighting / images) |
| 📦 **Batch processing** | Drop multiple files, parallel conversion + progress bar |
| 📋 **One-click copy** | Copy the converted result to clipboard |
| 💾 **Export to file** | Export as `.md` file (UTF-8) |
| 🎨 **Dark mode** | Follows Windows system theme automatically |
| 🌏 **Bilingual UI** | 中文 / English (v0.4.5+ window refreshes immediately on language switch, **no restart required**) |
| 📜 **History** | SQLite-backed, keeps the last 50 entries |
| 🔒 **Local-first** | Offline by default; the only network feature is YouTube subtitle fetching (v0.4.0+) |
| ⚠️ **Error code system** | 5 categories (E_FILE / E_CONVERT / E_SYS / E_INTERNAL / E_UPDATE), all with regression tests |

## 📦 Supported Formats (v1.0)

| Category | Formats |
|------|------|
| 📄 Documents | PDF · DOCX · DOC · PPTX · PPT · XLSX · XLS · EPUB |
| 🌐 Text | HTML · HTM · CSV · JSON · XML · TXT · MD |
| 🖼 Images | JPG · JPEG · PNG · GIF · BMP · WEBP |
| 📦 Archives | ZIP |
| ❌ **Not in v1.0** | MP3 · WAV · OGG · FLAC (planned for v1.1+, offline) |

## 🚀 Quick Start

### For End Users

1. Download the latest `Lei_MD-Setup-x.x.x.exe` from [Releases](https://github.com/raymondyan-zhijie/Lei_MD/releases)
2. Double-click to install (NSIS wizard)
3. Drop a file and start using!

### For Developers

```bash
git clone https://github.com/raymondyan-zhijie/Lei_MD.git
cd Lei_MD
pip install -e ".[dev]"
python src/main.py
```

### Building a Windows .exe

See [docs/07-build-release.md](docs/07-build-release.md) (one-line `pwsh scripts/build-windows.ps1` produces `.exe` and `Setup.exe`).

> ⚠️ **Test command** (run before any commit):
> ```bash
> source .venv/bin/activate   # on Linux/macOS
> python -m pytest -q
> ```
> 205/205 tests should pass.

## 📸 Screenshots

> To be added.

## 🗺 Roadmap

| Version | Date | Content | Status |
|------|------|------|------|
| 0.1.0 | 2026-06 | Project init + 6 planning docs | ✅ Released |
| 0.2.0 | 2026-06 | Enhanced: settings / batch / history / dark mode / Chinese / i18n | ✅ Released |
| 0.3.0 | 2026-06 | Cross-Sprint audit + P0-P3 hotfix + 6-dim review + docs cleanup (157/157 green) | ✅ Released |
| 0.4.0 | 2026-06 | CI workflow (8 matrix) + YouTube URL input + audio E_FILE_006 explicit rejection (205/205 green) | ✅ Released |
| 1.0.0 | 2026-Q3 | Full 20+ formats + NSIS installer (**400-500MB offline**) | ⏳ Planned |
| 1.1.0 | 2026-Q4 | Audio transcription (ffmpeg + whisper offline) + in-app update check | ⏳ Planned |
| 1.2.0 | 2027-Q1 | WinGet / Scoop distribution + optional auto-update | ⏳ Planned |
| 2.0.0 | 2027-Q4 | Cross-platform (macOS / Linux) | ⏳ Planned |

> Full release notes: [CHANGELOG.md](CHANGELOG.md) · Plan vs Implementation: [docs/IMPLEMENTATION_VS_PLAN.md](docs/IMPLEMENTATION_VS_PLAN.md)

## 🏗 Tech Stack

| Layer | Technology |
|----|------|
| GUI | PySide6 (Qt6) |
| Conversion engine | Microsoft MarkItDown[all] |
| Preview rendering | markdown + Pygments + QTextBrowser |
| History storage | SQLite (with integrity self-check) |
| Config storage | JSON (`%APPDATA%\Lei_MD\config.json`) |
| Packaging | PyInstaller + NSIS |
| CI/CD | GitHub Actions (Windows + Ubuntu) |

## 📁 Project Structure

```
Lei_MD/
├── src/                # Source code
│   ├── ui/             # GUI components (MainWindow, DropArea, PreviewPanel, ...)
│   ├── core/           # Business logic (Converter, BatchWorker, History, Config, Updater, YouTube)
│   └── resources/      # Icons + i18n + error code mapping
├── tests/              # Tests (unit + UI + integration + regression + E2E)
│   ├── conftest.py     # Global qapp fixture
│   └── fixtures/       # Sample files
├── docs/               # Planning docs (see "Documentation" below)
│   ├── 01-requirements.md
│   ├── 02-architecture.md
│   ├── 03-development-plan.md
│   ├── 04-testing-plan.md
│   ├── 05-release-plan.md
│   └── 06-dependency-update-strategy.md
├── scripts/            # Build scripts (PyInstaller, NSIS, bump_version) — planned for v1.0
├── .github/workflows/  # CI (test+lint+build) + CD (release)
├── CODE_OF_CONDUCT.md  # Code of conduct
├── CONTRIBUTING.md     # Contribution guide
├── CHANGELOG.md        # Release notes
├── LICENSE             # MIT
└── pyproject.toml      # Project config
```

## 📚 Documentation

The project ships with **5 planning docs** (each available in 中文 + English, marked by `.en.md` suffix):

| File | Chinese | English | Description |
|---|---|---|---|
| 01 Requirements | [01-requirements.md](docs/01-requirements.md) | [01-requirements.en.md](docs/01-requirements.en.md) | User personas, F1-F12 feature list, NF1-NF5 non-functional requirements |
| 02 Architecture | [02-architecture.md](docs/02-architecture.md) | [02-architecture.en.md](docs/02-architecture.en.md) | Tech choices, threading model, 5-category error code system |
| 03 Development Plan | [03-development-plan.md](docs/03-development-plan.md) | [03-development-plan.en.md](docs/03-development-plan.en.md) | Phase 0-5 task breakdown |
| 04 Testing Plan | [04-testing-plan.md](docs/04-testing-plan.md) | [04-testing-plan.en.md](docs/04-testing-plan.en.md) | Test pyramid, environment, CI integration |
| 05 Release Plan | [05-release-plan.md](docs/05-release-plan.md) | [05-release-plan.en.md](docs/05-release-plan.en.md) | SemVer strategy, deliverables, maintenance plan |
| 06 Dep Update | [06-dependency-update-strategy.md](docs/06-dependency-update-strategy.md) | [06-dependency-update-strategy.en.md](docs/06-dependency-update-strategy.en.md) | Upstream MarkItDown / library update policy |

> `IMPLEMENTATION_VS_PLAN.md` is project-internal (plan vs reality diff, v0.3.0 baseline). Not translated; available in Chinese only.

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.
Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

> **When upstream MarkItDown releases a new version**, see [docs/06-dependency-update-strategy.en.md](docs/06-dependency-update-strategy.en.md).

## 📄 License

**SPDX-License-Identifier: MIT** — Copyright (c) 2026 leimengde

This project (Lei_MD) is an **independently MIT-licensed** GUI wrapper for [Microsoft MarkItDown](https://github.com/microsoft/markitdown), **not part of** the upstream project.
- **Lei_MD license**: MIT ([LICENSE](LICENSE))
- **MarkItDown upstream license**: MIT ([upstream LICENSE](https://github.com/microsoft/markitdown/blob/main/LICENSE))
- **Dependency relationship**: invokes upstream at runtime via `pip install markitdown[all]`; upstream copyright is bundled with the distribution.

## 🙏 Acknowledgments

This project builds on the excellent work of the Microsoft AutoGen team: [MarkItDown](https://github.com/microsoft/markitdown)
