"""配置文件管理（）。+ 02 §6.4：
- 路径：Windows %APPDATA%\\Lei_MD\\config.json，Linux/macOS ~/.config/Lei_MD/config.json
- 持久化用户设置（output_dir / language / theme / LLM 等）
- 损坏文件自动备份 + 复位（E_INTERNAL_003）
- 未知字段静默忽略（forward-compat）.x、02 §3.3、04 §2 配置文件
"""
from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

def config_dir() -> Path:
    """跨平台配置目录：Windows %APPDATA%，Linux/macOS $XDG_CONFIG_HOME。

    每次调用都重新读 env（测试 monkeypatch 友好）。

    Windows 平台：优先读 ``XDG_CONFIG_HOME``（如果设置）— 用途是让
    CI 测试 ``monkeypatch.setenv('XDG_CONFIG_HOME', ...)`` 跨平台生效，
    不污染真实 %APPDATA%。production 默认仍走 %APPDATA%。
    """
    if os.name == "nt":
        # Windows: prefer XDG_CONFIG_HOME for test isolation; fall back to APPDATA.
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            base = Path(xdg)
        else:
            base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "Lei_MD"

def config_file() -> Path:
    """配置文件路径。每次调用重新求 config_dir()。"""
    return config_dir() / "config.json"

# 向后兼容
CONFIG_DIR: Path = config_dir()
CONFIG_FILE: Path = config_file()

@dataclass
class AppConfig:
    """Lei_MD 全局配置（.x + 02 §3.3）。"""

    # 输出行为
    output_dir: str = "same"            # "same" | "custom"
    custom_output_dir: str = ""

    # 转换行为
    auto_convert: bool = True           # 拖入即转（ .x 默认 True）
    max_history: int = 50               # 历史保留条数

    # 界面
    language: str = "system"            # "system" | "zh_CN" | "en_US"
    theme: str = "system"               # "system" | "light" | "dark"

    # 性能
    batch_concurrency: int = 4          # 批量并行

    # LLM 图片描述（ ，可选）
    llm_api_base: str = ""
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"

    # ---- audit 字段类型/取值校验 ----
    # 故意只校验已知"会被攻击者/老版本写坏"的字段；output_dir 这种
    # 业务枚举但 forward-compat 友好（值为 "same" / "custom" / 未来
    # 其它合法值）保持宽松，避免阻塞 schema 演进。
    _LANGUAGE_VALUES = frozenset({"system", "zh_CN", "en_US"})
    _THEME_VALUES = frozenset({"system", "light", "dark"})

    def __post_init__(self) -> None:
        """字段类型/取值校验。失败 → TypeError，触发 _load 的备份复位路径。

        设计要点：
        - bool 必须是 bool，不能是 int（避免 0/1 兼容陷阱——dataclass 默认不拒 int）
        - 数值字段给上下界，防止 max_history="fifty" / batch_concurrency=99999 这类
          半坏数据被静默接受
        - 枚举字段给白名单，language / theme 错值立即触发复位（不"宽容"）
        - LLM 三字段强制 str（防 list/dict 注入；空字符串允许，代表"未配置"）
        """
        if not isinstance(self.output_dir, str):
            raise TypeError(f"output_dir must be str, got {type(self.output_dir).__name__}")
        if not isinstance(self.custom_output_dir, str):
            raise TypeError(
                f"custom_output_dir must be str, got {type(self.custom_output_dir).__name__}"
            )
        # bool 必须是真正的 bool（int 在 dataclass 层面会被静默接受）
        if not isinstance(self.auto_convert, bool):
            raise TypeError(
                f"auto_convert must be bool, got {type(self.auto_convert).__name__}"
            )
        if not isinstance(self.max_history, int) or isinstance(self.max_history, bool):
            raise TypeError(
                f"max_history must be int, got {type(self.max_history).__name__}"
            )
        if not (1 <= self.max_history <= 999):
            raise TypeError(
                f"max_history must be in [1, 999], got {self.max_history}"
            )
        if not isinstance(self.language, str):
            raise TypeError(f"language must be str, got {type(self.language).__name__}")
        if self.language not in self._LANGUAGE_VALUES:
            raise TypeError(
                f"language must be one of {sorted(self._LANGUAGE_VALUES)}, "
                f"got {self.language!r}"
            )
        if not isinstance(self.theme, str):
            raise TypeError(f"theme must be str, got {type(self.theme).__name__}")
        if self.theme not in self._THEME_VALUES:
            raise TypeError(
                f"theme must be one of {sorted(self._THEME_VALUES)}, "
                f"got {self.theme!r}"
            )
        if not isinstance(self.batch_concurrency, int) or isinstance(self.batch_concurrency, bool):
            raise TypeError(
                f"batch_concurrency must be int, got {type(self.batch_concurrency).__name__}"
            )
        if not (1 <= self.batch_concurrency <= 32):
            raise TypeError(
                f"batch_concurrency must be in [1, 32], got {self.batch_concurrency}"
            )
        if not isinstance(self.llm_api_base, str):
            raise TypeError(
                f"llm_api_base must be str, got {type(self.llm_api_base).__name__}"
            )
        if not isinstance(self.llm_api_key, str):
            raise TypeError(
                f"llm_api_key must be str, got {type(self.llm_api_key).__name__}"
            )
        if not isinstance(self.llm_model, str):
            raise TypeError(
                f"llm_model must be str, got {type(self.llm_model).__name__}"
            )

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
            # ：用 utf-8-sig 自动剥离 BOM（Windows 记事本默认存 BOM）
            data: dict[str, Any] = json.loads(cfg_file.read_text(encoding="utf-8-sig"))
            # audit：json.loads 可能返回合法但非 dict 的值
            # （list / str / int / bool / null）。后续 data.items() 会抛
            # AttributeError → 杀启动。显式拒绝 + 抛 ValueError，被同 try
            # 块 except 接住走复位路径。
            if not isinstance(data, dict):
                raise ValueError("config root must be a JSON object")
        except (json.JSONDecodeError, UnicodeDecodeError, OSError, ValueError, AttributeError) as e:
            # 损坏：备份原文件 + 写默认（让用户重开就能跑）
            _logger.warning(
                "config file %s is unreadable (%s: %s) — backing up and resetting to defaults",
                cfg_file,
                type(e).__name__,
                e,
            )
            self._backup_and_reset()
            return AppConfig()
        # 过滤未知字段（forward-compat）
        known = {k: v for k, v in data.items() if k in AppConfig.__dataclass_fields__}
        try:
            return AppConfig(**known)
        except TypeError as e:
            # audit：AppConfig.__post_init__ 抛 TypeError
            # 表示字段类型/取值错（schema 不匹配 / 半坏数据）→ 备份复位。
            # 之前 except 只接住"未知 kwargs"导致的 TypeError；现在
            # __post_init__ 的类型错也走同一条复位路径，行为统一。
            # 日志带具体错信息（字段名/类型），方便用户排错。
            _logger.warning(
                "config schema/type mismatch in %s (%s: %s) — backing up and resetting to defaults",
                cfg_file,
                type(e).__name__,
                e,
            )
            self._backup_and_reset()
            return AppConfig()

    def _backup_and_reset(self) -> None:
        """把损坏的 config.json 备份为 .json.bak，然后写一份默认配置。

        audit 修复：原实现用 cfg_file.rename()，两个隐患：
        1) Windows rename 不允许覆盖已存在的 .json.bak（POSIX 允许），
           OSError → 直接 unlink 原文件 → 损坏内容没保留。
        2) 跨卷 rename 抛 OSError（exdev），同 1 后果。
        新实现三级 fallback，保证"先有 .bak 副本，再删原文件"：
        os.replace（原子 + Windows 友好 + 允许覆盖）→ shutil.move（跨卷）
        → unlink（最后兜底；此时 .bak 仍不存在，但至少不让坏文件留在原位）。
        """
        cfg_file = config_file()
        bak_file = cfg_file.with_suffix(".json.bak")
        # 1) 优先 os.replace（原子，Windows / POSIX 都能覆盖已存在的 .bak）
        try:
            os.replace(cfg_file, bak_file)
        except OSError:
            # 2) 跨卷：shutil.move 内部会 fallback 到 copy+remove
            try:
                shutil.move(str(cfg_file), str(bak_file))
            except OSError:
                # 3) 终极兜底：删原文件（至少不阻塞启动；坏内容可能在
                # 下次 save 时被默认覆盖；用户无 .bak 可恢复）
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
            # ：备份复位后同样收紧权限
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
        # ：写完收紧权限为仅当前用户可读写，
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
