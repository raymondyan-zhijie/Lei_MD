"""FileItem 文件项数据类（v0.4.2 P1 A1 实现 02-architecture.md §3.4 描述）。

之前文档 §3.4 把 FileItem 列为"文件项"模型，但代码里没有对应实现。
本次补齐：
- @dataclass，与文档 §3.4 字段对齐（path/format/size/status/result/error/duration）
- 行为：状态枚举 STRICT（pending/converting/done/error）
- 暴露给 UI 层（PreviewPanel / FileList）做单文件状态展示

设计：
- 不持久化（持久化用 HistoryRecord，这是运行期内存模型）
- 不放 src/ui/（UI 层依赖，core 层定义）—— 反向支持 02 §3.4 的分层图
- 默认值：pending 状态 + 空 result/error + 0 duration（dataclass field 顺序靠后）
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# 状态枚举（与文档 02 §3.4 一致；用 Literal 而不是 Enum 以便 JSON 序列化友好）
FileStatus = Literal["pending", "converting", "done", "error"]


@dataclass
class FileItem:
    """单文件转换项（v0.4.2 P1 A1）。

    字段顺序与文档 02 §3.4 对齐；无默认值的在前，有默认值的在后。
    """

    path: Path
    format: str           # 检测到的格式: pdf, docx, pptx...（小写，无点）
    size: int             # 文件大小（bytes）
    status: FileStatus = "pending"   # pending / converting / done / error
    result: str = ""      # 转换后的 Markdown 文本
    error: str = ""       # 错误信息（错误码 + 可读消息）
    duration: float = 0.0  # 转换耗时（秒）

    def is_done(self) -> bool:
        """是否成功完成。"""
        return self.status == "done"

    def is_failed(self) -> bool:
        """是否转换失败。"""
        return self.status == "error"

    def short_name(self) -> str:
        """文件名（不含目录），便于 UI 展示。"""
        return self.path.name

    def size_human(self) -> str:
        """文件大小转可读字符串（B / KB / MB / GB）。"""
        if self.size < 1024:
            return f"{self.size} B"
        if self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        if self.size < 1024 * 1024 * 1024:
            return f"{self.size / 1024 / 1024:.1f} MB"
        return f"{self.size / 1024 / 1024 / 1024:.2f} GB"
