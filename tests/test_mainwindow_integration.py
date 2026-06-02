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
    assert any("设置" in t for t in actions_text)
