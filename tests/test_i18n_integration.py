"""Integration tests for i18n wiring in MainWindow — Sprint 3 集成 3/3."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.core.config import ConfigManager
from src.core.history import HistoryManager
from src.ui.main_window import MainWindow


@pytest.fixture
def isolated_config(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    return ConfigManager()


@pytest.fixture
def isolated_history(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    return HistoryManager()


def test_mainwindow_calls_set_locale_on_start(isolated_config, isolated_history, qtbot):
    """MainWindow calls i18n.set_locale(config.language) on construction."""
    isolated_config.update(language="zh_CN")
    captured = []
    with patch("src.ui.main_window.set_locale", side_effect=lambda locale, **kw: captured.append(locale)):
        MainWindow(config_manager=isolated_config, history=isolated_history)
    assert "zh_CN" in captured


def test_mainwindow_set_locale_with_en_uses_key_fallback(isolated_config, isolated_history, qtbot):
    """When language='en', set_locale('en') is called (returns keys as fallback)."""
    isolated_config.update(language="en")
    captured = []
    with patch("src.ui.main_window.set_locale", side_effect=lambda locale, **kw: captured.append(locale)):
        MainWindow(config_manager=isolated_config, history=isolated_history)
    assert "en" in captured
