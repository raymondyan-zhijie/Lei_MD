"""文件扩展名 SSOT（Single Source of Truth）。

职责：
- 定义项目支持的扩展名集合（SUPPORTED_EXTENSIONS）
- 定义被显式拦截的音频扩展名集合（AUDIO_EXTENSIONS，v0.4.0 Task C）
- 这是 core 层，被 src/core/* 和 src/ui/* 共享引用

历史：v0.4.1 P0 S1 修复分层违例——原本定义在 src/ui/drop_area.py，
     converter.py（core 层）反向 import UI 层，破坏 src/core 独立性。
     现将 SSOT 上提到 core/supported.py，drop_area 重新 export 保持兼容。
"""
from __future__ import annotations

# 支持的扩展名（与 F2 + 03 § SUPPORTED 一致）
# 不支持音频：.wav / .mp3 / .ogg / .flac（详见 01 F9a，v1.0 离线实现）
SUPPORTED_EXTENSIONS: set[str] = {
    # 文档
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".ppt", ".doc",
    ".epub", ".rtf", ".odt", ".ods", ".odp",
    # 网页
    ".html", ".htm", ".xml",
    # 图片
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    # 数据
    ".csv", ".json", ".tsv",
    # 压缩
    ".zip",
    # 文本
    ".txt", ".md", ".rst", ".log",
}

# 音频扩展名集合（v0.4.0 Task C：显式拦截 + E_FILE_006 提示）
# v1.0 不支持音频转录（仅 v1.1+ 离线实现）
AUDIO_EXTENSIONS: set[str] = {
    ".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma", ".opus",
}
