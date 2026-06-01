"""MarkItDown 转换引擎封装（Task 1.3）。

职责：
- 调用 `markitdown.MarkItDown().convert()` 把任意支持文件转 Markdown
- 前置校验：文件存在、非空、<500MB
- 异常翻译：MarkItDown 抛异常 → ConversionError（带 E_CONVERT_* 错误码）
- 不向用户暴露 Python traceback（与 02 §6.1 一致）

设计：
- 单实例化（Converter 实例共享 MarkItDown 引擎，03 §Task 1.3 注：避免每个文件重新初始化插件/缓存）
- SUPPORTED 扩展名集合与 DropArea 对齐（SSOT：定义在 drop_area.py）
- 可选 LLM api_key（v1.0+ 图片描述，F8）
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from markitdown import MarkItDown

from src.core.errors import ConversionError, ErrorCode
from src.ui.drop_area import SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)

# 复用 DropArea 的 SSOT 集合
SUPPORTED = SUPPORTED_EXTENSIONS

# 500MB 上限（与 02 §5 / 04 §7 一致）
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024


class MarkItDownConverter:
    """Lei_MD 的转换引擎封装。"""

    # 类属性：暴露给测试断言（SSOT 对齐 DropArea）
    SUPPORTED = SUPPORTED_EXTENSIONS
    MAX_FILE_SIZE = MAX_FILE_SIZE_BYTES

    def __init__(self, llm_api_key: Optional[str] = None):
        """初始化。

        Args:
            llm_api_key: 可选 LLM API Key（用于图片描述，v1.0 P2 功能）
        """
        self.llm_api_key = llm_api_key
        # 实例化 MarkItDown（enable_plugins=False 避免未声明的第三方插件注入）
        # 如需 LLM 图片描述，应在调用前 monkey patch llm_client
        self._md = MarkItDown(enable_plugins=False)

    def convert(self, file_path: str) -> str:
        """把文件转 Markdown。

        Args:
            file_path: 绝对路径

        Returns:
            Markdown 文本

        Raises:
            ConversionError: 文件级 / 转换级错误（用户可见，错误码体系）
        """
        path = Path(file_path)
        filename = path.name

        # 前置校验
        if not path.exists():
            raise ConversionError(
                ErrorCode.E_FILE_001, filename=filename
            )

        size = os.path.getsize(file_path)
        if size == 0:
            raise ConversionError(
                ErrorCode.E_FILE_002, filename=filename
            )
        if size > MAX_FILE_SIZE_BYTES:
            raise ConversionError(
                ErrorCode.E_FILE_003, filename=filename
            )

        # 委托给 MarkItDown
        try:
            result = self._md.convert(str(path))
        except Exception as e:
            # 区分密码保护 vs 格式损坏 vs 其他
            err_msg = str(e).lower()
            if "password" in err_msg or "encrypted" in err_msg or "encrypt" in err_msg:
                raise ConversionError(
                    ErrorCode.E_CONVERT_001, filename=filename, cause=e
                ) from e
            # 其他：文件格式损坏（最常见）
            logger.warning("MarkItDown convert failed for %s: %s", filename, e)
            raise ConversionError(
                ErrorCode.E_CONVERT_002, filename=filename, cause=e
            ) from e

        return result.markdown
