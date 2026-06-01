"""配置文件管理（Task 1.8）。

按 03 §Task 1.8 + 02 §6.4：
- 路径：Windows %APPDATA%\\Lei_MD\\config.json，Linux/macOS ~/.config/Lei_MD/config.json
- 持久化用户设置（output_dir / language / theme / LLM 等）
- 损坏文件自动备份 + 复位（E_INTERNAL_003）
- 未知字段静默忽略（forward-compat）

SSOT：01 §5.x、02 §3.3、04 §2 配置文件
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


def config_dir() -> Path:
    """跨平台配置目录：Windows %APPDATA%，Linux/macOS $XDG_CONFIG_HOME。

    每次调用都重新读 env（测试 monkeypatch 友好）。
    """
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "Lei_MD"


def config_file() -> Path:
    """配置文件路径。每次调用重新求 config_dir()。"""
    return config_dir() / "config.json"


# 向后兼容（SSOT：早期文档用了大写）
CONFIG_DIR: Path = config_dir()
CONFIG_FILE: Path = config_file()


@dataclass
class AppConfig:
    """Lei_MD 全局配置（SSOT：01 §5.x + 02 §3.3）。"""

    # 输出行为
    output_dir: str = "same"            # "same" | "custom"
    custom_output_dir: str = ""

    # 转换行为
    auto_convert: bool = True           # 拖入即转（v0.1.x 默认 True）
    max_history: int = 50               # 历史保留条数

    # 界面
    language: str = "system"            # "system" | "zh_CN" | "en_US"
    theme: str = "system"               # "system" | "light" | "dark"

    # 性能
    batch_concurrency: int = 4          # Sprint 3 Task 2.2 批量并行

    # LLM 图片描述（v1.0 P2，可选）
    llm_api_base: str = ""
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"


class ConfigManager:
    """配置读写管理器。

    行为：
    - __init__: 自动 load（无文件→默认 / 有文件→parse / 损坏→备份+默认）
    - get(): 返回当前 AppConfig 实例
    - update(**kwargs): 修改字段 + save()
    - save(): 写盘（utf-8 + ensure_ascii=False）
    """

    def __init__(self) -> None:
        config_dir().mkdir(parents=True, exist_ok=True)
        self._config: AppConfig = self._load()

    def _load(self) -> AppConfig:
        """从磁盘加载。无文件/损坏→返回默认。"""
        cfg_file = config_file()
        if not cfg_file.exists():
            return AppConfig()
        try:
            # v0.2.1 hotfix（H3）：用 utf-8-sig 自动剥离 BOM（Windows 记事本默认存 BOM）
            data: dict[str, Any] = json.loads(cfg_file.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            # 损坏：备份原文件 + 写默认（让用户重开就能跑）
            self._backup_and_reset()
            return AppConfig()
        # 过滤未知字段（forward-compat）
        known = {k: v for k, v in data.items() if k in AppConfig.__dataclass_fields__}
        try:
            return AppConfig(**known)
        except TypeError:
            # 字段类型错（schema 升级）→ 备份复位
            self._backup_and_reset()
            return AppConfig()

    def _backup_and_reset(self) -> None:
        """把损坏的 config.json 备份为 .json.bak，然后写一份默认配置。"""
        cfg_file = config_file()
        try:
            cfg_file.rename(cfg_file.with_suffix(".json.bak"))
        except OSError:
            try:
                cfg_file.unlink()
            except OSError:
                pass
        # 写默认（用 AppConfig 自己的 asdict）
        try:
            cfg_file.write_text(
                json.dumps(asdict(AppConfig()), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            # v0.2.2 hotfix（H1）：备份复位后同样收紧权限
            self._restrict_permissions(cfg_file)
        except OSError:
            pass  # 只读盘？让上层 get() 返回内存默认即可

    def save(self) -> None:
        """写盘。"""
        config_dir().mkdir(parents=True, exist_ok=True)
        cfg = config_file()
        cfg.write_text(
            json.dumps(asdict(self._config), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        # v0.2.2 hotfix（H1）：写完收紧权限为仅当前用户可读写，
        # 防止 LLM API key 被同机其他用户/备份工具读取。
        # Windows 上 os.chmod 是只读位，0o600 会被映射为 ACL 拒绝；POSIX 上是真正的 0o600。
        self._restrict_permissions(cfg)

    @staticmethod
    def _restrict_permissions(path: Path) -> None:
        """设置文件权限为 0o600（仅当前用户可读写）。"""
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass  # Windows FS / FAT32 / 只读盘：忽略，靠后续 keyring 方案解决

    def get(self) -> AppConfig:
        """当前配置。返回引用（不是 copy），调用方应只读或走 update()。"""
        return self._config

    def update(self, **kwargs: Any) -> None:
        """修改一个或多个字段，立即 save。

        未知字段静默忽略（不写盘、不抛错）。
        """
        changed = False
        for k, v in kwargs.items():
            if k in AppConfig.__dataclass_fields__:
                setattr(self._config, k, v)
                changed = True
        if changed:
            self.save()
