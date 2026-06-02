"""Lei_MD 程序入口。

调用方式：
- 开发模式：`python src/main.py`
- 安装模式：`lei-md`（pyproject [project.scripts] 注册的命令）
- 测试模式：`pytest tests/test_main.py`（mock 掉 QApplication.exec）

入口职责：
1. 创建/获取 QApplication 单例
2. 调用 LeiMDApp.configure_application 设置元数据
3. 装配依赖：ConfigManager → HistoryManager → MainWindow
4. 显示窗口 + 进入事件循环
"""
from __future__ import annotations

import logging
import os
import sys

from PySide6.QtWidgets import QApplication

from src.app import LeiMDApp

# v0.4.2 P1 C3：基础 logging 配置。GUI 应用默认无 stderr 输出（Qt 拦截），
# 用户 / 客服反馈"出错了"时常因没 traceback 难以定位。设 WARNING 级把
# log.warning/error 推到 stderr；DEBUG / INFO 默认不开，CLI 运行可
# 用 LEI_MD_LOG=DEBUG 或 --debug 打开。
_LOG_LEVEL = logging.WARNING
if "--debug" in sys.argv or os.environ.get("LEI_MD_LOG", "").upper() == "DEBUG":
    _LOG_LEVEL = logging.DEBUG
logging.basicConfig(
    level=_LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def main() -> int:
    """主入口函数。

    Returns:
        QApplication.exec() 的退出码（0 = 正常退出）
    """
    # QApplication 单例：已有则复用，无则创建
    app = QApplication.instance() or QApplication(sys.argv)

    # 设置应用元数据
    LeiMDApp.configure_application(app)

    # 实例化主窗口，按 README 承诺连入历史记录与配置。
    # ConfigManager 先装，再按用户的 max_history 构造 HistoryManager，
    # 最后注入 MainWindow。这样单文件转换会自动写入历史库（P0.3）。
    from src.core.config import ConfigManager
    from src.core.history import HistoryManager
    from src.ui.main_window import MainWindow  # 延迟导入，避免循环引用

    config_manager = ConfigManager()
    history = HistoryManager(max_entries=config_manager.get().max_history)
    window = MainWindow(config_manager=config_manager, history=history)
    window.show()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
