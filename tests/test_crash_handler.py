"""Tests for crash_handler (v0.4.8).

Regression test for the v0.4.0~v0.4.7 lie: the UI told users
"已记录到 crash.log" but no code ever wrote a file. This module
implements that contract; these tests verify it.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from src.core import crash_handler


@pytest.fixture
def fake_crash_dir(tmp_path, monkeypatch):
    """Force crash_handler to write into a tmp dir regardless of platform."""
    crash_dir = tmp_path / "crash.log"
    monkeypatch.setattr(crash_handler, "_resolve_crash_dir", lambda: crash_dir)
    return crash_dir


def test_write_creates_file_in_resolved_dir(fake_crash_dir):
    """write(exc) creates a .log file under the resolved dir."""
    try:
        raise ValueError("boom from test")
    except ValueError as e:
        path = crash_handler.write(e, context="unit test", filename="/tmp/x.pdf")

    assert path is not None
    assert path.parent == fake_crash_dir
    assert path.exists()
    assert path.suffix == ".log"
    # Timestamp prefix YYYYMMDD-HHMMSS-XXXX
    assert re.match(r"^\d{8}-\d{6}-[0-9A-F]{4}\.log$", path.name)


def test_write_includes_traceback_text(fake_crash_dir):
    """The log file must contain the original traceback (not just header)."""
    try:
        raise RuntimeError("specific error string xyz123")
    except RuntimeError as e:
        path = crash_handler.write(e, context="test_ctx", filename="/tmp/a.pdf")

    text = path.read_text(encoding="utf-8")
    assert "specific error string xyz123" in text
    assert "Traceback" in text
    assert "test_ctx" in text
    assert "/tmp/a.pdf" in text


def test_write_includes_version_and_platform(fake_crash_dir):
    """The header should include version, platform, python version."""
    try:
        raise ValueError("x")
    except ValueError as e:
        path = crash_handler.write(e, context="ctx")

    text = path.read_text(encoding="utf-8")
    assert "Lei_MD crash report" in text
    assert "version:" in text
    assert "platform:" in text
    assert "python:" in text


def test_write_returns_none_on_permission_error(fake_crash_dir, monkeypatch):
    """If writing fails, write() returns None instead of raising."""
    # Force the Path.write_text call to fail
    def _boom(self, *args, **kwargs):  # noqa: ARG001
        raise PermissionError("disk locked")

    monkeypatch.setattr(Path, "write_text", _boom)
    try:
        raise ValueError("x")
    except ValueError as e:
        result = crash_handler.write(e)

    assert result is None  # best-effort, never raises


def test_write_chains_to_cause(fake_crash_dir):
    """When caller passes a ConversionError-like wrapper, write() the underlying cause.

    This is the path taken by worker.py when ce.cause is set — the
    underlying ValueError (not the wrapper) is what users need to see.
    """
    try:
        raise ValueError("underlying cause")
    except ValueError as underlying:
        # Simulate ConversionError(cause=underlying) the way worker.py does it
        wrapper = RuntimeError("wrapper")
        wrapper.__cause__ = underlying
        path = crash_handler.write(wrapper.__cause__)

    text = path.read_text(encoding="utf-8")
    assert "underlying cause" in text


def test_resolve_crash_dir_dev_mode(tmp_path, monkeypatch):
    """In dev (not frozen), _resolve_crash_dir() points under repo root."""
    # Make sure we look like dev (not frozen)
    monkeypatch.delattr(sys := __import__("sys"), "frozen", raising=False)
    crash_dir = crash_handler._resolve_crash_dir()
    # Should end with /crash.log
    assert crash_dir.name == "crash.log"
    # And live under the repo root (src/core/crash_handler.py -> parents[2])
    assert crash_dir.parent.name == "markitdown-gui"
