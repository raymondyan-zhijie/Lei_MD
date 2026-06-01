"""Tests for src/ui/i18n.py — Task 2.6 i18n (TDD red)."""
from __future__ import annotations

from src.ui.i18n import Translator, set_locale, tr


def test_tr_returns_key_when_no_locale_set(monkeypatch):
    """tr('hello') returns the key itself when no locale loaded."""
    t = Translator(locale="en")
    assert t.tr("missing.key") == "missing.key"


def test_tr_returns_translation_for_loaded_locale():
    """tr returns translated string for known key in zh_CN."""
    t = Translator(locale="zh_CN")
    t.load({"hello": "你好"})
    assert t.tr("hello") == "你好"


def test_tr_fallback_to_key_when_translation_missing():
    """If key absent in dict, tr returns the key."""
    t = Translator(locale="zh_CN")
    t.load({"hello": "你好"})
    assert t.tr("absent") == "absent"


def test_set_locale_changes_default():
    """set_locale() updates module-level default locale."""
    set_locale("zh_CN")
    # Default translator is created in set_locale
    from src.ui import i18n

    i18n._default.load({"greet": "欢迎"})
    assert tr("greet") == "欢迎"
    # restore
    set_locale("en")
