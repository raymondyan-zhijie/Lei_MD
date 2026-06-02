"""FileList 已添加文件列表测试（Task 1.6）。

按 03 §Task 1.6：4 个测试。
- QListWidget 包装
- add_files(paths: list[str]) 过滤已存在、过滤不支持扩展名
- clear() / count() / selected_paths()
- 双击/选中触发 file_selected(str) signal
"""
from __future__ import annotations


def test_filelist_starts_empty(qtbot):
    """初始：count() == 0。"""
    from src.ui.file_list import FileList
    fl = FileList()
    qtbot.addWidget(fl)
    assert fl.count() == 0


def test_filelist_add_files_dedupes(qtbot, tmp_path):
    """加重复路径：count 不重复加。"""
    from src.ui.file_list import FileList
    fl = FileList()
    qtbot.addWidget(fl)
    p = tmp_path / "a.pdf"
    p.write_text("dummy")
    fl.add_files([str(p), str(p), str(p)])
    assert fl.count() == 1


def test_filelist_add_files_filters_unsupported(qtbot, tmp_path):
    """加不支持扩展名：被静默过滤（drop_area 已预过滤，这里兜底）。"""
    from src.ui.file_list import FileList
    fl = FileList()
    qtbot.addWidget(fl)
    good = tmp_path / "a.pdf"
    good.write_text("dummy")
    bad = tmp_path / "a.xyz"
    bad.write_text("dummy")
    fl.add_files([str(good), str(bad)])
    assert fl.count() == 1


def test_filelist_clear_empties(qtbot, tmp_path):
    """clear() 后：count() == 0。"""
    from src.ui.file_list import FileList
    fl = FileList()
    qtbot.addWidget(fl)
    p = tmp_path / "a.pdf"
    p.write_text("dummy")
    fl.add_files([str(p)])
    assert fl.count() == 1
    fl.clear()
    assert fl.count() == 0
