# Lei_MD v0.5.0 UI Redesign — Project Context for AI Tools

> **Purpose**: This document is a self-contained handoff for any AI assistant
> (Claude, GPT-4, Gemini, etc.) to produce a **UI design proposal** for
> Lei_MD v0.5.0. You don't need any prior context — everything below is what
> you need to know.

---

## 1. What is Lei_MD?

**Lei_MD** is a Windows desktop GUI for [Microsoft MarkItDown](https://github.com/microsoft/markitdown) — a tool that converts documents to Markdown.

- **Repository**: https://github.com/raymondyan-zhijie/Lei_MD
- **Current version**: v0.4.9.1 (released 2026-06-03)
- **License**: MIT
- **Author**: leimengde (single maintainer)
- **Status**: Alpha, 282 tests passing
- **GitHub stars**: ~5 (early stage)

**Core value proposition**: "Drag files in, get Markdown out" — for non-technical users who want to convert PDF/DOCX/PPTX/XLSX/images/HTML/etc. to clean Markdown without using the command line.

---

## 2. What it does (user-facing)

1. **Drag & drop** one or more files (or a folder) onto the window
2. App **converts** each file to Markdown via MarkItDown library
3. **Live preview** the converted Markdown
4. **Copy** to clipboard or **save** as .md file
5. **History** of past conversions is stored (last 50)
6. **YouTube URL** support (v0.4.0+): paste URL, fetch subtitles as MD
7. **Settings**: theme (light/dark/system), language (zh/en), limits

**Supported input formats (v1.0)**:
- Documents: PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS, EPUB
- Text: HTML, HTM, CSV, JSON, XML, TXT, MD
- Images: JPG, JPEG, PNG, GIF, BMP, WEBP
- Archives: ZIP
- **NOT supported (planned v1.1)**: MP3, WAV, OGG, FLAC (audio transcription offline)

---

## 3. Tech stack (constraints for your design)

| Layer | Tech | Implication for UI design |
|---|---|---|
| **GUI framework** | PySide6 (Qt 6.7-6.10) | Native Qt widgets, not web. **Not** a web app. |
| **Styling** | Qt Style Sheets (QSS) — CSS-like but limited | No CSS Grid/Flexbox/Variables. Subset of CSS. |
| **i18n** | Custom `i18n.py` with `_tr()` function | Every visible string must be wrapped. |
| **Theme** | `darkdetect` for system detection, 3 modes (light/dark/high-contrast planned) | Real-time theme switch possible. |
| **Packaging** | PyInstaller onefile (142 MB) + NSIS installer | Single .exe, no runtime install on user side. |
| **Backend** | Pure Python, no server, no API | All state local. History = SQLite at `~/.lei_md/`. |
| **Target OS** | Windows 10/11 (Linux/macOS dev only) | Design for Windows aesthetic. |
| **Min Python** | 3.10 | Modern Python OK. |
| **Deps** | `markitdown[all]`, `PySide6`, `darkdetect`, `markdown`, `Pygments` | Optional: `qtawesome` for icons (v0.5.0 add). |

**Critical constraints**:
- ❌ **No WebEngine** (would add 200 MB) — preview must be Qt-native (QTextBrowser)
- ❌ **No heavy icon font** unless optional — `qtawesome` is the path
- ✅ Can use QSS for theming (limited CSS subset)
- ✅ Can use QPainter for custom rendering
- ❌ **No third-party UI framework** (no Material for Qt, no KDE Frameworks)
- ✅ Markdown rendering: use `markdown` library → HTML → `QTextBrowser.setHtml()`

---

## 4. Current UI (v0.4.9.1) — what's wrong

### Screenshots / layout
```
+------------------------------------------------------------+
| Menu bar: File | Edit | Settings | Help                    |
+------------------------------------------------------------+
| [YouTube URL input]                          [Fetch btn]   |
+------------+--------------------------+--------------------+
|            |                          |                    |
|  Drop Area |    File List             |   Preview          |
|  (QLabel)  |    (QListWidget)         |   (QPlainTextEdit) |
|            |                          |                    |
|  (huge,    |                          |   (plain text,     |
|   ugly)    |                          |    no MD render)   |
|            |                          |                    |
+------------+--------------------------+--------------------+
| [progress 60%]    [Cancel]   已添加 5 个文件               |
+------------------------------------------------------------+
```

### Pain points (real user feedback)

| # | Problem | Severity |
|---|---|---|
| 1 | **Drop Area wastes 1/3 of screen** when not in use | High |
| 2 | **No icons** — all text labels, looks like 2020 IDE | High |
| 3 | **Preview is plain text** — tables/code/headers not rendered | High |
| 4 | **Theme is just a 22-line QSS** — looks unfinished | High |
| 5 | **No design system** — ad-hoc colors, inconsistent spacing | High |
| 6 | **No dark mode visual polish** — just inverted colors | Med |
| 7 | **Progress bar in status bar** — easy to miss | Med |
| 8 | **Settings dialog uses Windows registry** — users can't find config | Med |
| 9 | **Splitter ratio not persisted** — resets on restart | Low |
| 10 | **No multi-select** in file list — can't batch-remove | Low |
| 11 | **Error popups block UI** — annoying on big files | Low |
| 12 | **No system tray / minimize to tray** | Low |
| 13 | **No keyboard shortcuts** beyond defaults | Low |
| 14 | **No first-run wizard / about dialog** | Low |

---

## 5. v0.5.0 redesign goals

### Must-have (MVP)
- **Modern Material 3-inspired visual language** (Google M3 color tokens, not literal M3)
- **Design token system** (Python dicts → QSS injection) — colors, spacing, radius, motion
- **3 themes**: light / dark / high-contrast
- **Icon system** via `qtawesome` (Material Icons or Font Awesome)
- **Markdown preview actually rendered** (QTextBrowser + `markdown` lib)
- **Custom file list row** with icon + name + status badge + size

### Nice-to-have
- **Left sidebar nav**: Home / History / Settings (replaces Drop Area)
- **Top bar** with search, theme toggle, settings, help
- **Status pill** at bottom (not progress bar) for active conversions
- **Error toasts** (non-blocking) instead of QMessageBox
- **Splitter ratio persistence**
- **Multi-select** in file list
- **System tray** icon
- **Keyboard shortcuts** (Ctrl+O, Ctrl+Shift+O, Ctrl+, , F1, etc.)

### Out of scope for v0.5.0
- WebEngine-based preview (v0.6.0+ if needed)
- Plugin system
- Cloud sync

---

## 6. Target users (personas)

### Primary: "Office Worker Wang" (王小李)
- 35 yo, accountant at a mid-size company
- Needs to convert monthly reports (PDF, XLSX) to Markdown for wiki
- **NOT technical** — won't read docs, won't use CLI
- **Wants**: drag → wait → copy. That's it.
- **Cares about**: not breaking, not losing data, looking professional
- **Doesn't care about**: themes, settings, advanced features

### Secondary: "Dev Zhang" (张工)
- 28 yo, backend developer
- Uses markitdown CLI daily, Lei_MD is for quick GUI testing
- **Technical** — reads code, opens issues
- **Wants**: keyboard shortcuts, batch processing, history search
- **Cares about**: speed, no bloat, clean UI
- **Doesn't care about**: glossy design, hand-holding

### Tertiary: "Student Liu" (小刘)
- 22 yo, CS student
- Converts lecture slides (PPTX) and papers (PDF) for note-taking
- **Cares about**: free, lightweight, no telemetry
- **Wants**: install once, works forever, no ads

---

## 7. What we need from you (the AI)

**Deliver**: A high-fidelity UI design proposal for v0.5.0. Pick ONE OR MORE of these formats:

### Option A: Text specification (most useful for implementation)
A markdown document covering:
1. **Layout** (top bar / sidebar / main area / status) with ASCII or text description
2. **Color tokens** (semantic names, not hex — e.g. `--color-primary` not `#1a73e8`)
3. **Typography scale** (font, sizes, weights, line-heights)
4. **Spacing system** (4/8/16/24/32 px scale)
5. **Component list** (button, list item, dialog, toast, etc.) with QSS snippets
6. **States** (hover, active, disabled, error) for each component
7. **3 themes** (light, dark, high-contrast) — full color matrix
8. **Accessibility** (focus rings, contrast ratios, keyboard nav)

### Option B: Wireframes (sketches)
ASCII or text-based wireframes of:
1. **Idle state** (3 files added, 1 done, 1 converting, 1 pending)
2. **Conversion in progress** (toast at bottom)
3. **Settings dialog** (theme, language, advanced)
4. **History view** (sidebar with nav, center with filter chips, right with preview)
5. **Error state** (file rejected, conversion failed)
6. **Empty state** (no files added yet)

### Option C: Visual design (if your tool supports it)
- Figma / Penpot file
- High-fidelity mockup
- Component library
- Style guide

### Option D: Implementation-ready QSS
- The actual QSS stylesheet for v0.5.0
- With comments explaining each token
- Tested in PySide6

---

## 8. Reference designs we admire (for inspiration, not copying)

| Product | Why we like it |
|---|---|
| **Obsidian** | Three-pane layout works, very keyboard-friendly |
| **VSCode** | Top bar + activity bar + editor + status bar pattern |
| **Linear** | Sidebar nav + clean lists + keyboard shortcuts |
| **Figma** | Property panels on the right, canvas center |
| **Notion** | Modern minimalism, good use of whitespace |
| **GitHub Desktop** | Native-feeling, simple nav, no clutter |
| **Mark Text** (a real MD editor) | Good MD preview rendering, but UI dated |
| **Typora** | WYSIWYG MD, very clean |

---

## 9. Hard constraints — DO NOT propose

❌ **Web technologies** (HTML/CSS in WebEngine, Electron-style) — adds 200 MB
❌ **3rd-party UI libraries** that need extra deps (Material for Qt, KDDockWidgets)
❌ **Animated splash screens** — slow first impression
❌ **Online account requirement** — local-first principle
❌ **Telemetry / analytics** — privacy
❌ **Auto-update** without consent
❌ **System tray app by default** — opt-in (some users hate tray apps)
❌ **Tabs for multiple files** — adds complexity, multi-window OK
❌ **Custom title bar** — use Windows native (consistency + accessibility)

---

## 10. Open questions (give your opinion)

1. **Should the Drop Area be removed entirely**, or kept as a "drop here" overlay on the file list?
2. **Sidebar nav (Home/History/Settings)** — yes or no? If no, where do History and Settings go?
3. **Status indicator at bottom** — toast (auto-dismiss) or persistent bar?
4. **Icon set** — Material Icons (Google) or Font Awesome? Or both?
5. **Brand color** — keep blue (#1a73e8) or shift to something more distinctive for Lei_MD?
6. **What 3-5 micro-interactions** would delight users? (e.g. file drop bounce, success confetti, etc.)

---

## 11. How to deliver

Reply with:
1. **Format chosen** (A / B / C / D or combination)
2. **Design rationale** (1-2 paragraphs — why this approach)
3. **Tradeoffs** — what you sacrificed and why
4. **Implementation effort estimate** (1 dev day / 1 sprint / etc.)
5. **Open issues** — what still needs to be decided before coding

**Don't worry about being perfect** — multiple proposals welcome. Maintainer will pick the best parts of each.

---

## 12. Context that may help

- **Project is solo-maintained** — keep complexity low
- **Windows-first** — don't propose macOS-style design
- **Privacy-first** — no cloud, no accounts, no telemetry
- **Open source** — design must be implementable by a hobbyist
- **Chinese + English users** — design must work for CJK (text width, line height, character spacing)
- **Existing tests** — 282 unit tests pass; visual changes should not break them

---

## Appendix: Current file structure (for context)

```
src/
├── main.py                # entry point
├── app.py                 # QApplication setup
├── core/                  # business logic, no Qt
│   ├── converter.py       # markitdown wrapper
│   ├── batch_worker.py    # async QThread workers
│   ├── config.py          # ConfigManager (JSON)
│   ├── history.py         # SQLite history
│   ├── errors.py          # 5 error code families
│   └── ...
├── ui/                    # Qt widgets
│   ├── main_window.py     # QMainWindow assembly
│   ├── drop_area.py       # QLabel drag target
│   ├── file_list.py       # QListWidget
│   ├── preview_panel.py   # QPlainTextEdit (TODO: QTextBrowser)
│   ├── settings_dialog.py # QDialog
│   ├── styles.py          # 22-line QSS (TODO: token system)
│   └── i18n.py            # tr() + locale loading
└── resources/             # icons, themes
```

**Existing prototypes** (do not duplicate, but you can reference for layout):
- `/home/admin/projects/markitdown-gui/docs/prototypes/v0.5.0/mockup-1-light-idle.html`
- `/home/admin/projects/markitdown-gui/docs/prototypes/v0.5.0/mockup-2-dark-converting.html`
- `/home/admin/projects/markitdown-gui/docs/prototypes/v0.5.0/mockup-3-light-settings.html`
- `/home/admin/projects/markitdown-gui/docs/prototypes/v0.5.0/mockup-4-dark-history.html`

(These are the maintainer's first-pass mockups. Your proposal can build on, replace, or critique them.)

---

**End of context document. Generate your proposal.**
