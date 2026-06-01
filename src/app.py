"""QApplication 初始化与全局配置。

封装 `QApplication` 的所有元数据设置（应用名、组织、版本），
让 `main.py` 入口只关心窗口启动。

设计要点：
- 不在 import 时创建 QApplication（Qt 禁止多次创建）
- 提供 `configure_application(app)` 静态方法，可重复调用
- 版本号从 src.__version__ 读（ src/__init__.py 写一次）
"""
from __future__ import annotations

from PySide6.QtWidgets import QApplication

from src import __version__ as LEI_MD_VERSION

class LeiMDApp:
    """Lei_MD 应用配置工具。"""

    APP_NAME = "Lei_MD"
    ORG_NAME = "leimengde"

    @staticmethod
    def configure_application(app: QApplication) -> None:
        """设置 QApplication 元数据（应用名、组织、版本）。

        Args:
            app: 已创建的 QApplication 实例
        """
        app.setApplicationName(LeiMDApp.APP_NAME)
        app.setOrganizationName(LeiMDApp.ORG_NAME)
        app.setApplicationVersion(LEI_MD_VERSION)
        # 展示名带品牌后缀（任务栏/About 框更友好）
        app.setApplicationDisplayName(f"{LeiMDApp.APP_NAME} — 文件转 Markdown")
        # PySide6 6.x 默认开启高 DPI 缩放，不需要显式设置（Qt.AA_EnableHighDpiScaling 已弃用）
