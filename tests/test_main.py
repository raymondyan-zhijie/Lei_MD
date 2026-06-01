"""Task 1.1: 程序入口 main() 测试。

测试目标：
- main() 不抛异常
- main() 会启动事件循环（用 monkeypatch 拦截）
"""
import sys
import pytest
from unittest.mock import patch


def test_main_exits_cleanly(qapp, monkeypatch):
    """main() 在没有窗口时也能正常退出（测试模式）。"""
    from src.main import main

    # 拦截 QApplication.exec() 让 main() 立即返回
    with patch.object(qapp, "exec", return_value=0):
        # 拦截 MainWindow（从 src.ui.main_window 导入）
        with patch("src.ui.main_window.MainWindow") as mock_mw:
            mock_mw.return_value.show.return_value = None
            exit_code = main()

    assert exit_code == 0
