"""i18n for Lei_MD — Task 2.6.

A tiny in-house translator. Loads a JSON dict of key -> translated string
for a given locale. Module-level default translator used by ``tr()``.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Default locale when none is set
DEFAULT_LOCALE = "en"

# v0.2.5 P3 audit (L1) 白名单：允许通过 set_locale() 显式切换的 locale。
# 不在白名单里的输入一律 fallback 到 DEFAULT_LOCALE，避免路径拼接（f"{locale}.json"）
# 时把攻击者控制的字符串拼到 _LOCALES_DIR 里。
# v0.2.7 P0：加 "en" 让英文用户（DEFAULT_LOCALE）启动时不打 warning。
# "en" 表示 keys 不翻译、UI 字符串保持源代码硬编码（tr() 在 v0.2.7 仍未接 UI）。
VALID_LOCALES: frozenset[str] = frozenset({"system", "en", "zh_CN", "en_US"})

# Built-in resource directory
_LOCALES_DIR = Path(__file__).resolve().parent.parent / "resources" / "locales"


class Translator:
    """Holds translations for one locale and looks up keys."""

    def __init__(self, locale: str = DEFAULT_LOCALE):
        self.locale = locale
        self._dict: dict[str, str] = {}

    def load(self, data: dict[str, str]) -> None:
        """Replace the translation table."""
        if not isinstance(data, dict):
            raise TypeError("translations must be a dict[str, str]")
        self._dict = dict(data)

    def load_file(self, path: Path) -> None:
        """Load translations from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            self.load(json.load(f))

    def tr(self, key: str) -> str:
        """Return translated string, or the key itself when missing."""
        return self._dict.get(key, key)

    def available_keys(self) -> list[str]:
        return list(self._dict.keys())


# Module-level default translator
_default: Translator = Translator(DEFAULT_LOCALE)

# Try to load a bundled zh_CN.json if present
_default_zh_path = _LOCALES_DIR / "zh_CN.json"
if _default_zh_path.is_file():
    try:
        _default.load_file(_default_zh_path)
    except Exception:  # noqa: BLE001
        log.warning("Failed to load bundled zh_CN translations", exc_info=True)


def set_locale(locale: str, translations: Optional[dict[str, str]] = None) -> Translator:
    """Set the default locale and optionally load translations.

    v0.2.5 P3 audit (L1): locale 不在 ``VALID_LOCALES`` 白名单时，fallback 到
    ``DEFAULT_LOCALE``（不再用攻击者控制的字符串拼 ``_LOCALES_DIR / f"{locale}.json"``）。
    """
    global _default
    # 白名单：拒绝未授权的 locale 字符串
    if locale not in VALID_LOCALES:
        log.warning(
            "set_locale(%r) not in whitelist %s; falling back to %r",
            locale, sorted(VALID_LOCALES), DEFAULT_LOCALE,
        )
        locale = DEFAULT_LOCALE
    _default = Translator(locale)
    if translations is not None:
        _default.load(translations)
    else:
        # Try to load bundled file for the requested locale
        path = _LOCALES_DIR / f"{locale}.json"
        if path.is_file():
            try:
                _default.load_file(path)
            except Exception:  # noqa: BLE001
                log.warning("Failed to load %s translations", locale, exc_info=True)
    return _default


def tr(key: str) -> str:
    """Translate a key using the default locale's translator."""
    return _default.tr(key)
