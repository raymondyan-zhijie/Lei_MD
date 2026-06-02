"""ConfigManager 测试（Task 1.8）。

按 03 §Task 1.8 + 02 §6.4：
- 路径：Windows %APPDATA%\\Lei_MD\\config.json，Linux ~/.config/Lei_MD/config.json
- 默认配置：AppConfig 所有字段
- 读存在文件 / 不存在 → 用默认
- update(**kwargs) 修改 + save 持久化
- 损坏 JSON → 备份为 .json.bak 后用默认（E_INTERNAL_003）
- 未知字段（schema_version forward-compat） → 忽略
"""
from __future__ import annotations

import json

import pytest


@pytest.fixture
def isolated_config_home(monkeypatch, tmp_path):
    """把 XDG_CONFIG_HOME / APPDATA 指到 tmp，避免污染真实 home。"""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("APPDATA", raising=False)
    return tmp_path


# ----------- 默认配置 -----------

def test_config_returns_defaults_when_no_file(isolated_config_home):
    """无 config.json → get() 返回 AppConfig() 默认值。"""
    from src.core.config import AppConfig, ConfigManager
    cm = ConfigManager()
    cfg = cm.get()
    assert isinstance(cfg, AppConfig)
    assert cfg.output_dir == "same"
    assert cfg.auto_convert is True
    assert cfg.max_history == 50
    assert cfg.language == "system"
    assert cfg.theme == "system"
    assert cfg.batch_concurrency == 4
    assert cfg.llm_model == "gpt-4o"


# ----------- 持久化 -----------

def test_config_update_persists_to_disk(isolated_config_home):
    """update(**kwargs) → save() → 重新 load 仍是新值。"""
    from src.core.config import ConfigManager
    cm = ConfigManager()
    cm.update(output_dir="custom", custom_output_dir="/tmp/out", max_history=100)
    # 新实例化应读到更新
    cm2 = ConfigManager()
    cfg = cm2.get()
    assert cfg.output_dir == "custom"
    assert cfg.custom_output_dir == "/tmp/out"
    assert cfg.max_history == 100


# ----------- 损坏恢复 -----------

def test_config_corrupted_file_is_backed_up_and_reset(isolated_config_home):
    """config.json 损坏 → 备份为 .json.bak + 用默认。"""
    from src.core.config import ConfigManager
    # 写坏 JSON
    config_dir = isolated_config_home / "Lei_MD"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"
    config_file.write_text("{this is not valid json", encoding="utf-8")

    cm = ConfigManager()
    cfg = cm.get()
    # 默认值
    assert cfg.output_dir == "same"
    # 备份文件存在
    bak = config_file.with_suffix(".json.bak")
    assert bak.exists(), f"备份文件未创建: {bak}"
    # 原文件已被新默认覆盖
    assert config_file.exists()


# ----------- Forward compat -----------

def test_config_ignores_unknown_fields(isolated_config_home):
    """config.json 含未知字段（未来 schema 扩展）→ 静默忽略。"""
    from src.core.config import ConfigManager
    config_dir = isolated_config_home / "Lei_MD"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"
    data = {
        "output_dir": "custom",
        "future_field_xyz": "should be ignored",  # AppConfig 没有
        "another_unknown": 42,
    }
    config_file.write_text(json.dumps(data), encoding="utf-8")

    cm = ConfigManager()
    cfg = cm.get()
    assert cfg.output_dir == "custom"
    # 不应抛异常
    assert not hasattr(cfg, "future_field_xyz")


# ----------- 目录创建 -----------

def test_config_creates_dir_if_missing(isolated_config_home):
    """CONFIG_DIR 不存在 → mkdir parents=True exist_ok=True。"""
    from src.core.config import ConfigManager
    # isolated_config_home/Lei_MD 不应存在
    config_dir = isolated_config_home / "Lei_MD"
    assert not config_dir.exists()
    ConfigManager()
    assert config_dir.is_dir()
