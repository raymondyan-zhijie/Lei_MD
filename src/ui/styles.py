"""Theme detection and application for Lei_MD — .

Detects system dark/light theme via darkdetect and applies a QPalette to
QApplication. Falls back to light theme on systems where darkdetect is
unavailable or fails.
"""
from __future__ import annotations

import logging

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

try:
    import darkdetect  # type: ignore
except ImportError:  # pragma: no cover
    darkdetect = None  # type: ignore

log = logging.getLogger(__name__)

# --- QSS strings (minimal) ----------------------------------------------------
DARK_QSS = """
QWidget { background-color: #2b2b2b; color: #e0e0e0; }
QPushButton { background-color: #3c3f41; color: #e0e0e0; border: 1px solid #555; padding: 4px; }
QPushButton:hover { background-color: #4e5254; }
QPushButton:disabled { color: #777; }
QTextEdit, QPlainTextEdit, QListWidget, QTableWidget, QLineEdit, QComboBox {
    background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #444;
}
QProgressBar {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #444;
    text-align: center;
}
QProgressBar::chunk { background-color: #2a82da; }
QMenuBar, QMenu { background-color: #2b2b2b; color: #e0e0e0; }
QMenu::item:selected { background-color: #2a82da; }
QStatusBar { background-color: #1e1e1e; color: #e0e0e0; }
QHeaderView::section { background-color: #3c3f41; color: #e0e0e0; padding: 4px; border: none; }
"""

LIGHT_QSS = """
QPushButton { padding: 4px; }
"""

def is_system_dark() -> bool:
    """Return True if the OS reports a dark theme; False otherwise.

    Never raises. Returns False when darkdetect is unavailable or fails.
    """
    if darkdetect is None:
        return False
    try:
        result = darkdetect.theme()
    except Exception:  # noqa: BLE001
        log.warning("is_system_dark: darkdetect.theme() failed; treating as light", exc_info=True)
        return False
    return str(result).lower() == "dark"

def _build_dark_palette() -> QPalette:
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(43, 43, 43))
    pal.setColor(QPalette.WindowText, QColor(224, 224, 224))
    pal.setColor(QPalette.Base, QColor(30, 30, 30))
    pal.setColor(QPalette.AlternateBase, QColor(43, 43, 43))
    pal.setColor(QPalette.ToolTipBase, QColor(43, 43, 43))
    pal.setColor(QPalette.ToolTipText, QColor(224, 224, 224))
    pal.setColor(QPalette.Text, QColor(224, 224, 224))
    pal.setColor(QPalette.Button, QColor(60, 63, 65))
    pal.setColor(QPalette.ButtonText, QColor(224, 224, 224))
    pal.setColor(QPalette.BrightText, QColor(255, 255, 255))
    pal.setColor(QPalette.Link, QColor(42, 130, 218))
    pal.setColor(QPalette.Highlight, QColor(42, 130, 218))
    pal.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
    return pal

def apply_theme(mode: str, app: QApplication | None = None) -> None:
    """Apply theme to QApplication.

    mode: 'dark' | 'light' | 'system'
    """
    target = QApplication.instance() if app is None else app
    if target is None:
        return
    if mode == "system":
        mode = "dark" if is_system_dark() else "light"
    if mode == "dark":
        target.setPalette(_build_dark_palette())
        target.setStyleSheet(DARK_QSS)
    else:
        target.setPalette(target.style().standardPalette())
        target.setStyleSheet(LIGHT_QSS)
    log.info("Applied theme: %s", mode)

class ThemeManager:
    """Reactive theme manager that listens to system theme changes.

    On Linux/Windows with darkdetect installed, the system palette can change
    at runtime. Callbacks are invoked when the theme flips.
    """

    def __init__(self, on_change=None):
        self._on_change = on_change
        self._current: bool | None = None

    def current(self) -> str | None:
        return "dark" if self._current else ("light" if self._current is False else None)

    def refresh(self) -> str:
        is_dark = is_system_dark()
        changed = (self._current is not None) and (is_dark != self._current)
        self._current = is_dark
        mode = "dark" if is_dark else "light"
        if changed and self._on_change is not None:
            try:
                self._on_change(mode)
            except Exception:  # noqa: BLE001
                log.exception("Theme change callback failed")
        return mode
