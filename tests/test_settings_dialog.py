"""设置对话框测试（Task 2.1）。

按 03 §Task 2.1 + 02 §3.3（AppConfig 字段）：
- 构造时载入 ConfigManager 当前配置到 UI
- accept() → ConfigManager.update 持久化
- cancel()/reject() → 不改 config
- 字段映射：output_dir (ComboBox)、language (ComboBox)、theme (ComboBox)、
  auto_convert (CheckBox)、max_history/batch_concurrency (QSpinBox)、
  llm_api_base/llm_api_key/llm_model (QLineEdit)
- reset_to_defaults 按钮 → 重置 UI 到默认（不自动 save）

SSOT 偏离记录：02 §3.3 规范用嵌套 llm{} 块 + config_version，但 Sprint 2 推的
ConfigManager 用了扁平 llm_api_base/llm_api_key/llm_model。Sprint 3 先尊重已
实现 schema，留待 v0.3.0 迁移。
"""
from __future__ import annotations

import pytest


@pytest.fixture
def config_in_tmp(monkeypatch, tmp_path):
    """隔离 XDG_CONFIG_HOME。"""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("APPDATA", raising=False)
    from src.core.config import ConfigManager
    cm = ConfigManager()
    yield cm


# ----------- 构造时载入 -----------

def test_settings_dialog_loads_current_config(qtbot, config_in_tmp):
    """构造时 UI 反映当前 AppConfig 字段值。"""
    from src.core.config import ConfigManager
    from src.ui.settings_dialog import SettingsDialog
    cm = config_in_tmp
    cm.update(output_dir="custom", custom_output_dir="/tmp/out", max_history=100, auto_convert=False)
    cm.save()
    cm2 = ConfigManager()

    dlg = SettingsDialog(cm2)
    qtbot.addWidget(dlg)

    assert dlg.output_dir_combo.currentText() in ("same", "custom")
    assert dlg.custom_output_edit.text() == "/tmp/out"
    assert dlg.max_history_spin.value() == 100
    assert dlg.auto_convert_check.isChecked() is False


# ----------- accept 持久化 -----------

def test_settings_dialog_accept_persists_changes(qtbot, config_in_tmp):
    """改 UI + accept() → ConfigManager.update + 落盘。"""
    from src.core.config import ConfigManager
    from src.ui.settings_dialog import SettingsDialog
    cm = config_in_tmp

    dlg = SettingsDialog(cm)
    qtbot.addWidget(dlg)

    # 改字段
    dlg.language_combo.setCurrentText("zh_CN")
    dlg.theme_combo.setCurrentText("dark")
    dlg.batch_concurrency_spin.setValue(8)
    dlg.llm_model_edit.setText("gpt-4o-mini")

    # 模拟 accept
    dlg._on_accept()

    # 重新 load → 看新值
    cm2 = ConfigManager()
    cfg = cm2.get()
    assert cfg.language == "zh_CN"
    assert cfg.theme == "dark"
    assert cfg.batch_concurrency == 8
    assert cfg.llm_model == "gpt-4o-mini"


# ----------- reject 不改 config -----------

def test_settings_dialog_reject_does_not_persist(qtbot, config_in_tmp):
    """改 UI + reject() → config 不变。"""
    from src.core.config import ConfigManager
    from src.ui.settings_dialog import SettingsDialog
    cm = config_in_tmp

    dlg = SettingsDialog(cm)
    qtbot.addWidget(dlg)

    dlg.language_combo.setCurrentText("en_US")
    dlg._on_reject()

    cm2 = ConfigManager()
    assert cm2.get().language == "system"


# ----------- 字段类型 -----------

def test_settings_dialog_has_all_field_widgets(qtbot, config_in_tmp):
    """所有 AppConfig 字段都有对应 widget。"""
    from src.ui.settings_dialog import SettingsDialog
    dlg = SettingsDialog(config_in_tmp)
    qtbot.addWidget(dlg)

    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QLineEdit,
        QSpinBox,
    )
    assert isinstance(dlg.output_dir_combo, QComboBox)
    assert isinstance(dlg.language_combo, QComboBox)
    assert isinstance(dlg.theme_combo, QComboBox)
    assert isinstance(dlg.auto_convert_check, QCheckBox)
    assert isinstance(dlg.max_history_spin, QSpinBox)
    assert isinstance(dlg.batch_concurrency_spin, QSpinBox)
    assert isinstance(dlg.custom_output_edit, QLineEdit)
    assert isinstance(dlg.llm_api_base_edit, QLineEdit)
    assert isinstance(dlg.llm_api_key_edit, QLineEdit)
    assert isinstance(dlg.llm_model_edit, QLineEdit)

    # ComboBox 选项
    def opts(c):
        return [c.itemText(i) for i in range(c.count())]
    assert "same" in opts(dlg.output_dir_combo)
    assert "custom" in opts(dlg.output_dir_combo)
    assert "system" in opts(dlg.language_combo)
    assert "zh_CN" in opts(dlg.language_combo)
    assert "en_US" in opts(dlg.language_combo)
    assert "light" in opts(dlg.theme_combo)
    assert "dark" in opts(dlg.theme_combo)


# ----------- reset to defaults -----------

def test_settings_dialog_reset_to_defaults(qtbot, config_in_tmp):
    """reset_to_defaults 按钮 → UI 重置到默认（不 save）。"""
    from src.core.config import AppConfig, ConfigManager
    from src.ui.settings_dialog import SettingsDialog
    cm = config_in_tmp
    cm.update(language="en_US", theme="dark", max_history=200)
    cm.save()
    cm2 = ConfigManager()

    dlg = SettingsDialog(cm2)
    qtbot.addWidget(dlg)

    assert hasattr(dlg, "reset_button")

    dlg._on_reset_defaults()

    # UI 重置
    assert dlg.language_combo.currentText() == "system"
    assert dlg.theme_combo.currentText() == "system"
    assert dlg.max_history_spin.value() == 50

    # 内存中 cm 引用被改（reset 把 UI 反映到内存，但不 save）
    assert cm2.get().language == "system"

    # 重新 load → 磁盘未变（reset 不 save）
    cm3 = ConfigManager()
    assert cm3.get().language == "en_US"
