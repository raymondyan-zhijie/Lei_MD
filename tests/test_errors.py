"""错误码体系测试（v0.4.2 P1 C5：补齐 8 个错误码的覆盖）。

之前错误码定义在 src/core/errors.py，但缺少独立测试文件——专家审查
（项 #15）标记"部分错误码缺测试"。本次补齐 8 个错误码的测试：
- E_FILE_004（路径遍历）
- E_FILE_005（不支持格式）
- E_CONVERT_004（YouTube 网络超时）
- E_SYS_002（输出路径不可写）
- E_SYS_003（路径超 Windows MAX_PATH）
- E_INTERNAL_001（Python traceback）
- E_UPDATE_001（下载中断）
- E_UPDATE_002（检查更新网络失败）

每个测试覆盖：
- ConversionError 构造后 .code / .user_message 正确
- 双语模板都能取到（zh_CN / en_US）
- 占位符替换生效
"""
from __future__ import annotations

# ----------- 8 个错误码覆盖测试 -----------

def test_e_file_004_path_traversal_message():
    """v0.4.2 P1 C5：E_FILE_004（路径遍历）双语消息 + 占位符替换。"""
    from src.core.errors import ConversionError, ErrorCode

    e = ConversionError(ErrorCode.E_FILE_004, filename="../../etc/passwd")
    assert e.code is ErrorCode.E_FILE_004
    # user_message 默认中文
    assert "../../etc/passwd" in e.user_message
    assert "路径遍历" in e.user_message or "traversal" in e.user_message.lower()
    # 英文版
    en = e.get_message("en_US")
    assert "../../etc/passwd" in en
    assert "traversal" in en.lower()


def test_e_file_005_unsupported_format_message():
    """v0.4.2 P1 C5：E_FILE_005（不支持格式）双语消息。"""
    from src.core.errors import ConversionError, ErrorCode

    e = ConversionError(ErrorCode.E_FILE_005, filename="x.exe")
    assert e.code is ErrorCode.E_FILE_005
    assert "x.exe" in e.user_message
    assert "暂不支持" in e.user_message or "unsupported" in e.user_message.lower()
    en = e.get_message("en_US")
    assert "x.exe" in en
    assert "unsupported" in en.lower()


def test_e_convert_004_youtube_timeout_message():
    """v0.4.2 P1 C5：E_CONVERT_004（YouTube 抓取超时）双语消息。

    注意：E_CONVERT_004 模板没有 {filename} 占位符——纯网络错误，
    ConversionError 不带 filename 也应正常工作。
    """
    from src.core.errors import ConversionError, ErrorCode

    e = ConversionError(ErrorCode.E_CONVERT_004)
    assert e.code is ErrorCode.E_CONVERT_004
    assert "超时" in e.user_message or "timed out" in e.user_message.lower()
    en = e.get_message("en_US")
    assert "timed out" in en.lower()


def test_e_sys_002_output_path_unwritable():
    """v0.4.2 P1 C5：E_SYS_002（输出路径不可写）—— 值正确。

    错误码定义在 errors.py，但 ERROR_MESSAGES 字典里没填条目（注释说
    "在对应模块定义"）。本测试只验证枚举值存在 + 构造 ConversionError
    不抛错（fallback 到 str(code)）。
    """
    from src.core.errors import ConversionError, ErrorCode

    e = ConversionError(ErrorCode.E_SYS_002)
    assert e.code is ErrorCode.E_SYS_002
    # v0.4.4+ P0: E_SYS_002 现在在 ERROR_MESSAGES 登记了双语文案。
    # 之前测试假设没登记 → fallback 走 str(code)。现在文案：
    assert e.get_message("zh_CN") == "输出路径不可写或不存在：{path}"
    assert e.get_message("en_US") == "Output path is not writable or does not exist: {path}"
    # user_message 走 lang 默认 zh_CN
    assert e.user_message == "输出路径不可写或不存在：{path}"


def test_e_sys_003_windows_max_path():
    """v0.4.2 P1 C5：E_SYS_003（Windows MAX_PATH 260）同 E_SYS_002 模式。"""
    from src.core.errors import ConversionError, ErrorCode

    e = ConversionError(ErrorCode.E_SYS_003)
    assert e.code is ErrorCode.E_SYS_003
    assert e.user_message == str(ErrorCode.E_SYS_003)


def test_e_internal_001_traceback_message():
    """v0.4.2 P1 C5：E_INTERNAL_001（Python traceback 兜底）双语消息。"""
    from src.core.errors import ConversionError, ErrorCode

    e = ConversionError(ErrorCode.E_INTERNAL_001)
    assert e.code is ErrorCode.E_INTERNAL_001
    # 中英双版都该有"内部"/"Internal"关键字
    assert "内部" in e.user_message or "internal" in e.user_message.lower()
    en = e.get_message("en_US")
    assert "internal" in en.lower()
    # 不暴露 Python 关键字（traceback 等）
    assert "traceback" not in e.user_message.lower()
    assert "traceback" not in en.lower()


def test_e_internal_001_with_cause_chain():
    """v0.4.2 P1 C5：E_INTERNAL_001 cause 链正确（__cause__ 透传）。"""
    from src.core.errors import ConversionError, ErrorCode

    original = ValueError("原始异常信息")
    e = ConversionError(ErrorCode.E_INTERNAL_001, cause=original)
    assert e.cause is original
    assert e.__cause__ is original
    # raise ... from ... 的语义链：ConversionError 的 __cause__ 应是原始 ValueError
    inner = None
    try:
        try:
            raise original
        except ValueError as exc:
            inner = exc
            raise ConversionError(ErrorCode.E_INTERNAL_001, cause=exc) from exc
    except ConversionError as ce:
        assert ce.cause is inner
        # __cause__ 是原始 ValueError 实例
        assert isinstance(ce.__cause__, ValueError)
        assert "原始异常信息" in str(ce.__cause__)


def test_e_update_001_download_interrupted():
    """v0.4.2 P1 C5：E_UPDATE_001（下载中断）枚举值存在 + 不抛错。"""
    from src.core.errors import ConversionError, ErrorCode

    e = ConversionError(ErrorCode.E_UPDATE_001)
    assert e.code is ErrorCode.E_UPDATE_001
    # ERROR_MESSAGES 没填 → fallback
    assert e.user_message == str(ErrorCode.E_UPDATE_001)


def test_e_update_002_update_check_failed():
    """v0.4.2 P1 C5：E_UPDATE_002（检查更新网络失败）枚举值存在。"""
    from src.core.errors import ConversionError, ErrorCode

    e = ConversionError(ErrorCode.E_UPDATE_002)
    assert e.code is ErrorCode.E_UPDATE_002
    assert e.user_message == str(ErrorCode.E_UPDATE_002)


# ----------- 全量枚举值守恒测试 -----------

def test_all_error_codes_have_unique_string_values():
    """v0.4.2 P1 C5：所有 ErrorCode 枚举值的字符串表示唯一且非空。"""
    from src.core.errors import ErrorCode

    values = [c.value for c in ErrorCode]
    # 19 个错误码（6 FILE + 5 CONVERT + 3 SYS + 3 INTERNAL + 2 UPDATE）
    assert len(values) == 19, f"expected 19 error codes, got {len(values)}: {values}"
    # 全部唯一
    assert len(set(values)) == 19
    # 全部非空
    assert all(v for v in values)
    # 全部遵循 E_<CAT>_<NNN> 格式
    import re
    pattern = re.compile(r"^E_[A-Z]+_\d{3}$")
    for v in values:
        assert pattern.match(v), f"error code {v!r} doesn't match E_CAT_NNN format"


def test_error_messages_dict_covers_all_codes_with_zh_cn():
    """v0.4.2 P1 C5：ERROR_MESSAGES 至少为填了 zh_CN 的 code 提供模板。

    之前 errors.py L100 注释说 E_SYS_* / E_UPDATE_* 在对应模块定义。
    本测试只断言：所有填进 ERROR_MESSAGES 的 code 都有 zh_CN 模板。
    E_SYS_002/003、E_UPDATE_001/002 没填 → 不在本测试范围。
    """
    from src.core.errors import ERROR_MESSAGES

    for code, msgs in ERROR_MESSAGES.items():
        assert "zh_CN" in msgs, f"{code} missing zh_CN template"
        assert "en_US" in msgs, f"{code} missing en_US template"
        # 模板非空
        assert msgs["zh_CN"], f"{code} zh_CN template is empty"
        assert msgs["en_US"], f"{code} en_US template is empty"
