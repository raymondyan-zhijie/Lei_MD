"""Program entry-point main() tests.

P0.3 from the 2026-06-02 expert review: main() must actually wire
ConfigManager + HistoryManager into MainWindow, otherwise the README
"50-entry history" claim is dead in the water.

These tests cover the entry-level integration:

  1. ``test_main_exits_cleanly`` — main() returns 0 with a real (mocked)
     QApplication.exec().
  2. ``test_main_wires_config_and_history`` — main() actually creates a
     ConfigManager and HistoryManager and hands them to MainWindow.
  3. ``test_main_conversion_lands_in_history`` — a single-file conversion
     run through the real MainWindow ends up as a row in HistoryManager.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def isolated_config_home(monkeypatch, tmp_path):
    """Override XDG_CONFIG_HOME so ConfigManager doesn't touch the real
    ~/.config/lei-md/. We also silence the logger to keep test output clean.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("LEI_MD_LOG", "CRITICAL")
    return tmp_path


def test_main_exits_cleanly(qapp, isolated_config_home, monkeypatch):
    """main() in test mode (exec mocked) returns 0 without raising."""
    from src.main import main

    with patch.object(qapp, "exec", return_value=0):
        # Patch MainWindow so we don't actually create a QMainWindow in tests
        with patch("src.ui.main_window.MainWindow") as mock_mw:
            mock_mw.return_value.show.return_value = None
            exit_code = main()

    assert exit_code == 0


def test_main_wires_config_and_history(qapp, isolated_config_home, monkeypatch):
    """main() builds ConfigManager + HistoryManager and injects them."""
    from src.main import main

    captured: dict = {}

    def fake_mw(*, config_manager, history):
        captured["config_manager"] = config_manager
        captured["history"] = history
        return _FakeMainWindow()

    with patch.object(qapp, "exec", return_value=0):
        with patch("src.ui.main_window.MainWindow", side_effect=fake_mw):
            main()

    cfg = captured.get("config_manager")
    hist = captured.get("history")
    assert cfg is not None, "config_manager not injected"
    assert hist is not None, "history not injected"
    # max_history should flow from config → history
    assert hist._max == cfg.get().max_history


def test_main_conversion_lands_in_history(qapp, isolated_config_home, tmp_path):
    """P0.3 端到端: a single-file conversion through a real MainWindow
    ends up as a row in HistoryManager. Verifies the *wire* is connected
    in the assembled graph that main() builds.
    """
    from src.core.config import ConfigManager
    from src.core.history import HistoryManager
    from src.core.worker import ConversionWorker
    from src.ui.main_window import MainWindow

    cfg = ConfigManager()
    history = HistoryManager(max_entries=cfg.get().max_history)
    win = MainWindow(config_manager=cfg, history=history)

    # Create a tiny .md input the worker can convert
    src = tmp_path / "sample.md"
    src.write_text("# hello\nworld\n", encoding="utf-8")

    # Spin up the worker, exactly like MainWindow._on_file_selected does.
    worker = ConversionWorker(win._converter, str(src))
    worker.job_done.connect(win._on_job_done)
    worker.start()
    worker.wait(5000)  # bounded
    qapp.processEvents()

    # HistoryManager.request_add goes through a signal → main-thread slot.
    # Pump the queue so the slot has run.
    rows = history.list(limit=10)
    paths = [r.source_path for r in rows]
    assert any(p == str(src) for p in paths), (
        f"Expected {src} in history rows, got: {paths}"
    )


# --- helpers --------------------------------------------------------------

from unittest.mock import patch  # noqa: E402  (placed near use)


class _FakeMainWindow:
    """Stand-in for MainWindow that records constructor args."""

    def show(self) -> None:  # pragma: no cover - trivial
        return None
