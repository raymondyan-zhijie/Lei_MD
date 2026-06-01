"""MarkItDown 转换引擎封装（Task 1.3）。

职责：
- 调用 `markitdown.MarkItDown().convert()` 把任意支持文件转 Markdown
- 前置校验：文件存在、是普通文件、非空、<500MB
- 异常翻译：MarkItDown 抛异常 → ConversionError（带 E_CONVERT_* 错误码）
- 不向用户暴露 Python traceback（与 02 §6.1 一致）

设计：
- 单实例化（Converter 实例共享 MarkItDown 引擎，03 §Task 1.3 注：避免每个文件重新初始化插件/缓存）
- SUPPORTED 扩展名集合与 DropArea 对齐（SSOT：定义在 drop_area.py）
- 可选 LLM api_key（v1.0+ 图片描述，F8）
- v0.2.4 P2 审计 M3.8：MarkItDown 引擎不是线程安全的；构造延迟到首次
  convert()/clone_for_thread()，batch 场景下每个 runnable 通过 clone_for_thread()
  获得独立实例，避免共享 MarkItDown 内部状态/锁
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
        # v0.2.4 P2 审计 M3.8：MarkItDown 引擎延迟到首次 convert()/clone_for_thread()
        # 构造，避免 __init__ 阶段就创建不可重入的内部状态。原 _md 是在 __init__ 直接
        # 构造的，导致 BatchWorker 多个 _ConvertRunnable 共享同一 MarkItDown 实例，
        # 触发潜在的 lock 竞争 / 状态污染。clone_for_thread() 会为每个线程构造
        # 独立 MarkItDown；单线程场景下 _ensure_md() 在首次 convert() 时构造。
        self._md: Optional[MarkItDown] = None

    def _ensure_md(self) -> MarkItDown:
        """惰性构造 MarkItDown 引擎（v0.2.4 P2 审计 M3.8）。

        单线程路径（src/core/worker.py）首次调用 convert() 时构造；
        多线程路径（BatchWorker）由 clone_for_thread() 提前构造好。
        """
        if self._md is None:
            # enable_plugins=False 避免未声明的第三方插件注入
            # 如需 LLM 图片描述，应在调用前 monkey patch llm_client
            self._md = MarkItDown(enable_plugins=False)
        return self._md

    def clone_for_thread(self) -> "MarkItDownConverter":
        """v0.2.4 P2 审计 M3.8：返回带独立 MarkItDown 引擎的新实例。

        BatchWorker._ConvertRunnable 在 run() 入口调用本方法，让每个
        worker 线程持有自己的 MarkItDown 引擎，避免共享同一实例带来的
        非可重入锁 / 内部缓存状态污染。llm_api_key 透传，保证语义一致。
        """
        clone = MarkItDownConverter(llm_api_key=self.llm_api_key)
        # 各自构造 MarkItDown（不等首次 convert() 触发）
        clone._md = MarkItDown(enable_plugins=False)
        return clone

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
        # v0.2.4 P2 审计 M3.7：拒绝目录、socket、设备文件等"存在但非普通文件"。
        # 不加这条的话，目录在 Linux 上 getsize() 返回 4096、某些平台返回 0，
        # 会误导触发 E_FILE_002（空文件）或 E_FILE_003（超大文件）。
        if not path.is_file():
            raise ConversionError(
                ErrorCode.E_FILE_001, filename=filename
            )

        # v0.2.4 P2 审计 M5.3：os.path.getsize() 在权限被拒 / IO 错误时抛 OSError。
        # 不抓会被上层的 "except Exception" 吞掉并错误归类为 E_CONVERT_002
        # （文件损坏）；这里显式翻译为 E_FILE_001（文件读不到）。
        try:
            size = os.path.getsize(file_path)
        except OSError as e:
            raise ConversionError(
                ErrorCode.E_FILE_001, filename=filename, cause=e
            ) from e

        if size == 0:
            raise ConversionError(
                ErrorCode.E_FILE_002, filename=filename
            )
        if size > MAX_FILE_SIZE_BYTES:
            raise ConversionError(
                ErrorCode.E_FILE_003, filename=filename
            )

        # 委托给 MarkItDown（lazy 构造，M3.8）
        md = self._ensure_md()
        try:
            result = md.convert(str(path))
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
