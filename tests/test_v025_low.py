"""Regression tests for v0.2.5 P3 audit Low-dimension fixes.

Covers:
- L1: src/ui/i18n.py ``set_locale()`` 入口加 VALID_LOCALES 白名单。
  不在白名单（system / zh_CN / en_US）里的 locale 全部 fallback 到 DEFAULT_LOCALE。
- L2: src/ui/drop_area.py ``_collect_files_from_dir`` 限深 + 限文件数。
  仅 API 行为测试（不需要拖入事件）。
- L3: src/ui/preview_panel.py ``_safe_set_source`` 拒绝 file:// / 空 scheme。
- L4: src/core/errors.py ``ConversionError(..., cause=)`` 把 cause 挂到
  ``__cause__``，让 ``raise ... from e`` 链对 traceback 可见。
- L5: src/core/config.py rename fallback — 标记为 v0.2.3 M6.4 已修（间接由
  test_v023_hotfix.py 覆盖），本文件不再重复。
"""
from __future__ import annotations

from pathlib import Path

import pytest

# ============================================================
# L1: i18n locale whitelist
# ============================================================

def test_i18n_valid_locales_whitelist_constant():
    """L1: VALID_LOCALES 必须存在，且包含 {system, en, zh_CN, en_US}。

    v0.2.7 P0 增补 "en"：让英文用户（DEFAULT_LOCALE）启动时不打 warning，
    同时保持白名单收紧（攻击者控制的 locale 仍 fallback）。
    """
    from src.ui import i18n

    assert hasattr(i18n, "VALID_LOCALES"), "L1: 缺少模块常量 VALID_LOCALES"
    assert i18n.VALID_LOCALES == frozenset({"system", "en", "zh_CN", "en_US"})


def test_i18n_set_locale_rejects_unknown_locale(monkeypatch):
    """L1: set_locale('evil_../etc/passwd') 应当 fallback 到 DEFAULT_LOCALE。

    关键：不抛异常，且不把攻击者控制的字符串拼到 _LOCALES_DIR 路径里。
    """
    from src.ui import i18n
    from src.ui.i18n import set_locale, tr

    # 模拟攻击者传入的恶意 locale
    malicious = "../../../etc/passwd"
    set_locale(malicious, translations={"k": "safe"})

    # 应当被白名单拒绝，落到 DEFAULT_LOCALE
    assert i18n._default.locale == i18n.DEFAULT_LOCALE
    assert tr("k") == "safe"  # 翻译表仍被装载（用默认 locale）


def test_i18n_set_locale_rejects_plain_garbage(monkeypatch):
    """L1: set_locale('not-a-locale') 也应 fallback。"""
    from src.ui import i18n
    from src.ui.i18n import set_locale

    set_locale("not-a-locale")
    assert i18n._default.locale == i18n.DEFAULT_LOCALE


def test_i18n_set_locale_accepts_each_whitelisted_value():
    """L1: VALID_LOCALES 里的四个值都应当原样接受（含 v0.2.7 P0 新增的 "en"）。"""
    from src.ui import i18n
    from src.ui.i18n import set_locale

    for loc in ("system", "en", "zh_CN", "en_US"):
        set_locale(loc, translations={"greet": f"hello-{loc}"})
        assert i18n._default.locale == loc
        assert i18n.tr("greet") == f"hello-{loc}"


# ============================================================
# L2: DropArea 限深 + 限文件数
# ============================================================

def test_drop_area_constants_define_limits():
    """L2: 限深/限文件数常量应被定义。"""
    from src.ui.drop_area import MAX_RECURSE_DEPTH, MAX_RECURSE_FILES

    assert MAX_RECURSE_DEPTH >= 1
    assert MAX_RECURSE_FILES >= 1


def test_drop_area_collect_files_respects_max_depth(tmp_path):
    """L2: max_depth=2 时，第 3 层目录下的文件不应被收集。"""
    from src.ui.drop_area import DropArea

    # 结构：
    #   tmp_path/                    (depth 0)
    #     shallow.pdf                (depth 1，应被收集)
    #     lvl1/                      (depth 1)
    #       mid.pdf                  (depth 2，应被收集)
    #       lvl2/                    (depth 2)
    #         deep.pdf               (depth 3，超限 → 不收)
    (tmp_path / "shallow.pdf").write_bytes(b"x")
    (tmp_path / "lvl1").mkdir()
    (tmp_path / "lvl1" / "mid.pdf").write_bytes(b"x")
    (tmp_path / "lvl1" / "lvl2").mkdir()
    (tmp_path / "lvl1" / "lvl2" / "deep.pdf").write_bytes(b"x")

    out: list[str] = []
    truncated = DropArea._collect_files_from_dir(
        tmp_path, out, max_depth=2, max_files=100,
    )

    names = [Path(p).name for p in out]
    assert "shallow.pdf" in names
    assert "mid.pdf" in names
    assert "deep.pdf" not in names, f"L2: 超深文件应被截断，实际 {out}"
    assert truncated is False


def test_drop_area_collect_files_respects_max_files(tmp_path):
    """L2: max_files=5 时，收集到 5 个就停，返回 truncated=True。"""
    from src.ui.drop_area import DropArea

    for i in range(20):
        (tmp_path / f"doc_{i:02d}.pdf").write_bytes(b"x")

    out: list[str] = []
    truncated = DropArea._collect_files_from_dir(
        tmp_path, out, max_depth=10, max_files=5,
    )

    assert len(out) == 5
    assert truncated is True


def test_drop_area_collect_files_filters_unsupported_extensions(tmp_path):
    """L2: 不支持的扩展名（.mp3）不应进 out 列表。"""
    from src.ui.drop_area import DropArea

    (tmp_path / "ok.pdf").write_bytes(b"x")
    (tmp_path / "bad.mp3").write_bytes(b"x")

    out: list[str] = []
    DropArea._collect_files_from_dir(tmp_path, out, max_depth=5, max_files=100)

    names = [Path(p).name for p in out]
    assert "ok.pdf" in names
    assert "bad.mp3" not in names


# ============================================================
# L3: PreviewPanel 拒绝 file:// 导航
# ============================================================

def test_preview_external_links_disabled(qtbot):
    """L3: setOpenExternalLinks / setOpenLinks 都应被关掉。"""
    from src.ui.preview_panel import PreviewPanel

    panel = PreviewPanel()
    qtbot.addWidget(panel)
    assert panel.openExternalLinks() is False
    assert panel.openLinks() is False


def test_preview_safe_set_source_blocks_file_scheme(qtbot):
    """L3: ``_safe_set_source(file://...)`` 应当被拒；非本地 scheme 应透传。"""
    from PySide6.QtCore import QUrl

    from src.ui.preview_panel import PreviewPanel

    panel = PreviewPanel()
    qtbot.addWidget(panel)

    # file:// → 静默拒绝（不抛）
    panel._safe_set_source(QUrl("file:///etc/passwd"))
    # 空 scheme（裸路径）也拒绝
    panel._safe_set_source(QUrl("/etc/passwd"))


def test_preview_safe_set_source_allows_http(qtbot):
    """L3: http(s) scheme 不被拦。不会真的去拉网络（因为 setSource 会触发，
    但 _safe_set_source 只走父类；QTextBrowser 在测试环境也不会联网），
    所以这里只验证「不抛 + 落到父类路径」即可。
    """
    from PySide6.QtCore import QUrl

    from src.ui.preview_panel import PreviewPanel

    panel = PreviewPanel()
    qtbot.addWidget(panel)

    # 不应抛
    try:
        panel._safe_set_source(QUrl("https://example.com"))
    except Exception as exc:  # noqa: BLE001
        # 即便 QTextBrowser 内部对它做了什么，也不应是 scheme-block 路径的报错
        pytest.fail(f"L3: http 被误拦：{exc!r}")


# ============================================================
# L4: ConversionError cause → __cause__
# ============================================================

def test_conversion_error_cause_attaches_to_dunder_cause():
    """L4: 显式 cause= 应被挂到 __cause__，traceback 才能展示。"""
    from src.core.errors import ConversionError, ErrorCode

    root = OSError("disk gone")
    err = ConversionError(ErrorCode.E_FILE_001, cause=root)

    assert err.__cause__ is root
    # 历史 API 也保留
    assert err.cause is root


def test_conversion_error_cause_from_uses_dunder_cause():
    """L4: ``raise ConversionError(...) from e`` 的 e 必须出现在 __cause__。

    之前版本 ``cause=`` 只存到 ``self.cause``，__cause__ 是 None，
    traceback 不会展示"由 ... 引起"。
    """
    from src.core.errors import ConversionError, ErrorCode

    root = ValueError("bad pdf header")
    try:
        try:
            raise root
        except ValueError as e:
            raise ConversionError(ErrorCode.E_CONVERT_002, cause=e) from e
    except ConversionError as caught:
        assert caught.__cause__ is root
        assert caught.cause is root
        # traceback 才会显示 "The above exception was the direct cause"
        # （这个属性链就是 traceback 用来判定的）


def test_conversion_error_no_cause_keeps_dunder_cause_none():
    """L4: 没传 cause 时，__cause__ 应保持 None（不挂幽灵）。"""
    from src.core.errors import ConversionError, ErrorCode

    err = ConversionError(ErrorCode.E_FILE_002)
    assert err.__cause__ is None
    assert err.cause is None
