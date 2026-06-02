"""Regression tests for v0.2.2 P1 hotfixes: H1 / H5 / H6 / H9."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QTimer

from src.core.batch_worker import BatchWorker
from src.core.config import ConfigManager

# ============ H1: chmod 0o600 ============


def test_config_save_sets_file_mode_0o600(monkeypatch, tmp_path):
    """H1: ConfigManager.save() makes config.json owner-read/write only (POSIX)."""
    if os.name == "nt":
        pytest.skip("POSIX-only assertion; chmod semantics differ on Windows")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    cm = ConfigManager()
    cm.update(llm_api_key="sk-secret-xyz")
    cfg_file = tmp_path / "config" / "Lei_MD" / "config.json"
    assert cfg_file.exists()
    mode = cfg_file.stat().st_mode & 0o777
    assert mode == 0o600, f"expected 0o600, got {oct(mode)}"


def test_config_backup_reset_also_restricts(monkeypatch, tmp_path):
    """H1: when config is corrupt, the reset default also gets 0o600."""
    if os.name == "nt":
        pytest.skip("POSIX-only assertion")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    cfg_file = tmp_path / "config" / "Lei_MD" / "config.json"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text("{ not valid json", encoding="utf-8")
    ConfigManager()  # triggers _backup_and_reset
    mode = cfg_file.stat().st_mode & 0o777
    assert mode == 0o600, f"expected 0o600, got {oct(mode)}"


# ============ H5: BatchWorker done_count 互斥 + finished 单发 ============


def test_batch_worker_finished_emits_exactly_once_under_cancel(qtbot, monkeypatch):
    """H5: cancel() + 自然完成并发时，finished 只发一次。"""
    converter = MagicMock()
    converter.convert = lambda p: f"# {p}"

    # 用真实 BatchWorker 跑 5 个小任务
    paths = [f"/tmp/file_{i}.txt" for i in range(5)]
    bw = BatchWorker(converter, paths, concurrency=2)
    finished_count = []

    def _on_finished():
        finished_count.append(1)

    bw.finished.connect(_on_finished)

    # 立即取消 → 与第一个 item_done 并发
    bw.start()
    QTimer.singleShot(0, bw.cancel)

    qtbot.waitUntil(lambda: len(finished_count) >= 1, timeout=3000)
    # 给事件循环一拍时间，看是否双发
    QTimer.singleShot(100, lambda: finished_count.append("sentinel"))
    qtbot.waitUntil(lambda: "sentinel" in finished_count, timeout=2000)

    real_finished_emits = sum(1 for x in finished_count if x == 1)
    assert real_finished_emits == 1, (
        f"finished should emit exactly once, got {real_finished_emits} times"
    )


# ============ H6: HistoryManager 主线程 assert ============


def test_history_raises_when_called_from_worker_thread(qtbot, monkeypatch, tmp_path):
    """H6: HistoryManager public methods raise RuntimeError from non-main thread."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    from src.core.history import HistoryManager

    hm = HistoryManager()  # created in main thread (qtbot provides qapp)
    errors = []

    def _attack():
        try:
            hm.list()  # 应在主线程调
        except RuntimeError as e:
            errors.append(str(e))

    t = threading.Thread(target=_attack)
    t.start()
    t.join(timeout=2)

    assert errors, "expected RuntimeError when calling list() from worker thread"
    assert "main thread" in errors[0].lower()


# ============ H9: i18n 500MB 匹配代码 ============


def test_zh_cn_i18n_matches_code_file_size_limit():
    """H9: zh_CN.json E_FILE_TOO_LARGE string should say 500MB (matches errors.py)."""
    locale_path = Path(__file__).resolve().parent.parent / "src" / "resources" / "locales" / "zh_CN.json"
    data = json.loads(locale_path.read_text(encoding="utf-8"))
    msg = data.get("error.E_FILE_TOO_LARGE", "")
    assert "500MB" in msg, f"expected 500MB, got: {msg}"
