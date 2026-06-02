"""Regression tests for v0.2.3 P2 audit fixes: M4.1 / M4.2 (closeEvent).

M4.1 — closeEvent + worker/batch lifecycle:
  原实现没有 closeEvent override，QThread 被 force-terminate 时 Qt 会
  报 "QThread: Destroyed while thread is still running"。修复：
  - override closeEvent，按顺序 cancel batch / cancel worker /
    wait(2000) / waitForDone(2000) / accept event。
  - 超时也 accept event 避免卡死用户，但 log.warning。
  - _cleanup_worker 末尾 worker.deleteLater()。
  - _on_batch_finished 末尾 bw.deleteLater()。

M4.2 — _active_batch 完整生命周期:
  - __init__ 声明 self._active_batch = None（v0.2.1 H2 已修）。
  - closeEvent 路径下手动清 _active_batch 引用（避免 dangling pointer）。

测试策略：用 MagicMock 注入 _active_worker / _active_batch，避免真实
线程时序，让断言聚焦在"closeEvent 触发了哪些方法"和"引用是否清掉"。
"""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtGui import QCloseEvent

from src.core.config import ConfigManager
from src.core.history import HistoryManager


@pytest.fixture
def isolated_config(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    return ConfigManager()


@pytest.fixture
def isolated_history(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    return HistoryManager()


# ============ M4.1: closeEvent with no active worker/batch ============


def test_m4_1_close_event_none_safe_when_idle(qtbot, isolated_config, isolated_history):
    """M4.1: 没活动 worker / batch 时 close() 不抛，event.accept() 被调。"""
    from src.ui.main_window import MainWindow

    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    qtbot.addWidget(win)
    assert win._active_worker is None
    assert win._active_batch is None

    # 模拟 close event（QCloseEvent 实例化需要接受一个 QEvent.RegisteredType，
    # 但 closeEvent 只看 event.accept() 是否被调）
    evt = QCloseEvent()  # type: ignore[call-arg]
    win.closeEvent(evt)
    # accept() 后 event.isAccepted() 应为 True
    assert evt.isAccepted(), "closeEvent should accept the event in the idle path"


# ============ M4.1: closeEvent cancels active worker ============


def test_m4_1_close_event_cancels_and_waits_worker(
    qtbot, isolated_config, isolated_history
):
    """M4.1: 有 active worker 时，closeEvent 调 worker.cancel() + worker.wait(2000)。

    用 MagicMock 注入 _active_worker，记录调用序列。
    """
    from src.ui.main_window import MainWindow

    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    qtbot.addWidget(win)

    # 注入一个 spy worker：cancel() 和 wait() 都被记录
    fake_worker = MagicMock()
    fake_worker.isRunning.return_value = True
    fake_worker.wait.return_value = True  # 2000ms 内"成功"退出
    win._active_worker = fake_worker

    # 注入 None batch 避免 closeEvent 走 batch 分支
    win._active_batch = None

    evt = QCloseEvent()  # type: ignore[call-arg]
    win.closeEvent(evt)

    # 主契约：cancel 调了、wait(2000) 调了、event 接受了
    assert fake_worker.cancel.called, "worker.cancel() should be called"
    assert fake_worker.wait.called, "worker.wait(2000) should be called"
    wait_args, _wait_kwargs = fake_worker.wait.call_args
    assert wait_args == (2000,), f"wait() 应传 2000ms, got {wait_args}"
    assert evt.isAccepted(), "event should be accepted even after successful wait"


def test_m4_1_close_event_warning_when_worker_times_out(
    qtbot, isolated_config, isolated_history, caplog
):
    """M4.1 异常路径：worker.wait(2000) 超时仍 accept event，但 log.warning。"""
    from src.ui.main_window import MainWindow

    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    qtbot.addWidget(win)

    fake_worker = MagicMock()
    fake_worker.cancel.return_value = None
    fake_worker.wait.return_value = False  # 模拟超时
    win._active_worker = fake_worker
    win._active_batch = None

    evt = QCloseEvent()  # type: ignore[call-arg]
    with caplog.at_level("WARNING"):
        win.closeEvent(evt)

    # 异常路径：仍 accept event（避免卡死用户）
    assert evt.isAccepted(), "异常路径：event 必须 accept，不卡用户"
    # 异常路径：应写一条 warning
    assert any(
        "ConversionWorker 2000ms 内未退出" in rec.message
        for rec in caplog.records
    ), f"应发出 worker 超时 warning, got: {[r.message for r in caplog.records]}"


# ============ M4.1: closeEvent cancels active batch ============


def test_m4_1_close_event_cancels_batch_and_clears_ref(
    qtbot, isolated_config, isolated_history
):
    """M4.1 + M4.2: 有 active batch 时 closeEvent 调 batch.cancel() +
    waitForDone(2000)，并清掉 _active_batch 引用避免 dangling。
    """
    from src.ui.main_window import MainWindow

    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    qtbot.addWidget(win)

    # 注入 spy batch：v0.4.1 P0 S3 后 main_window 改用 public wait_finished()
    # （不再直接访问 _pool），所以 mock 的契约点从 _pool.waitForDone 移到
    # bw.wait_finished()。fake_pool 仍保留是为了 assert pool 路径不被外部触发。
    fake_pool = MagicMock()
    fake_batch = MagicMock()
    fake_batch.wait_finished = MagicMock(return_value=True)
    fake_batch.cancel.return_value = None
    win._active_batch = fake_batch
    # worker 分支不触发
    win._active_worker = None

    evt = QCloseEvent()  # type: ignore[call-arg]
    win.closeEvent(evt)

    # 主契约：batch.cancel() 调了
    assert fake_batch.cancel.called, "batch.cancel() should be called"
    # v0.4.1 P0 S3：改用 public wait_finished(2000) 而非 _pool.waitForDone
    assert fake_batch.wait_finished.called
    wf_args, _ = fake_batch.wait_finished.call_args
    assert wf_args == (2000,), f"wait_finished 应传 2000, got {wf_args}"
    # 反向断言：S3 修复后不应再有人访问 _pool（除非 closeEvent 自己——已删）
    assert not fake_pool.waitForDone.called, (
        "S3 修复后 closeEvent 不应再访问 _pool.waitForDone"
    )
    # M4.2：closeEvent 路径下手动清 _active_batch 引用
    assert win._active_batch is None, (
        "M4.2: closeEvent 路径下 _active_batch 必须清掉（避免 dangling pointer）"
    )
    assert evt.isAccepted()


def test_m4_1_close_event_warning_when_batch_pool_times_out(
    qtbot, isolated_config, isolated_history, caplog
):
    """M4.1 异常路径：batch.wait_finished(2000) 超时仍 accept，但 log.warning。"""
    from src.ui.main_window import MainWindow

    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    qtbot.addWidget(win)

    # v0.4.1 P0 S3：mock 契约点从 _pool.waitForDone 移到 batch.wait_finished()
    fake_batch = MagicMock()
    fake_batch.wait_finished = MagicMock(return_value=False)  # 模拟超时
    win._active_batch = fake_batch
    win._active_worker = None

    evt = QCloseEvent()  # type: ignore[call-arg]
    with caplog.at_level("WARNING"):
        win.closeEvent(evt)

    assert evt.isAccepted(), "异常路径：event 必须 accept"
    assert any(
        "BatchWorker 2000ms 内未排空" in rec.message
        for rec in caplog.records
    ), f"应发出 batch wait_finished 超时 warning, got: {[r.message for r in caplog.records]}"
    # 即使超时也要清掉 _active_batch（M4.2 dangling 防护）
    assert win._active_batch is None


# ============ M4.1: deleteLater 在 _cleanup_worker 末尾被调 ============


def test_m4_1_cleanup_worker_calls_delete_later(
    qtbot, isolated_config, isolated_history
):
    """M4.1: ConversionWorker.finished 触发的 _cleanup_worker 末尾调 deleteLater()。"""
    from src.ui.main_window import MainWindow

    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    qtbot.addWidget(win)

    fake_worker = MagicMock()
    win._active_worker = fake_worker

    win._cleanup_worker(fake_worker)

    # _active_worker 清掉
    assert win._active_worker is None
    # M4.1：worker.deleteLater() 调了
    assert fake_worker.deleteLater.called, (
        "M4.1: _cleanup_worker 末尾必须调 worker.deleteLater()，"
        "避免 QThread force-terminate 警告"
    )


# ============ M4.1: deleteLater 在 _on_batch_finished 末尾被调 ============


def test_m4_1_on_batch_finished_calls_delete_later(
    qtbot, isolated_config, isolated_history
):
    """M4.1: BatchWorker.finished 触发的 _on_batch_finished 末尾调 bw.deleteLater()。"""
    from src.ui.main_window import MainWindow

    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    qtbot.addWidget(win)

    fake_bw = MagicMock()
    win._active_batch = fake_bw

    win._on_batch_finished(fake_bw)

    # M4.2：_on_batch_finished 把 _active_batch 清掉
    assert win._active_batch is None
    # M4.1：bw.deleteLater() 调了
    assert fake_bw.deleteLater.called, (
        "M4.1: _on_batch_finished 末尾必须调 bw.deleteLater()，"
        "避免 QObject 树根泄漏"
    )


# ============ M4.2: closeEvent 引用清理 — 真实 BatchWorker 集成 ============


def test_m4_2_close_event_with_real_batch_clears_active_ref(
    qtbot, isolated_config, isolated_history, tmp_path
):
    """M4.2: 用真实 BatchWorker 跑一遍：start 后 close，_active_batch 应被清。"""
    from src.core.batch_worker import BatchWorker
    from src.ui.main_window import MainWindow

    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    qtbot.addWidget(win)

    # 准备真实文件 + 极慢 converter 让 batch 跑得久一点
    a = tmp_path / "a.txt"
    a.write_text("hi")
    b = tmp_path / "b.txt"
    b.write_text("hi")

    class _SlowConverter:
        def __init__(self):
            self.cancel_observed = []

        def convert(self, path: str) -> str:
            time.sleep(0.05)  # 短一点，不影响测试
            return f"# {Path(path).name}"

    # 直接注入一个真实的 BatchWorker（不走 _start_batch 避免触发真实调度）
    slow = _SlowConverter()
    bw = BatchWorker(slow, [str(a), str(b)], concurrency=1)
    bw.finished.connect(lambda b=bw: win._on_batch_finished(b))
    win._active_batch = bw
    bw.start()
    assert win._active_batch is bw

    # 等 finished 自动触发（事件循环会跑）
    qtbot.waitUntil(lambda: win._active_batch is None, timeout=3000)
    # _on_batch_finished 把 _active_batch 清掉 + bw.deleteLater() 被调
    assert win._active_batch is None


# ============ closeEvent 端到端：close() 不崩 + 接受事件 ============


def test_m4_1_mainwindow_close_does_not_crash_with_active_worker(
    qtbot, isolated_config, isolated_history
):
    """M4.1 端到端：MainWindow.close() 在 active worker 存在时不崩。

    之前没有 closeEvent override，QThread force-terminate 时会出
    "QThread: Destroyed while thread is still running" 警告。
    """
    from src.ui.main_window import MainWindow

    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    qtbot.addWidget(win)

    # 注入 mock worker
    fake_worker = MagicMock()
    fake_worker.isRunning.return_value = True
    fake_worker.wait.return_value = True
    win._active_worker = fake_worker
    win._active_batch = None

    # close() 内部会调 closeEvent，不应崩
    win.close()
    # closeEvent 末尾应已 accept
    assert fake_worker.cancel.called
    assert fake_worker.wait.called
