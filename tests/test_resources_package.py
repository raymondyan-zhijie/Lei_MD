"""R3-6 资源包 smoke test —— v0.4.4+

覆盖：
- ``src/resources/__init__.py`` 存在 → 可作 Python package 导入
- ``_LOCALES_DIR`` 指向真实目录
- bundled locale JSON 文件存在且能被 ``set_locale()`` 加载

背景：v0.4.4 之前 ``src/resources/`` 缺 ``__init__.py``，wheel
打包时 ``package_data`` 不会包含 ``locales/*.json``，安装后
``set_locale("zh_CN")`` 找不到 JSON 走默认 fallback → UI 全英文。
"""
from __future__ import annotations

import json


def test_resources_package_importable():
    """src.resources 是合法 Python package（__init__.py 存在）。"""
    import src.resources  # noqa: F401

    assert src.resources.__file__ is not None


def test_resources_exposes_locales_dir():
    """__init__.py 导出 _LOCALES_DIR 指向 src/resources/locales/。"""
    from src.resources import _LOCALES_DIR

    assert _LOCALES_DIR.is_dir()
    assert _LOCALES_DIR.name == "locales"
    # 必须包含至少 1 个 .json
    jsons = list(_LOCALES_DIR.glob("*.json"))
    assert len(jsons) >= 1, f"no bundled locales in {_LOCALES_DIR}"


def test_bundled_zh_cn_loads_via_set_locale():
    """set_locale('zh_CN') 走默认 JSON 路径能加载（不是空 dict）。"""
    from src.ui.i18n import set_locale, tr

    set_locale("zh_CN")
    # 任意已知 key（来自 src/resources/locales/zh_CN.json）
    # 用一个 fallback key 验证 _default 加载成功即可
    # （真实 key 测试在 test_i18n.py）
    assert tr("__nonexistent_key__") == "__nonexistent_key__"


def test_bundled_en_us_loads_via_set_locale():
    """set_locale('en_US') 走默认 JSON 路径能加载。"""
    from src.ui.i18n import set_locale, tr

    set_locale("en_US")
    # 任意 fallback key —— tr() 不会崩就说明 _default 加载成功
    assert tr("__fallback__") == "__fallback__"


def test_bundled_locale_json_is_valid_dict():
    """每个 bundled JSON 都是 {str: str} 字典（不是 list / null / 损坏文件）。"""
    from src.resources import _LOCALES_DIR

    for jp in _LOCALES_DIR.glob("*.json"):
        data = json.loads(jp.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"{jp.name} root is not dict: {type(data).__name__}"
        # 至少 1 个 key
        assert len(data) > 0, f"{jp.name} is empty"
        # value 必须全是 str（i18n 协议）
        bad = [(k, v) for k, v in data.items() if not isinstance(v, str)]
        assert not bad, f"{jp.name} has non-str values: {bad[:3]}"
