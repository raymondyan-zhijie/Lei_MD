"""Task 1.2: DropArea 拖拽组件测试。

测试目标：
- 默认提示文本正确
- 接受文件拖拽（setAcceptDrops）
- 文件拖入时 emit files_dropped Signal
- 不接受文本/URL 拖入
- 支持的文件扩展名过滤
"""
import pytest
from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl
from PySide6.QtGui import QDropEvent


@pytest.fixture
def drop_area(qapp):
    from src.ui.drop_area import DropArea

    area = DropArea()
    yield area


def test_drop_area_default_placeholder(drop_area):
    """默认提示文本应包含「拖拽」字样。"""
    text = drop_area.placeholder_text()
    assert "拖" in text or "drag" in text.lower()


def test_drop_area_accepts_file_drops(drop_area):
    """DropArea 必须接受文件拖拽（不是 URL/文本）。"""
    assert drop_area.acceptDrops() is True


def test_drop_area_supported_extensions_excludes_audio(drop_area):
    """v1.0 不支持音频（mp3/wav/ogg/flac），02 §1.1 F9a 决定。"""
    exts = drop_area.supported_extensions()
    for audio in [".mp3", ".wav", ".ogg", ".flac"]:
        assert audio not in exts, f"音频 {audio} 不应在 v1.0 支持列表"


def test_drop_area_supported_extensions_includes_pdf_docx(qapp):
    """核心格式必须支持：PDF/Word/Excel/PPT/HTML/EPUB/图片/CSV/JSON/XML/ZIP。"""
    from src.ui.drop_area import DropArea

    area = DropArea()
    exts = area.supported_extensions()
    must_have = [".pdf", ".docx", ".xlsx", ".pptx", ".html", ".epub",
                 ".jpg", ".png", ".csv", ".json", ".xml", ".zip"]
    for ext in must_have:
        assert ext in exts, f"核心格式 {ext} 应在支持列表"


def test_drop_area_emits_signal_on_file_drop(qapp, drop_area, qtbot, tmp_path):
    """拖入 1 个 PDF 文件应 emit files_dropped Signal 且路径正确。"""
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    received = []
    drop_area.files_dropped.connect(received.append)

    # 构造 QDropEvent
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(pdf))])
    drop_event = QDropEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    drop_area.dropEvent(drop_event)

    assert len(received) == 1
    assert str(pdf) in received[0]


def test_drop_area_filters_unsupported_files(drop_area, qtbot, tmp_path):
    """拖入 .xyz 不支持格式应被过滤（或 emit 警告）。"""
    bad = tmp_path / "test.xyz"
    bad.write_bytes(b"fake")
    received = []
    drop_area.files_dropped.connect(received.append)

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(bad))])
    drop_event = QDropEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    drop_area.dropEvent(drop_event)

    # .xyz 不在支持列表，应被过滤
    assert received == []


def test_drop_area_recursive_directory_expansion(drop_area, qtbot, tmp_path):
    """拖入目录应递归展开所有支持文件（Task 1.2 §递归支持）。"""
    # 在 tmp_path 下创建几个支持 + 不支持文件
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4\n")
    (tmp_path / "b.docx").write_bytes(b"fake")
    (tmp_path / "c.xyz").write_bytes(b"fake")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "d.xlsx").write_bytes(b"fake")

    received = []
    drop_area.files_dropped.connect(received.append)

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(tmp_path))])
    drop_event = QDropEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    drop_area.dropEvent(drop_event)

    # 1 次 emit 内含 3 个支持文件（a.pdf / b.docx / d.xlsx），不含 c.xyz
    assert len(received) == 1
    paths = received[0]
    assert len(paths) == 3
    assert any("a.pdf" in p for p in paths)
    assert any("b.docx" in p for p in paths)
    assert any("d.xlsx" in p for p in paths)
    assert not any("c.xyz" in p for p in paths)
