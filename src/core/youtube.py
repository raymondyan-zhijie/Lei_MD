"""YouTube 字幕抓取模块（Task 2.4 补齐）。

职责：
- 接受 YouTube URL（watch?v= / youtu.be/ / shorts/）
- 调 yt-dlp 抓取自动字幕（vtt/srv1/srv2/srv3）
- 转 Markdown 输出
- 异常翻译到错误码体系（E_CONVERT_001/002 + 新增 E_CONVERT_003 视频不可访问）

设计：
- 不阻塞 UI（独立 QThread/QRunnable 调用）
- yt-dlp 是可选依赖（settings.yt_enabled=false 时不 import）
- 不下载视频，只取字幕，流量极小
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# SSOT：URL 模式识别（v0.4.0 Task 2.4）
YOUTUBE_URL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^https?://(?:www\.|m\.)?youtube\.com/watch\?(?:.*&)?v=([\w-]{11})(?:[&#].*)?$"),
    re.compile(r"^https?://youtu\.be/([\w-]{11})(?:[?#].*)?$"),
    re.compile(r"^https?://(?:www\.)?youtube\.com/shorts/([\w-]{11})(?:[?#].*)?$"),
    re.compile(r"^https?://(?:www\.)?youtube\.com/embed/([\w-]{11})(?:[?#].*)?$"),
)

# 自动字幕语言优先级
PREFERRED_SUB_LANGS: tuple[str, ...] = ("zh-Hans", "zh-CN", "zh-Hant", "zh-TW", "en", "en-US")


def extract_video_id(url: str) -> str | None:
    """从 YouTube URL 提取 11 位 video id。

    支持格式：watch?v=、youtu.be/、shorts/、embed/
    非 YouTube URL 返回 None。

    Args:
        url: 用户输入的 URL 字符串

    Returns:
        11 位 video id（如 "dQw4w9WgXcQ"），失败返回 None
    """
    if not isinstance(url, str):
        return None
    url = url.strip()
    for pat in YOUTUBE_URL_PATTERNS:
        m = pat.match(url)
        if m:
            return m.group(1)
    return None


def is_youtube_url(url: str) -> bool:
    """快速判断是否为 YouTube URL（用于 DropArea 拖入时路由）。"""
    return extract_video_id(url) is not None


class YouTubeFetchError(Exception):
    """YouTube 抓取失败（包装底层 yt-dpp 异常，附 user_message）。"""

    def __init__(self, code: str, message: str, *, cause: BaseException | None = None):
        self.code = code
        self.message = message
        self.cause = cause
        super().__init__(message)
        if cause is not None:
            self.__cause__ = cause


def fetch_youtube_transcript(url: str, *, timeout: int = 30) -> str:
    """从 YouTube URL 抓取字幕并转为 Markdown。

    Args:
        url: YouTube 视频 URL
        timeout: 网络请求超时（秒），默认 30

    Returns:
        Markdown 文本，含元信息头（视频标题/作者/URL）+ 字幕正文

    Raises:
        YouTubeFetchError: 抓取失败（用户可见）
            - E_CONVERT_001: 视频不可访问（私密/地区限制/不存在）
            - E_CONVERT_002: 视频无字幕
            - E_CONVERT_003: yt-dlp 未安装（settings.yt_enabled 误开）
            - E_CONVERT_004: 网络超时
    """
    vid = extract_video_id(url)
    if vid is None:
        raise YouTubeFetchError(
            "E_CONVERT_005",  # 非 YouTube URL
            f"不是有效的 YouTube URL: {url}",
        )

    # 懒加载 yt-dlp（避免 settings.yt_enabled=false 时硬依赖）
    try:
        import yt_dlp  # noqa: F401
    except ImportError as e:
        raise YouTubeFetchError(
            "E_CONVERT_003",
            "yt-dlp 未安装，无法抓取 YouTube 字幕（pip install yt-dlp 后启用）",
            cause=e,
        )

    # 抓元数据
    try:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,  # 只取字幕，不下视频
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": list(PREFERRED_SUB_LANGS),
            "socket_timeout": timeout,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        err = str(e).lower()
        if "timeout" in err or "timed out" in err:
            code = "E_CONVERT_004"
        elif "private" in err or "unavailable" in err or "blocked" in err or "404" in err:
            code = "E_CONVERT_001"
        else:
            code = "E_CONVERT_002"
        raise YouTubeFetchError(code, f"YouTube 抓取失败: {e}", cause=e)

    if info is None:
        raise YouTubeFetchError("E_CONVERT_002", "yt-dlp 返回空结果")

    # 构造 Markdown 输出
    title = info.get("title", "(无标题)")
    uploader = info.get("uploader", info.get("channel", "(未知作者)"))
    duration = info.get("duration", 0)
    webpage = info.get("webpage_url", url)

    lines: list[str] = [
        f"# {title}",
        "",
        f"- **作者**：{uploader}",
        f"- **时长**：{duration // 60}:{duration % 60:02d}",
        f"- **URL**：{webpage}",
        "",
        "## 字幕",
        "",
    ]

    # 优先用人工字幕，否则用自动字幕
    subs = info.get("subtitles") or {}
    auto_subs = info.get("automatic_captions") or {}

    transcript_text = _pick_best_subtitle(subs) or _pick_best_subtitle(auto_subs)
    if not transcript_text:
        raise YouTubeFetchError(
            "E_CONVERT_002",
            f"视频 {vid} 无可用字幕（人工或自动）",
        )

    lines.append(transcript_text)
    return "\n".join(lines)


def _pick_best_subtitle(subs: dict) -> str | None:
    """从 yt-dlp 的字幕字典里挑最佳语言。

    优先级：PREFERRED_SUB_LANGS → 任意可用语言
    返回原始 vtt/srv 文本（v0.4.0 不做 vtt→纯文本转换，直接展示）。
    """
    if not subs:
        return None
    for lang in PREFERRED_SUB_LANGS:
        if lang in subs and subs[lang]:
            # subs[lang] is a list of format dicts
            for fmt in subs[lang]:
                if fmt.get("ext") in ("vtt", "srv1", "srv2", "srv3", "ttml"):
                    url = fmt.get("url")
                    if url:
                        try:
                            import urllib.request

                            with urllib.request.urlopen(url, timeout=15) as resp:
                                return resp.read().decode("utf-8", errors="replace")
                        except Exception as e:
                            logger.warning("Failed to fetch subtitle %s: %s", lang, e)
                            continue
    # 兜底：取任意第一个有 url 的
    for lang, formats in subs.items():
        for fmt in formats:
            url = fmt.get("url")
            if url:
                try:
                    import urllib.request

                    with urllib.request.urlopen(url, timeout=15) as resp:
                        return resp.read().decode("utf-8", errors="replace")
                except Exception as e:
                    logger.warning("Failed to fetch fallback subtitle %s: %s", lang, e)
                    continue
    return None
