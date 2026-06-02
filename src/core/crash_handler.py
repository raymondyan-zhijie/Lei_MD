"""Crash log handler — write unhandled exceptions to a file.

v0.4.8 fix: prior to this, the UI told the user "已记录到 crash.log"
but no code ever wrote that file. The error message was a lie.
This module fulfills that promise by writing the original traceback
to a timestamped file under %LOCALAPPDATA%\Lei_MD\crash.log\.

Design:
- Path: %LOCALAPPDATA%\\Lei_MD\\crash.log\\YYYYMMDD-HHMMSS-<random>.log
  - %LOCALAPPDATA% works for both normal and OneFile-frozen apps
  - One crash per file (no append) → easy to share, never grows huge
  - Subdir ``crash.log`` (with the dot) so users searching for
    "crash.log" find it (matches the UI promise)
- Best-effort: never raise out of write() — if disk is full or
  permissions are blocked, the function returns silently so we don't
  crash the crash handler
- Thread-safe: only called from QThread.run() except branches, but
  we still take a lock to be safe (multiple workers could fail at
  once)
- Dev mode (no ``sys._MEIPASS``): write to repo-root ``crash.log/``
  so it's findable during ``python src/main.py`` testing

Why not use ``logging`` / ``logger.exception``?  Because:
1. The app doesn't configure a file handler for the root logger.
   Adding one would change global state and risk log spam in
   production.
2. We need a separate per-crash file with the full traceback +
   contextual info (filename, timestamp, version). Standard logging
   is line-oriented and would interleave with other log records.
3. Users occasionally want to share a single crash file with the
   dev — having a unique path per crash makes that easy.
"""

from __future__ import annotations

import os
import platform
import random
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path


_write_lock = threading.Lock()


def _resolve_crash_dir() -> Path:
    """Return the directory crash logs go into.

    Frozen (PyInstaller OneFile) on Windows/macOS/Linux: ``%LOCALAPPDATA%\\Lei_MD\\crash.log\\``
    Dev (no ``sys._MEIPASS``): ``<repo>/crash.log/`` so a ``python src/main.py`` run
    also drops the file in a findable spot.
    """
    if getattr(sys, "frozen", False):
        # OneFile: use OS user data dir
        system = platform.system()
        if system == "Windows":
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        elif system == "Darwin":
            base = os.path.expanduser("~/Library/Application Support")
        else:
            base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        return Path(base) / "Lei_MD" / "crash.log"
    # Dev: repo root / crash.log/
    # __file__ is .../src/core/crash_handler.py → parents[2] = repo root
    return Path(__file__).resolve().parents[2] / "crash.log"


def write(exc: BaseException, *, context: str = "", filename: str = "") -> Path | None:
    """Write a single crash report to disk. Returns the path or None on failure.

    Args:
        exc: The original exception (e.g. ``ce.cause`` or the raw ``e``).
        context: Optional short label, e.g. "ConversionWorker".
        filename: The file being processed when the crash happened, for
            user reference. Already printed in the report but accepted
            separately so the caller doesn't have to mutate the
            traceback text.

    Returns:
        Absolute path of the written log, or ``None`` if writing
        failed (best-effort — never raises).
    """
    try:
        crash_dir = _resolve_crash_dir()
        with _write_lock:
            crash_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            # random suffix avoids collisions if two crashes land in the same second
            rand = f"{random.randint(0, 0xFFFF):04X}"
            log_path = crash_dir / f"{stamp}-{rand}.log"

            tb_text = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
            header_lines = [
                f"Lei_MD crash report",
                f"timestamp:  {datetime.now().isoformat(timespec='seconds')}",
                f"version:    {_get_version()}",
                f"platform:   {platform.platform()}",
                f"python:     {sys.version.split()[0]}",
                f"frozen:     {getattr(sys, 'frozen', False)}",
            ]
            if context:
                header_lines.append(f"context:    {context}")
            if filename:
                header_lines.append(f"file:       {filename}")
            header = "\n".join(header_lines) + "\n\n"

            log_path.write_text(header + tb_text, encoding="utf-8", errors="replace")
            return log_path
    except Exception:
        # Last resort: don't crash the crash handler
        return None


def _get_version() -> str:
    try:
        from src import __version__  # type: ignore
        return str(__version__)
    except Exception:
        return "unknown"
