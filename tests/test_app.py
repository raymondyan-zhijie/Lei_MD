"""Task 1.1: QApplication 初始化 + 应用名/版本测试。

测试目标：
- QApplication 单例
- 应用名为 "Lei_MD"
- 组织名为 "leimengde"
- LeiMDApp 不重复创建 QApplication
"""
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt


def test_application_name_is_lei_md(qapp):
    """应用名必须是 Lei_MD（与项目品牌一致）。"""
    from src.app import LeiMDApp

    LeiMDApp.configure_application(qapp)
    assert qapp.applicationName() == "Lei_MD"


def test_organization_name_is_leimengde(qapp):
    """组织名是 leimengde（品牌归属）。"""
    from src.app import LeiMDApp

    LeiMDApp.configure_application(qapp)
    assert qapp.organizationName() == "leimengde"


def test_application_display_name_includes_brand(qapp):
    """应用展示名包含品牌（任务栏/About 框显示用）。"""
    from src.app import LeiMDApp

    LeiMDApp.configure_application(qapp)
    display = qapp.applicationDisplayName()
    assert "Lei_MD" in display


def test_configure_is_idempotent(qapp):
    """重复调用 configure_application 不应出错或重置。"""
    from src.app import LeiMDApp

    LeiMDApp.configure_application(qapp)
    name1 = qapp.applicationName()

    LeiMDApp.configure_application(qapp)
    name2 = qapp.applicationName()

    assert name1 == name2 == "Lei_MD"
