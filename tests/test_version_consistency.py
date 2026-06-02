"""Version-consistency test.

P0.2 from the 2026-06-02 expert review: every place a version number is
hard-coded must agree with pyproject.toml. This test is the local mirror of
the ``version-consistency`` GitHub Actions job — if it passes locally and
the job fails, drift was just introduced.

What we check:
  1. ``src.__version__`` == ``pyproject.toml`` ``[project] version``
  2. No hard-coded ``0.X.Y`` strings in **executable lines** of the build
     chain (scripts/build-windows.ps1, installer/installer.nsi, Lei_MD.spec).
     Comment lines starting with ``#`` (bash/PS), ``;`` (NSIS), or ``#`` in
     Python are ignored — documentation examples are fine.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tomllib 是 Python 3.11+ 标准库（PEP 680）。CI 矩阵含 3.10
# （github-hosted runners 仍提供 3.10），所以 py3.10 走 tomli backport，
# py3.11+ 直接用 stdlib。R1.2 写的时候没注意 — 当时 v0.4.2 CI 矩阵把 3.10
# 排除了，但 v0.4.1 之前的 CI 没排；现在 R1.6 跑了 v0.4.3 = 7 job 矩阵含
# 3.10 触发 ImportError。
try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # py3.10
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"

# Files where a hard-coded version string in *executable* lines would be a
# problem. Comments are excluded so the README-style example
# "; → Lei_MD-0.4.2-Setup.exe" doesn't false-positive.
VERSION_SENSITIVE_FILES = [
    ROOT / "scripts" / "build-windows.ps1",
    ROOT / "installer" / "installer.nsi",
    ROOT / "Lei_MD.spec",
]

# 0.4.2 / 0.10.0 / 1.0.0-rc.1 — but NOT the bare 1 or 0 cases
VERSION_RE = re.compile(r"\b\d+\.\d+\.\d+(?:[-.][A-Za-z0-9.]+)?")

# Comment prefixes per file
COMMENT_PREFIXES = ("#", ";")


def _is_comment_line(line: str) -> bool:
    stripped = line.lstrip()
    return any(stripped.startswith(p) for p in COMMENT_PREFIXES)


def _read_pyproject_version() -> str:
    with PYPROJECT.open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def _read_src_version() -> str:
    """Import src package and read __version__ without triggering heavy deps."""
    import importlib

    src = importlib.import_module("src")
    return src.__version__


def test_src_and_pyproject_agree() -> None:
    py = _read_pyproject_version()
    src = _read_src_version()
    assert py == src, f"pyproject.toml={py!r} != src.__version__={src!r}"


@pytest.mark.parametrize(
    "path",
    VERSION_SENSITIVE_FILES,
    ids=lambda p: str(p.relative_to(ROOT)),
)
def test_no_hardcoded_version(path: Path) -> None:
    """No hard-coded semver in non-comment lines of build-chain files.

    Build files must read from pyproject.toml (or accept it as a parameter
    like NSIS's /DAPP_VERSION).
    """
    if not path.exists():
        pytest.skip(f"{path} not present")
    text = path.read_text(encoding="utf-8")
    bad: list[tuple[int, str, list[str]]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if _is_comment_line(line):
            continue
        matches = VERSION_RE.findall(line)
        if matches:
            bad.append((lineno, line.rstrip(), matches))
    assert not bad, (
        f"Hard-coded version in {path.relative_to(ROOT)}:\n"
        + "\n".join(f"  L{ln}: {line!r} → {m}" for ln, line, m in bad)
    )
