# Lei_MD Architecture Design Document

> 🌐 **Language**: [中文](02-architecture.md) | **English**

> **Brand:** leimengde
> **Version:** Planning snapshot (see [CHANGELOG](../../CHANGELOG.md) for actual implementation) | **Date:** 2026-06-01
>
> This document is an **original snapshot from the initial project planning phase**. The plan-vs-v0.3.0-implementation diff is in [IMPLEMENTATION_VS_PLAN.md](IMPLEMENTATION_VS_PLAN.md).

> **SSOT index**: This document is the **authoritative definition** for:
> - §1 Tech stack (PySide6 + key dependencies)
> - §3 Core architecture design (threading model, data model)
> - §6 Error handling design (5-category error code system)
>
> Other documents reference this one when related topics appear; no duplicate definitions.

---

## 1. Tech Stack

### 1.1 GUI Framework Comparison

| Option | Pros | Cons | Verdict |
|------|------|------|------|
| **PySide6 (Qt)** | Native look, good drag-and-drop, rich components, full docs | Bundle size ~120MB | ✅ **First choice** |
| Tkinter | Python built-in, zero deps | Ugly UI, no modern widgets | ❌ |
| Dear PyGui | GPU-accelerated, good-looking | Immature ecosystem, complex packaging | ❌ |
| Electron | Frontend tech stack | Size >200MB, heavy Node dependency | ❌ |
| WPF + Python.NET | Most native Windows | Fragmented stack, hard to debug | ❌ |

**Conclusion**: Choose **PySide6**. Reasons:
1. Qt is the most mature cross-platform GUI framework in the industry
2. Native support for file drag-and-drop, system tray, multithreading
3. Qt Designer accelerates UI development
4. PyInstaller packaging is mature

### 1.1.1 Alternative evaluation: QWebEngineView (under evaluation, v2.0+ roadmap)

> User feedback mentions "evaluate the possibility of introducing QWebEngineView". This section is a **tech radar entry**; v1.0 does not implement it; re-evaluate at v2.0+.

**What is QWebEngineView**: A Chromium embedded component bundled with PySide6. Renders full HTML / CSS / JS (for Markdown preview much closer to GitHub rendering).

| Dimension | Current: `QTextBrowser` | Alternative: `QWebEngineView` |
|------|------------------------|----------------------|
| Render quality | Basic Markdown → HTML (no JS, no complex CSS) | Full GitHub-Flavored Markdown render |
| Bundle size | PySide6 baseline ~120MB | **+ 80-150MB** (Chromium core) → total ~200-270MB |
| Startup time | < 1s | + 1-2s (Chromium init) |
| Memory | < 100MB | + 100-200MB |
| Security risk | Very low (local HTML only) | **High** (Chromium has many historical vulns; even when network is disabled, the rendering engine is still a 0-day surface) |
| Maintenance | Low | Medium (Chromium version aligned with PySide6 release cycle) |

**v1.0 decision**: **Do not introduce**; keep QTextBrowser. Reasons:
1. Violates NF3 "all-in-one single installer ~400-500MB" (adding 100MB more = 550-650MB)
2. Violates the "fully offline" security posture (Chromium is an attack surface even with network disabled)

## 2. System Architecture Overview

The architecture follows the classic **3-tier** pattern: Presentation / Business Logic / Data. The MarkItDown engine is wrapped by our own `MarkItDownConverter`, which provides pre-validation, post-translation, and error mapping.

Key design decisions:
- **Single instance, lazy engine construction** (avoid blocking UI startup)
- **Thread isolation** (`clone_for_thread()`) for parallel batch conversion to prevent MarkItDown internal state from being shared
- **Signal-driven cross-thread communication** (main thread always wins for SQLite writes)

## 3. Core Architecture Design

### 3.1 Module Layout

```
src/
├── main.py             # Entry point
├── app.py              # QApplication initialization
├── core/               # Business logic
│   ├── converter.py    # MarkItDown wrapper
│   ├── batch_worker.py # QThreadPool parallel batch
│   ├── history.py      # SQLite history (WAL + Signal serialized)
│   ├── config.py       # JSON config (chmod 0o600)
│   ├── errors.py       # Error code system (SSOT)
│   └── youtube.py      # YouTube URL fetcher (v0.4.0)
├── ui/                 # GUI components
│   ├── main_window.py  # Main window (signal routing)
│   ├── drop_area.py    # Drag-and-drop region
│   ├── file_list.py    # File list widget
│   ├── preview_panel.py # Markdown preview
│   ├── settings_dialog.py # Settings dialog
│   ├── history_panel.py # History panel
│   ├── styles.py       # Theme manager (light/dark)
│   └── i18n.py         # Internationalization
└── resources/          # Icons + locale JSON + error code mapping
```

### 3.2 Threading Model

Three thread types:

| Thread | Responsibility | Notes |
|------|------|------|
| **Main (UI) thread** | All Qt widget operations; SQLite writes | Qt widgets are not thread-safe; SQLite is single-writer |
| **Worker thread (QThread)** | Single-file `ConversionWorker` | Cooperative cancel via `_cancel_event` |
| **Pool worker (QRunnable + QThreadPool)** | Batch conversion parallelism | Each runnable calls `clone_for_thread()` to get independent MarkItDown engine |

**Concurrency invariants**:
1. SQLite writes only happen on the main thread (via `add_requested` Signal)
2. Each `BatchWorker._ConvertRunnable` has its own `MarkItDown` instance (no shared internal state)
3. `BatchWorker` uses a state machine: `IDLE → RUNNING → CANCELLED | FINISHED` to prevent double-start / double-cancel

### 3.3 Data Model

#### 3.3.1 History (SQLite)

```sql
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,
    source_format TEXT NOT NULL,
    markdown_length INTEGER,
    duration_ms INTEGER,
    success INTEGER NOT NULL,
    error_msg TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_history_created_at ON history(created_at DESC);
```

**Concurrency model** (WAL + Signal serialization):
```sql
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;
```

**Implementation details** (see [03-development-plan.md](03-development-plan.md) historical task 1.9):

```python
# src/core/history.py
class HistoryManager(QObject):
    # Signal: ConverterWorker emits in any thread; slot always runs on main thread
    add_requested = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")     # Key 1
        self._conn.execute("PRAGMA busy_timeout=5000")    # Key 2
        self._conn.execute("PRAGMA synchronous=NORMAL")   # WAL recommended
        # ...
        self.add_requested.connect(self._on_add)           # Key 3

    def request_add(self, **kwargs):
        """Thread-safe entry: ConverterWorker calls this; no direct DB writes"""
        self.add_requested.emit(kwargs)

    @pyqtSlot(dict)
    def _on_add(self, kwargs):
        """Slot: always runs on main thread, writes DB"""
        self._conn.execute("INSERT INTO history ...", ...)
```

**Why double-safety**:
- WAL alone handles 99% of scenarios, but **brief conflicts between writers** are still possible (WAL serializes writers, but write + checkpoint can briefly block readers)
- Signal serialization **logically enforces a single writer** (main thread), eliminating races at the source
- The combination: writers never conflict + readers are fully concurrent with writers

#### 3.3.2 Config (JSON)

Stored at `%APPDATA%\Lei_MD\config.json` (Windows) or `~/.config/Lei_MD/config.json` (POSIX, v2.0+).

Schema:
```json
{
  "config_version": 1,
  "output_dir": "default",
  "custom_output_dir": null,
  "auto_convert": false,
  "max_history": 50,
  "language": "system",
  "theme": "system",
  "batch_concurrency": 4,
  "llm_api_base": null,
  "llm_api_key": null,
  "llm_model": "gpt-4o"
}
```

| Version | Range | Strategy |
|------|------|------|
| `config_version: 1` | v1.0 ~ v1.x | Baseline version, load directly |
| `config_version: 2+` | Future | On startup, detect → call `migrate(old_version, data)` chained migration |
| Missing field | Any version | Treat as `config_version: 0` (pre-v1.0 dev) → fill with defaults |

**Migration function** (pseudocode, see [03-development-plan.md](03-development-plan.md) historical task 1.8):

```python
# src/core/config.py
CONFIG_VERSION = 1
MIGRATIONS = {
    # 0 → 1: add batch_concurrency field
    # 1 → 2: rename custom_output_dir → output_dir_custom (example)
    # ...
}

def load_config(path: Path) -> dict:
    data = json.loads(path.read_text()) if path.exists() else {}
    version = data.get("config_version", 0)
```

## 4. Security Architecture

### 4.1 File Permissions

- `config.json` written with `0o600` permissions (current user only); tolerant to Windows / FAT32 / read-only filesystems
- Bundled SQLite database inherits the app's umask

### 4.2 Threat Model (STRIDE)

| Threat | Mitigation |
|------|------|
| **Spoofing** | Code signing certificate (planned v1.1+; v1.0 ships unsigned with README install notes) |
| **Tampering** | Installer checksum (planned v1.0+; v1.0 relies on TLS from GitHub Releases) |
| **Repudiation** | SQLite history + structured logging |
| **Information Disclosure** | Config file `0o600`; no network exfiltration; offline design |
| **Denial of Service** | DropArea `os.walk` depth limit 10 + file count limit 2000; SQLite busy_timeout 5000 |
| **Elevation of Privilege** | Runs as current user; no admin required for v1.0 install |

## 5. Internationalization (i18n)

### 5.1 Architecture

```python
# src/ui/i18n.py
class Translator:
    def __init__(self):
        self._strings: dict[str, str] = {}
        self._locale: str = "en"

    def load(self, locale: str, json_path: Path) -> None:
        data = json.loads(json_path.read_text(encoding="utf-8-sig"))
        self._strings = data
        self._locale = locale

    def tr(self, key: str) -> str:
        return self._strings.get(key, key)  # fallback to key itself

_TRANSLATOR = Translator()

def tr(key: str) -> str:
    return _TRANSLATOR.tr(key)

def set_locale(locale: str) -> None:
    # Whitelist: "system" / "en" / "zh_CN" / "en_US" (v0.2.5 P3 L1)
    if locale not in ("system", "en", "zh_CN", "en_US"):
        _log.warning("Unknown locale %r, fallback to 'en'", locale)
        locale = "en"
    ...
```

### 5.2 Translation Files

`src/resources/locales/zh_CN.json`: 53 keys covering menu / status / settings / history / error codes.
`en.json` is intentionally not provided; missing locale falls back to key names (English keys are already readable).

## 6. Error Handling Design

### 6.1 Error Code System (5 categories, 16 codes)

| Category | Range | Count | Examples |
|------|------|------|------|
| **E_FILE_** (file-level) | 001-006 | 6 | E_FILE_001 file not found, E_FILE_006 audio not supported |
| **E_CONVERT_** (conversion-level) | 001-005 | 5 | E_CONVERT_001 password-protected, E_CONVERT_003 yt-dlp missing (v0.4.0) |
| **E_SYS_** (system-level) | 001-003 | 3 | E_SYS_001 user force-closed, E_SYS_002 path not writable |
| **E_INTERNAL_** (internal-level) | 001-003 | 3 | E_INTERNAL_001 Python traceback |
| **E_UPDATE_** (update-level) | 001-002 | 2 | E_UPDATE_001 download interrupted |

### 6.2 Design Principles

1. **Never leak Python traceback to user**. Internal errors go to `crash.log`; user sees only the localized message
2. **One code per scenario**. No ambiguous codes
3. **All codes have a user-visible next-action** (e.g. "File is locked. Close the locking program and retry.")
4. **Bilingual messages**. zh_CN (primary) + en_US

### 6.3 Error Class Hierarchy

```python
class ErrorCode(str, Enum):
    E_FILE_001 = "E_FILE_001"
    # ...16 codes

class ConversionError(Exception):
    def __init__(self, code: ErrorCode, message: str = None, *, cause: Exception = None, **format_kwargs):
        self.code = code
        self.cause = cause
        # Default user message (zh_CN)
        template = ERROR_MESSAGES.get(code, {}).get("zh_CN", str(code))
        if message is None:
            message = template.format(**format_kwargs)
        super().__init__(message)
        self.user_message = message
        if cause is not None:
            self.__cause__ = cause  # v0.2.5 P3 L4: chain visible

    def get_message(self, lang: str = "zh_CN") -> str:
        # ...get localized message
```

### 6.4 Crash Recovery Strategy

| Resource | Corruption handling |
|------|------|
| SQLite history | On startup, `PRAGMA integrity_check`; if corrupt → backup `.db.bak.<ts>` + rebuild empty DB (E_INTERNAL_002) |
| config.json | On startup, if `json.JSONDecodeError` → backup `.json.bak` + reset to defaults (E_INTERNAL_003) |
| log file | Truncate to last 10MB on startup; max 3 rotations |
| processing.lock | On startup, if stale (last update > 1h ago) → delete and clean incomplete files |

Recovery is always silent + automatic; users see no interruption.

## 7. Performance Budget

| Component | RAM | CPU (idle) | Disk |
|------|------|------|------|
| PySide6 baseline | 80MB | 0% | 0 |
| MainWindow + QSS | 120MB | <1% | 0 |
| ConversionWorker (per file) | +50MB peak | 10-30% (PDF) | temp .md in same dir |
| BatchWorker (4 concurrent) | +200MB peak | 50-80% (4 cores) | as above |
| SQLite history | 5-10MB | <0.1% | grows ~1KB per record |
| **Total typical** | **~250MB** | **<5% idle** | **<10MB** |

## 8. Build & Release

- v1.0: PyInstaller + NSIS, single ~400-500MB installer
- v1.0+: WinGet / Scoop / pip package (per release plan)
