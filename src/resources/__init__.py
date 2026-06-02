"""Bundled resources for Lei_MD。

目录：
- locales/: i18n JSON（zh_CN.json / en_US.json），由 src/ui/i18n.py 加载

v0.4.4+ (R3-6)：显式 package marker —— 没有这个 __init__.py，
setuptools 不会把 ``src/resources/locales/*.json`` 识别为 wheel 的
``package_data``。wheel 安装时 locales/ 会被漏掉，set_locale()
fallback 到默认 en，UI 全英文。
"""
from __future__ import annotations

from pathlib import Path

# 显式导出 _LOCALES_DIR 供测试和 i18n.py 复用（避免每个调用方
# 都重新算 Path(__file__).parent / "locales"）。
_LOCALES_DIR: Path = Path(__file__).resolve().parent / "locales"


__all__ = ["_LOCALES_DIR"]
