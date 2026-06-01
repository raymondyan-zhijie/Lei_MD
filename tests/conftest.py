"""全局 pytest 配置。

在 Linux CI 环境强制 offscreen 模式（Windows 桌面无 libGL 依赖）。
"""
import os
import sys

# Linux/headless 环境：强制 Qt offscreen
if sys.platform != "win32" and "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
