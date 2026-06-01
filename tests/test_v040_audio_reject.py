"""v0.4.0 Task C 回归测试：音频 E_FILE_006 显式拦截。"""
from __future__ import annotations

import pytest
from PySide6.QtCore import QMimeData, QPoint, QUrl, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication

from src.ui.drop_area import AUDIO_EXTENSIONS, DropArea


# ============ SSOT ============


class TestAudioExtensionsSSOT:
    """AUDIO_EXTENSIONS 集合的内容锁定。"""

    def test_mp3_in_audio(self):
        assert ".mp3" in AUDIO_EXTENSIONS

    def test_wav_in_audio(self):
        assert ".wav" in AUDIO_EXTENSIONS

    def test_ogg_in_audio(self):
        assert ".ogg" in AUDIO_EXTENSIONS

    def test_flac_in_audio(self):
        assert ".flac" in AUDIO_EXTENSIONS

    def test_m4a_aac_wma_opus_in_audio(self):
        """v0.4.0 扩展：把常见音频格式都包进来。"""
        for ext in (".m4a", ".aac", ".wma", ".opus"):
            assert ext in AUDIO_EXTENSIONS, f"{ext} should be in AUDIO_EXTENSIONS"

    def test_audio_disjoint_from_supported(self):
        """关键不变量：音频不能在 SUPPORTED_EXTENSIONS 里（否则被静默接受）。"""
        from src.ui.drop_area import SUPPORTED_EXTENSIONS

        overlap = AUDIO_EXTENSIONS & SUPPORTED_EXTENSIONS
        assert not overlap, f"音频/支持集合重叠: {overlap}"

    def test_drop_area_exposes_audio_extensions(self):
        """DropArea.audio_extensions() 是 AUDIO_EXTENSIONS 的 SSOT 入口。"""
        assert DropArea.audio_extensions() is AUDIO_EXTENSIONS


# ============ 行为：拖入音频时 audio_rejected Signal ============


@pytest.fixture
def drop_area(qtbot):
    da = DropArea()
    qtbot.addWidget(da)
    return da


class TestAudioDropBehavior:
    """拖入 .mp3/.wav 等应触发 audio_rejected，**不**触发 files_dropped。"""

    def test_drop_mp3_emits_audio_rejected(self, drop_area, qtbot, tmp_path):
        f = tmp_path / "song.mp3"
        f.write_bytes(b"fake mp3 content")
        captured_audio: list[list[str]] = []
        captured_files: list[list[str]] = []
        drop_area.audio_rejected.connect(lambda p: captured_audio.append(p))
        drop_area.files_dropped.connect(lambda p: captured_files.append(p))

        _simulate_drop(drop_area, [str(f)])

        assert len(captured_audio) == 1
        assert captured_audio[0] == [str(f.resolve())]
        # 关键：音频**不**进 files_dropped（不然会被当成合法文件尝试转换）
        assert captured_files == []

    def test_drop_wav_emits_audio_rejected(self, drop_area, qtbot, tmp_path):
        f = tmp_path / "voice.wav"
        f.write_bytes(b"RIFF" + b"\x00" * 100)
        captured: list[list[str]] = []
        drop_area.audio_rejected.connect(lambda p: captured.append(p))

        _simulate_drop(drop_area, [str(f)])

        assert len(captured) == 1
        assert captured[0] == [str(f.resolve())]

    @pytest.mark.parametrize("ext", [".mp3", ".wav", ".ogg", ".flac", ".m4a"])
    def test_all_audio_extensions_trigger_rejection(
        self, drop_area, qtbot, tmp_path, ext
    ):
        f = tmp_path / f"audio{ext}"
        f.write_bytes(b"x")
        captured: list[list[str]] = []
        drop_area.audio_rejected.connect(lambda p: captured.append(p))

        _simulate_drop(drop_area, [str(f)])

        assert len(captured) == 1, f"{ext} should trigger audio_rejected"

    def test_drop_pdf_does_not_emit_audio_rejected(self, drop_area, qtbot, tmp_path):
        """回归：合法 PDF 不应被误判为音频。"""
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4\n%fake\n")
        captured_audio: list[list[str]] = []
        captured_files: list[list[str]] = []
        drop_area.audio_rejected.connect(lambda p: captured_audio.append(p))
        drop_area.files_dropped.connect(lambda p: captured_files.append(p))

        _simulate_drop(drop_area, [str(f)])

        assert captured_audio == []
        assert len(captured_files) == 1  # PDF 走正常路径

    def test_drop_mixed_audio_and_pdf(self, drop_area, qtbot, tmp_path):
        """混合拖入：PDF 走 files_dropped，mp3 走 audio_rejected。"""
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        mp3 = tmp_path / "song.mp3"
        mp3.write_bytes(b"x")

        captured_audio: list[list[str]] = []
        captured_files: list[list[str]] = []
        drop_area.audio_rejected.connect(lambda p: captured_audio.append(p))
        drop_area.files_dropped.connect(lambda p: captured_files.append(p))

        _simulate_drop(drop_area, [str(pdf), str(mp3)])

        assert len(captured_files) == 1
        assert captured_files[0] == [str(pdf.resolve())]
        assert len(captured_audio) == 1
        assert captured_audio[0] == [str(mp3.resolve())]


# ============ 错误码注册 ============


class TestErrorCodeRegistration:
    """E_FILE_006 必须在 ErrorCode 枚举中且有 zh_CN 翻译。"""

    def test_e_file_006_in_enum(self):
        from src.core.errors import ErrorCode

        assert hasattr(ErrorCode, "E_FILE_006")
        assert ErrorCode.E_FILE_006.value == "E_FILE_006"

    def test_e_file_006_has_zh_message(self):
        from src.core.errors import ERROR_MESSAGES, ErrorCode

        assert "zh_CN" in ERROR_MESSAGES[ErrorCode.E_FILE_006]
        # 翻译必须含"音频"关键词
        assert "音频" in ERROR_MESSAGES[ErrorCode.E_FILE_006]["zh_CN"]


# ============ 辅助 ============


def _simulate_drop(drop_area: DropArea, file_paths: list[str]) -> None:
    """用 QMimeData 模拟一次完整 drop 事件。"""
    md = QMimeData()
    md.setUrls([QUrl.fromLocalFile(p) for p in file_paths])
    # dragEnter 必须先 accept，dropEvent 才生效
    # PySide6 6.9: QDragEnterEvent 签名是 (QPoint, DropAction, MimeData, MouseButton, KeyboardModifier)
    enter = QDragEnterEvent(
        QPoint(0, 0),
        Qt.CopyAction,
        md,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    drop_area.dragEnterEvent(enter)
    drop = QDropEvent(
        QPoint(0, 0),
        Qt.CopyAction,
        md,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    drop_area.dropEvent(drop)
