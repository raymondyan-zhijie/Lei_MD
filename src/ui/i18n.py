"""i18n for Lei_MD — .

A tiny in-house translator. Loads a JSON dict of key -> translated string
for a given locale. Module-level default translator used by ``tr()``.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

log = logging.getLogger(__name__)

# Default locale when none is set
DEFAULT_LOCALE = "en"

# P3 安全白名单：允许通过 set_locale() 显式切换的 locale。
# 注意："system" 在 v0.4.4+ 不再是字面 locale；它是触发器，会被
# _resolve_system_locale() 解析为真实 locale（zh_CN/en_US）后传给 set_locale。
# VALID_LOCALES 只列真 locale 字符串。
VALID_LOCALES: frozenset[str] = frozenset({"en", "zh_CN", "en_US"})

# 触发器：set_locale 看到它会调 _resolve_system_locale() 展开。
SYSTEM_LOCALE_TRIGGER = "system"

# Built-in resource directory.
# - In dev (running from source): src/ui/i18n.py → ../../src/resources/locales
# - In frozen (PyInstaller onefile): sys._MEIPASS is the bundle root, where
#   the spec's `datas` placed resources/locales/. Falling back to that
#   path makes the same code work in both modes.
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _LOCALES_DIR = Path(sys._MEIPASS) / "resources" / "locales"
else:
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
        with open(path, encoding="utf-8") as f:
            self.load(json.load(f))

    def tr(self, key: str) -> str:
        """Return translated string, or the key itself when missing."""
        return self._dict.get(key, key)

    def available_keys(self) -> list[str]:
        return list(self._dict.keys())

# Module-level default translator
_default: Translator = Translator(DEFAULT_LOCALE)

# Try to load a bundled zh_CN.json if present (开发态默认 fallback，让旧
# import 路径下的 _tr() 行为不变；新代码走 set_locale() 会覆盖 _default)。
_default_zh_path = _LOCALES_DIR / "zh_CN.json"
if _default_zh_path.is_file():
    try:
        _default.load_file(_default_zh_path)
    except Exception:  # noqa: BLE001
        log.warning("Failed to load bundled zh_CN translations", exc_info=True)


def _resolve_system_locale() -> str:
    """v0.4.4+ P0: 解析 ``"system"`` 触发器为真实 locale。

    优先级：
    1. ``$LC_ALL`` 环境变量
    2. ``$LANG`` 环境变量
    3. ``locale.getdefaultlocale()``（py3.11+ 已 deprecated，但 py3.10 还能用）
    4. 都没匹配上 → 兜底 ``"en_US"``

    返回值一定在 ``VALID_LOCALES`` 内。
    """
    import locale as _locale_mod

    candidate = ""
    for env_var in ("LC_ALL", "LANG"):
        v = os.environ.get(env_var, "").strip()
        if v and v.lower() != "c" and v.lower() != "posix":
            candidate = v
            break
    if not candidate:
        try:
            candidate = _locale_mod.getdefaultlocale()[0] or ""
        except Exception:  # noqa: BLE001
            candidate = ""
    # candidate 形如 "zh_CN.UTF-8" / "en_US" / "zh_CN"
    if not candidate:
        return "en_US"
    base = candidate.split(".")[0].replace("-", "_")
    if base.startswith("zh"):
        return "zh_CN"
    if base.startswith("en"):
        return "en_US"
    # 其他语言（ja, ko, fr, ...）全部回落到 en_US（项目当前只支持 zh + en）
    return "en_US"


def set_locale(locale: str, translations: dict[str, str] | None = None) -> Translator:
    """Set the default locale and optionally load translations.

    v0.4.4+ P0 (专家审查 P1.2 配套)：
    - ``locale == "system"`` 走 ``_resolve_system_locale()`` 解析为
      zh_CN / en_US，再加载对应 bundled JSON
    - 其他字面 locale 走 P3 白名单校验 + bundled JSON 路径
    """
    global _default
    # 触发器：system 不是字面 locale
    if locale == SYSTEM_LOCALE_TRIGGER:
        resolved = _resolve_system_locale()
        log.info("set_locale('system') resolved to %r", resolved)
        locale = resolved
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
        else:
            log.info("No bundled translations for locale %r", locale)
    return _default

def tr(key: str) -> str:
    """Translate a key using the default locale's translator."""
    return _default.tr(key)
