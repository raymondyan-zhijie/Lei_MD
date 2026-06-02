"""v0.4.2 P1 A1：FileItem 数据类测试。

测试目标：
- 默认值（status=pending, result="", error="", duration=0.0）
- 状态变更（is_done / is_failed 行为）
- 工具方法：short_name / size_human
- 字段顺序与文档 02 §3.4 一致
"""
from __future__ import annotations

from pathlib import Path


def test_file_item_defaults():
    """FileItem() 默认值：status=pending, result="", error="", duration=0.0。"""
    from src.core.file_item import FileItem

    item = FileItem(path=Path("a.pdf"), format="pdf", size=1024)
    assert item.path == Path("a.pdf")
    assert item.format == "pdf"
    assert item.size == 1024
    assert item.status == "pending"
    assert item.result == ""
    assert item.error == ""
    assert item.duration == 0.0
    assert item.is_done() is False
    assert item.is_failed() is False


def test_file_item_status_transitions():
    """status 字段允许 pending / converting / done / error，is_done/is_failed 行为正确。"""
    from src.core.file_item import FileItem

    item = FileItem(path=Path("a.pdf"), format="pdf", size=1024)
    # converting 阶段
    item.status = "converting"
    assert item.is_done() is False
    assert item.is_failed() is False
    # done 阶段
    item.status = "done"
    item.result = "# Hello"
    item.duration = 1.5
    assert item.is_done() is True
    assert item.is_failed() is False
    # error 阶段
    item.status = "error"
    item.error = "E_CONVERT_002"
    assert item.is_done() is False
    assert item.is_failed() is True


def test_file_item_short_name():
    """short_name() 返回文件名（不含目录）。"""
    from src.core.file_item import FileItem

    item = FileItem(
        path=Path("/home/user/Documents/report.pdf"),
        format="pdf",
        size=2048,
    )
    assert item.short_name() == "report.pdf"


def test_file_item_size_human_b():
    """size_human() < 1024 → 整数 B。"""
    from src.core.file_item import FileItem

    item = FileItem(path=Path("a.txt"), format="txt", size=512)
    assert item.size_human() == "512 B"


def test_file_item_size_human_kb():
    """size_human() < 1MB → KB 一位小数。"""
    from src.core.file_item import FileItem

    item = FileItem(path=Path("a.txt"), format="txt", size=2048)
    assert item.size_human() == "2.0 KB"
    item = FileItem(path=Path("a.txt"), format="txt", size=1536)
    assert item.size_human() == "1.5 KB"


def test_file_item_size_human_mb():
    """size_human() < 1GB → MB 一位小数。"""
    from src.core.file_item import FileItem

    item = FileItem(path=Path("a.pdf"), format="pdf", size=2 * 1024 * 1024)
    assert item.size_human() == "2.0 MB"


def test_file_item_size_human_gb():
    """size_human() ≥ 1GB → GB 两位小数。"""
    from src.core.file_item import FileItem

    item = FileItem(path=Path("a.zip"), format="zip", size=2 * 1024 * 1024 * 1024)
    assert item.size_human() == "2.00 GB"
