"""Integration tests for MainWindow — Task 集成 1/4 (Sprint 3)."""
from __future__ import annotations

import pytest

from src.core.config import ConfigManager
from src.core.history import HistoryManager
from src.ui.main_window import MainWindow


@pytest.fixture
def app(qapp):
    return qapp


@pytest.fixture
def isolated_config(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    return ConfigManager()


@pytest.fixture
def isolated_history(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    return HistoryManager()


def test_mainwindow_accepts_config_and_history(app, isolated_config, isolated_history):
    """MainWindow takes config_manager and history_manager kwargs."""
    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    assert win._config is isolated_config
    assert win._history is isolated_history


def test_mainwindow_applies_theme_from_config_on_start(app, isolated_config, isolated_history, monkeypatch):
    """MainWindow calls apply_theme() using config.theme on construction."""
    isolated_config.update(theme="light")
    captured = []
    monkeypatch.setattr("src.ui.main_window.apply_theme", lambda mode: captured.append(mode))
    MainWindow(config_manager=isolated_config, history=isolated_history)
    assert "light" in captured


def test_mainwindow_has_settings_menu_action(app, isolated_config, isolated_history):
    """MainWindow has a '设置' (Settings) action in menubar."""
    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    menubar = win.menuBar()
    actions_text = []
    for top_action in menubar.actions():
        menu = top_action.menu()
        if menu is not None:
            for sub_action in menu.actions():
                actions_text.append(sub_action.text())
    # v0.4.5+ A4：菜单走 i18n，中英文案都接受
    assert any(
        ("设置" in t) or ("Settings" in t) or ("settings" in t.lower())
        for t in actions_text
    ), f"settings menu action not found in: {actions_text}"


# ────────────────────────────────────────────────────────────────────────
# P0.4: drop → auto_convert behaviour
# ────────────────────────────────────────────────────────────────────────

from PySide6.QtCore import QObject, Signal  # noqa: E402


class _StubWorker(QObject):
    """Stand-in for ConversionWorker that records start() calls without
    spinning up a real QThread. Signals are real Qt signals so
    MainWindow can ``.connect()`` to them."""

    instances: list = []

    progress = Signal(int)
    finished_with_md = Signal(str)
    error = Signal(object)
    job_done = Signal(str, str, int, int, bool, str)
    finished = Signal()

    def __init__(self, converter, path, *a, **kw) -> None:
        super().__init__()
        self.converter = converter
        self.path = path
        self.cancel_called = False
        self.started = False
        _StubWorker.instances.append(self)

    def start(self) -> None:
        self.started = True

    def cancel(self) -> None:
        self.cancel_called = True


def test_drop_single_file_triggers_conversion_when_auto_on(
    app, isolated_config, isolated_history, tmp_path, monkeypatch
):
    """P0.4: a single file dropped with auto_convert=True starts a worker."""
    from src.ui import main_window as mw_module

    monkeypatch.setattr(mw_module, "ConversionWorker", _StubWorker)
    isolated_config.update(auto_convert=True)

    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    _StubWorker.instances.clear()

    sample = tmp_path / "hello.md"
    sample.write_text("# hello\n", encoding="utf-8")

    win._on_files_dropped([str(sample)])
    # Pump Qt event queue so file_list → main_window wiring fires.
    app.processEvents()

    assert any(w.path == str(sample) for w in _StubWorker.instances), (
        f"Expected a worker for {sample}, got: {[w.path for w in _StubWorker.instances]}"
    )


def test_drop_single_file_does_not_convert_when_auto_off(
    app, isolated_config, isolated_history, tmp_path, monkeypatch
):
    """P0.4: a single file dropped with auto_convert=False adds to the list only."""
    from src.ui import main_window as mw_module

    monkeypatch.setattr(mw_module, "ConversionWorker", _StubWorker)
    isolated_config.update(auto_convert=False)

    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    _StubWorker.instances.clear()

    sample = tmp_path / "hello.md"
    sample.write_text("# hello\n", encoding="utf-8")

    win._on_files_dropped([str(sample)])
    app.processEvents()

    assert _StubWorker.instances == [], (
        f"Expected no worker when auto_convert=False, got: "
        f"{[w.path for w in _StubWorker.instances]}"
    )
    # File should still be in the list:
    assert str(sample) in win.file_list.all_paths()


def test_drop_multiple_files_does_not_autobatch(
    app, isolated_config, isolated_history, tmp_path, monkeypatch
):
    """P0.4: multi-file drop adds to the list but does NOT start a batch
    worker (user must click the batch button or menu)."""
    from src.ui import main_window as mw_module

    monkeypatch.setattr(mw_module, "ConversionWorker", _StubWorker)
    monkeypatch.setattr(mw_module, "BatchWorker", _StubWorker)
    isolated_config.update(auto_convert=True)

    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    _StubWorker.instances.clear()

    files = []
    for i in range(3):
        p = tmp_path / f"file{i}.md"
        p.write_text(f"# {i}\n", encoding="utf-8")
        files.append(str(p))

    win._on_files_dropped(files)
    app.processEvents()

    assert _StubWorker.instances == [], (
        f"Multi-file drop should not auto-start a worker, got: "
        f"{[w.path for w in _StubWorker.instances]}"
    )
    # All three should be in the list:
    listed = win.file_list.all_paths()
    for f in files:
        assert f in listed
