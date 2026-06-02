"""HistoryManager 测试（Task 1.9）。

按 03 §Task 1.9 + 02 §3.3.1：
- 路径：Windows %APPDATA%\\Lei_MD\\history.db，Linux/macOS ~/.local/share/Lei_MD/history.db
- Schema: history(id, source_path, source_format, markdown_length, duration_ms, success, error_msg, created_at)
- 并发：WAL + busy_timeout=5000 + synchronous=NORMAL
- 写入：request_add() → emit add_requested(dict) → 主线程槽 _on_add
- 读取：list(limit=20) -> list[HistoryEntry]
- 容量：_trim 保留 max_entries=50
- 崩溃恢复：PRAGMA integrity_check，损坏 → 备份 .db.bak.<ts> + 重建（E_INTERNAL_002）
- 关闭：close() → PRAGMA wal_checkpoint(TRUNCATE)
"""
from __future__ import annotations

import pytest


@pytest.fixture
def isolated_data_home(monkeypatch, tmp_path):
    """XDG_DATA_HOME / APPDATA → tmp。"""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.delenv("APPDATA", raising=False)
    return tmp_path


@pytest.fixture
def history_manager(isolated_data_home, qtbot):
    """qtbot 触发事件循环，使 Signal 槽能 dispatch。"""
    from src.core.history import HistoryManager
    hm = HistoryManager(max_entries=5)
    yield hm
    hm.close()


# ----------- 基础增删查 -----------

def test_history_add_and_list(history_manager, qtbot):
    """request_add → list 应含新条目。"""
    hm = history_manager
    hm.request_add(source_path="/tmp/a.pdf", fmt="pdf", md_len=100, duration_ms=50, success=True)
    qtbot.waitUntil(lambda: len(hm.list(limit=10)) >= 1, timeout=2000)
    rows = hm.list(limit=10)
    assert len(rows) == 1
    assert rows[0].source_path == "/tmp/a.pdf"
    assert rows[0].source_format == "pdf"
    assert rows[0].markdown_length == 100
    assert bool(rows[0].success) is True


def test_history_list_ordered_newest_first(history_manager, qtbot):
    """list() 按 id DESC：最新条目在最前。"""
    hm = history_manager
    for i in range(3):
        hm.request_add(source_path=f"/tmp/f{i}.pdf", fmt="pdf", md_len=10, duration_ms=5, success=True)
        qtbot.waitUntil(lambda i=i: len(hm.list(limit=10)) >= i + 1, timeout=2000)
    rows = hm.list(limit=10)
    paths = [r.source_path for r in rows]
    assert paths == ["/tmp/f2.pdf", "/tmp/f1.pdf", "/tmp/f0.pdf"]


# ----------- 容量 trim -----------

def test_history_trim_keeps_max_entries(history_manager, qtbot):
    """超 max_entries → _trim 删除最旧。"""
    hm = history_manager  # max_entries=5
    for i in range(8):
        hm.request_add(source_path=f"/tmp/f{i}.pdf", fmt="pdf", md_len=10, duration_ms=5, success=True)
    # 等最后一条入
    qtbot.waitUntil(lambda: any(r.source_path == "/tmp/f7.pdf" for r in hm.list(limit=20)), timeout=3000)
    rows = hm.list(limit=20)
    assert len(rows) == 5
    # 最新 5 条保留
    paths = [r.source_path for r in rows]
    assert "/tmp/f7.pdf" in paths
    assert "/tmp/f0.pdf" not in paths
    assert "/tmp/f2.pdf" not in paths  # 旧的被 trim


# ----------- 失败条目 -----------

def test_history_records_failure_with_error(history_manager, qtbot):
    """success=False + error_msg 写入。"""
    hm = history_manager
    hm.request_add(
        source_path="/tmp/bad.pdf", fmt="pdf", md_len=0,
        duration_ms=10, success=False, error="E_CONVERT_002",
    )
    qtbot.waitUntil(lambda: len(hm.list(limit=10)) >= 1, timeout=2000)
    rows = hm.list(limit=10)
    assert bool(rows[0].success) is False
    assert rows[0].error_msg == "E_CONVERT_002"


# ----------- 跨线程安全 -----------

def test_history_request_add_from_thread_is_safe(history_manager, qtbot):
    """从子线程调 request_add → Signal queued → 主线程写。"""
    import threading
    hm = history_manager
    result = {}

    def worker():
        try:
            for i in range(3):
                hm.request_add(
                    source_path=f"/tmp/thread{i}.pdf", fmt="pdf",
                    md_len=10, duration_ms=1, success=True,
                )
            result["ok"] = True
        except Exception as e:
            result["err"] = str(e)

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=2.0)
    assert result.get("ok") is True, result
    qtbot.waitUntil(lambda: len(hm.list(limit=20)) >= 3, timeout=3000)
    rows = hm.list(limit=20)
    assert len(rows) == 3


# ----------- 崩溃恢复 -----------

def test_history_corrupted_db_is_backed_up_and_recreated(isolated_data_home, qtbot):
    """history.db 损坏 → 启动时备份 .db.bak.<ts> + 重建空表。"""
    from src.core.history import HistoryManager

    # 写坏 DB（不是有效 SQLite）
    db_dir = isolated_data_home / "Lei_MD"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "history.db"
    db_path.write_bytes(b"this is not a sqlite db, just random bytes abcdef0123456789" * 100)

    # 实例化应触发 integrity_check 失败 → 备份 + 重建
    hm = HistoryManager(max_entries=10)

    # 应能正常 add（重建后的表）
    hm.request_add(source_path="/tmp/post.pdf", fmt="pdf", md_len=1, duration_ms=1, success=True)
    qtbot.waitUntil(lambda: len(hm.list(limit=10)) >= 1, timeout=2000)

    # 备份存在
    bak_files = list(db_dir.glob("history.db.bak.*"))
    assert len(bak_files) == 1, f"应有 1 个备份文件，实际: {bak_files}"
    hm.close()
