"""v0.1.1: MainWindow 异步转换 + 进度条 + 取消按钮 测试。

按 03 §Sprint 2 + v0.1.1 changelog：把 ConversionWorker 接入 MainWindow。

新行为：
- 选文件 → 启 Worker（异步，不阻塞 UI）
- status bar 显示 QProgressBar（0~100%）
- 转换中显示"取消"按钮，按下 worker.cancel()
- finished_with_md → preview 显示 + progress 隐藏
- error → preview 显示错误信息 + progress 隐藏
- Converter 注入（默认 MarkItDownConverter，可换 Stub）
- 选新文件前 cancel 旧 worker
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


class _StubConverter:
    """可注入的 Converter 替身：可控制 sleep / fail / 进度。"""

    def __init__(self, *, sleep: float = 0.05, fail: bool = False):
        self.sleep = sleep
        self.fail = fail
        self.calls: list[str] = []

    def convert(self, file_path: str) -> str:
        self.calls.append(file_path)
        if self.sleep:
            import time
            time.sleep(self.sleep)
        if self.fail:
            from src.core.errors import ConversionError, ErrorCode
            raise ConversionError(ErrorCode.E_CONVERT_002, filename=Path(file_path).name)
        return f"# {Path(file_path).name}\n\nok"


@pytest.fixture
def main_window(qtbot):
    from src.ui.main_window import MainWindow
    w = MainWindow(converter=_StubConverter(sleep=0.05))
    qtbot.addWidget(w)
    yield w


def test_mainwindow_has_progress_bar(main_window):
    """v0.1.1: status bar 含 QProgressBar，初始隐藏。"""
    from PySide6.QtWidgets import QProgressBar
    assert hasattr(main_window, "progress_bar")
    assert isinstance(main_window.progress_bar, QProgressBar)
    assert main_window.progress_bar.isHidden() is True
    assert main_window.progress_bar.minimum() == 0
    assert main_window.progress_bar.maximum() == 100


def test_mainwindow_has_cancel_button(main_window):
    """v0.1.1: status bar 含取消按钮，转换中才显示。"""
    from PySide6.QtWidgets import QPushButton
    assert hasattr(main_window, "cancel_button")
    assert isinstance(main_window.cancel_button, QPushButton)
    assert main_window.cancel_button.isHidden() is True


def test_mainwindow_converter_injectable():
    """v0.1.1: 构造时注入 converter，测试可换 Stub。"""
    from src.ui.main_window import MainWindow
    stub = _StubConverter()
    from PySide6.QtWidgets import QMainWindow
    w = MainWindow(converter=stub)
    assert w._converter is stub


def test_mainwindow_file_selected_uses_worker(qtbot, tmp_path):
    """v0.1.1: 选文件 → 启 Worker → finished_with_md → preview 显示。"""
    from src.ui.main_window import MainWindow
    stub = _StubConverter(sleep=0.02)
    w = MainWindow(converter=stub)
    qtbot.addWidget(w)

    p = tmp_path / "a.pdf"
    p.write_text("dummy")
    w._on_file_selected(str(p))

    # 等 worker 完成
    qtbot.waitUntil(lambda: not w.preview_panel.is_empty(), timeout=3000)
    assert "a.pdf" in w.preview_panel.toPlainText() or "a.pdf" in w.preview_panel.toHtml()
    assert stub.calls == [str(p)]
    # 完成后 worker 退出
    qtbot.waitUntil(lambda: w._active_worker is None, timeout=2000)


def test_mainwindow_progress_bar_shows_during_conversion(qtbot, tmp_path):
    """v0.1.1: 转换中 progress signal 更新 progress_bar.value()。"""
    from src.ui.main_window import MainWindow
    stub = _StubConverter(sleep=0.3)  # 长任务
    w = MainWindow(converter=stub)
    qtbot.addWidget(w)

    p = tmp_path / "slow.pdf"
    p.write_text("dummy")
    w._on_file_selected(str(p))

    # 等 progress signal 推到 100（QProgressBar 跟着更新）
    qtbot.waitUntil(lambda: w.progress_bar.value() == 100, timeout=3000)
    assert w.progress_bar.maximum() == 100
    assert w.progress_bar.minimum() == 0


def test_mainwindow_cancel_button_stops_worker(qtbot, tmp_path):
    """v0.1.1: 取消按钮 → worker.cancel() → 不发 finished。"""
    from src.ui.main_window import MainWindow
    stub = _StubConverter(sleep=0.5)  # 长任务
    w = MainWindow(converter=stub)
    qtbot.addWidget(w)

    p = tmp_path / "long.pdf"
    p.write_text("dummy")
    w._on_file_selected(str(p))

    # 等 progress 更新（说明 worker 真启动了，progress 0 emit）
    qtbot.waitUntil(lambda: w.progress_bar.value() > 0, timeout=2000)
    # 点取消
    w.cancel_button.click()
    # 等线程结束
    qtbot.waitUntil(lambda: w._active_worker is None or not w._active_worker.isRunning(), timeout=3000)
    # preview 仍空（没完成）
    assert w.preview_panel.is_empty() is True


def test_mainwindow_error_shows_in_preview(qtbot, tmp_path):
    """v0.1.1: ConversionError → preview 显示错误信息，progress 隐藏。"""
    from src.core.errors import ConversionError
    from src.ui.main_window import MainWindow
    stub = _StubConverter(fail=True)
    w = MainWindow(converter=stub)
    qtbot.addWidget(w)

    p = tmp_path / "bad.pdf"
    p.write_text("dummy")
    w._on_file_selected(str(p))

    # 错误信息显示在 preview（中文 user_message：无法转换 bad.pdf：文件已损坏，无法解析）
    qtbot.waitUntil(lambda: not w.preview_panel.is_empty(), timeout=3000)
    txt = w.preview_panel.toPlainText()
    assert "bad.pdf" in txt
    assert "损坏" in txt or "无法" in txt  # 中文错误信息
    qtbot.waitUntil(lambda: w._active_worker is None, timeout=2000)


def test_mainwindow_switch_file_cancels_previous(qtbot, tmp_path):
    """v0.1.1: 选新文件 → 自动 cancel 上一个 worker。"""
    from src.ui.main_window import MainWindow
    stub = _StubConverter(sleep=0.3)
    w = MainWindow(converter=stub)
    qtbot.addWidget(w)

    p1 = tmp_path / "first.pdf"
    p1.write_text("dummy")
    p2 = tmp_path / "second.pdf"
    p2.write_text("dummy")

    w._on_file_selected(str(p1))
    # 第一个 worker 还在跑时选第二个
    qtbot.waitUntil(lambda: w._active_worker is not None and w._active_worker.isRunning(), timeout=2000)
    w._on_file_selected(str(p2))
    # 等第二个完成
    qtbot.waitUntil(lambda: not w.preview_panel.is_empty(), timeout=3000)
    # 第一个不应该完成（cancel 了）
    # stub.calls 可能有 1 或 2 个，取决于时序；但 preview 一定显示 second
    txt = w.preview_panel.toPlainText() + w.preview_panel.toHtml()
    assert "second" in txt
