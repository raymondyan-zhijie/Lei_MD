# Lei_MD Dependency Update Strategy

> 🌐 **Language**: [中文](06-dependency-update-strategy.md) | **English**

> **Brand:** leimengde
> **Version:** Planning snapshot (actual deps in [pyproject.toml](../../pyproject.toml)) | **Date:** 2026-06-01
> **Scope:** Version evolution and upstream dependency management after the initial release
>
> v0.4.0 actual dependency versions and strategy: see [IMPLEMENTATION_VS_PLAN.md](IMPLEMENTATION_VS_PLAN.md).

> **SSOT index**: This document is the **authoritative definition** of:
> - §3 markitdown upstream update strategy
> - §4 Underlying library update strategy
> - §5 SemVer release rules
> - §7 Failure recovery mechanism

---

## 1. Overview

Lei_MD is a GUI wrapper for Microsoft MarkItDown. **It is not an island** — it depends on a **critical upstream** (MarkItDown) and **7+ underlying libraries** (PySide6, PyMuPDF, python-docx, etc.). Any one of them updating can break this project.

This document defines:
1. The follow-up strategy for upstream MarkItDown updates
2. The handling flow for underlying library updates
3. Lei_MD's own SemVer release rules
4. User update channels
5. Recovery mechanism on update failure

---

## 2. Dependency Layers

```
┌─────────────────────────────────────────┐
│  Lei_MD v0.4.0                           │   ← Us
├─────────────────────────────────────────┤
│  markitdown[all] v0.1.x                  │   ← Critical upstream (1)
├─────────────────────────────────────────┤
│  PySide6 / markdown / Pygments /        │   ← Underlying libs (7+)
│  PyMuPDF / python-docx / python-pptx /  │
│  openpyxl / magika / pydub / ...        │
├─────────────────────────────────────────┤
│  Python 3.10 / 3.11 / 3.12 / 3.13       │   ← Runtime
└─────────────────────────────────────────┘
```

**Update frequency (rough)**:
- MarkItDown: 1-2 minors per month
- PySide6: 1 minor per quarter
- Underlying libs: Dependabot PRs every week

---

## 3. Upstream MarkItDown Update Strategy

### 3.1 Version lock rules

`pyproject.toml` current constraint (at v0.4.0):
```toml
"markitdown[all]>=0.1.0,<0.2.0"
```

- **`<0.2.0` upper bound**: Do not actively open up **before v0.2.0 is released**.
  - Actually v0.2.0 has been released; this is a historical pin.
- Dependabot auto-opens PR (`versioning-strategy: increase within bounds`).
- When `markitdown v0.2.0` is published → Dependabot **will not** auto-upgrade (out of bounds) → manual review.

### 3.2 Evaluation cycle (when markitdown ships a minor)

| Step | Action | Time |
|------|------|------|
| 1 | Read release notes (breaking changes?) | 1 day |
| 2 | Local `pip install markitdown==0.2.0` + run tests | half day |
| 3 | Run sample conversions (PDF / Word / Excel / PPT / HTML × 1) | half day |
| 4 | Check whether `MarkItDown.convert()` signature changed | 1 hour |
| 5 | Update `pyproject.toml` cap + update code | 1 day |
| 6a | No breaking → open PR "deps: bump markitdown to 0.2.x" | half day |
| 6b | Breaking → open PR "feat!: migrate to markitdown 0.2 API" + **Lei_MD minor bump** | 1-2 days |

### 3.3 Emergency handling (markitdown ships a serious bug)

If upstream ships `0.1.5` to fix a serious bug:
- **Do not wait until Monday**; manually PR the same day
- PR title: `hotfix(deps): bump markitdown to 0.1.5 for CVE-xxx`
- hotfix branch → merge to main → immediate patch release (0.1.5.1)

---

## 4. Underlying Library Update Strategy

### 4.1 Automatic vs manual

| Library | Type | Strategy |
|----|------|------|
| PySide6 | GUI core | **Manual**, major deferred 1 minor cycle |
| PyMuPDF / pdfminer | PDF parsing | Dependabot auto (patch + minor) |
| python-docx | Word parsing | Dependabot auto |
| python-pptx | PPT parsing | Dependabot auto |
| openpyxl | Excel parsing | Dependabot auto |
| magika | Format detection | Dependabot auto |
| markdown | Markdown rendering | Dependabot auto |
| Pygments | Code highlighting | Dependabot auto |

### 4.2 Dependabot config

`.github/dependabot.yml` (planned):
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
    groups:
      minor-and-patch:
        patterns: ["*"]
        update-types: ["minor", "patch"]
    labels:
      - "dependencies"
    commit-message:
      prefix: "deps"
    # PySide6 exception, separate PR
    ignore:
      - dependency-name: "PySide6"
        update-types: ["minor", "major"]
```

### 4.3 PR merge rules

| PR type | Merge method |
|---------|----------|
| Dependabot patch auto PR | **Merge on CI pass** (auto-merge enabled) |
| Dependabot minor auto PR | Manual review + local smoke (start app + convert 1 file) |
| Dependabot major PR | Manual evaluation, usually deferred |
| PySide6 minor | Separate evaluation; CI must run full platform + full samples |

### 4.4 CI smoke test (auto-run)

`pytest -m smoke`:
- Start app
- Convert 1 .txt
- Convert 1 .pdf
- Convert 1 .docx
- Verify history write to SQLite

**This is the hard threshold for PR merge** — any failure blocks the merge.

---

## 5. Lei_MD Self SemVer Release Rules

### 5.1 Version convention

```
v MAJOR . MINOR . PATCH
  ↑        ↑        ↑
  Major    New      Bug fix
  breaking feature
```

### 5.2 Trigger conditions

| Change | Version bump | Example |
|------|-----------|------|
| Bug fix, performance optimization, doc update | **PATCH** (0.0.X) | v0.4.0 → v0.4.1 |
| New P1 feature, markitdown 0.1.x → 0.1.y (patch) | **PATCH** (0.0.X) | v0.4.0 → v0.4.1 |
| New P2 advanced feature, underlying lib minor upgrade, markitdown 0.1.x → 0.2.0 (minor) | **MINOR** (0.X.0) | v0.4.0 → v0.5.0 |
| GUI rewrite, config schema incompatible, markitdown 0.x → 1.0 | **MAJOR** (X.0.0) | v0.x.x → v1.0.0 |

### 5.3 Automation

`.github/workflows/release.yml` (planned):
- Listens for `v*` tag
- Runs all tests
- PyInstaller + NSIS packaging
- Creates GitHub Release (auto-generates notes)

**Manually tag** (not automated in CI):
```bash
git tag -a v0.4.1 -m "hotfix: fix X"
git push origin v0.4.1
```

---

## 6. User-side Updates

### 6.1 Three channels

| Channel | Use case | Frequency |
|------|------|------|
| **In-app "Check for Updates"** | Installed users | User-initiated |
| **GitHub Releases RSS** | Followers | Each release |
| **GitHub Watch → Releases only** | Developers | Email notification |

### 6.2 In-app "Check for Updates" implementation

```python
# src/core/updater.py
import urllib.request
import json
from packaging import version

GITHUB_API = "https://api.github.com/repos/raymondyan-zhijie/Lei_MD/releases/latest"
CURRENT = "0.4.0"

def check_update() -> dict | None:
    """Returns new version info, or None if no update."""
    try:
        with urllib.request.urlopen(GITHUB_API, timeout=5) as resp:
            data = json.loads(resp.read())
        latest_tag = data["tag_name"].lstrip("v")
        if version.parse(latest_tag) > version.parse(CURRENT):
            return {
                "version": latest_tag,
                "url": data["html_url"],
                "notes": data["body"],
            }
    except Exception as e:
        log_error("E_UPDATE_001", e)  # does not block user
    return None
```

**UI dialog**:
```
┌─────────────────────────────┐
│  New version v0.5.0 found     │
│                              │
│  [Full release notes]         │
│                              │
│  [Visit download]  [Later]  [Ignore]
└─────────────────────────────┘
```

### 6.3 No auto-update (**by design**)

- Offline product philosophy: user controls upgrade timing
- Avoid background silent downloads of large files
- NSIS installer requires explicit user action

---

## 7. Failure Recovery

### 7.1 User update failure

| Scenario | Behavior | Code |
|------|------|--------|
| No network | "Update check failed, please try again later" | `E_UPDATE_001` |
| GitHub API rate limit | "Service busy, please try again later" | `E_UPDATE_002` |
| Download interrupted | Show downloaded percentage + resume button | `E_UPDATE_003` |
| Checksum mismatch | Reject install, prompt re-download | `E_UPDATE_004` |
| Disk full | Prompt to free disk | `E_UPDATE_005` |
| Old → new schema incompatible | NSIS uninstalls old + installs new (**no config migration**) | (NSIS handles) |

### 7.2 In-app SQLite corruption

On startup, detect → backup `.bak` → rebuild (see [02-architecture.md §6.4](02-architecture.md))

### 7.3 In-app config corruption

On startup, detect → backup `.bak` → reset to defaults (same [02 §6.4](02-architecture.md))

### 7.4 Power loss mid-update

NSIS installer **atomicity** guarantee:
- Installation script either fully succeeds or fully fails
- No "half-installed" state

---

## 8. Monitoring & Alerts (v1.1+ roadmap)

| Metric | Source | Alert |
|------|------|------|
| Crash rate | Sentry / self-hosted crash report | >1% triggers alert |
| Update failure rate | In-app `E_UPDATE_*` reports | >5% triggers alert |
| MarkItDown upstream release | GitHub Watch | Notify on receipt, manual evaluation |

**v1.0 ships no monitoring** — DAU is below the threshold to make it meaningful.

---

## 9. Long-term Roadmap (update perspective)

```
v0.4.0  2026-06   CI workflow + YouTube + audio E_FILE_006 (released, 205/205 green)
v0.5.0  2026 Q3   Add "Check for Updates" + auto-follow markitdown 0.1.x
v0.6.0  2026 Q4   WinGet / Scoop distribution + optional auto-update
v1.0.0  2027 Q3   Cross-platform (macOS / Linux) + platform-specific packaging
```

---

## 10. References

- [Dependabot configuration docs](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file)
- [Semantic Versioning 2.0.0](https://semver.org/)
- [PyInstaller + NSIS packaging practice](https://nsis.sourceforge.io/Download)
- [Microsoft MarkItDown releases](https://github.com/microsoft/markitdown/releases)
