"""Regression tests for v0.2.3 P2 audit config fixes (M6.2/M6.3/M6.4)."""
from __future__ import annotations

import pytest

from src.core.config import AppConfig, ConfigManager

# ============ M6.2: 非 dict JSON 不杀启动 ============


def test_config_rejects_non_dict_json_root(monkeypatch, tmp_path):
    """M6.2: config.json containing a JSON array resets to defaults (no crash)."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    cfg_file = tmp_path / "config" / "Lei_MD" / "config.json"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text("[1, 2, 3]", encoding="utf-8")
    cm = ConfigManager()  # 不应抛 AttributeError
    assert cm.get().language == "system"  # 默认值
    assert cm.get().theme == "system"


def test_config_rejects_json_string_root(monkeypatch, tmp_path):
    """M6.2: config.json = "hello" 也复位。"""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    cfg_file = tmp_path / "config" / "Lei_MD" / "config.json"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text('"hello"', encoding="utf-8")
    cm = ConfigManager()
    assert cm.get().theme == "system"


def test_config_rejects_json_number_root(monkeypatch, tmp_path):
    """M6.2: config.json = 42 也复位。"""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    cfg_file = tmp_path / "config" / "Lei_MD" / "config.json"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text("42", encoding="utf-8")
    cm = ConfigManager()
    assert cm.get().theme == "system"


# ============ M6.3: AppConfig 字段类型/取值校验 ============


def test_appconfig_rejects_wrong_type_max_history():
    """M6.3: max_history=\"fifty\" 触发 TypeError。"""
    with pytest.raises(TypeError):
        AppConfig(max_history="fifty")


def test_appconfig_rejects_out_of_range_max_history():
    """M6.3: max_history=0 或 1001 触发 TypeError（v0.4.1 P0 S2 上限扩到 1000）。

    之前 v0.4.0 上限是 999，所以测试用 1000；v0.4.1 把上限放宽到 1000
    （用户要存更多历史），测试相应改为 1001。
    """
    with pytest.raises(TypeError):
        AppConfig(max_history=0)
    with pytest.raises(TypeError):
        AppConfig(max_history=1001)


def test_appconfig_rejects_wrong_type_auto_convert():
    """M6.3: auto_convert=1 (int) 触发 TypeError（bool 必须真 bool）。"""
    with pytest.raises(TypeError):
        AppConfig(auto_convert=1)


def test_appconfig_rejects_unknown_language():
    """M6.3: language=\"fr_FR\" 触发 TypeError。"""
    with pytest.raises(TypeError):
        AppConfig(language="fr_FR")


def test_appconfig_rejects_unknown_theme():
    """M6.3: theme=\"pink\" 触发 TypeError。"""
    with pytest.raises(TypeError):
        AppConfig(theme="pink")


def test_config_resets_on_wrong_type_field(monkeypatch, tmp_path):
    """M6.3: max_history 错值 → ConfigManager 复位到默认。"""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    cfg_file = tmp_path / "config" / "Lei_MD" / "config.json"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text('{"max_history": "fifty"}', encoding="utf-8")
    cm = ConfigManager()
    assert cm.get().max_history == 50  # 默认值


# ============ M6.4: rename fallback 保留坏文件 ============


def test_config_backup_uses_os_replace_atomically(monkeypatch, tmp_path):
    """M6.4: 损坏时备份用 os.replace（或 fallback shutil.move），保留坏文件。"""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    cfg_file = tmp_path / "config" / "Lei_MD" / "config.json"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text("{ not valid json", encoding="utf-8")

    ConfigManager()  # 触发复位

    bak_file = cfg_file.with_suffix(".json.bak")
    # 坏文件应被备份为 .bak
    assert bak_file.exists(), "expected .json.bak to be preserved"
    assert "{ not valid json" in bak_file.read_text(encoding="utf-8")
    # 原位置应被默认配置覆盖
    assert cfg_file.exists()
    assert "language" in cfg_file.read_text(encoding="utf-8")
