# Lei_MD Development Plan

> 🌐 **Language**: [中文](03-development-plan.md) | **English**

> **Brand:** leimengde
> **For Hermes:** Use the `subagent-driven-development` skill to implement this plan task-by-task.
>
> **Goal:** Build a Windows-native GUI app that wraps Microsoft MarkItDown's file-to-Markdown capabilities. **All-in-one + offline + traditional installer**.
>
> **Architecture:** PySide6 GUI + MarkItDown engine + SQLite history + QThread async conversion.
>
> **Tech Stack:** Python 3.10 ~ 3.13, PySide6, MarkItDown[all], SQLite, PyInstaller + NSIS
>
> **Total time estimate:** MVP 4-6 weeks (conservative, not 2 weeks)
>
> ⚠️ **Document status**: **Historical planning archive**. v0.1.0 → v0.4.0 has been implemented based on this plan. The plan-vs-v0.3.0-implementation diff is in [IMPLEMENTATION_VS_PLAN.md](IMPLEMENTATION_VS_PLAN.md). Actual implementation records are in [CHANGELOG.md](../../CHANGELOG.md) sections for v0.1.0 / v0.2.0 / v0.3.0 / v0.4.0.
>
> The `Phase 0 ~ 5 / Task 0.1 ~ 5.x` sections retained here are an **implementation index** (in planning order), for tracing "why this task exists". Task titles are kept; version / stage labels have been stripped.

> **SSOT index**: This document is the **authoritative definition** of development task breakdown. Tech choices: [02 §1](02-architecture.md). Error handling: [02 §6](02-architecture.md). Testing: [04-testing-plan.md](04-testing-plan.md). Release: [05-release-plan.md](05-release-plan.md). Upstream updates: [06-dependency-update-strategy.md](06-dependency-update-strategy.md).

---

## Phase 0: Project Initialization

### Task 0.1: Create project skeleton

**Objective:** Initialize project directory structure, Git repository, dependency management

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `requirements-build.txt`
- Create: `src/__init__.py`
- Create: `.gitignore`
- Create: `README.md`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "lei-md"
version = "0.1.0"
description = "Windows GUI for Microsoft MarkItDown - convert files to Markdown with drag & drop, offline and all-in-one"
authors = [{name = "leimengde"}]
license = {text = "MIT"}
requires-python = ">=3.10,<3.14"
dependencies = [
    "markitdown[all]>=0.1.0,<0.2.0",
    "PySide6>=6.7,<7.0",
    "darkdetect>=0.8,<0.9",
    "markdown>=3.6,<4.0",
    "Pygments>=2.18,<3.0",
    "packaging>=24.0",  # for upstream version check (src/core/updater.py)
]
```

### Task 0.2: Configure CI/CD

GitHub Actions workflow:
- `test` job: windows-latest × Python 3.10/3.11/3.12/3.13 matrix + `pytest tests/ -v --cov=src/`
- `lint` job: ubuntu-latest + `ruff check src/ tests/`
- `build` job: windows-latest + `python scripts/build.py` (PyInstaller dry-run, verify packaging succeeds; **do not** upload artifact)

> Implementation status: deferred to v0.4.0. v0.4.0 builds `.github/workflows/test.yml` with 8 matrix (ubuntu + windows × py 3.10-3.13, excluding win+3.10).

---

## Phase 1: Core Features — MVP

### Task 1.1: Program entry and window skeleton

**Objective:** Create a runnable empty window

**Files:**
- Create: `src/main.py` — QApplication init
- Create: `src/app.py` — sys.exit hook
- Create: `src/ui/main_window.py` — QMainWindow subclass
- Create: `src/ui/styles.py` — QSS theme

**Step 1: src/main.py**

```python
import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

### Task 1.2: Drag-and-drop area component

**Files:**
- Create: `src/ui/drop_area.py`

A `QLabel` subclass with `setAcceptDrops(True)` overriding `dragEnterEvent` / `dragMoveEvent` / `dropEvent`. Emits a `files_dropped(list[str])` signal.

### Task 1.3: Conversion engine wrapper

**Files:**
- Create: `src/core/converter.py`

Wraps `markitdown.MarkItDown().convert()`. Pre-checks: file exists, is a normal file, non-empty, <500MB. Maps MarkItDown exceptions to `ConversionError` (with E_CONVERT_001 / E_CONVERT_002 codes).

### Task 1.4: Async conversion worker

**Files:**
- Create: `src/core/worker.py`

A `QThread` subclass.
- signals: `progress(int)`, `finished_with_md(str)`, `error(ConversionError)`
- `cancel()` cooperative interrupt
- Emits via Signal/slot; main thread is always the consumer

### Task 1.5: Markdown preview panel

**Files:**
- Create: `src/ui/preview_panel.py`

A `QTextBrowser` (or `QTextEdit`) showing Markdown rendering. Includes NUL-byte cleansing as a fallback.

### Task 1.6: File list and status

**Files:**
- Create: `src/ui/file_list.py`

A `QListWidget` (or `QTableWidget`) showing added files. Supports:
- Dedup
- Extension filter
- Selection signal (`file_selected(str)`)
- Visual status: ⏳ / ✅ / ❌

### Task 1.7: Main window integration

**Files:**
- Modify: `src/ui/main_window.py`

Three-pane QSplitter assembly: `DropArea` (top) / `FileList` (left) / `PreviewPanel` (right). Plus a status bar showing current state.

### Task 1.8: Configuration file management

**Files:**
- Create: `src/core/config.py`

`AppConfig` dataclass + `ConfigManager` JSON persistence.
- Storage path: Windows `%APPDATA%\Lei_MD\config.json`, POSIX `~/.config/Lei_MD/config.json`
- Corrupt-file auto-backup + reset (E_INTERNAL_003)
- `update(**kwargs)` writes immediately
- File permissions tightened to `0o600` (H1)
- 3-tier backup fallback `os.replace` → `shutil.move` → `unlink` (M6.4)

### Task 1.9: History records

**Files:**
- Create: `src/core/history.py`

SQLite persistence. Concurrency model: WAL + Signal serialization.
- schema: `source_path / source_format / markdown_length / duration_ms / success / error_msg / created_at`
- `add_requested` Signal → main-thread slot writes
- Capacity trim: keep `max_entries=50`
- `PRAGMA integrity_check` on startup; corrupt → backup + rebuild (E_INTERNAL_002)

---

## Phase 2: Enhanced Features

### Task 2.1: Settings dialog

**Files:**
- Create: `src/ui/settings_dialog.py`

A modal dialog injected with `ConfigManager`. Five sections: output / history / appearance / language / LLM. Reset uses a staging copy so live config is not mutated (M3.3).

### Task 2.2: Batch parallel conversion

**Files:**
- Create: `src/core/batch_worker.py`

QThreadPool + QRunnable. Signals: `progress(done, total)` / `finished()` / `item_failed(path, err)`. `cancel()` immediately fires `finished`. State machine: `IDLE → RUNNING → CANCELLED | FINISHED` (M1.3).

### Task 2.3: History panel

**Files:**
- Create: `src/ui/history_panel.py`

A table view: time / source / output / status. Search box filters by `source_path` substring. Double-click row triggers `file_selected(path)`.

### Task 2.4: YouTube URL input

**Files:**
- Create: `src/core/youtube.py` (v0.4.0)

A URL fetcher that supports 4 URL forms (`watch?v=` / `youtu.be/` / `shorts/` / `embed/`), extracts captions via `yt-dlp`, never downloads video. Error codes: E_CONVERT_003 (yt-dlp missing) / E_CONVERT_004 (timeout) / E_CONVERT_005 (invalid URL).

> Implementation status: completed in v0.4.0. See [tests/test_youtube.py](../../tests/test_youtube.py) for 30 regression tests.

### Task 2.5: Dark mode

**Files:**
- Create: `src/ui/styles.py` (modify)

`darkdetect` for system theme. `apply_theme('dark'|'light'|'system')` switches QPalette + QSS.

### Task 2.6: Chinese UI

**Files:**
- Create: `src/ui/i18n.py`
- Create: `src/resources/locales/zh_CN.json`

`Translator` class + module-level singleton + `tr(key)` helper. 53 zh_CN translations.

---

## Phase 3: Packaging & Delivery (v1.0 plan)

### Task 3.1: PyInstaller build script

**Files (planned):**
- Create: `scripts/build.py`

Drives `pyinstaller` to produce `dist/Lei_MD/Lei_MD.exe`.

> Status: deferred to v1.0. v0.4.0 ships as `pip install lei-md==0.4.0` (no installer yet).

### Task 3.2: NSIS installer

**Files (planned):**
- Create: `scripts/installer.nsi`

NSIS script that wraps the PyInstaller output and produces `Lei_MD-Setup-x.x.x.exe` (~400-500MB).

> Status: deferred to v1.0. Same reason as Task 3.1.

### Task 3.3: GitHub Release automation

`release.yml` workflow fires on `v*` tags. v0.3.0 + v0.4.0 both shipped via `curl` calling the GitHub Releases API (manual trigger, not full Actions automation).

---

## Phase 4: Testing Strategy

### Task 4.1: Unit tests

```python
# tests/conftest.py
import os
import sys
from pathlib import Path

import pytest

# Make src/ importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Provides a global QApplication instance, reused by all UI tests."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()
```

### Task 4.2: Test inventory

| Test type | Coverage | Tool |
|---------|----------|------|
| Unit | converter, config, history, worker, batch_worker, errors, youtube | pytest |
| UI | MainWindow, DropArea, signals/slots | pytest-qt |
| Integration | end-to-end conversion flow | pytest + sample files |
| Regression | v0.2.1 P0 / v0.2.2 P1 / v0.2.7 P0/P1 / v0.4.0 | pytest |
| Performance | large file conversion time | pytest-benchmark |

> Actual count at v0.4.0: **205/205 green**, 30 test files.

---

## Phase 5: Final Checklist (v1.0 wrap-up)

- [ ] Drag PDF / Word / Excel / PPT / HTML / images / ZIP all convert successfully
- [ ] Drop a directory to auto-recurse
- [ ] Drop audio (mp3 / wav) shows clear unsupported prompt (v1.0 unsupported)
- [ ] Batch-convert 10 files without crashing
- [ ] Preview window correctly renders Markdown (tables, code blocks, images)
- [ ] Copy to clipboard works
- [ ] Export .md file works (UTF-8)
- [ ] Dark / light mode switch works
- [ ] Chinese UI complete, no gaps
- [ ] `tests/test_youtube.py` regression passes (4 URL forms)
- [ ] `tests/test_v040_audio_reject.py` regression passes (8 audio extensions)
- [ ] All 6 CI matrix cells (ubuntu+windows × py 3.11-3.13) green
