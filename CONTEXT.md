# Lei_MD — Project Context for AI Assistants

> **Purpose**: Self-contained handoff for any AI assistant (Claude/GPT/Gemini/Hermes 跨 channel) to immediately understand the Lei_MD project state without reading prior conversation history. Updated by maintainer or Hermes after major milestones.

**Last updated**: 2026-06-04
**Maintainer**: leimengde (raymondyan@gmail.com)
**Repo**: https://github.com/raymondyan-zhijie/Lei_MD

---

## 1. What is Lei_MD?

Windows desktop GUI wrapper for Microsoft MarkItDown. Drag files in, get Markdown out.

- **License**: MIT
- **Status**: Alpha, **282 tests green** (v0.4.9.1)
- **Latest release**: v0.4.9.1
- **GitHub stars**: ~5

**Core value**: Non-technical users converting PDF/DOCX/PPTX/XLSX/images/HTML/etc. to clean Markdown without CLI.

---

## 2. Tech stack (hard constraints)

| Layer | Tech | Implication |
|---|---|---|
| GUI | PySide6 (Qt 6.7-6.10) | Native Qt, **NOT web** |
| Styling | QSS (Qt Style Sheets) | Limited CSS subset, no Grid/Flexbox |
| i18n | Custom `i18n.py` with `_tr()` | Every string must be wrapped |
| Theme | `darkdetect` + 3 modes | light / dark / high-contrast |
| Packaging | PyInstaller onefile (142 MB) + NSIS | Single .exe, no runtime install |
| Backend | Pure Python, no server, no API | All state local, history = SQLite |
| Target OS | Windows 10/11 | Design for Windows aesthetic |
| Min Python | 3.10 | Modern OK |

**Hard "DO NOT"**:
- ❌ WebEngine (would add 200 MB)
- ❌ 3rd-party UI framework (no Material for Qt)
- ❌ Online account / telemetry
- ❌ Auto-update without consent
- ❌ Custom title bar
- ❌ Tabs for multi-file (multi-window OK)

---

## 3. Current state (v0.4.9.1)

### Released versions

| Version | Date | Highlights |
|---|---|---|
| **v0.4.9.1** | 2026-06-03 | Setup.exe installer (build.yml if 条件修) |
| v0.4.8 | 2026-06-02 | PyInstaller onefile (139 MB), green-only |
| v0.4.7 | 2026-06-02 | magika data hook fix, multi-cmd test |
| v0.4.6 | 2026-06-01 | Resilient migrations, defusedxml |
| v0.3.0 | 2026-06-01 | Cross-sprint audit, 23 Medium + 6 Low fixed |
| v0.2.7 | 2026-06-01 | P0/P1 review fixes |

### Test count history
- v0.2.2: 97 tests
- v0.2.3-2.7: +60 (P0/P1/P2/P3 regression)
- v0.3.0: 157 tests green
- v0.4.x: 282 tests green (latest)

---

## 4. Current pain points (v0.4.9.1 UI)

| # | Problem | Severity |
|---|---|---|
| 1 | Drop Area wastes 1/3 screen when idle | High |
| 2 | No icons — looks like 2020 IDE | High |
| 3 | Preview is plain text, not rendered MD | High |
| 4 | Theme is 22-line QSS, looks unfinished | High |
| 5 | No design system, ad-hoc colors | High |
| 6 | Dark mode = just inverted colors | Med |
| 7 | Progress bar in status bar, easy to miss | Med |
| 8 | Settings dialog uses registry, hard to find | Med |
| 9 | Splitter ratio not persisted | Low |
| 10 | No multi-select in file list | Low |
| 11 | Error popups block UI | Low |
| 12 | No system tray / min-to-tray | Low |
| 13 | No keyboard shortcuts beyond defaults | Low |
| 14 | No first-run wizard / about dialog | Low |

---

## 5. v0.5.0 redesign — **OPEN, IN PROGRESS**

### What's done (2026-06-03)
- ✅ 4 HTML prototypes: `docs/prototypes/v0.5.0/mockup-{1,2,3,4}-*.html`
- ✅ 4 PNG screenshots in `docs/prototypes/v0.5.0/screenshots/`
- ✅ `AI-CONTEXT.md` (13KB handoff for external AI design tools)
- ✅ Penpot self-hosting research (4GB RAM minimum, your ECS 3.5GB tight)

### Open decisions (maintainer hasn't picked)

| Question | Hermes recommendation | Status |
|---|---|---|
| Drop Area remove entirely? | ✅ Yes, waste of space | **TBD** |
| Sidebar nav (Home/History/Settings)? | ✅ Yes, mainstream pattern | **TBD** |
| Brand color keep #1a73e8? | Keep — align with M3 | **TBD** |
| Figma vs Penpot? | Figma desktop offline > Penpot (you'd need to deploy) | **TBD** |
| Penpot self-host? | ECS 3.5GB too tight, need +¥30/mo upgrade to 4GB | **TBD** |

### v0.5.0 must-have (MVP)
- Modern Material 3-inspired visual language
- Design token system (Python dicts → QSS injection)
- 3 themes (light / dark / high-contrast)
- Icon system via `qtawesome`
- **Markdown preview actually rendered** (QTextBrowser + `markdown` lib)
- Custom file list row with icon + name + status badge + size

### v0.5.0 nice-to-have
- Left sidebar nav (replaces Drop Area)
- Top bar (search, theme toggle, settings, help)
- Status pill at bottom (not progress bar)
- Error toasts (non-blocking) over QMessageBox
- Splitter ratio persistence
- Multi-select in file list
- System tray icon
- Keyboard shortcuts (Ctrl+O, Ctrl+Shift+O, Ctrl+,, F1, etc.)

### v0.5.0 out of scope
- WebEngine-based preview
- Plugin system
- Cloud sync

---

## 6. Reference designs (inspiration, not copy)

Obsidian · VSCode · Linear · Figma · Notion · GitHub Desktop · Mark Text · Typora

---

## 7. Discarded ideas (don't re-propose)

| Idea | Why discarded | Date |
|---|---|---|
| **Rust rewrite** | Too complex, 6-18 mo, ecosystem gap (no markitdown equivalent) | 2026-06-02 |
| Penpot self-host on current ECS | 3.5GB RAM too tight, need upgrade | 2026-06-03 |
| WebEngine preview | +200MB, breaks onefile principle | — |

---

## 8. Environment

### Local dev
- Path: `/home/admin/projects/markitdown-gui/`
- Python: 3.10+ with venv
- Test: `pytest` (157/157 → 282/282 currently green)

### Build / release pipeline
- **GitHub Actions** on `windows-latest`
- **build.yml** workflow: spec → PyInstaller → optional NSIS
- **Two artifacts**: green .exe (always) + Setup.exe (default for tag push, opt-in for manual)
- **Tag push triggers release** build, manual `workflow_dispatch` for ad-hoc
- See `windows-desktop-build-pipeline` skill (Hermes) for full pain log

### Known build pipeline issues (all fixed by v0.4.9.1)
- ✅ PAT workflow scope (need repo + workflow)
- ✅ `with_installer` if condition (v0.4.8 broke installer, v0.4.9 fixed)
- ✅ magika data hook (PyInstaller `Path(magika.__file__).parent / 'models'`)
- ✅ Hermes terminal masks `Bearer *** ` literal PATs (use `GH_TOKEN` env + `shell=True`)

---

## 9. Channels / communication

| Channel | Use case | Status |
|---|---|---|
| **WeChat (微信)** | Daily back-and-forth, quick Q&A | Active, **rate-limited on debug bursts** |
| **Feishu (飞书)** | Debug / long sessions (planned) | **Not configured** |
| GitHub Issues | Bug reports, feature requests | Empty |
| Email | Maintainer only | raymondyan@gmail.com |

**Channel switching (planned)**: Feishu for multi-section debug (no 5 QPS limit), WeChat for daily. Hermes `/handoff` command may bridge sessions.

---

## 10. Backup & local artifacts

- **Source**: GitHub `raymondyan-zhijie/Lei_MD` is canonical
- **Local backup**: `/home/admin/files/2026-06-01...04/` (Filebrowser 127.0.0.1:8081, file.leimengde.net via CF Tunnel)
- **Older exe snapshots**: `/home/admin/files/2026-06-02/v0.4.5-8/`

---

## 11. Quick commands for AI

```bash
# Run tests
cd /home/admin/projects/markitdown-gui && pytest

# Check git status
git status && git log --oneline | head -20

# View v0.5.0 prototypes
ls docs/prototypes/v0.5.0/

# Read AI context for design tools
cat docs/prototypes/v0.5.0/AI-CONTEXT.md
```

---

## 12. Maintainer preferences (from session history)

- 中文交流, 简洁直接
- 严格 hold 文件: token/密钥默认 acknowledge + hold, 显式授权才落盘
- 大清单节奏: 先 fact-check (grep/读文件验属实性) + 分配 R-round + 给 2-3 执行选项 → 用户单字批准
- 汇报节奏: Task 边界 (开始+结束) 1-3 行; 连续推进不需确认; 全部完成时主动报+下一步; 只在阻塞/失败时停
- "继续" = 显式批准上轮方案
- 微信限流: 单条短消息, 不堆叠, 默认静默
- 跨会话回项目偏好: 先看"状态摘要" (位置/产物/待办) 不自动动手

---

**End of context. For deeper history: `git log`, `git show <commit>`, `docs/` plans, or this file's git history.**
