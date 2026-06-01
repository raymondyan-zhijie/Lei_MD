# Lei_MD Requirements Document

> 🌐 **Language**: [中文](01-requirements.md) | **English**

> **Project name:** Lei_MD
> **Brand:** leimengde
> **Version:** Planning snapshot (see [CHANGELOG](../../CHANGELOG.md) for actual implementation)
> **Date:** 2026-06-01
>
> This document is an **original snapshot from the initial project planning phase**. The plan-vs-v0.3.0-implementation diff is in [IMPLEMENTATION_VS_PLAN.md](IMPLEMENTATION_VS_PLAN.md).

> **SSOT index**: This document is the **authoritative definition** for:
> - §2 User personas
> - §3 Functional requirements (F1-F12, F9a audio planned for v1.1+)
> - §3.3 Non-functional requirements (NF1-NF5)
> - §4 Constraints
>
> Error code system: see [02 §6](02-architecture.md). Tech stack: see [02 §1](02-architecture.md).

---

## 1. Project Background

[Microsoft MarkItDown](https://github.com/microsoft/markitdown) (⭐ 136,328 stars · 9,300 forks) is Microsoft's open-source Python file-to-Markdown tool. It supports 20+ formats including PDF, Word, Excel, PowerPoint, HTML, EPUB, images (OCR), audio (transcription), and YouTube. However, it only provides a CLI interface, which is not friendly enough for average Windows users.

This project (**Lei_MD**) builds a **comprehensive, offline-capable Windows native GUI** on top of MarkItDown, so non-technical users can drag-and-drop files for conversion.

## 2. User Personas

| Role | Needs | Pain points |
|------|------|------|
| Students / researchers | Convert paper PDFs, lecture PPTs to Markdown for notes | CLI is too hard to use |
| Content creators | Convert Word / web articles to Markdown for publishing | Switching tools back and forth is cumbersome |
| Office workers | Batch-convert Excel / Word documents to text | Format loss, multi-step workflow |
| Developers | Quickly preview file Markdown output | CLI not intuitive |

## 3. Functional Requirements

### 3.1 Core Features (MVP — v1.0)

| ID | Feature | Priority | Description |
|------|------|--------|------|
| F1 | File drag-and-drop conversion | P0 | Drag single or multiple files into the window; auto-detect format and convert |
| F2 | Format support list | P0 | Support MarkItDown core formats (PDF/Word/Excel/PPT/HTML/EPUB/Images/CSV/JSON/XML/ZIP) |
| F3 | Conversion result preview | P0 | Built-in Markdown live preview window, supports rendering view |
| F4 | One-click copy / export | P0 | Copy Markdown source to clipboard, export as .md file |
| F5 | Batch conversion | P1 | Parallel / sequential multi-file batch conversion with progress bar |
| F6 | Output directory selection | P1 | User can specify output directory, default to source file directory |
| F7 | History records | P1 | Keep the latest 50 conversion records, viewable later |

### 3.2 Advanced Features (v1.1+)

| ID | Feature | Priority | Description |
|------|------|--------|------|
| F8 | LLM image description | P2 | Integrate OpenAI-compatible API, generate descriptions for images / images in PPT |
| F9 | YouTube link conversion | P2 | Enter YouTube URL, fetch subtitles and convert to Markdown |
| F9a | Audio transcription (v1.1+) | P2 | Drop MP3/WAV, local ffmpeg + whisper tiny model for offline transcription |
| F10 | Plugin support | P2 | Support MarkItDown third-party plugins |
| F11 | Import / export config | P2 | User can save / load conversion config presets |
| F12 | Dark mode | P2 | Support Windows dark / light theme switching |

### 3.3 Non-Functional Requirements

| ID | Requirement | Metric |
|------|------|------|
| NF1 | Performance | Single file <5MB conversion completes in under 3 seconds |
| NF2 | Compatibility | Windows 10/11, Python 3.10 ~ 3.13 |
| NF3 | Installer size | Comprehensive single installer (see [05 §3.1](05-release-plan.md) for details) |
| NF4 | Memory footprint | Idle <100MB, during conversion <500MB |
| NF5 | Internationalization | Support zh / en UI switching |

## 4. Constraints

- **Depends on MarkItDown library**: Core conversion capability is provided by the upstream library; this project is only a GUI wrapper
- **Comprehensive + offline**: Single installer bundles all 20+ format dependencies, **fully offline**, no network required from the user
- **Must work on Windows**: Use PyInstaller + NSIS to package as a standard Windows installer
- **MIT license compliance**: This project (Lei_MD) is an **independently MIT-licensed** GUI wrapper, distributed separately from upstream MarkItDown (MIT) but with compatible licensing; both copyright notices must be preserved. SPDX identifier: see [LICENSE](../LICENSE)
- **Python ecosystem**: GUI framework limited to Python ecosystem (PySide6), reducing maintenance cost

## 5. Error Handling Requirements

The error code system (5 major category prefixes, error message conventions, i18n plan, crash recovery strategy) is **authoritatively defined** in [docs/02-architecture.md §6](02-architecture.md).

At the requirements layer, we only commit to:
- ✅ 5 major error code categories (specific definitions not duplicated here)
- ✅ No Python traceback shown; **all error messages localized** + provide **next-action guidance**

### 5.1 Exception Scenarios (user perspective)

> The requirements layer first defines "what behavior the user sees"; the architecture / testing layers then implement the details.
> Error code IDs correspond 1:1 to 02 §6.1.

| Scenario | User-visible behavior | Code (see 02 §6.1) |
|------|-------------|------------------------|
| File doesn't exist / deleted after drop | File list marks ❌ failed; hover for details | `E_FILE_001` |
| File locked by another program | File list marks ❌ failed + prompt "Please close the locking program and retry" | `E_FILE_001` |
| **0-byte empty file** | File list marks ❌ failed + prompt "File is empty, skipped" | `E_FILE_002` |
| **Oversize file (>500MB)** | Reject + prompt "File exceeds 500MB limit" | `E_FILE_003` |
| Malicious filename (path traversal `../../`) | Reject + prompt "Illegal filename" | `E_FILE_004` |
| Drop unsupported format (`.xyz` etc.) | Reject + prompt "This format is not supported (v1.0 supports 20+ formats, see F2)" | `E_FILE_005` |
| **Drop audio (mp3/wav)** | v1.0 explicitly says "Supported in v1.1+" ([01 F9a](#32-advanced-features-v11)) | `E_FILE_006` |
| **Password-protected PDF / encrypted Office** | File list marks ❌ failed + prompt "File is password-protected, not supported" | `E_CONVERT_001` |
| Corrupted file format (e.g. docx is actually a broken zip) | File list marks ❌ failed + prompt "File is corrupted and cannot be parsed" | `E_CONVERT_002` |
| User force-closes during conversion | On next startup, check `processing.lock` to clean incomplete files | `E_SYS_001` |
| Output path not writable (disk full / permission denied) | Modal dialog + "Open output directory" button | `E_SYS_002` |
| Path exceeds Windows MAX_PATH 260 | Auto-detect and try `\\?\` prefix; fail with error if still invalid | `E_SYS_003` |
| Conversion engine crash (Python traceback) | Catch and don't exit + UI red bar + log upload | `E_INTERNAL_001` |
| SQLite history DB corrupted | On next startup, detect → auto-backup original + rebuild empty DB | `E_INTERNAL_002` |
| Config file (`config.json`) corrupted | On next startup, detect → backup original + reset to defaults | `E_INTERNAL_003` |
| Update file download interrupted / checksum failed | Keep old version + prompt retry | `E_UPDATE_001` |
| In-app "Check for Updates" network failure | Silently ignore + status bar shows "Cannot reach server" | `E_UPDATE_002` |

- ✅ App startup **auto-detects corruption** (SQLite / config) and recovers
