"""YouTube fetcher 单元测试（v0.4.0 Task 2.4 补齐）。"""
from __future__ import annotations

import pytest

from src.core.youtube import (
    YOUTUBE_URL_PATTERNS,
    YouTubeFetchError,
    extract_video_id,
    is_youtube_url,
)


# ============ URL 解析 ============


class TestExtractVideoId:
    """URL 解析：4 种格式 + 各种非 YouTube URL。"""

    @pytest.mark.parametrize(
        "url,expected_vid",
        [
            # 标准 watch?v=
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("http://www.youtube.com/watch?v=abc_DEF-123", "abc_DEF-123"),
            # youtu.be 短链
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/abc12345678", "abc12345678"),
            # shorts
            ("https://www.youtube.com/shorts/abc_DEF-123", "abc_DEF-123"),
            ("https://youtube.com/shorts/xxxxxxxxxxx", "xxxxxxxxxxx"),
            # embed
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            # 移动端 m.youtube.com
            ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ],
    )
    def test_valid_youtube_urls_extract_vid(self, url, expected_vid):
        assert extract_video_id(url) == expected_vid

    @pytest.mark.parametrize(
        "url",
        [
            "",  # 空串
            "   ",  # 空白
            "not a url",
            "https://example.com",
            "https://vimeo.com/12345",
            "https://www.bilibili.com/video/BV1xx",
            # YouTube 域但非视频
            "https://www.youtube.com/",
            "https://www.youtube.com/feed/trending",
            "https://www.youtube.com/channel/UCxxxx",
            "https://www.youtube.com/playlist?list=PLxxx",
            # 视频 id 长度不对
            "https://youtu.be/short",  # 5 字符
            "https://youtu.be/waytoolongvideoid12345",  # 22 字符
        ],
    )
    def test_invalid_urls_return_none(self, url):
        assert extract_video_id(url) is None

    def test_non_string_returns_none(self):
        assert extract_video_id(None) is None  # type: ignore[arg-type]
        assert extract_video_id(123) is None  # type: ignore[arg-type]

    def test_whitespace_stripped(self):
        assert extract_video_id("  https://youtu.be/dQw4w9WgXcQ  ") == "dQw4w9WgXcQ"


class TestIsYoutubeUrl:
    def test_youtube_url(self):
        assert is_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True

    def test_non_youtube_url(self):
        assert is_youtube_url("https://example.com") is False

    def test_empty(self):
        assert is_youtube_url("") is False


# ============ fetch_youtube_transcript 错误处理 ============


class TestFetchErrors:
    """fetch_youtube_transcript 的错误码映射。"""

    def test_invalid_url_raises_005(self):
        """E_CONVERT_005: 非 YouTube URL"""
        from src.core.youtube import fetch_youtube_transcript

        with pytest.raises(YouTubeFetchError) as exc:
            fetch_youtube_transcript("https://example.com")
        assert exc.value.code == "E_CONVERT_005"
        assert "不是有效的 YouTube URL" in exc.value.message or "Not a valid" in exc.value.message

    def test_ytdlp_missing_raises_003(self, monkeypatch):
        """E_CONVERT_003: yt-dlp 未安装时 import 失败"""
        from src.core.youtube import fetch_youtube_transcript

        # 把 yt_dlp 强制设为导入失败
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "yt_dlp" or name.startswith("yt_dlp"):
                raise ImportError("simulated missing yt-dlp")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(YouTubeFetchError) as exc:
            fetch_youtube_transcript("https://youtu.be/dQw4w9WgXcQ")
        assert exc.value.code == "E_CONVERT_003"
        assert "yt-dlp" in exc.value.message


# ============ SSOT 一致性 ============


class TestPatternsSSOT:
    """YOUTUBE_URL_PATTERNS 应覆盖所有 4 种 YouTube URL 形式。"""

    def test_all_four_patterns_compile(self):
        # 4 种 URL 形式都被 pattern 覆盖
        for url in [
            "https://www.youtube.com/watch?v=ABCDEFGHIJK",
            "https://youtu.be/ABCDEFGHIJK",
            "https://www.youtube.com/shorts/ABCDEFGHIJK",
            "https://www.youtube.com/embed/ABCDEFGHIJK",
        ]:
            matched = any(p.match(url) for p in YOUTUBE_URL_PATTERNS)
            assert matched, f"No pattern matched {url}"

    def test_pattern_count(self):
        # 锁定 4 种格式（新增需加测试）
        assert len(YOUTUBE_URL_PATTERNS) == 4
