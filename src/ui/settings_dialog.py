"""设置对话框（Task 2.1）。

按 03 §Task 2.1 + 02 §3.3（AppConfig 字段）：
- 构造时载入 ConfigManager 当前配置到 UI
- accept() → ConfigManager.update 持久化
- reject() → 不改 config
- reset_to_defaults 按钮 → 重置 UI + 内存对象（不 save）

字段映射（已实现 AppConfig 扁平 schema）：
- output_dir: "same" | "custom"  (QComboBox)
- custom_output_dir: str  (QLineEdit)
- auto_convert: bool  (QCheckBox)
- max_history: int  (QSpinBox 1~999)
- language: "system" | "zh_CN" | "en_US"  (QComboBox)
- theme: "system" | "light" | "dark"  (QComboBox)
- batch_concurrency: int 1~8  (QSpinBox)
- llm_api_base/llm_api_key/llm_model: str  (QLineEdit)

SSOT 偏离：02 §3.3 规范用嵌套 llm{} + config_version，Sprint 2 推的 AppConfig
用了扁平字段 + 无 config_version。Sprint 3 不回头改（v0.2.0-rc1 已发布），
留 v0.3.0 迁移。
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SettingsDialog(QDialog):
    """Lei_MD 设置对话框。"""

    # 输出目录选项
    _OUTPUT_DIR_OPTIONS = ("same", "custom")
    # 语言
    _LANGUAGE_OPTIONS = ("system", "zh_CN", "en_US")
    # 主题
    _THEME_OPTIONS = ("system", "light", "dark")

    def __init__(self, config_manager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cm = config_manager
        self.setWindowTitle("Lei_MD 设置")
        self.resize(560, 480)

        # 构造所有 widget
        self._build_widgets()
        self._build_layout()
        self._wire_signals()

        # 载入当前 config
        self._load_from_config()

    def _build_widgets(self) -> None:
        """构造所有输入 widget。"""
        # 输出行为
        self.output_dir_combo = QComboBox()
        self.output_dir_combo.addItems(self._OUTPUT_DIR_OPTIONS)
        self.custom_output_edit = QLineEdit()
        self.auto_convert_check = QCheckBox("拖入后自动转换")

        # 容量
        self.max_history_spin = QSpinBox()
        self.max_history_spin.setRange(1, 999)
        self.max_history_spin.setSuffix(" 条")

        # 界面
        self.language_combo = QComboBox()
        self.language_combo.addItems(self._LANGUAGE_OPTIONS)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(self._THEME_OPTIONS)

        # 性能
        self.batch_concurrency_spin = QSpinBox()
        self.batch_concurrency_spin.setRange(1, 8)

        # LLM
        self.llm_api_base_edit = QLineEdit()
        self.llm_api_base_edit.setPlaceholderText("https://api.openai.com/v1")
        self.llm_api_key_edit = QLineEdit()
        self.llm_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.llm_api_key_edit.setPlaceholderText("（密码隐藏）")
        self.llm_model_edit = QLineEdit()
        self.llm_model_edit.setPlaceholderText("gpt-4o")

        # 按钮
        self.reset_button = QPushButton("恢复默认")
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        # 中文按钮文字
        ok_btn = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("确定")
        cancel_btn = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("取消")

    def _build_layout(self) -> None:
        """布局。"""
        root = QVBoxLayout(self)

        # 输出
        out_group = QWidget()
        out_form = QFormLayout(out_group)
        out_form.addRow("输出目录：", self.output_dir_combo)
        out_form.addRow("自定义输出路径：", self.custom_output_edit)
        out_form.addRow("", self.auto_convert_check)
        root.addWidget(QLabel("── 输出行为 ──"))
        root.addWidget(out_group)

        # 容量 / 性能
        cap_group = QWidget()
        cap_form = QFormLayout(cap_group)
        cap_form.addRow("历史保留条数：", self.max_history_spin)
        cap_form.addRow("批量并发数 (1-8)：", self.batch_concurrency_spin)
        root.addWidget(QLabel("── 容量 / 性能 ──"))
        root.addWidget(cap_group)

        # 界面
        ui_group = QWidget()
        ui_form = QFormLayout(ui_group)
        ui_form.addRow("语言：", self.language_combo)
        ui_form.addRow("主题：", self.theme_combo)
        root.addWidget(QLabel("── 界面 ──"))
        root.addWidget(ui_group)

        # LLM
        llm_group = QWidget()
        llm_form = QFormLayout(llm_group)
        llm_form.addRow("LLM API Base：", self.llm_api_base_edit)
        llm_form.addRow("LLM API Key：", self.llm_api_key_edit)
        llm_form.addRow("LLM Model：", self.llm_model_edit)
        root.addWidget(QLabel("── LLM 图片描述（v1.0 P2，可选）──"))
        root.addWidget(llm_group)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.reset_button)
        btn_row.addStretch()
        btn_row.addWidget(self.button_box)
        root.addLayout(btn_row)

    def _wire_signals(self) -> None:
        self.reset_button.clicked.connect(self._on_reset_defaults)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self._on_reject)

    def _load_from_config(self) -> None:
        """从 ConfigManager 读当前配置 → 填到 UI。"""
        cfg = self._cm.get()
        # Combo 用 setCurrentText 找不到就保持默认
        if cfg.output_dir in self._OUTPUT_DIR_OPTIONS:
            self.output_dir_combo.setCurrentText(cfg.output_dir)
        self.custom_output_edit.setText(cfg.custom_output_dir)
        self.auto_convert_check.setChecked(cfg.auto_convert)
        self.max_history_spin.setValue(cfg.max_history)
        if cfg.language in self._LANGUAGE_OPTIONS:
            self.language_combo.setCurrentText(cfg.language)
        if cfg.theme in self._THEME_OPTIONS:
            self.theme_combo.setCurrentText(cfg.theme)
        self.batch_concurrency_spin.setValue(cfg.batch_concurrency)
        self.llm_api_base_edit.setText(cfg.llm_api_base)
        self.llm_api_key_edit.setText(cfg.llm_api_key)
        self.llm_model_edit.setText(cfg.llm_model)

    def _collect_from_ui(self) -> dict:
        """从 UI 读所有字段 → dict（传给 ConfigManager.update）。"""
        return {
            "output_dir": self.output_dir_combo.currentText(),
            "custom_output_dir": self.custom_output_edit.text(),
            "auto_convert": self.auto_convert_check.isChecked(),
            "max_history": self.max_history_spin.value(),
            "language": self.language_combo.currentText(),
            "theme": self.theme_combo.currentText(),
            "batch_concurrency": self.batch_concurrency_spin.value(),
            "llm_api_base": self.llm_api_base_edit.text(),
            "llm_api_key": self.llm_api_key_edit.text(),
            "llm_model": self.llm_model_edit.text(),
        }

    # -------- slots --------

    def _on_accept(self) -> None:
        """确定 → update 落盘。"""
        self._cm.update(**self._collect_from_ui())
        self.accept()  # QDialog.accept() 关闭并返回 Accepted

    def _on_reject(self) -> None:
        """取消 → 不动 config。"""
        self.reject()

    def _on_reset_defaults(self) -> None:
        """恢复默认 → UI 重置 + 内存对象 reset（不 save 磁盘）。"""
        from src.core.config import AppConfig
        default = AppConfig()
        # 内存对象改回默认
        for k, v in default.__dict__.items():
            if hasattr(self._cm.get(), k):
                setattr(self._cm.get(), k, v)
        # UI 刷新
        self._load_from_config()
