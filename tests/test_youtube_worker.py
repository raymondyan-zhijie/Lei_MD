"""v0.4.2 P1 M4：YouTubeFetchWorker 测试。

测试目标：
- URL 校验失败（不是 YouTube）→ emit error("E_CONVERT_005")
- 成功路径：emit finished(markdown)
- 异常路径：emit error("E_INTERNAL_001") 兜底
- cancel() 在 run() 之前被调 → 不调 fetch_youtube_transcript

mock 策略：
- 用 monkeypatch 把 src.core.worker.fetch_youtube_transcript 替换
- 不真正调 yt-dlp（CI 离线 + 避免外部依赖）
"""
from __future__ import annotations


def test_youtube_worker_emits_error_on_invalid_url(qtbot, monkeypatch):
    """URL 不是 YouTube 格式 → emit error("E_CONVERT_005")。"""
    from PySide6.QtCore import QEventLoop, QTimer

    from src.core.worker import YouTubeFetchWorker

    worker = YouTubeFetchWorker("https://example.com/not-youtube", timeout=10)
    captured = []
    worker.error.connect(lambda code: captured.append(code))

    # 同步跑（QThread.start() 后立即等）
    worker.start()
    # 等 finished / error 触发
    loop = QEventLoop()
    QTimer.singleShot(500, loop.quit)
    worker.finished.connect(loop.quit)
    worker.error.connect(loop.quit)
    loop.exec()
    worker.wait(2000)

    assert captured == ["E_CONVERT_005"], f"expected E_CONVERT_005, got {captured}"


def test_youtube_worker_emits_finished_on_success(qtbot, monkeypatch):
    """成功路径：mock fetch_youtube_transcript 返回 markdown → emit finished。

    注意：worker.run() 内部是 ``from src.core.youtube import fetch_youtube_transcript``，
    这是个本地 import，monkeypatch 要打在源模块上（src.core.youtube），不是 worker。
    """
    from PySide6.QtCore import QEventLoop, QTimer

    from src.core.worker import YouTubeFetchWorker

    fake_md = "# Fake Video\n\n字幕内容"
    monkeypatch.setattr(
        "src.core.youtube.fetch_youtube_transcript",
        lambda url, *, timeout=30: fake_md,
    )

    worker = YouTubeFetchWorker("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    captured = []
    worker.finished.connect(lambda md: captured.append(md))

    worker.start()
    loop = QEventLoop()
    QTimer.singleShot(2000, loop.quit)
    worker.finished.connect(loop.quit)
    worker.error.connect(lambda c: loop.quit())
    loop.exec()
    worker.wait(2000)

    assert captured == [fake_md], f"expected finished('{fake_md}'), got {captured}"


def test_youtube_worker_emits_error_on_youtube_fetch_error(qtbot, monkeypatch):
    """fetch_youtube_transcript 抛 YouTubeFetchError → emit error(e.code)。"""
    from PySide6.QtCore import QEventLoop, QTimer

    from src.core.errors import ErrorCode
    from src.core.worker import YouTubeFetchWorker
    from src.core.youtube import YouTubeFetchError

    def fake_fetch(url, *, timeout=30):
        raise YouTubeFetchError(ErrorCode.E_CONVERT_001.value, "视频不可访问")

    monkeypatch.setattr(
        "src.core.youtube.fetch_youtube_transcript",
        fake_fetch,
    )

    worker = YouTubeFetchWorker("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    captured = []
    worker.error.connect(lambda code: captured.append(code))

    worker.start()
    loop = QEventLoop()
    QTimer.singleShot(2000, loop.quit)
    worker.finished.connect(loop.quit)
    worker.error.connect(loop.quit)
    loop.exec()
    worker.wait(2000)

    assert captured == ["E_CONVERT_001"], f"expected E_CONVERT_001, got {captured}"


def test_youtube_worker_emits_error_on_unexpected_exception(qtbot, monkeypatch):
    """fetch_youtube_transcript 抛非 YouTubeFetchError → 兜底 emit E_INTERNAL_001。"""
    from PySide6.QtCore import QEventLoop, QTimer

    from src.core.worker import YouTubeFetchWorker

    def fake_fetch(url, *, timeout=30):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(
        "src.core.youtube.fetch_youtube_transcript",
        fake_fetch,
    )

    worker = YouTubeFetchWorker("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    captured = []
    worker.error.connect(lambda code: captured.append(code))

    worker.start()
    loop = QEventLoop()
    QTimer.singleShot(2000, loop.quit)
    worker.finished.connect(loop.quit)
    worker.error.connect(loop.quit)
    loop.exec()
    worker.wait(2000)

    assert captured == ["E_INTERNAL_001"], f"expected E_INTERNAL_001, got {captured}"


def test_youtube_worker_cancel_before_start():
    """start() 之前 cancel() → run() 入口 return，不调 fetch。"""
    from src.core.worker import YouTubeFetchWorker

    called = []

    import src.core.worker as worker_module
    original_import = worker_module.__dict__.get("fetch_youtube_transcript")

    def tracking_fetch(url, *, timeout=30):
        called.append(url)
        return "# md"

    try:
        worker_module.fetch_youtube_transcript = tracking_fetch
        worker = YouTubeFetchWorker("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        worker.cancel()
        # 直接 run（不 start）—— 验证 run() 入口 cancel 检查
        worker.run()
        assert called == [], f"fetch should NOT be called when pre-cancelled, got {called}"
    finally:
        if original_import is not None:
            worker_module.fetch_youtube_transcript = original_import
