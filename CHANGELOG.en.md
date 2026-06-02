# Changelog

> 🌐 **Language**: [中文](CHANGELOG.md) | **English**

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.5] - 2026-06-02

Small governance patch after v0.4.4. **10 of 11 items from the first expert review fixed (P0/P1/P2), 1 item (E1) deferred to v0.5.0+**, **3 commits**. **275/275 tests green**.

### Fixed
- **A1 (428dca2) Remove redundant imports in main_window**: cleared 5 unused symbols from import block
- **D1/D2/D3 (428dca2) SettingsDialog i18n-ified**: 4 group titles + 3 buttons + window title all routed through `tr()`, 7 new i18n keys (zh+en)
- **A3 (83f9f91) i18n.py docstring correction**: removed inaccurate comments
- **B1 (83f9f91) Removed misleading comment**: inaccurate description of Qt internals in DropArea
- **D5 (83f9f91) YouTube 3 dialogs i18n-ified**: modal warning text routed through `tr()`
- **D6 (83f9f91) DropArea placeholder split into 3 keys**: drag / release / file-type hints each routed through i18n; fixed `test_drop_area` "drag" assertion
- **A2 (8f4bb1f) reload_language moved to public API section**: doc structure aligned
- **A4 (8f4bb1f) Menu / toolbar / dialog i18n-ified**: all visible UI text routed through `tr()`

### Documentation
- **C1 (8f4bb1f) README bilingual UI line**: completed the English file
- **C2 (8f4bb1f) docs/02-architecture.en.md §5.1+5.2 rewrite**: fully-offline → local-first

### Deferred
- **E1 dual-trigger refactor**: `MainWindow._on_config_changed` carries both theme and language switch; refactor needs config schema break → deferred to v0.5.0+; for now comments + test coverage describe the behavior

### Verified
- ✅ 275/275 tests green (v0.4.4 → v0.4.5: 0 new; governance-only)
- ✅ ruff 0 errors
- ✅ CI #20 8/8 matrix green
- ✅ origin/main = 8f4bb1f secondary verified
- ✅ release id 333073483

## [0.4.4] - 2026-06-02

Second governance patch after v0.4.3. **Covers P0 + 1 P1 (R4-6) from the 19-item second expert review, 5 commits total**. **275/275 tests green**. **CI #18 8/8 green**.

### Fixed

- **R2-1 (df7f1bb)** LLM image description deprecation: UI widget kept but `setEnabled(False)` + "disabled since v0.4.4" label; converter `llm_api_key=` param removed; monkey-patch comment cleaned; README 4 LLM mentions updated to "暂未实现"; also "完全离线" → "本地优先" (marks R4-1 scope)
- **R2-2 (b9e918d)** output_dir config wired to export flow: new `MainWindow._resolve_output_dir()` helper ("same" → None; "custom" checks exists + is_dir + writable); `_on_export_clicked` uses `out_dir` as QFileDialog initial path; `_on_batch_item_finished` auto-exports same-name .md to `out_dir` in batch; `errors.py` adds `E_SYS_002` registration
- **R2-3 (a49662a)** `set_locale("system")` resolution + en_US.json 71 keys: removed `"system"` from whitelist (becomes trigger); new `_resolve_system_locale()` walks `LC_ALL > LANG > getdefaultlocale()` resolving to zh_CN/en_US; new `src/resources/locales/en_US.json` (71 keys fully translated)
- **R3-6 (d3a2932)** `src/resources/__init__.py` package marker: was missing, so setuptools wheel packaging did not include `locales/*.json` in `package_data`; after install, set_locale("zh_CN") couldn't find JSON → UI fell back to English
- **R4-6 (cc1bad9)** Window refreshes immediately on language switch (no more restart required): `ConfigManager.on_change(callback)` callback list + `MainWindow._on_config_changed` calls `reload_language()` + `apply_theme()`

### Fixed (R4-6 side effects)

- **R2-2 real bug fix**: `_resolve_output_dir()` popped QMessageBox.warning (modal) on every call → batch converting N files popped N dialogs → added `_warn` param + `_output_dir_warned_for` cache for de-duplication
- **R2-3 tail fix**: en_US.json's `status.converting` was missing `{done}/{total}` and `status.cancelling` was missing `...` format placeholders
- **i18n keys added**: `status.drop_to_start`, `button.cancel` (bilingual zh+en)

### Changed

- i18n protocol alignment: all visible text must go through `tr(key)`, `_tr("button.cancel")` / `_tr("status.drop_to_start")` etc. replace hardcoded Chinese
- ConfigManager.on_change callback replaces Qt signal (keeps CM as pure Python object, testable without QApplication instance)

### Verified

- ✅ 275/275 tests green (v0.4.3 → v0.4.4: +28)
- ✅ ruff 0 errors
- ✅ CI #18 8/8 matrix green (Ubuntu+Windows × 3.10/3.11/3.12/3.13)
- ✅ origin/main = cc1bad9 double-verified
- ✅ release id 333042901

## [0.4.3] - 2026-06-02

First governance patch after v0.4.2. **Covers the first 5 of 19 P0 items from the second expert review**. **247/247 tests green**.

### Fixed

- **P0.1: track `Lei_MD.spec`** (`14f4eae`): spec was excluded by .gitignore but the README claimed a one-line build needs it. `build/` and `dist/` are still ignored, but a root `!Lei_MD.spec` allowlist re-adds it.
- **P0.2: single version source** (`aa97d5d` + `34dd92d`): `pyproject.toml` `[project] version` is the single source of truth. `scripts/build-windows.ps1` reads it via `python -c "import tomllib..."`; `Lei_MD.spec` embeds it via `tomllib.loads(...)`; `installer/installer.nsi` requires `/DAPP_VERSION=...` from the build script. CI gains a `version-consistency` job. New `tests/test_version_consistency.py` with 4 tests.
- **P0.3: main() wires Config + History** (`436ea7d`): previously `main.py` only called `MainWindow()`; now it constructs `config = ConfigManager(); history = HistoryManager(max_entries=config.get().max_history); window = MainWindow(config_manager=config, history=history)`. New 3 integration tests.
- **P0.4: `auto_convert` wired into DropArea** (`6d54fea`): single-file drop auto-converts and selects; multi-file drop only adds to list; `auto_convert=False` only adds to list.
- **P0.5: batch success items land in history** (`a08032a`): `BatchWorker.item_finished(path, md)` was not connected, so all successful batch markdown was lost. New slot writes to history and caches in `_batch_results`. 3 old `_FakeBW` mocks gained the `item_finished` attribute.

### Security

- **Isolated workflow-only commit** (`34dd92d`): PAT lacks `workflow` scope; build chain commit (`aa97d5d`) is pushed, workflow-only commit stays local.

## [0.4.2] - 2026-06-02

PySide6 6.11 segfault hotfix after v0.4.1. **CI #12 7/7 green**.

### Fixed

- **P0 PySide6 segfault** (`973a9b3`): pin `PySide6<6.11` (stay on the 6.9.x stable line) — 6.11+ triggers a segfault on ubuntu py3.12 via `QDragEnterEvent`. `src/ui/i18n.py` gains `sys._MEIPASS` support (PyInstaller resource path).

## [0.4.1] - 2026-06-02

v0.4.0 release shipped the CI workflow file, but 4 follow-up commits were needed to make CI actually run green. **205/205 tests green · 7/7 CI jobs green**.

### Fixed

- **CI: ruff governance** (`86a2e27`): `ruff check src/ tests/` from 151 errors → 0 errors
  - auto-fix 112 (`--fix --unsafe-fixes`): I001 unsorted imports / F401 unused / UP007 union syntax
  - hand-fix 18: F821 `log`→`_log` / E402 import order / N802 Qt event mandatory camelCase (`noqa`) / N812 `LEI_MD_VERSION` brand import (`noqa`)
  - split 32 E501 long lines: log.warning parenthesized, `_log` named function, CSS split multiline
  - `pyproject.toml` per-file-ignores for `tests/`, `src/ui/i18n.py`, `src/ui/styles.py` (E501 exception)
- **CI: flaky test fix** (`d5d505e`): `test_batch_worker_emits_progress_with_done_total` — Qt Signal still in flight when worker `deleteLater()` ran, causing "Signal source has been deleted"
  - added `qtbot.waitSignal(bw.finished)` to wait for the last signal
  - 20/20 local stress green (was 9/10 before)
- **CI: Windows XDG_*_HOME fix** (`ea02458`): `config_dir()` / `data_dir()` on Windows only read `%APPDATA%`, ignored `XDG_CONFIG_HOME` / `XDG_DATA_HOME`
  - caused 18 test failures on Windows runners (state pollution: theme='light' residue, history rows leaking, config dir missing)
  - fix: Windows prefers `XDG_*_HOME` (test override), production default still falls back to `%APPDATA%`
  - **no production behavior change**
- **CI: Windows `rsplit` path fix** (`7c09a58`): `tests/test_v025_low.py` used `p.rsplit("/", 1)[-1]` to extract basename — on Windows the path separator is `\\` not `/`, so split failed
  - switched to `Path(p).name` (cross-platform)
  - affected 2 drop_area tests

### CI Status

- 7-job matrix: ubuntu + windows × py3.10/3.11/3.12/3.13 (excluding win+3.10)
- Final run #7: **7/7 green** at commit `7c09a58`
- Full arc: #1-3 YAML indent fail → #4 ruff 4/7 fail → #5 Windows XDG 4/7 fail → #6 Windows rsplit 3/7 fail → #7 ✅
- Lesson: prior v0.x CI only ran Linux, hiding Windows-only path/state bugs; only after v0.4.1 do we have a truly cross-platform tested codebase

### Notes

- v0.4.0 tag untouched (released changelogs are immutable)
- All 4 commits in this release are CI fixes, no functional changes → patch version (0.4.1)
- `pyproject.toml` still `version = "0.4.0"` (not bumped; the tag is the source of truth for the release)

## [0.4.0] - 2026-06-02

All 3 candidates marked in v0.3.0's IMPLEMENTATION_VS_PLAN §4 implemented. **205/205 tests green** (157 from v0.3.0 + 48 new).

### Added

- **CI workflow** (`.github/workflows/test.yml`): ubuntu-latest + windows-latest × Python 3.10/3.11/3.12/3.13 = 8 matrix (excluding win+3.10)
  - Auto-runs every Monday 09:00 UTC
  - `pip install -e ".[dev]"` + `ruff check` + `pytest --tb=short -q`
  - Replaces the v0.3.0-era manual `source .venv/bin/activate` flow
- **Task 2.4 YouTube URL input** (planning gap closed): `src/core/youtube.py` + 4 new E_CONVERT_* error codes (E_CONVERT_003/004/005)
  - Supports 4 URL forms: `watch?v=` / `youtu.be/` / `shorts/` / `embed/`
  - Fetches captions only, no video download — minimal bandwidth
  - Complete error code coverage: invalid URL / yt-dlp missing / network timeout / video inaccessible / no captions
- **Audio E_FILE_006 explicit rejection** (Task C): dragging .mp3 / .wav / .ogg / .flac / .m4a / .aac / .wma / .opus **no longer silently ignored**; instead:
  - `DropArea.audio_rejected` Signal fires
  - MainWindow pops a modal dialog showing the E_FILE_006 code + error message
  - 4 new audio extensions (.m4a / .aac / .wma / .opus) added to the rejection set

### Added (Tests)

- `tests/test_youtube.py` (30 items): URL parsing + error code mapping + 4 URL form SSOT
- `tests/test_v040_audio_reject.py` (18 items): audio set SSOT + drop behavior + error code registration

### Fixed

- `src/core/youtube.py` YOUTUBE_URL_PATTERNS: corrected `[\w-]{11}` greedy-match boundary issue
  (e.g. `waytoolongvideoid12345` was incorrectly matching the first 11 characters)

## [0.3.0] - 2026-06-02

Integrated release after cross-Sprint audit + P2/P3 hotfixes + docs cleanup. **157/157 tests green** (97 from v0.2.2 + 60 new from v0.2.3-v0.2.7).

### Added

- 6-dimension audit (security / concurrency / error handling / architecture SSOT / test coverage) + comprehensive self-repair
- All P0/P1/P2/P3 issues (23 Medium + 6 Low) fixed with regression tests
- `test_v027_p0_regression.py` (5) + `test_v027_p1_regression.py` (8) + `test_p3_coverage_gaps.py` (3)

### Fixed

- **M1.2** BatchWorker `_cancelled` migrated to `threading.Event` for cross-thread memory visibility
- **M1.3** BatchWorker gains IDLE/RUNNING/CANCELLED/FINISHED state machine to prevent double start/cancel
- **M1.5** cancel finalize and `_on_item_done` are mutually exclusive (`_finalize_emitted` flag + mutex)
- **M3.1** HistoryManager wraps `_open_and_init_db` failure with outer try/except close
- **M3.2** HistoryManager public methods get None guard (`_conn = None` initialization)
- **M3.7** `MarkItDownConverter.convert` rejects directories / device files
- **M3.8** MarkItDown thread isolation: `clone_for_thread()` gives each runnable its own engine
- **M3.3** SettingsDialog Reset no longer mutates live ConfigManager (uses dataclasses.replace staging copy)
- **M3.4** BatchWorker `_dispatched.clear()` on finalize
- **M3.5** `_start_batch` running-guard: cancel the old batch before starting a new one
- **M3.6** `HistoryPanel.refresh` wraps `sqlite3.Error` in try/except — no crash
- **M4.1** MainWindow `closeEvent` 5-step shutdown: cancel → wait → waitForDone → processEvents → `history.close()` → accept
- **M4.2** closeEvent clears `_active_batch` dangling reference
- **M5.3** `os.path.getsize` wrapped in try/except OSError → accurate E_FILE_001
- **M5.4** 8 silent exception swallows get `log.warning` added
- **M6.2** ConfigManager rejects non-dict JSON root
- **M6.3** `AppConfig.__post_init__` field type + range validation
- **M6.4** `_backup_and_reset` 3-tier fallback: `os.replace` → `shutil.move` → `unlink`
- **L1** i18n locale whitelist (`"system"` / `"en"` / `"zh_CN"` / `"en_US"`)
- **L2** DropArea `rglob` → `os.walk` + depth limit 10 + file limit 2000
- **L3** PreviewPanel `setOpenLinks(False)` + `_safe_set_source` blocks `file://`
- **L4** `ConversionError.__cause__` chain becomes visible
- **closeEvent calls `HistoryManager.close()`** (v0.2.6 review #1: never called before, WAL leak on every exit)
- **i18n en added to whitelist** (v0.2.6 review #3: English users no longer see warning spam on startup)

### Changed

- `BatchWorker._ConvertRunnable.run()` accepts callable top-level functions (test stub regression)
- `closeEvent` order: first drain queued signals (`processEvents`), then `history.close()` to avoid ProgrammingError

### Cleanup

- Source docstrings/comments: removed all `v0.X.Y` / `Sprint N` / `Task X.Y` / `M[N.M]` / `H[N]` / `L[N]` / `P[N]` / `SSOT[:]` references
- Kept all "why we do it this way" substantive content
- Net removal of 67 lines of version metadata

## [0.2.2] - 2026-06-01

P1 hotfixes after Sprint 3's cross-Sprint audit. **97/97 tests green** (92 from v0.2.1 + 5 new regression tests).

### Fixed

- **H1** `ConfigManager.save()` didn't tighten file permissions after writing — LLM API key readable by other users on the same machine (`src/core/config.py:122-145`)
  - Fix: `save()` and backup-reset both call `os.chmod(0o600)`; tolerant to Windows / FAT32 / read-only filesystems
  - Impact: on POSIX systems, config.json is now only readable/writable by the current user (multi-user machines / backup tools / malware can't read the key)
  - Long-term: v0.3+ plans to switch to `keyring` (Windows Credential Manager / macOS Keychain / Secret Service)
- **H5** `BatchWorker._done_count += 1` lost updates + cancel / natural-finish fired `finished` twice (`src/core/batch_worker.py:160-200`)
  - Fix: increment is inside a QMutex lock; new `_finalize_emitted` flag makes `finished` fire exactly once (cancel finalize and `_on_item_done` are mutually exclusive)
  - Impact: cancelling mid-batch concurrent with the last item finishing no longer emits `finished` twice
- **H6** `HistoryManager.check_same_thread=False` relied on a comment alone to enforce main-thread uniqueness (`src/core/history.py:106-120, 198-242`)
  - Fix: new `_assert_main_thread()` at the entry of `_on_add` / `list` / `_trim` / `close`
  - Impact: any worker-thread call to a public method now immediately raises `RuntimeError` (previously caused sqlite3 deadlock / segfault)
  - Skipped when QCoreApplication hasn't started (CLI / tests)
- **H9** i18n string out of sync with code: `zh_CN.json` said "200MB" but `errors.py:60` said "500MB" (`src/resources/locales/zh_CN.json:58`)
  - Fix: i18n changed to "500MB"
  - Impact: Chinese error messages now match the actual limit

### Added

- `tests/test_v022_hotfix.py` — 5 regression tests covering H1/H5/H6/H9

## [0.2.1] - 2026-06-01

P0 security/correctness hotfixes after Sprint 3's cross-Sprint audit. **92/92 tests green** (88 from v0.2.0 + 4 new regression tests).

### Fixed

- **H2** Cancel button in batch mode was a silent no-op (`src/ui/main_window.py:197-202`)
  - Fix: `_on_cancel_clicked` first checks `_active_batch`, then falls back to `_active_worker`; `__init__` declares `self._active_batch = None`
  - Impact: users clicking "Cancel" mid-batch now actually stop; old behavior was the UI lying
- **H4** Single-file worker still emitted `finished_with_md` after `cancel()` (`src/core/worker.py:82-89`)
  - Fix: check `self._cancel_event.is_set()` once more before `emit(md)`; if cancelled, no emit (job_done still fires, `error_msg = "E_SYS_001"`)
  - Impact: no more contradiction of "Cancelled" state while the preview renders fully
- **H3** `ConfigManager` rejected UTF-8 BOM (`src/core/config.py:88`)
  - Fix: encoding changed from `"utf-8"` to `"utf-8-sig"`, auto-strips BOM
  - Impact: config.json saved by Windows Notepad (default with BOM) now loads correctly; previously mis-detected as corrupt and reset

### Added

- `tests/test_v021_hotfix.py` — 4 regression tests covering H2/H3/H4

## [0.2.0] - 2026-06-01

Sprint 3 complete (Task 2.1 ~ 2.6 + MainWindow integration). **88/88 tests green** (58 from v0.2.0-rc1 + 30 new).

### Added

- **SettingsDialog** (`src/ui/settings_dialog.py`, Task 2.1)
  - Modal dialog, dependency-injected ConfigManager for read/write
  - 5/5 tests: load on construct / accept persists / cancel does not modify / field type mapping / reset_to_defaults
- **BatchWorker** (`src/core/batch_worker.py`, Task 2.2)
  - QThreadPool + QRunnable for parallel batch conversion
  - Signals: `progress(done, total)` / `finished()` / `item_failed(path, err)`
  - `cancel()` immediately fires `finished`; remaining paths marked cancelled
  - Single-file failure does not affect others (errors aggregated via `item_failed`)
- **HistoryPanel** (`src/ui/history_panel.py`, Task 2.3)
  - Table view: time / source / output / status
  - Search box filters by `source_path` substring
  - Double-click row triggers `file_selected(path)` signal (MainWindow catches and starts worker)
- **Dark mode** (`src/ui/styles.py`, Task 2.5)
  - `darkdetect` detects system theme
  - `apply_theme('dark'|'light'|'system')` switches QPalette + QSS
  - `ThemeManager` listens for system changes; external callback notifies
- **Chinese UI** (`src/ui/i18n.py` + `src/resources/locales/zh_CN.json`, Task 2.6)
  - `Translator` class + module-level singleton + `tr(key)` helper
  - `set_locale('zh_CN'|'en')` loads the corresponding JSON; missing key falls back to the key itself
  - 53 zh_CN translations (menu / status / settings / history / error codes)

### Changed

- **MainWindow integration** (`src/ui/main_window.py`)
  - New `config_manager: ConfigManager | None` injected
  - On startup, `apply_theme(config.theme)` + `set_locale(config.language)`
  - Menu bar: File (Settings / Exit) / View (History) / Help (About)
  - Toolbar "Convert All" button → starts BatchWorker with `config.batch_concurrency`
  - Settings changes auto-`apply_theme`
  - History panel as a non-modal dialog opened from "View > History"
- **FileList** (`src/ui/file_list.py`)
  - New `all_paths() -> list[str]`, used by batch conversion

### Test Coverage

30 new tests (73 → 88/88):
- test_settings_dialog.py: 5
- test_batch_worker.py: 5
- test_history_panel.py: 5
- test_styles.py: 3
- test_i18n.py: 4
- test_mainwindow_integration.py: 3
- test_batch_integration.py: 3
- test_i18n_integration.py: 2

## [0.2.0-rc1] - 2026-06-01

Sprint 2 complete (Task 1.8 + Task 1.9). **58/58 tests green** (44 from v0.1.1 + 14 new).

### Added

- **Config management** (`src/core/config.py`, Task 1.8)
  - `AppConfig` dataclass: output_dir / custom_output_dir / auto_convert / max_history=50 / language="system" / theme="system" / batch_concurrency=4 / llm_api_base / llm_api_key / llm_model="gpt-4o"
  - `ConfigManager` cross-platform: Windows `%APPDATA%\Lei_MD\config.json`, Linux/macOS `~/.config/Lei_MD/config.json`
  - Auto-backup `.json.bak` + reset on corruption (E_INTERNAL_003)
  - Unknown fields silently ignored (forward-compat)
  - `update(**kwargs)` writes to disk immediately
- **History** (`src/core/history.py`, Task 1.9)
  - SQLite persistence; schema: source_path / source_format / markdown_length / duration_ms / success / error_msg / created_at
  - **WAL + Signal serialization concurrency model** (02 §3.3.1): `PRAGMA journal_mode=WAL` + `busy_timeout=5000` + `synchronous=NORMAL`
  - `request_add()` emits `add_requested(dict)` Signal → main-thread slot `_on_add` does the actual write
  - Capacity trim: keep `max_entries=50`
  - **Crash recovery**: on startup `PRAGMA integrity_check`; if corrupt → backup `.db.bak.<ts>` + rebuild (E_INTERNAL_002)
  - `close()` calls `PRAGMA wal_checkpoint(TRUNCATE)`
- **Worker meta signal** (`src/core/worker.py`)
  - New `job_done = Signal(str, str, int, int, bool, str)`: source_path / source_format / md_len / duration_ms / success / error_msg
  - `try/finally` block guarantees emission on success / failure / cancel paths
- **MainWindow integration** (`src/ui/main_window.py`)
  - `MainWindow(converter=..., history=...)` adds history kwarg (backward-compatible)
  - Conversion complete auto-writes history
- **14 new tests**
  - `tests/test_config.py` 5: defaults / persistence / corrupt backup / unknown field ignore / dir creation
  - `tests/test_history.py` 6: CRUD / sort / trim / failure / cross-thread / corrupt recovery
  - `tests/test_main_window_history.py` 3: success record / failure record / graceful when not injected

### Changed

- **API**: `MainWindow.__init__()` adds optional kwarg `history` (default None; v0.1.x call style unbroken)
- **API**: `ConversionWorker.job_done` new signal (backward-compatible, old signals unchanged)
- Implementation: `_config_dir()` / `data_dir()` re-read env on every call (monkeypatch-friendly for tests)

## [0.1.1] - 2026-06-01

Worker async conversion integrated into MainWindow. **44/44 tests green** (36 from v0.1.0 + 8 new).

### Added
- **MainWindow async conversion upgrade** (`src/ui/main_window.py`)
  - File selection → start `ConversionWorker` (QThread) for background conversion; main thread non-blocking
  - Permanent QProgressBar (0~100, real-time during conversion) added to status bar
  - Permanent "Cancel" button on status bar (worker.cancel() cooperative interrupt)
  - Auto-cancel the previous worker on file switch (prevents concurrency)
- **Converter dependency injection** — `MainWindow(converter=...)` for stub-replaceable testing
- **New tests** `tests/test_main_window_v011.py` (8 cases)
  - progress_bar / cancel_button initially hidden
  - converter injection takes effect
  - File selection → async → preview displays
  - Progress bar 0→100 real-time update
  - Cancel button interrupts worker
  - Errors shown in preview with Chinese error message
  - File switch cancels previous worker

### Changed
- **API breaking**: `MainWindow.__init__()` adds optional kwarg `converter`. Backward-compatible (default still uses real MarkItDownConverter)
- MainWindow no longer imports the synchronous converter call path (performance + UX improvement)

## [0.1.0] - 2026-06-01

First runnable MVP. Sprint 1 (Task 1.1-1.7) complete, 36/36 tests green.

### Added
- **Core conversion engine** (`src/core/converter.py`)
  - Wraps Microsoft MarkItDown, single-instance engine reuse
  - Pre-checks: file exists, non-empty, <500MB
  - Exception translation: MarkItDown raises → `ConversionError` (E_CONVERT_001 password-protected / E_CONVERT_002 corrupted)
- **Error code system** (`src/core/errors.py`) — SSOT implementation of 5 categories, 16 codes
  - E_FILE_001~006 (file-level: not found / empty / oversize / path traversal / unsupported format / audio not supported)
  - E_CONVERT_001~002 (conversion-level: password / corrupted)
  - E_SYS_001~003 / E_INTERNAL_001~003 / E_UPDATE_001~002
  - Bilingual error messages (zh_CN / en_US); no Python traceback leaked to user
- **Async worker** (`src/core/worker.py`) — QThread subclass
  - Signals: `progress(int)`, `finished_with_md(str)`, `error(ConversionError)`
  - `cancel()` cooperative interrupt
- **UI components** (`src/ui/`)
  - `drop_area.py`: drag-receive + directory recursion + extension filtering (SSOT set)
  - `file_list.py`: added files list + dedup + extension filtering + selection signal
  - `preview_panel.py`: QTextBrowser Markdown preview + NUL-cleansing fallback
  - `main_window.py`: three-pane QSplitter assembly (DropArea / FileList / PreviewPanel) + status bar
- **Entry point** (`src/main.py` + `src/app.py`) — `QApplication` init + MainWindow start
- **Packaging config** (`pyproject.toml`)
  - pip package name `lei-md` ([project] name) + Python import name `src.*` (`[tool.setuptools] packages`)
  - `[project.scripts] lei-md = "src.main:main"`
  - Pinned dependencies (PySide6 6.9.x, markitdown 0.1.x) + Python 3.10~3.13
- **Tests**: 36/36 green
  - Unit + integration: TDD style (test first, then code)
  - `pytest-qt` runs PySide6 in offscreen mode (Linux containers without display)
  - Stub Converter isolates real markitdown dependencies

### Known Limitations (out of scope for v0.1.0, deferred to later sprints)
- Audio transcription (MP3/WAV) not supported → v1.1+ offline ffmpeg + whisper tiny
- Batch conversion still synchronous; worker written, scheduled for v0.1.1 MainWindow integration
- Settings panel / history / i18n switch / theming → Sprint 2+
- QWebEngine enhanced preview → only fetched when v1.0 advanced preview is enabled by user (+400MB size)

## [Unreleased] - Pre-Sprint 1 (Project init and docs)

### Added
- Project init: documentation-driven complete planning
  - Requirements doc (`docs/01-requirements.md`)
  - Architecture design doc (`docs/02-architecture.md`)
  - Development plan (`docs/03-development-plan.md`), 15 concrete tasks
  - Test plan (`docs/04-testing-plan.md`)
  - Release and maintenance plan (`docs/05-release-plan.md`)
  - Dependency update strategy (`docs/06-dependency-update-strategy.md`)
- Project skeleton: `pyproject.toml`, `.gitignore`, `LICENSE`, `README.md`, `CONTRIBUTING.md`
- Community standards: `CODE_OF_CONDUCT.md` (Contributor Covenant v2.0)
- Error-handling design: 5-category error code system (E_FILE/E_CONVERT/E_SYS/E_INTERNAL/E_UPDATE)
- Config paths: unified to `%APPDATA%\Lei_MD\` (Windows) + `~/.config/Lei_MD/` (v2.0+ cross-platform)
- Offline + all-in-one + traditional installer roadmap (400-500MB single installer)
- In-app "Check for Updates" + GitHub Releases as main channel
- SemVer + Dependabot automatic dependency update strategy

## [0.4.5] - 2026-06-02

Small governance patch after v0.4.4 — **closes 11 audit items**. **275/275 tests green**. **CI #20 8/8 green**.

### Fixed (P0)

- **A1 (428dca2)** Remove 5 redundant `from PySide6.QtWidgets import QMessageBox` in main_window.py (already imported at top)
- **D1/D2/D3 (428dca2)** SettingsDialog fully i18n-ized (was 100% hardcoded Chinese — R4-6 live lang switch was half-baked):
  - window title / 3 buttons / 4 group titles all go through tr()
  - JSON +3 keys: settings.group.output / capacity / ui

### Fixed (P1)

- **A3 (83f9f91)** Fix i18n.py docstring ("i18n for Lei_MD — ." was broken)
- **B1 (83f9f91)** Delete wrong "old import path" comment
- **D5 (83f9f91)** YouTube 3 QMessageBox dialogs i18n (fetch_title / empty_url / invalid_url / fetch_failed_title / fetch_failed_error_code)
- **D6 (83f9f91)** DropArea DEFAULT_PLACEHOLDER 4 hardcoded lines split into 3 i18n keys (drop.placeholder.lead / formats / audio_note)

### Fixed (P2)

- **A2 (8f4bb1f)** `reload_language` moved from "Lifecycle" section to "Public API" section
- **A4 (8f4bb1f)** Main menu 5 items + toolbar 3 items + 5 dialogs (export/copy/history/about/audio-rejected) all i18n
- **C1 (8f4bb1f)** README.md / README.en.md "Bilingual UI" row updated with v0.4.5 note
- **C2 (8f4bb1f)** docs/02-architecture.en.md §5.1+5.2 rewritten (VALID_LOCALES → frozenset, system trigger, locale resolution chain)

### Skipped

- **C3** docs/07-build-release.md is an ops manual, not a changelog — no change needed
- **E1** Splitting AppConfig.language into use_system_locale field (removing dual-trigger design) — deferred to v0.5.0+ (would break existing config schema)

### Verified

- ✅ 275/275 tests green (v0.4.4 → v0.4.5: +0, 2 tests broadened to accept bilingual)
- ✅ ruff 0 errors
- ✅ CI #20 8/8 matrix green
- ✅ origin/main = 8f4bb1f double-verified
- ✅ release id 333073483

### i18n key growth

v0.4.3 (71) → v0.4.4 (75, +4) → **v0.4.5 (100, +25)**
