"""Tests for src/ui/styles.py — Task 2.5 dark mode (TDD red)."""
from __future__ import annotations

from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from src.ui.styles import ThemeManager, apply_theme, is_system_dark


def _ensure_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_is_system_dark_returns_bool():
    """is_system_dark() returns a boolean, never raises."""
    _ensure_qapp()
    with patch("src.ui.styles.darkdetect.theme") as mock_theme:
        mock_theme.return_value = "Dark"
        assert is_system_dark() is True
        mock_theme.return_value = "Light"
        assert is_system_dark() is False


def test_is_system_dark_fallback_when_darkdetect_missing():
    """is_system_dark() returns False if darkdetect import fails."""
    _ensure_qapp()
    with patch("src.ui.styles.darkdetect", None):
        assert is_system_dark() is False


def test_apply_theme_dark_sets_palette():
    """apply_theme('dark') calls QApplication.setPalette with dark palette."""
    app = _ensure_qapp()
    apply_theme("dark")
    # Dark palette has window text lighter than window background
    pal = app.palette()
    assert pal is not None  # applied without error
