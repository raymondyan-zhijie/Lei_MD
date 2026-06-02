"""批量并行转换测试（Task 2.2）。

按 03 §Task 2.2 + Sprint 2 AppConfig.batch_concurrency（默认 4）：
- QThreadPool 跑 N 个 QRunnable，并发度可配
- progress(int done, int total) 每完成一个 emit
- item_finished(path, markdown) / item_failed(path, err) 单独 signal
- finished() 所有完成时 emit（成功失败都计 done）
- 单文件失败不影响其他
- cancel() 不启动新文件，已跑的不强杀（collaborative）
"""
from __future__ import annotations

import time
from pathlib import Path


class _StubConverter:
    """可控制 sleep / fail 的转换器替身。"""

    def __init__(self, *, sleep: float = 0.02, fail_paths: set[str] | None = None):
        self.sleep = sleep
        self.fail_paths = fail_paths or set()
        self.calls: list[str] = []

    def convert(self, path: str) -> str:
        self.calls.append(path)
        if self.sleep:
            time.sleep(self.sleep)
        if path in self.fail_paths:
            from src.core.errors import ConversionError, ErrorCode
            raise ConversionError(ErrorCode.E_CONVERT_002, filename=Path(path).name)
        return f"# {Path(path).name}\n\nok"


def _make_paths(tmp_path, names):
    paths = []
    for n in names:
        p = tmp_path / n
        p.write_text("dummy")
        paths.append(str(p))
    return paths


# ----------- 全部成功 -----------

def test_batch_worker_runs_all_and_emits_finished(qtbot, tmp_path):
    """N 个文件全部成功 → finished() + N 个 item_finished。"""
    from src.core.batch_worker import BatchWorker
    paths = _make_paths(tmp_path, ["a.pdf", "b.docx", "c.html"])
    stub = _StubConverter(sleep=0.01)
    bw = BatchWorker(stub, paths, concurrency=2)
    finished_seen = []
    item_finished_count = []
    bw.finished.connect(lambda: finished_seen.append(True))
    bw.item_finished.connect(lambda p, md: item_finished_count.append(p))

    bw.start()
    qtbot.waitUntil(lambda: bool(finished_seen), timeout=5000)
    assert len(item_finished_count) == 3
    assert len(stub.calls) == 3


# ----------- 进度信号 -----------

def test_batch_worker_emits_progress_with_done_total(qtbot, tmp_path):
    """progress(done, total) done 0→N 单调递增。"""
    from src.core.batch_worker import BatchWorker
    paths = _make_paths(tmp_path, [f"f{i}.pdf" for i in range(6)])
    stub = _StubConverter(sleep=0.02)
    bw = BatchWorker(stub, paths, concurrency=3)
    progress = []
    bw.progress.connect(lambda d, t: progress.append((d, t)))

    bw.start()
    qtbot.waitUntil(lambda: bw._done_count == 6, timeout=5000)
    # done 终值 == 6, total == 6
    last = progress[-1]
    assert last == (6, 6)
    # done 单调不减
    dones = [p[0] for p in progress]
    assert dones == sorted(dones)


# ----------- 单文件失败不影响其他 -----------

def test_batch_worker_item_failure_does_not_stop_others(qtbot, tmp_path):
    """一个失败 → item_failed + 其他继续 → 仍 finished。"""
    from src.core.batch_worker import BatchWorker
    paths = _make_paths(tmp_path, ["a.pdf", "b.pdf", "c.pdf"])
    stub = _StubConverter(sleep=0.01, fail_paths={paths[1]})  # b 失败
    bw = BatchWorker(stub, paths, concurrency=2)
    finished_seen = []
    item_ok = []
    item_failed = []
    bw.finished.connect(lambda: finished_seen.append(True))
    bw.item_finished.connect(lambda p, md: item_ok.append(p))
    bw.item_failed.connect(lambda p, err: item_failed.append(p))

    bw.start()
    qtbot.waitUntil(lambda: bool(finished_seen), timeout=5000)
    # 3 个都"处理了"（2 成功 + 1 失败）
    assert len(item_ok) == 2
    assert len(item_failed) == 1
    assert paths[1] in item_failed
    assert paths[0] in item_ok
    assert paths[2] in item_ok


# ----------- 并发度限制 -----------

def test_batch_worker_respects_concurrency(qtbot, tmp_path):
    """concurrency=2 → 同一时刻最多 2 个在跑（用慢任务验证）。"""
    from src.core.batch_worker import BatchWorker
    paths = _make_paths(tmp_path, [f"f{i}.pdf" for i in range(6)])
    # 慢任务 + 计数器
    in_flight = 0
    max_in_flight = 0
    lock = __import__("threading").Lock()

    class _TrackingConverter:
        def convert(self, p):
            nonlocal in_flight, max_in_flight
            with lock:
                in_flight += 1
                if in_flight > max_in_flight:
                    max_in_flight = in_flight
            time.sleep(0.05)
            with lock:
                in_flight -= 1
            return f"# {Path(p).name}"

    bw = BatchWorker(_TrackingConverter(), paths, concurrency=2)
    finished_seen = []
    bw.finished.connect(lambda: finished_seen.append(True))
    bw.start()
    qtbot.waitUntil(lambda: bool(finished_seen), timeout=5000)
    assert max_in_flight <= 2, f"并发 > 2: {max_in_flight}"


# ----------- cancel -----------

def test_batch_worker_cancel_stops_new_dispatch(qtbot, tmp_path):
    """cancel() → 已 dispatch 的可跑完，pending 不再启动。"""
    from src.core.batch_worker import BatchWorker
    # 6 个慢任务，concurrency=2
    paths = _make_paths(tmp_path, [f"f{i}.pdf" for i in range(6)])

    class _SlowConverter:
        def __init__(self):
            self.calls = []
        def convert(self, p):
            self.calls.append(p)
            time.sleep(0.1)
            return f"# {p}"

    conv = _SlowConverter()
    bw = BatchWorker(conv, paths, concurrency=2)
    finished_seen = []
    bw.finished.connect(lambda: finished_seen.append(True))
    bw.start()
    # 立即 cancel（任务还没开始）
    bw.cancel()
    qtbot.waitUntil(lambda: bool(finished_seen), timeout=3000)
    # 不应 6 个都跑（只跑了已 dispatch 的，最多 2 个）
    assert len(conv.calls) < 6, f"cancel 后还在跑：{len(conv.calls)}/6"
