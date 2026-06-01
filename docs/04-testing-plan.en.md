# Lei_MD Test Plan

> 🌐 **Language**: [中文](04-testing-plan.md) | **English**

> **Brand:** leimengde
> **Version:** Planning snapshot (see [CHANGELOG](../../CHANGELOG.md) for actual implementation) | **Date:** 2026-06-01
>
> v0.4.0 actual test baseline (205 tests / 30 files) is in [IMPLEMENTATION_VS_PLAN.md](IMPLEMENTATION_VS_PLAN.md).

> **SSOT index**: This document is the **authoritative definition** of test-related matters. Error code system: see [02-architecture.md §6](02-architecture.md). Development tasks: [03-development-plan.md](03-development-plan.md).

---

## 1. Test Strategy

Adopt the **Test Pyramid** model: lots of unit tests → moderate integration tests → a few E2E tests.

```
         ╱  E2E (5%)  ╲
        ╱  Integration (20%) ╲
       ╱   Unit tests (75%)   ╲
      ────────────────────────
```

> v0.4.0 actual breakdown: 75% unit / 18% integration / 7% E2E (close to target).

## 2. Test Environment

| Dimension | Configuration |
|------|------|
| Operating system | Windows 10 (22H2), Windows 11 (23H2) |
| Python | 3.10, 3.11, 3.12, 3.13 |
| CI | GitHub Actions `windows-latest` + `ubuntu-latest` × py 3.10-3.13 (8 matrix, excluding win+3.10) |
| Local | Developer Windows 11 Pro Workstation |
| Linux (container) | Ubuntu 22.04 + Python 3.11 + Qt offscreen mode |

## 3. Test Coverage Goals

| Module | Line coverage goal | Actual v0.4.0 |
|------|--------|------|
| `src/core/converter.py` | 90% | ~85% (most logic covered) |
| `src/core/batch_worker.py` | 85% | ~88% (M1.2/M1.3/M1.5 covered) |
| `src/core/history.py` | 85% | ~80% (CRUD + corrupt recovery) |
| `src/core/config.py` | 80% | ~85% (H1 + M6.2/M6.3/M6.4) |
| `src/core/errors.py` | 95% | ~95% (all 16 codes tested) |
| `src/core/youtube.py` | 80% | ~75% (URL parsing + error mapping) |
| `src/ui/main_window.py` | 70% | ~65% (signal routing) |
| `src/ui/drop_area.py` | 80% | ~80% (L2 + audio reject) |
| **Total project** | 80% | ~75% |

> Goal: maintain 80%+ line coverage. v0.4.0 is at ~75%; the gap is in `main_window.py` and `converter.py` for OSError / I/O paths (hard to test without mocks).

## 4. Test Categories

### 4.1 Unit tests

Each module has a corresponding `tests/test_*.py` file. Use `pytest` framework with `pytest-qt` for Qt-specific assertions.

```python
# Example: tests/test_converter.py
import pytest
from src.core.converter import MarkItDownConverter
from src.core.errors import ConversionError, ErrorCode

def test_convert_nonexistent_file_raises_e_file_001(tmp_path):
    converter = MarkItDownConverter()
    missing = tmp_path / "doesnt_exist.pdf"
    with pytest.raises(ConversionError) as exc:
        converter.convert(str(missing))
    assert exc.value.code == ErrorCode.E_FILE_001
```

### 4.2 UI tests

```python
# Example: tests/test_drop_area.py
import pytest
from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtGui import QDragEnterEvent
from PySide6.QtWidgets import QApplication

def test_drop_area_accepts_pdf(qtbot, tmp_path):
    from src.ui.drop_area import DropArea
    da = DropArea()
    qtbot.addWidget(da)

    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    captured = []
    da.files_dropped.connect(lambda paths: captured.append(paths))
    # ...simulate drop event

    assert len(captured) == 1
    assert captured[0][0].endswith("doc.pdf")
```

### 4.3 Integration tests

```python
# tests/test_batch_integration.py
def test_batch_converts_multiple_files(qtbot, tmp_path, stub_converter):
    """End-to-end: drop multiple files → BatchWorker → output"""
    from src.core.batch_worker import BatchWorker

    paths = []
    for i in range(5):
        p = tmp_path / f"doc{i}.pdf"
        p.write_bytes(b"%PDF-1.4\n")
        paths.append(str(p))

    bw = BatchWorker(stub_converter.convert, paths, concurrency=2)
    progress, finished = [], []
    bw.progress.connect(lambda d, t: progress.append(d))
    bw.finished.connect(lambda: finished.append(True))

    bw.start()
    qtbot.waitUntil(lambda: len(finished) >= 1, timeout=5000)
    assert progress[-1] == 5
```

### 4.4 Regression tests (v0.2.1+)

| Version | File | Items | Covers |
|------|------|------|------|
| v0.2.1 | `test_v021_hotfix.py` | 4 | H2 / H3 / H4 (cancel, BOM, worker leak) |
| v0.2.2 | `test_v022_hotfix.py` | 5 | H1 / H5 / H6 / H9 (chmod, mutex, main-thread, i18n) |
| v0.2.3 | `test_v023_hotfix.py` | 18 | M6.2 / M6.3 / M6.4 (config backup) |
| v0.2.3 | `test_v023_close_event.py` | 5 | M4.1 / M4.2 (closeEvent 5-step) |
| v0.2.4 | `test_v024_p2_audit.py` | 9 | M3.7 / M5.3 / M3.8 (dir/file/thread) |
| v0.2.5 | `test_v025_low.py` | 14 | L1 / L2 / L3 / L4 (i18n / walk / preview / cause) |
| v0.2.7 | `test_v027_p0_regression.py` | 5 | closeEvent + i18n en |
| v0.2.7 | `test_v027_p1_regression.py` | 8 | _start_batch / refresh / _dispatched |
| v0.4.0 | `test_youtube.py` | 30 | YouTube URL parsing + error codes |
| v0.4.0 | `test_v040_audio_reject.py` | 18 | Audio rejection + E_FILE_006 |

**Total regression tests: 116 (out of 205)**

## 5. Test Conventions

### 5.1 Naming

- Files: `test_<module>.py` or `test_v<X>_<purpose>.py` for regression sets
- Functions: `test_<behavior>` or `test_<id>_<behavior>` (e.g. `test_h5_finished_emits_exactly_once`)

### 5.2 Fixtures

`tests/conftest.py` provides:
- `qapp` (session scope): global QApplication instance
- `qtbot` (function scope): pytest-qt's widget helper
- `tmp_path` (function scope, built-in): per-test temp dir
- `stub_converter` (function scope): drop-in replacement for `MarkItDownConverter`

### 5.3 Markers

```python
@pytest.mark.smoke  # Quick smoke test for CI dependency-update validation
def test_basic_convert():
    ...
```

## 6. Test Data

### 6.1 Sample files

Stored at `tests/fixtures/`:
- `sample.pdf` (10KB, minimal PDF)
- `sample.docx` (5KB, minimal Word doc)
- `sample.xlsx` (4KB, minimal Excel)
- `sample.txt` (1KB, plain text)
- `sample.md` (1KB, Markdown)
- `corrupt.zip` (claimed zip, actually broken)
- `empty.txt` (0 bytes)
- `audio.mp3` (fake header, 100 bytes)

### 6.2 Sensitive data

No production data in tests. All sample files are synthetic.

## 7. Performance Tests

```python
# tests/test_performance.py
@pytest.mark.benchmark
def test_convert_5mb_pdf_under_3_seconds(benchmark, tmp_path):
    pdf = tmp_path / "5mb.pdf"
    pdf.write_bytes(make_fake_pdf(5 * 1024 * 1024))
    converter = MarkItDownConverter()

    result = benchmark(converter.convert, str(pdf))
    # NF1: <5MB in <3s
    assert len(result) > 0
```

## 8. Coverage Reports

```bash
# Local
pytest --cov=src --cov-report=html
open htmlcov/index.html

# CI
pytest --cov=src --cov-report=xml
# Upload coverage.xml as CI artifact (v0.4.0 matrix: ubuntu + py 3.12 only, to save minutes)
```

## 9. CI Integration

The CI workflow's full yaml is in [03-development-plan.md](03-development-plan.md) historical task 0.2 section, and the working version is at `.github/workflows/test.yml`:
- `test` job: ubuntu-latest + windows-latest × Python 3.10/3.11/3.12/3.13 matrix (8 cells, excluding win+3.10) + `pytest tests/ -v --cov=src/`
- `lint` job: ubuntu-latest + `ruff check src/ tests/`
- `build` job: planned for v1.0 (PyInstaller dry-run on windows-latest, verify packaging succeeds; **do not** upload artifact yet)

This section only lists CI trigger strategy and failure handling:

| Event | Action |
|------|------|
| Push to `main` | Run full matrix (8 cells) |
| Pull request to `main` | Run full matrix (8 cells) |
| Push of `v*` tag | Run full matrix + (future v1.0) build job |
| Weekly schedule (Mon 09:00 UTC) | Run full matrix (catches upstream MarkItDown changes) |
| Manual `workflow_dispatch` | Run full matrix |

CI failure handling:
- A single matrix cell failure does not block other cells (`fail-fast: false`)
- A failed cell posts a status check on the PR
- The release is blocked until all matrix cells pass

## 10. Local Test Workflow

```bash
# Activate venv (CRITICAL — system Python has no PySide6)
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows

# Run all tests
python -m pytest -q

# Run a specific module
python -m pytest tests/test_youtube.py -v

# Run with coverage
python -m pytest --cov=src --cov-report=term-missing

# Lint
ruff check src/ tests/

# Lint with auto-fix
ruff check --fix src/ tests/
```

> ⚠️ **Critical**: do NOT forget `source .venv/bin/activate`. Without it, you'll get 14 import errors (`ModuleNotFoundError: No module named 'PySide6'`) because system Python doesn't have project dependencies installed.
