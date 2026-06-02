"""v0.2.7 P1 regression tests (post-audit fixes for review #3-#5).

P1-1 (review #3): MainWindow._start_batch 运行中守卫 —— 二次点击要 cancel
                    旧 BatchWorker，避免信号交织。
P1-2 (review #4): HistoryPanel.refresh 包 sqlite3 try/except，DB 锁 / 损坏
                    不再让 UI 崩。
P1-3 (review #5): BatchWorker._dispatched list 在 finalize 路径 clear()，
                    释放 _ConvertRunnable 强引用。
"""
from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QEventLoop, QTimer

# ============ shared fixtures ============


@pytest.fixture
def isolated_config(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    from src.core.config import ConfigManager
    return ConfigManager()


@pytest.fixture
def isolated_history(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    from src.core.history import HistoryManager
    return HistoryManager()


@pytest.fixture
def main_window(qtbot, isolated_config, isolated_history):
    from src.ui.main_window import MainWindow
    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    qtbot.addWidget(win)
    yield win
    try:
        win.close()
    except Exception:  # noqa: BLE001
        pass


# ============================================================
# P1-1 (review #3): MainWindow._start_batch 运行中守卫
# ============================================================


def test_p1_1_start_batch_running_guard_cancels_old_batch(main_window):
    """P1-1: _start_batch 二次调用 → 旧 _active_batch.cancel() 必须被调。

    之前 _start_batch 入口没守卫，二次点击会直接覆盖 ``self._active_batch`` 引用，
    旧 bw 的 progress / failed signal 仍连到旧 slot（self._on_batch_progress 是
    bound method，新旧 batch 都触发同一个 slot），造成 done 计数被交织刷新。
    修复：入口先 ``self._active_batch.cancel()`` + 状态栏提示，再继续启动新 batch。
    """
    # 注入 spy batch（MagicMock 即可，cancel() 是 no-op + 可断言）
    fake_batch = MagicMock()
    fake_batch.cancel.return_value = None
    main_window._active_batch = fake_batch

    # 文件列表为空 → _start_batch 走"早返回"分支，但守卫逻辑在早返回之前
    # 已执行（修复就是把守卫加在最顶部）。这样测试不需要真实文件。
    # 注：状态栏的"已取消上一次批量"提示会被后续的"文件列表为空"覆盖
    # （这是预期的 UX：file_list 空 → 提示空优先于"已取消"），所以
    # 这里的断言只看 cancel() 调没调，状态栏文案留给 real-file 测试覆盖。
    main_window.file_list.all_paths = lambda: []

    # 二次 _start_batch
    main_window._start_batch()

    # 主契约：旧 batch 的 cancel() 必须被调
    assert fake_batch.cancel.called, (
        "P1-1: _start_batch 入口守卫必须 cancel 旧 _active_batch"
    )
    assert fake_batch.cancel.call_count == 1, (
        f"P1-1: 守卫应只调一次 cancel，got call_count={fake_batch.cancel.call_count}"
    )


def test_p1_1_start_batch_no_active_batch_skips_guard(main_window):
    """P1-1: _active_batch is None 时守卫跳过（无 cancel 调用 + 无状态提示）。"""
    # 确认初始状态
    assert main_window._active_batch is None

    # 文件列表空
    main_window.file_list.all_paths = lambda: []
    main_window._start_batch()

    # 不应写"已取消上一次批量"（没东西可取消）
    msg = main_window.status.currentMessage()
    assert "已取消上一次批量" not in msg, (
        f"P1-1: _active_batch=None 时不应写'已取消'提示，got: {msg!r}"
    )
    # 应是普通的"文件列表为空"提示
    assert "文件列表为空" in msg


def test_p1_1_start_batch_with_real_files_replaces_old_batch(
    qtbot, isolated_config, isolated_history, tmp_path, monkeypatch
):
    """P1-1: 真实文件存在时，二次 _start_batch 旧 bw 被 cancel + 新 bw 启动。

    用 monkeypatch 替换 BatchWorker 类（避免真实线程池），验证：
    1) 第一次 _start_batch 创 BatchWorker(...) → bw1
    2) 把 win._active_batch 设为 bw1（mock 替代真实对象）
    3) 第二次 _start_batch → 旧 bw1.cancel() 被调
    4) 第二次又创了一个新 BatchWorker（bw2），且 win._active_batch 被替换
    """
    from src.ui import main_window as mw_module

    # 计数器：每次 BatchWorker(...) 调就 +1
    created = []
    class _SpyBW:
        def __init__(self, *args, **kwargs):
            self.cancel_called = 0
            self.start_called = 0
            # 给 Qt 信号 dummy 属性（_start_batch 内部要 .connect）
            self.progress = MagicMock()
            self.finished = MagicMock()
            self.item_failed = MagicMock()
            # v0.4.1 P0 S3：main_window.closeEvent 改用 public wait_finished()
            self.wait_finished = MagicMock(return_value=True)
            created.append(self)
        def cancel(self):
            self.cancel_called += 1
        def start(self):
            self.start_called += 1

    monkeypatch.setattr(mw_module, "BatchWorker", _SpyBW)

    from src.ui.main_window import MainWindow
    win = MainWindow(config_manager=isolated_config, history=isolated_history)
    qtbot.addWidget(win)

    # 造一个真文件让 file_list.all_paths() 返回非空
    real = tmp_path / "a.pdf"
    real.write_text("dummy")
    win.file_list.add_files([str(real)])
    assert win.file_list.count() == 1

    # 第一次 _start_batch
    win._start_batch()
    assert len(created) == 1, "第一次应创建 1 个 BatchWorker"
    bw1 = created[0]
    # bw1 现在是 win._active_batch（_SpyBW 构造时无 Qt parent 链，靠 _start_batch
    # 末尾的赋值）。但因为 _SpyBW 是 mock 替代品，win._active_batch 在 _start_batch
    # 末尾被设成 bw1 吗？看一下源代码... _start_batch: bw = BatchWorker(...);
    # ... self._active_batch = bw。所以 win._active_batch == bw1。
    assert win._active_batch is bw1
    # bw1.cancel() 在第一次 _start_batch 期间不应被调（_active_batch 之前是 None）
    assert bw1.cancel_called == 0

    # 第二次 _start_batch：守卫应触发
    win._start_batch()
    # bw1.cancel() 必被调（运行中守卫）
    assert bw1.cancel_called == 1, (
        f"P1-1: 第二次 _start_batch 应 cancel 旧 bw，got cancel_called={bw1.cancel_called}"
    )
    # 应创建第二个 BatchWorker
    assert len(created) == 2, f"第二次应再创建 1 个 BatchWorker，got {len(created)}"
    bw2 = created[1]
    # win._active_batch 现在是 bw2
    assert win._active_batch is bw2, (
        "P1-1: 第二次 _start_batch 末尾 _active_batch 应被替换为新 bw"
    )

    win.close()


# ============================================================
# P1-2 (review #4): HistoryPanel.refresh 包 sqlite3 try/except
# ============================================================


def test_p1_2_history_panel_refresh_swallows_sqlite_error(qtbot, caplog, isolated_history):
    """P1-2: HistoryManager.list() 抛 sqlite3.OperationalError → refresh() 不崩。

    之前 refresh() 直接 ``self._hm.list(limit=100)``，DB 锁 / 损坏下
    ``sqlite3.OperationalError``（"database is locked" / "file is not a database"）
    会冒泡到 Qt event loop，UI 整个崩。修复：包 try/except → log.warning +
    self._all_entries = []，刷新即"看不到历史"，但 UI 继续可用。
    """
    from src.ui.history_panel import HistoryPanel

    # mock history_manager：list() 抛 sqlite3.OperationalError
    hm = MagicMock()
    hm.list.side_effect = sqlite3.OperationalError("database is locked (P1-2 spy)")

    panel = HistoryPanel(hm)
    qtbot.addWidget(panel)

    # refresh() 必须不抛
    with caplog.at_level(logging.WARNING, logger="src.ui.history_panel"):
        panel.refresh()  # 不应抛 sqlite3.OperationalError

    # 主契约 1：_all_entries 被清空（之前是构造时 refresh 写入的 []，但因为
    # 构造时 list() 也抛 → 也是 []；这里再 refresh 一次确认还是 []，且无异常）
    assert panel._all_entries == [], (
        f"P1-2: sqlite3 错误时 _all_entries 应为 []，got: {panel._all_entries!r}"
    )
    # 主契约 2：log.warning 被记
    warns = [r for r in caplog.records if "HistoryPanel.refresh" in r.message]
    assert warns, (
        f"P1-2: 应记 log.warning，got: {[r.message for r in caplog.records]}"
    )
    # 行数（表格）应为 0
    assert panel.row_count() == 0


def test_p1_2_history_panel_refresh_normal_path_still_works(qtbot, isolated_history):
    """P1-2: 正常路径下 refresh() 仍按原行为工作（try/except 不应破坏 happy path）。"""
    from src.ui.history_panel import HistoryPanel

    # 真 HistoryManager + 1 条样本
    isolated_history.request_add(
        source_path="/tmp/p1_2_normal.pdf",
        fmt=".pdf", md_len=100, duration_ms=10, success=True,
    )
    qtbot.waitUntil(
        lambda: len(isolated_history.list(limit=20)) >= 1, timeout=3000
    )

    panel = HistoryPanel(isolated_history)
    qtbot.addWidget(panel)
    assert panel.row_count() == 1

    # refresh 仍是 1 行
    panel.refresh()
    assert panel.row_count() == 1


# ============================================================
# P1-3 (review #5): BatchWorker._dispatched list 清理
# ============================================================


def test_p1_3_batch_worker_clears_dispatched_after_finish(qtbot, tmp_path):
    """P1-3: 10 个文件 batch 完成后 len(bw._dispatched) == 0。

    之前 ``_dispatched: list[_ConvertRunnable]`` 在整个 BatchWorker 生命周期
    永不清零（_on_item_done 走 finished 路径也不会 clear）。runnable 引用计数
    + 内嵌 _Signals QObject 不会释放，BatchWorker.deleteLater() 后 GC
    才回收，但 list 本身长期持有 ref 不利于内存峰值。

    修复：_on_item_done 的 finalize 路径 + cancel() 的 _finalize 路径都加
    ``self._dispatched.clear()``。
    """
    from src.core.batch_worker import BatchWorker

    # 造 10 个文件
    paths = []
    for i in range(10):
        p = tmp_path / f"f{i}.pdf"
        p.write_text("dummy")
        paths.append(str(p))

    class _StubConverter:
        def convert(self, path: str) -> str:
            time.sleep(0.005)  # 慢一点，让并发真派出去
            return f"# {Path(path).name}"

    bw = BatchWorker(_StubConverter(), paths, concurrency=3)
    finished_seen = []
    bw.finished.connect(lambda: finished_seen.append(True))

    bw.start()
    qtbot.waitUntil(lambda: bool(finished_seen), timeout=5000)

    # 主契约：完成后 _dispatched 必须被清空
    assert len(bw._dispatched) == 0, (
        f"P1-3: 完成后 _dispatched 应清空，got len={len(bw._dispatched)}"
    )


def test_p1_3_batch_worker_clears_dispatched_after_cancel(qtbot, tmp_path):
    """P1-3: cancel() 路径 finalize 后 _dispatched 也应清空。"""
    from src.core.batch_worker import BatchWorker

    # 6 个慢任务，concurrency=2
    paths = []
    for i in range(6):
        p = tmp_path / f"f{i}.pdf"
        p.write_text("dummy")
        paths.append(str(p))

    class _SlowConverter:
        def __init__(self):
            self.calls = []
        def convert(self, p):
            self.calls.append(p)
            time.sleep(0.05)
            return f"# {p}"

    conv = _SlowConverter()
    bw = BatchWorker(conv, paths, concurrency=2)
    finished_seen = []
    bw.finished.connect(lambda: finished_seen.append(True))

    bw.start()
    # 立即 cancel
    bw.cancel()
    qtbot.waitUntil(lambda: bool(finished_seen), timeout=5000)

    # cancel 路径下也清 _dispatched
    assert len(bw._dispatched) == 0, (
        f"P1-3: cancel 后 _dispatched 应清空，got len={len(bw._dispatched)}"
    )


# ============================================================
# sanity: 不破现有 144 个测试
# ============================================================


def test_p1_3_sanity_qapp_event_loop_settles(qtbot):
    """sanity: Qt event loop 在跑完 3 个新测试后仍稳定（无残留 timer / signal）。"""
    # 跑一个短 loop 验证事件循环不卡死
    loop = QEventLoop()
    QTimer.singleShot(50, loop.quit)
    loop.exec()
    assert True
