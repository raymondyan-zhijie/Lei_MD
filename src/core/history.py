"""历史记录管理（）。+ 02 §3.3.1：
- SQLite 持久化转换历史
- 并发模型：WAL + Signal 串行化（读写不互斥，写者唯一在主线程）
- 损坏自动备份 + 重建（02 §6.4 E_INTERNAL_002）
- 容量 trim（默认 50 条）、02 §3.3.1、02 §6.4、04 §2 测试矩阵
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QCoreApplication, QObject, QThread, Signal, Slot


def data_dir() -> Path:
    """跨平台数据目录：Windows %APPDATA%，Linux/macOS $XDG_DATA_HOME。

    每次调用都重新读 env（测试 monkeypatch 友好）。
    """
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "Lei_MD"

def history_db_path() -> Path:
    """history.db 路径。"""
    return data_dir() / "history.db"

# 向后兼容
DB_PATH: Path = history_db_path()

# 表 schema SSOT
_SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,
    source_format TEXT,
    markdown_length INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    success BOOLEAN DEFAULT 1,
    error_msg TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime'))
)
"""

_INDEX = "CREATE INDEX IF NOT EXISTS idx_created_at ON history(created_at DESC)"

@dataclass
class HistoryEntry:
    """一条历史记录（ history 表 schema）。"""

    id: int
    source_path: str
    source_format: str
    markdown_length: int
    duration_ms: int
    success: bool
    error_msg: str
    created_at: str

class HistoryManager(QObject):
    """SQLite 历史记录管理器。

    并发模型（WAL + Signal 串行化，详见 02 §3.3.1）：
    - PRAGMA journal_mode=WAL    读写并发不互斥
    - PRAGMA busy_timeout=5000   极端竞争自动 retry
    - PRAGMA synchronous=NORMAL  WAL 推荐配置
    - 所有写入走 add_requested Signal → 槽永远在主线程执行，写者唯一
    - 调用方（ConverterWorker）调 request_add()，不直接碰 DB

    崩溃恢复（02 §6.4 E_INTERNAL_002）：
    - 启动时 PRAGMA integrity_check
    - 损坏 → 备份 .db.bak.<ts> + 重建
    """

    # ConverterWorker 线程 emit，Qt 自动 queued 到主线程
    add_requested = Signal(dict)

    def __init__(self, max_entries: int = 50, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # hotfix: _conn 必须先初始化为 None，
        # 这样 _open_and_init_db() 在 try/except 路径中途失败时，
        # 公共方法 (_on_add / list / _trim / close) 的 None 守卫可命中，
        # 不会 AttributeError 崩溃整个 UI。
        self._conn: sqlite3.Connection | None = None
        db_dir = data_dir()
        db_dir.mkdir(parents=True, exist_ok=True)
        self._max = max_entries

        # 初始化 DB（含损坏恢复）
        # try/finally 保护：即使 _open_and_init_db 抛异常，
        # __init__ 也能完成，self._conn 保持为 None。
        try:
            self._open_and_init_db()
        finally:
            # Signal → 主线程槽
            self.add_requested.connect(self._on_add)

    def _assert_main_thread(self) -> None:
        """：强制 contract —— 公共方法只在主线程调。

        check_same_thread=False 仅靠注释保证，运行时一旦从 worker 线程误调
        会导致 sqlite3 锁死/段错误。QCoreApplication 未启动时（CLI/测试初始化）
        跳过该断言。
        """
        app = QCoreApplication.instance()
        if app is None:
            return
        if QThread.currentThread() is not app.thread():
            raise RuntimeError(
                "HistoryManager must be called from the main thread "
                "(uses check_same_thread=False sqlite connection; "
                "see docs/02-architecture.md §3.3.1)."
            )

    def _open_and_init_db(self) -> None:
        """打开 + PRAGMA + integrity_check + CREATE TABLE。损坏则备份重建。"""
        db_path = history_db_path()
        try:
            self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            # 完整性检查（PRAGMA 成功后才查）
            try:
                result = self._conn.execute("PRAGMA integrity_check").fetchone()
            except sqlite3.DatabaseError:
                result = None
            if result is None or (result and result[0] != "ok"):
                # 逻辑损坏：备份 + 重建
                self._conn.close()
                self._conn = None  # : 显式重置让 _backup_and_recreate 接管
                self._backup_and_recreate()
                return
        except sqlite3.DatabaseError:
            # 物理损坏（PRAGMA 都进不去）：备份 + 重建
            # hotfix: sqlite3.connect() 成功但 PRAGMA 失败时，
            # _conn 已创建但没被 close，会泄漏到 GC。先关再重建。
            if hasattr(self, "_conn") and self._conn is not None:
                try:
                    self._conn.close()
                except sqlite3.Error:
                    pass
                self._conn = None
            self._backup_and_recreate()
            return

        # 正常路径：建表 + 索引
        self._conn.execute(_SCHEMA)
        self._conn.execute(_INDEX)
        self._conn.commit()

    def _backup_and_recreate(self) -> None:
        """备份当前 db 文件（如果有）→ 删除 → 重新建空表。"""
        db_path = history_db_path()
        if db_path.exists():
            bak = db_path.with_suffix(f".db.bak.{int(time.time())}")
            try:
                shutil.copy2(db_path, bak)
            except OSError:
                pass
            try:
                db_path.unlink()
            except OSError:
                pass
        # 新连接
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute(_SCHEMA)
        self._conn.execute(_INDEX)
        self._conn.commit()

    def request_add(
        self,
        source_path: str,
        fmt: str,
        md_len: int,
        duration_ms: int,
        success: bool,
        error: str = "",
    ) -> None:
        """线程安全入口。ConverterWorker 在 QThread 中调这个。

        Signal 会把执行切回主线程的 _on_add 槽。
        """
        self.add_requested.emit({
            "source_path": source_path,
            "fmt": fmt,
            "md_len": md_len,
            "duration_ms": duration_ms,
            "success": success,
            "error": error,
        })

    @Slot(dict)
    def _on_add(self, payload: dict[str, Any]) -> None:
        """实际写入槽。永远在主线程执行。"""
        self._assert_main_thread()
        # hotfix: _conn 初始化失败时静默跳过，
        # 避免 UI 在用户首次交互时 AttributeError 崩溃。
        if self._conn is None:
            return
        self._conn.execute(
            "INSERT INTO history "
            "(source_path, source_format, markdown_length, duration_ms, success, error_msg) "
            "VALUES (?,?,?,?,?,?)",
            (
                payload["source_path"],
                payload["fmt"],
                payload["md_len"],
                payload["duration_ms"],
                payload["success"],
                payload["error"],
            ),
        )
        self._conn.commit()
        self._trim()

    def list(self, limit: int = 20) -> list[HistoryEntry]:
        """读取。WAL 模式下读不阻塞写，只在主线程调用所以无需额外保护。"""
        self._assert_main_thread()
        # hotfix: _conn 未初始化时返回空列表，
        # 让 UI 显示空状态而不是抛 AttributeError。
        if self._conn is None:
            return []
        rows = self._conn.execute(
            "SELECT id, source_path, source_format, markdown_length, "
            "duration_ms, success, error_msg, created_at "
            "FROM history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [HistoryEntry(*r) for r in rows]

    def _trim(self) -> None:
        """保留最新 max_entries 条，删除更旧的。"""
        self._assert_main_thread()
        # hotfix: _conn 未初始化时跳过 trim。
        if self._conn is None:
            return
        self._conn.execute(
            "DELETE FROM history WHERE id NOT IN ("
            "  SELECT id FROM history ORDER BY id DESC LIMIT ?"
            ")",
            (self._max,),
        )
        self._conn.commit()

    def close(self) -> None:
        """应用退出时调用。WAL checkpoint + 关闭连接。"""
        self._assert_main_thread()
        # hotfix: _conn 未初始化时不需要 close。
        if self._conn is None:
            return
        try:
            self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass
        try:
            self._conn.close()
        except sqlite3.Error:
            pass
