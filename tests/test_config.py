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


# ----------- v0.4.1 P0 S2：max_history 范围扩到 1000 -----------

def test_config_max_history_accepts_1000_upper_bound(isolated_config_home):
    """v0.4.1 P0 S2：max_history 上限扩到 1000（v0.4.0 是 999）。

    验证：
    - 1000 应被接受（v0.4.1 扩界）
    - 1001 应被拒绝
    - 0 应被拒绝（下界）
    """
    from src.core.config import AppConfig
    # 上界 1000：应被接受
    cfg = AppConfig(max_history=1000)
    assert cfg.max_history == 1000
    # 超出 1000：应被拒绝
    with pytest.raises(TypeError, match=r"max_history must be in \[1, 1000\]"):
        AppConfig(max_history=1001)
    # 下界 0：应被拒绝
    with pytest.raises(TypeError, match=r"max_history must be in \[1, 1000\]"):
        AppConfig(max_history=0)


# ----------- v0.4.1 P0 S1：分层修复 — SUPPORTED_EXTENSIONS 在 core -----------

def test_supported_extensions_lives_in_core_layer(isolated_config_home):
    """v0.4.1 P0 S1：SUPPORTED_EXTENSIONS / AUDIO_EXTENSIONS SSOT 在 core/supported.py。

    验证：
    - core/supported.py 模块存在
    - converter.py 不再 import src.ui.drop_area（仅允许 core）
    - converter.py 仍可读 SUPPORTED_EXTENSIONS
    - drop_area 仍可读（re-export 兼容老测试）
    """
    from src.core import supported
    from src.core.supported import AUDIO_EXTENSIONS, SUPPORTED_EXTENSIONS
    # 集合非空
    assert len(SUPPORTED_EXTENSIONS) > 0
    assert len(AUDIO_EXTENSIONS) > 0
    # 音频集合独立于支持集合（一个被支持，一个被显式拦截）
    assert AUDIO_EXTENSIONS.isdisjoint(SUPPORTED_EXTENSIONS)
    # converter 应能 import SUPPORTED（不再依赖 UI 层）
    from src.core.converter import MarkItDownConverter
    assert MarkItDownConverter.SUPPORTED is SUPPORTED_EXTENSIONS
    # drop_area 仍可读（re-export，向后兼容）
    from src.ui import drop_area
    assert drop_area.SUPPORTED_EXTENSIONS is SUPPORTED_EXTENSIONS
    assert drop_area.AUDIO_EXTENSIONS is AUDIO_EXTENSIONS
    # 二次访问返回的是同一个对象（SSOT 真·唯一）
    assert supported.SUPPORTED_EXTENSIONS is SUPPORTED_EXTENSIONS


def test_converter_does_not_import_drop_area(isolated_config_home):
    """v0.4.1 P0 S1：converter.py 静态源码不应 import src.ui.drop_area。

    静态扫描 src/core/converter.py，验证没有 from src.ui.drop_area import。
    """
    from pathlib import Path
    converter_path = Path("src/core/converter.py")
    src = converter_path.read_text(encoding="utf-8")
    assert "from src.ui.drop_area" not in src, (
        f"converter.py still imports src.ui.drop_area — layering violation:\n{src[:2000]}"
    )
    # 允许 from src.core.supported 出现
    assert "from src.core.supported" in src
