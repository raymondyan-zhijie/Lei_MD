"""Regression tests for v0.2.4 P2 audit fixes (M3.7 / M5.3 / M3.8).

Covers:
- M3.7: `is_file()` 拒绝目录/socket 等"存在但非普通文件"输入
- M5.3: os.path.getsize() 抛 OSError（权限/IO）→ 翻译为 E_FILE_001，
  不再被上层 "except Exception" 误归类为 E_CONVERT_002
- M3.8: MarkItDownConverter.clone_for_thread() 返回独立实例；
  BatchWorker 每个 _ConvertRunnable 持有独立 converter（线程隔离）
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest


@pytest.fixture
def converter(qapp):
    """Local copy of test_converter.py::converter fixture (avoids cross-file fixture dep)."""
    from src.core.converter import MarkItDownConverter
    return MarkItDownConverter()


# ============ M3.7: is_file() 拒绝目录 ============


def test_converter_rejects_directory_with_e_file_001(converter, tmp_path):
    """M3.7: 目录传入 → E_FILE_001（不再误触 E_FILE_002 / E_FILE_003）。"""
    from src.core.errors import ConversionError, ErrorCode

    dir_path = tmp_path / "a_directory"
    dir_path.mkdir()
    assert dir_path.exists()
    assert not dir_path.is_file()

    with pytest.raises(ConversionError) as exc:
        converter.convert(str(dir_path))
    assert exc.value.code == ErrorCode.E_FILE_001
    # 文件名应是目录名
    assert "a_directory" in exc.value.user_message


def test_converter_directory_not_misclassified_as_empty(converter, tmp_path):
    """M3.7: 目录不会被误判为空文件（E_FILE_002）。"""
    from src.core.errors import ConversionError, ErrorCode

    dir_path = tmp_path / "subdir"
    dir_path.mkdir()
    with pytest.raises(ConversionError) as exc:
        converter.convert(str(dir_path))
    # 必须是 E_FILE_001，绝不能是 E_FILE_002
    assert exc.value.code == ErrorCode.E_FILE_001
    assert exc.value.code != ErrorCode.E_FILE_002


# ============ M5.3: OSError → E_FILE_001 ============


def test_converter_translates_oserror_to_e_file_001(converter, tmp_path, monkeypatch):
    """M5.3: os.path.getsize() 抛 OSError（权限/IO）→ E_FILE_001。"""
    from src.core.errors import ConversionError, ErrorCode

    pdf = tmp_path / "locked.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    def raise_oserror(p):
        raise OSError(13, "Permission denied")

    monkeypatch.setattr("os.path.getsize", raise_oserror)

    with pytest.raises(ConversionError) as exc:
        converter.convert(str(pdf))
    assert exc.value.code == ErrorCode.E_FILE_001
    # cause 链保留原始 OSError
    assert exc.value.cause is not None
    assert isinstance(exc.value.cause, OSError)


def test_converter_translates_oserror_not_misclassified_as_corrupt(converter, tmp_path, monkeypatch):
    """M5.3: OSError 不会向上冒泡为 E_CONVERT_002（文件损坏）误报。"""
    from src.core.errors import ConversionError, ErrorCode

    pdf = tmp_path / "no_perm.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr("os.path.getsize", lambda p: (_ for _ in ()).throw(OSError(5, "I/O error")))

    with pytest.raises(ConversionError) as exc:
        converter.convert(str(pdf))
    # 必须是 E_FILE_001，绝不能是 E_CONVERT_002
    assert exc.value.code == ErrorCode.E_FILE_001
    assert exc.value.code != ErrorCode.E_CONVERT_002


# ============ M3.8: clone_for_thread 独立实例 ============


def test_clone_for_thread_returns_independent_instance():
    """M3.8: clone_for_thread() 返回新对象，与原对象不是同一个。

    v0.4.4+：LLM 参数已移除，构造改成无参。
    """
    from src.core.converter import MarkItDownConverter

    orig = MarkItDownConverter()
    clone = orig.clone_for_thread()
    # 是新实例，不是 orig 本身
    assert clone is not orig
    assert isinstance(clone, MarkItDownConverter)


def test_clone_for_thread_gives_independent_markitdown_engine(monkeypatch):
    """M3.8: 原实例与 clone 的 _md 是不同对象（线程隔离的关键）。"""
    from src.core.converter import MarkItDownConverter

    # 记录 MarkItDown 构造次数和实例
    instances: list[object] = []

    class _FakeMD:
        def __init__(self, *args, **kwargs):
            instances.append(self)

        def convert(self, p):
            from unittest.mock import MagicMock
            return MagicMock(markdown="# ok")

    monkeypatch.setattr("src.core.converter.MarkItDown", _FakeMD)

    orig = MarkItDownConverter()
    # 触发一次原实例 lazy 构造 _md
    pdf = "/tmp/fake.pdf"
    # 先 patch exists/is_file/getsize 让 convert 走到 _ensure_md
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
    monkeypatch.setattr("pathlib.Path.is_file", lambda self: True)
    monkeypatch.setattr("os.path.getsize", lambda p: 100)
    orig.convert(pdf)
    # 此时 instances 应有 1 个（orig 的 _md）

    clone = orig.clone_for_thread()
    # clone_for_thread 主动构造 _md，instances 应有 2 个
    assert len(instances) == 2
    # orig._md 和 clone._md 是不同对象
    assert orig._md is not clone._md
    # 两者都是 _FakeMD 实例
    assert isinstance(orig._md, _FakeMD)
    assert isinstance(clone._md, _FakeMD)


def test_clone_for_thread_does_not_share_state_with_original(monkeypatch):
    """M3.8: 修改 clone 的 _md 不会影响 orig 的 _md（独立状态）。"""
    from src.core.converter import MarkItDownConverter

    orig = MarkItDownConverter()
    # 直接给 orig 赋一个假 _md
    orig._md = object()
    clone = orig.clone_for_thread()
    # orig 仍持有它自己的 _md
    assert clone._md is not orig._md
    assert clone._md is not None


# ============ M3.8: BatchWorker 每个 runnable 独立 converter ============


def test_batch_worker_runnable_uses_independent_cloned_converter(qtbot, tmp_path, monkeypatch):
    """M3.8: BatchWorker 跑 N 个文件后，MarkItDown 被构造 N 次（每次 clone_for_thread）。"""
    from src.core.batch_worker import BatchWorker
    from src.core.converter import MarkItDownConverter

    # 记录所有 MarkItDown 实例
    md_instances: list[object] = []
    orig_init_count = [0]

    class _CountingMD:
        def __init__(self, *args, **kwargs):
            md_instances.append(self)
            orig_init_count[0] += 1

        def convert(self, p):
            from unittest.mock import MagicMock
            return MagicMock(markdown=f"# {Path(p).name}")

    monkeypatch.setattr("src.core.converter.MarkItDown", _CountingMD)

    # 准备 4 个文件
    paths = []
    for i in range(4):
        p = tmp_path / f"f{i}.pdf"
        p.write_bytes(b"%PDF-1.4\n")
        paths.append(str(p))

    # 真实 MarkItDownConverter
    converter = MarkItDownConverter()
    # patch 掉 _ensure_md / clone_for_thread 内部的 MarkItDown 构造走我们的计数器
    # （上面 monkeypatch 已经把 src.core.converter.MarkItDown 替换了）

    bw = BatchWorker(converter, paths, concurrency=2)
    finished_seen = []
    bw.finished.connect(lambda: finished_seen.append(True))

    bw.start()
    qtbot.waitUntil(lambda: bool(finished_seen), timeout=5000)

    # BatchWorker 不在 init 时 clone（lazy），所以此时还没有 MarkItDown 实例
    # 4 个 runnable 在 run() 入口各调一次 clone_for_thread()，每次构造 1 个 MarkItDown
    # 总计应 = 4（每个 runnable 1 个独立 _md）
    assert orig_init_count[0] == 4, (
        f"expected 4 MarkItDown instances (1 per runnable clone), got {orig_init_count[0]}"
    )
    # 每个实例都不同
    assert len(set(id(m) for m in md_instances)) == 4


def test_batch_worker_runnable_falls_back_when_no_clone_for_thread(qtbot, tmp_path):
    """M3.8 fallback: 替身 converter 没有 clone_for_thread 时，runnable 仍能工作。"""
    from src.core.batch_worker import BatchWorker

    class _PlainConverter:
        """无 clone_for_thread 的替身（_StubConverter 风格）。"""
        def __init__(self):
            self.calls = []
        def convert(self, p):
            self.calls.append(p)
            time.sleep(0.01)
            return f"# {Path(p).name}"

    paths = []
    for i in range(3):
        p = tmp_path / f"x{i}.pdf"
        p.write_bytes(b"x")
        paths.append(str(p))

    conv = _PlainConverter()
    bw = BatchWorker(conv, paths, concurrency=2)
    finished_seen = []
    bw.finished.connect(lambda: finished_seen.append(True))

    bw.start()
    qtbot.waitUntil(lambda: bool(finished_seen), timeout=5000)
    # 3 个都跑了（fallback 到原 converter）
    assert len(conv.calls) == 3
