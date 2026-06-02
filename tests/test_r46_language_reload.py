"""R4-6 切换语言后窗口刷新测试 —— v0.4.4+

覆盖：
- ConfigManager.on_change 回调在 update() 后调
- MainWindow 通过 on_change 注册 → 触发 reload_language() / apply_theme()
- SettingsDialog accept 写回 cm 后主窗口文字立即刷新（不需重启）
"""
from __future__ import annotations

import pytest


@pytest.fixture
def isolated_config(monkeypatch, tmp_path):
    """isolate XDG_CONFIG_HOME → ConfigManager 写到 tmp。"""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    from src.core.config import ConfigManager
    return ConfigManager()


def test_config_manager_on_change_fires_on_update(isolated_config):
    """ConfigManager.update() save 后调所有 on_change 回调。"""
    captured = []

    def on_change(new_cfg):
        captured.append(new_cfg)

    isolated_config.on_change(on_change)
    isolated_config.update(language="en_US")
    assert len(captured) == 1
    assert captured[0].language == "en_US"


def test_config_manager_on_change_skips_when_no_real_change(isolated_config):
    """只调 update() 但所有 kwargs 都是未知字段 → 不调 on_change。"""
    captured = []

    isolated_config.on_change(lambda _: captured.append(1))
    isolated_config.update(this_is_not_a_field="x")  # noqa
    assert captured == []


def test_config_manager_on_change_callback_exception_isolated(isolated_config):
    """一个回调抛异常不影响其它回调 / 后续 save 正常完成。"""
    ok_called = []

    def bad(_):
        raise RuntimeError("boom")

    def good(_):
        ok_called.append(1)

    isolated_config.on_change(bad)
    isolated_config.on_change(good)
    # 不应崩
    isolated_config.update(language="en_US")
    assert ok_called == [1]
    # save 也正常
    assert isolated_config.get().language == "en_US"


def test_mainwindow_subscribes_via_on_change(isolated_config, qtbot):
    """MainWindow 构造后通过 on_change 注册了 _on_config_changed。"""
    from src.core.config import AppConfig
    from src.ui.main_window import MainWindow

    win = MainWindow(config_manager=isolated_config)
    qtbot.addWidget(win)

    # on_change 列表至少 1 个（MainWindow 注册的）
    assert len(isolated_config._on_change_callbacks) >= 1

    # 端到端：再注册一个观察者，update 触发后两个回调都被调
    captured = []
    isolated_config.on_change(lambda c: captured.append(c))
    isolated_config.update(max_history=77)
    assert len(captured) == 1
    assert isinstance(captured[0], AppConfig)
    assert captured[0].max_history == 77


def test_mainwindow_reload_language_updates_cancel_button_text(isolated_config, qtbot):
    """改 language → reload_language() → cancel_button 文案刷新。"""
    from src.ui.i18n import set_locale
    from src.ui.main_window import MainWindow

    isolated_config.update(language="zh_CN")
    set_locale("zh_CN")
    win = MainWindow(config_manager=isolated_config)
    qtbot.addWidget(win)
    zh_text = win.cancel_button.text()
    assert zh_text == "取消", f"initial zh cancel text wrong: {zh_text!r}"

    isolated_config.update(language="en_US")
    en_text = win.cancel_button.text()
    assert en_text == "Cancel", f"after en reload text wrong: {en_text!r}"


def test_mainwindow_reload_language_updates_yt_placeholder(isolated_config, qtbot):
    """改 language → YouTube URL placeholder 也跟着切。"""
    from src.ui.i18n import set_locale
    from src.ui.main_window import MainWindow

    isolated_config.update(language="zh_CN")
    set_locale("zh_CN")
    win = MainWindow(config_manager=isolated_config)
    qtbot.addWidget(win)
    zh_placeholder = win.yt_url_edit.placeholderText()
    assert "粘贴" in zh_placeholder or "YouTube" in zh_placeholder

    isolated_config.update(language="en_US")
    en_placeholder = win.yt_url_edit.placeholderText()
    assert en_placeholder != zh_placeholder


def test_settings_dialog_accept_triggers_window_reload(isolated_config, qtbot):
    """端到端：开 SettingsDialog → 改 language → accept → MainWindow 刷新。"""
    from src.ui.i18n import set_locale
    from src.ui.main_window import MainWindow
    from src.ui.settings_dialog import SettingsDialog

    isolated_config.update(language="zh_CN")
    set_locale("zh_CN")
    win = MainWindow(config_manager=isolated_config)
    qtbot.addWidget(win)
    dlg = SettingsDialog(isolated_config, parent=win)
    qtbot.addWidget(dlg)

    dlg.language_combo.setCurrentText("en_US")
    dlg._on_accept()

    assert win.cancel_button.text() == "Cancel"
    msg = win.status.currentMessage()
    assert "drop" in msg.lower() or "Drop" in msg


def test_settings_dialog_reject_does_not_reload(isolated_config, qtbot):
    """reject → 不写 cm → MainWindow 不刷新。"""
    from src.ui.i18n import set_locale
    from src.ui.main_window import MainWindow
    from src.ui.settings_dialog import SettingsDialog

    isolated_config.update(language="zh_CN")
    set_locale("zh_CN")
    win = MainWindow(config_manager=isolated_config)
    qtbot.addWidget(win)
    dlg = SettingsDialog(isolated_config, parent=win)
    qtbot.addWidget(dlg)

    dlg.language_combo.setCurrentText("en_US")
    dlg._on_reject()

    assert win.cancel_button.text() == "取消"
    assert isolated_config.get().language == "zh_CN"


def test_config_manager_no_qt_dependency(isolated_config):
    """ConfigManager 不依赖 QObject —— 无 QApplication 也能 update + on_change。"""
    # isolated_config fixture 没启 qapp；能 update 不崩就是合规
    isolated_config.update(language="en_US")
    assert isolated_config.get().language == "en_US"
