"""错误码体系（）。

提供：
- ErrorCode 枚举（5 大类 + 具体 ID）
- ConversionError 异常（带 code + user_message + 可选 cause）
- LocalizedError 模板（占位符替换）

设计：
- 错误码 ID 与 01 §5.1 / 02 §6.1 一一对应
- 用户可见信息双语（zh_CN / en_US）
- 不暴露 Python traceback 给用户（E_INTERNAL_001 兜底写到 crash.log）
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

class ErrorCode(str, Enum):
    """5 大类错误码（16 个具体 ID）。"""

    # 文件级
    E_FILE_001 = "E_FILE_001"   # 文件不存在/被锁
    E_FILE_002 = "E_FILE_002"   # 0 字节空文件
    E_FILE_003 = "E_FILE_003"   # 超大文件 >500MB
    E_FILE_004 = "E_FILE_004"   # 路径遍历/非法文件名
    E_FILE_005 = "E_FILE_005"   # 不支持格式
    E_FILE_006 = "E_FILE_006"   # 拖入音频（ 不支持）

    # 转换级
    E_CONVERT_001 = "E_CONVERT_001"   # 密码保护/加密
    E_CONVERT_002 = "E_CONVERT_002"   # 文件格式损坏

    # 系统级
    E_SYS_001 = "E_SYS_001"   # 转换中用户强关（下次启动清理）
    E_SYS_002 = "E_SYS_002"   # 输出路径不可写
    E_SYS_003 = "E_SYS_003"   # 路径超 Windows MAX_PATH 260

    # 内部级
    E_INTERNAL_001 = "E_INTERNAL_001"   # Python traceback
    E_INTERNAL_002 = "E_INTERNAL_002"   # SQLite 损坏
    E_INTERNAL_003 = "E_INTERNAL_003"   # config.json 损坏

    # 更新级
    E_UPDATE_001 = "E_UPDATE_001"   # 下载中断/checksum 失败
    E_UPDATE_002 = "E_UPDATE_002"   # 检查更新网络失败

# 双语错误信息（占位符用 {name} 风格）
ERROR_MESSAGES: dict[ErrorCode, dict[str, str]] = {
    ErrorCode.E_FILE_001: {
        "zh_CN": "无法读取 {filename}：文件不存在或被其他程序占用",
        "en_US": "Cannot read {filename}: file not found or locked by another process",
    },
    ErrorCode.E_FILE_002: {
        "zh_CN": "无法读取 {filename}：文件为空（0 字节），已跳过",
        "en_US": "Cannot read {filename}: file is empty (0 bytes), skipped",
    },
    ErrorCode.E_FILE_003: {
        "zh_CN": "无法处理 {filename}：文件超出 500MB 限制",
        "en_US": "Cannot process {filename}: file exceeds 500MB limit",
    },
    ErrorCode.E_FILE_004: {
        "zh_CN": "非法文件名 {filename}：检测到路径遍历",
        "en_US": "Invalid filename {filename}: path traversal detected",
    },
    ErrorCode.E_FILE_005: {
        "zh_CN": "暂不支持此格式：{filename}",
        "en_US": "Unsupported format: {filename}",
    },
    ErrorCode.E_FILE_006: {
        "zh_CN": "音频转录 (MP3/WAV) 在 不支持， + 离线实现",
        "en_US": "Audio transcription (MP3/WAV) not supported in (planned +)",
    },
    ErrorCode.E_CONVERT_001: {
        "zh_CN": "无法转换 {filename}：文件受密码保护或加密",
        "en_US": "Cannot convert {filename}: file is password-protected or encrypted",
    },
    ErrorCode.E_CONVERT_002: {
        "zh_CN": "无法转换 {filename}：文件已损坏，无法解析",
        "en_US": "Cannot convert {filename}: file is corrupted and cannot be parsed",
    },
    ErrorCode.E_INTERNAL_001: {
        "zh_CN": "内部错误：转换引擎异常（已记录到 crash.log）",
        "en_US": "Internal error: converter exception (logged to crash.log)",
    },
    # E_SYS_* / E_UPDATE_* 在对应模块定义
}

class ConversionError(Exception):
    """转换过程中可预期的错误（用户可见，不含 traceback）。"""

    def __init__(
        self,
        code: ErrorCode,
        message: Optional[str] = None,
        *,
        cause: Optional[BaseException] = None,
        **format_kwargs,
    ):
        self.code = code
        self.cause = cause
        # 默认用户消息（中文）
        template = ERROR_MESSAGES.get(code, {}).get("zh_CN", str(code))
        if message is None:
            try:
                message = template.format(**format_kwargs)
            except (KeyError, IndexError):
                message = template
        super().__init__(message)
        # 用户消息属性
        self.user_message = message
        # P3 ) 把 cause 挂到 __cause__，让
        # ``raise ConversionError(...) from e`` 的语义链对 traceback 可见，
        # 同时也兼容调用方显式 ``cause=`` 传参。
        if cause is not None:
            self.__cause__ = cause

    def get_message(self, lang: str = "zh_CN") -> str:
        """按语言取本地化消息。"""
        template = ERROR_MESSAGES.get(self.code, {}).get(lang, str(self.code))
        try:
            return template.format(**self.__dict__)
        except (KeyError, IndexError):
            return template
