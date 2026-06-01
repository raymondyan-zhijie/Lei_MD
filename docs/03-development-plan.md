# Lei_MD 开发计划

> 🌐 **Language**: **中文** | [English](03-development-plan.en.md)

> **品牌：** leimengde  
> **For Hermes:** Use `subagent-driven-development` skill to implement this plan task-by-task.  
>  
> **Goal:** 构建一个 Windows 原生 GUI 应用，封装 Microsoft MarkItDown 的文件转 Markdown 功能。**大而全 + 离线运行 + 传统安装程序**。  
>  
> **Architecture:** PySide6 GUI + MarkItDown 引擎 + SQLite 历史 + QThread 异步转换。  
>  
> **Tech Stack:** Python 3.10 ~ 3.13, PySide6, MarkItDown[all], SQLite, PyInstaller + NSIS  
>  
> **总时间预估:** MVP 4-6 周（保守，非 2 周）
>
> ⚠️ **本文档状态**：**历史规划档案**。v0.1.0 → v0.3.0 已基于本文档实施完成。
> 规划任务（Phase 0 ~ 5）大部分已落地，详见对照表 [IMPLEMENTATION_VS_PLAN.md](IMPLEMENTATION_VS_PLAN.md)。
> 实际实施记录见 [CHANGELOG.md](../CHANGELOG.md) v0.1.0 / v0.2.0 / v0.3.0 三段。
>
> 本文件中保留的"Phase 0 ~ 5 / Task 0.1 ~ 5.x"章节是**实施索引**（按规划顺序），方便回溯"为什么这个 Task 出现"。任务标题保留，但版本/阶段标签已剥离。

> **SSOT 索引**：本文档是**开发任务分解**的权威定义。
> 技术选型见 [02 §1](02-architecture.md)，错误处理见 [02 §6](02-architecture.md)，测试见 [04-testing-plan.md](04-testing-plan.md)，发布见 [05-release-plan.md](05-release-plan.md)，上游更新见 [06-dependency-update-strategy.md](06-dependency-update-strategy.md)。

---

## Phase 0: 项目初始化

### Task 0.1: 创建项目骨架

**Objective:** 初始化项目目录结构、Git 仓库、依赖管理

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `requirements-build.txt`
- Create: `src/__init__.py`
- Create: `.gitignore`
- Create: `README.md`

**Step 1: 创建 pyproject.toml**

```toml
[project]
name = "lei-md"
version = "0.1.0"
description = "Windows GUI for Microsoft MarkItDown - convert files to Markdown with drag & drop, offline and all-in-one"
authors = [{name = "leimengde"}]
license = {text = "MIT"}
requires-python = ">=3.10,<3.14"
dependencies = [
    "markitdown[all]>=0.1.0,<0.2.0",
    "PySide6>=6.7,<7.0",
    "darkdetect>=0.8,<0.9",
    "markdown>=3.6,<4.0",
    "Pygments>=2.18,<3.0",
    "packaging>=24.0",  # 用于上游版本检查（src/core/updater.py）
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Operating System :: Microsoft :: Windows",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]

[project.scripts]
lei-md = "src.main:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

**Step 2: 创建 requirements.txt**

```
# 与 pyproject.toml dependencies 保持一致（P2-2 锁版本）
markitdown[all]>=0.1.0,<0.2.0
PySide6>=6.7,<7.0
darkdetect>=0.8,<0.9
markdown>=3.6,<4.0
Pygments>=2.18,<3.0
packaging>=24.0
```

**Step 3: 创建 .gitignore**

```
__pycache__/
*.pyc
*.pyo
.env
.venv/
dist/
build/
*.spec
*.exe
*.dmg
*.msi
.history/
*.db
*.log
.DS_Store
Thumbs.db
```

**Step 4: 初始化 Git 并提交**

```bash
cd /path/to/Lei_MD
git init
git add .
git commit -m "chore: initialize project skeleton"
```

---

### Task 0.2: 配置 CI/CD

**Objective:** 创建 GitHub Actions 工作流，自动测试和构建

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/release.yml`

**CI 工作流：**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: windows-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt', 'pyproject.toml') }}
          restore-keys: |
            ${{ runner.os }}-pip-
      - name: Run tests
        run: |
          pytest tests/ -v --cov=src/ --cov-report=term

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Lint
        run: |
          pip install ruff
          ruff check src/ tests/

  build:
    needs: [test, lint]
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Build
        run: |
          pip install pyinstaller
          python scripts/build.py
      - uses: actions/upload-artifact@v4
        with:
          name: lei-md-win64
          path: dist/
```

---

## Phase 1: 核心功能 — MVP

### Task 1.1: 程序入口与窗口骨架

**Objective:** 创建最小可运行的 PySide6 应用窗口

**Files:**
- Create: `src/main.py`
- Create: `src/app.py`
- Create: `src/ui/main_window.py`

**Step 1: 写 failing test**

```python
# tests/test_app.py
def test_app_creation(qapp):
    """App should create without errors."""
    from src.app import MarkItDownApp
    app = MarkItDownApp([])
    assert app is not None

def test_main_window_title(qapp):
    """Main window should have correct title."""
    from src.ui.main_window import MainWindow
    window = MainWindow()
    assert "Lei_MD" in window.windowTitle()
```

**Step 2: 实现 main.py**

```python
import sys
from src.app import main

if __name__ == "__main__":
    sys.exit(main())
```

**Step 3: 实现 app.py**

```python
import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

class MarkItDownApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("Lei_MD")
        self.setOrganizationName("leimengde")
        self.window = MainWindow()

def main():
    app = MarkItDownApp(sys.argv)
    app.window.show()
    return app.exec()
```

**Step 4: 实现 main_window.py**

```python
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lei_MD — 文件转 Markdown")
        self.resize(900, 650)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setAlignment(Qt.AlignCenter)
        placeholder = QLabel("拖拽文件到此处开始转换\n\n支持 PDF · Word · Excel · PPT · HTML · EPUB · 图片 · ZIP 等\n（音频 MP3/WAV/OGG/FLAC 见 01 F9a，v1.1+ 离线支持）")
        placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(placeholder)
```

### Task 1.2: 拖拽区域组件

**Objective:** 实现文件拖拽接收和格式检测

**Files:**
- Create: `src/ui/drop_area.py`
- Modify: `src/ui/main_window.py`

**Step 1: 写 failing test**

```python
def test_drop_area_accepts_files(qapp):
    from src.ui.drop_area import DropArea
    area = DropArea()
    assert area.acceptDrops() == True
```

**Step 2: 实现 drop_area.py**

```python
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, Signal
from pathlib import Path
import mimetypes

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt",
    ".xlsx", ".xls", ".html", ".htm", ".epub",
    ".csv", ".json", ".xml", ".txt", ".md",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    # 音频格式 v1.0 不支持（详见 01 F9a，v1.1+ 离线实现）
    # ".wav", ".mp3", ".ogg", ".flac",
    ".zip", ".msg", ".ipynb",
}

class DropArea(QLabel):
    files_dropped = Signal(list)  # list[Path]

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(120)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 12px;
                padding: 30px;
                font-size: 14px;
                color: #666;
            }
            QLabel:hover {
                border-color: #4a9eff;
                color: #4a9eff;
            }
        """)
        self.setText("📂  拖拽文件到此处\n或点击选择文件")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """收集所有支持的文件：单文件 + 目录递归展开。"""
        paths = []
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir():
                # 递归展开目录，flat 列表
                for child in p.rglob("*"):
                    if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS:
                        paths.append(child)
            elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                paths.append(p)
        if paths:
            self.files_dropped.emit(paths)
```

**Step 3: 集成到 MainWindow**

```python
# 在 MainWindow.__init__ 中替换 placeholder
from src.ui.drop_area import DropArea
self.drop_area = DropArea()
self.drop_area.files_dropped.connect(self.on_files_dropped)
layout.addWidget(self.drop_area)

def on_files_dropped(self, paths):
    print(f"接收文件: {paths}")
```

### Task 1.3: 转换引擎封装

**Objective:** 封装 MarkItDown 引擎，提供线程安全的转换接口

**Files:**
- Create: `src/core/converter.py`

**Step 1: 写 test**

```python
# tests/test_converter.py
from src.core.converter import MarkItDownConverter

def test_converter_init():
    conv = MarkItDownConverter()
    assert conv is not None

def test_converter_supported_extensions():
    conv = MarkItDownConverter()
    exts = conv.supported_extensions()
    assert ".pdf" in exts
    assert ".docx" in exts
```

**Step 2: 实现 converter.py**

```python
from markitdown import MarkItDown
from pathlib import Path
from typing import Optional

class MarkItDownConverter:
    """封装 MarkItDown 引擎，提供同步转换接口。
    注意：此类应在 QThread 中调用，避免阻塞 GUI。
    """
    
    SUPPORTED = {
        ".pdf", ".docx", ".doc", ".pptx", ".ppt",
        ".xlsx", ".xls", ".csv", ".html", ".htm",
        ".epub", ".jpg", ".jpeg", ".png", ".gif",
        ".bmp", ".webp", ".zip",
        ".msg", ".ipynb", ".json", ".xml", ".txt", ".md",
        # 音频格式 v1.0 不支持（详见 01 F9a，v1.1+ 离线实现）
        # ".wav", ".mp3", ".ogg", ".flac",
    }
    
    def __init__(self, enable_plugins: bool = False):
        self._md = MarkItDown(enable_plugins=enable_plugins)
    
    def convert(self, path: Path) -> str:
        """转换单个文件，返回 Markdown 文本。"""
        result = self._md.convert(str(path))
        return result.text_content
    
    @classmethod
    def supported_extensions(cls) -> set:
        return cls.SUPPORTED
```

### Task 1.4: 异步转换 Worker

**Objective:** 实现 QThread 后台转换，避免阻塞 UI

**Files:**
- Create: `src/core/batch_worker.py`

**Step 1: 实现 batch_worker.py**

```python
from PySide6.QtCore import QThread, Signal
from pathlib import Path
from src.core.converter import MarkItDownConverter
from dataclasses import dataclass
import time

@dataclass
class ConversionResult:
    path: Path
    markdown: str = ""
    error: str = ""
    duration_ms: float = 0
    success: bool = False

class ConverterWorker(QThread):
    progress = Signal(int)           # 当前进度 (0-100)
    file_done = Signal(ConversionResult)  # 单个文件完成
    all_done = Signal(list)          # 全部完成

    def __init__(self, files: list[Path]):
        super().__init__()
        self.files = files
        # Converter 实例共享——避免每个文件重新初始化插件/缓存
        self._converter = MarkItDownConverter()

    def run(self):
        results = []
        total = len(self.files)
        for i, path in enumerate(self.files):
            result = ConversionResult(path=path)
            try:
                start = time.time()
                result.markdown = self._converter.convert(path)
                result.duration_ms = (time.time() - start) * 1000
                result.success = True
            except Exception as e:
                result.error = str(e)
            results.append(result)
            self.file_done.emit(result)
            self.progress.emit(int((i + 1) / total * 100))
        self.all_done.emit(results)
```

### Task 1.5: Markdown 预览面板

**Objective:** 实时预览转换后的 Markdown 内容

**Files:**
- Create: `src/ui/preview_panel.py`
- Modify: `src/ui/main_window.py`

**Step 1: 实现 preview_panel.py**

```python
from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget
from PySide6.QtCore import Qt
import markdown

class PreviewPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setStyleSheet("""
            QTextBrowser {
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                font-size: 14px;
                padding: 12px;
            }
        """)
        layout.addWidget(self.browser)
        
        self._raw_md = ""
    
    def set_markdown(self, md_text: str):
        """设置 Markdown 文本并渲染"""
        self._raw_md = md_text
        html = markdown.markdown(
            md_text,
            extensions=['tables', 'fenced_code', 'codehilite', 'nl2br']
        )
        css = """
        <style>
            body { line-height: 1.6; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            code { background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
            pre { background-color: #2d2d2d; color: #f8f8f2; padding: 16px; border-radius: 6px; }
            img { max-width: 100%; }
        </style>
        """
        self.browser.setHtml(css + html)
    
    def clear(self):
        self._raw_md = ""
        self.browser.clear()
    
    def get_raw_markdown(self) -> str:
        return self._raw_md
```

### Task 1.6: 文件列表与状态

**Objective:** 显示待转换文件列表及转换状态

**Files:**
- Create: `src/ui/file_list.py`
- Modify: `src/ui/main_window.py`

**Step 1: 实现 file_list.py**

```python
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QListWidget,
                                QListWidgetItem, QLabel)
from PySide6.QtCore import Qt
from pathlib import Path

class FileList(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        header = QLabel("文件列表")
        header.setStyleSheet("font-weight: bold; font-size: 12px; padding: 4px;")
        layout.addWidget(header)
        
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        self.list.setMaximumHeight(200)
        layout.addWidget(self.list)
    
    def add_files(self, paths: list[Path]):
        self.list.clear()
        for p in paths:
            item = QListWidgetItem(f"⏳ {p.name}  ({self._fmt_size(p)})")
            item.setData(Qt.UserRole, str(p))
            self.list.addItem(item)
    
    def update_status(self, path: str, status: str, icon: str = "✅"):
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(Qt.UserRole) == path:
                item.setText(f"{icon} {Path(path).name} — {status}")
                break
    
    def _fmt_size(self, p: Path) -> str:
        size = p.stat().st_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
```

### Task 1.7: 主窗口整合

**Objective:** 将所有组件整合到主窗口，实现完整转换流程

**Files:**
- Modify: `src/ui/main_window.py`

**Step 1: 完整 main_window.py**

```python
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                                QHBoxLayout, QPushButton, QSplitter,
                                QMessageBox, QFileDialog, QProgressBar)
from PySide6.QtCore import Qt
from pathlib import Path

from src.ui.drop_area import DropArea
from src.ui.preview_panel import PreviewPanel
from src.ui.file_list import FileList
from src.core.batch_worker import ConverterWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lei_MD — 文件转 Markdown")
        self.resize(1000, 700)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Drop Area
        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self.on_files_dropped)
        main_layout.addWidget(self.drop_area)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        main_layout.addWidget(self.progress)
        
        # Splitter: File List | Preview
        splitter = QSplitter(Qt.Horizontal)
        
        self.file_list = FileList()
        splitter.addWidget(self.file_list)
        
        self.preview = PreviewPanel()
        splitter.addWidget(self.preview)
        
        splitter.setSizes([300, 700])
        main_layout.addWidget(splitter)
        
        # Bottom buttons
        btn_layout = QHBoxLayout()
        self.btn_convert = QPushButton("🔄 开始转换")
        self.btn_convert.clicked.connect(self.start_convert)
        self.btn_convert.setEnabled(False)
        
        self.btn_copy = QPushButton("📋 复制")
        self.btn_copy.clicked.connect(self.copy_markdown)
        self.btn_copy.setEnabled(False)
        
        self.btn_export = QPushButton("💾 导出 .md")
        self.btn_export.clicked.connect(self.export_markdown)
        self.btn_export.setEnabled(False)
        
        self.btn_clear = QPushButton("🗑 清空")
        self.btn_clear.clicked.connect(self.clear_all)
        
        btn_layout.addWidget(self.btn_convert)
        btn_layout.addWidget(self.btn_copy)
        btn_layout.addWidget(self.btn_export)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_clear)
        main_layout.addLayout(btn_layout)
        
        self._files: list[Path] = []
        self._worker: ConverterWorker | None = None
    
    def on_files_dropped(self, paths: list[Path]):
        self._files = paths
        self.file_list.add_files(paths)
        self.btn_convert.setEnabled(True)
    
    def start_convert(self):
        if not self._files:
            return
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.btn_convert.setEnabled(False)
        
        self._worker = ConverterWorker(self._files)
        self._worker.file_done.connect(self.on_file_done)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.all_done.connect(self.on_all_done)
        self._worker.start()
    
    def on_file_done(self, result):
        if result.success:
            self.file_list.update_status(str(result.path),
                f"完成 ({result.duration_ms:.0f}ms)", "✅")
            self.preview.set_markdown(result.markdown)
            self.btn_copy.setEnabled(True)
            self.btn_export.setEnabled(True)
        else:
            self.file_list.update_status(str(result.path),
                f"失败: {result.error}", "❌")
    
    def on_all_done(self, results):
        self.progress.setVisible(False)
        self.btn_convert.setEnabled(True)
    
    def copy_markdown(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.preview.get_raw_markdown())
    
    def export_markdown(self):
        md = self.preview.get_raw_markdown()
        if not md:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 Markdown", "output.md",
            "Markdown (*.md);;All Files (*)"
        )
        if path:
            Path(path).write_text(md, encoding="utf-8")
    
    def clear_all(self):
        self._files = []
        self.file_list.list.clear()
        self.preview.clear()
        self.progress.setVisible(False)
        self.btn_convert.setEnabled(False)
        self.btn_copy.setEnabled(False)
        self.btn_export.setEnabled(False)
```

### Task 1.8: 配置文件管理

**Objective:** 持久化用户设置

**Files:**
- Create: `src/core/config.py`

**Step 1: 实现 config.py**

```python
import json
import os
from pathlib import Path
from dataclasses import dataclass

# Windows: %APPDATA%\Lei_MD\config.json
# macOS/Linux (v2.0+): ~/.config/Lei_MD/config.json
def _config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "Lei_MD"

CONFIG_DIR = _config_dir()
CONFIG_FILE = CONFIG_DIR / "config.json"

@dataclass
class AppConfig:
    output_dir: str = "same"  # same | custom
    custom_output_dir: str = ""
    auto_convert: bool = True
    max_history: int = 50
    language: str = "system"
    theme: str = "system"
    batch_concurrency: int = 4
    llm_api_base: str = ""
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"

class ConfigManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._config = self._load()
    
    def _load(self) -> AppConfig:
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                return AppConfig(**{k: v for k, v in data.items() 
                                   if k in AppConfig.__dataclass_fields__})
            except (json.JSONDecodeError, TypeError):
                # 配置损坏：备份+重置
                CONFIG_FILE.rename(CONFIG_FILE.with_suffix(".json.bak"))
        return AppConfig()
    
    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(self._config.__dict__, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    def get(self) -> AppConfig:
        return self._config
    
    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self._config, k):
                setattr(self._config, k, v)
        self.save()
```

### Task 1.9: 历史记录

**Objective:** SQLite 存储转换历史（**WAL + Signal 串行化**并发策略，详见 [02 §3.3.1](02-architecture.md)）

**Files:**
- Create: `src/core/history.py`

```python
import sqlite3
import time
import os
from pathlib import Path
from dataclasses import dataclass
from PySide6.QtCore import QObject, pyqtSignal, pyqtSlot

def _data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "Lei_MD"

DB_PATH = _data_dir() / "history.db"

@dataclass
class HistoryEntry:
    id: int
    source_path: str
    source_format: str
    markdown_length: int
    duration_ms: int
    success: bool
    error_msg: str
    created_at: str

class HistoryManager(QObject):
    """
    SQLite 历史记录管理器。

    并发模型（WAL + Signal 串行化）：
    - PRAGMA journal_mode=WAL          读写并发不互斥
    - PRAGMA busy_timeout=5000         极端竞争自动 retry
    - 所有写入走 add_requested Signal   槽永远在主线程执行，写者唯一
    - ConverterWorker 调 request_add()  不直接碰 DB
    """
    add_requested = pyqtSignal(dict)   # ConverterWorker 线程 emit，主线程槽

    def __init__(self, max_entries: int = 50):
        super().__init__()
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._max = max_entries

        # check_same_thread=False 是必要的：
        # 我们用 Signal 强制主线程执行写入，所以连接本身可被多线程引用
        # 但实际所有 _conn.execute(...) 只在主线程发生
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")      # 关键 1
        self._conn.execute("PRAGMA busy_timeout=5000")     # 关键 2
        self._conn.execute("PRAGMA synchronous=NORMAL")    # WAL 推荐

        # 启动时检查数据库完整性（详见 02 §6.4 崩溃恢复）
        result = self._conn.execute("PRAGMA integrity_check").fetchone()
        if result[0] != "ok":
            # 损坏：备份 + 重建（对应 E_INTERNAL_002）
            import shutil
            shutil.copy2(DB_PATH, DB_PATH.with_suffix(f".db.bak.{int(time.time())}"))
            DB_PATH.unlink()
            self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")

        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT NOT NULL,
                source_format TEXT,
                markdown_length INTEGER DEFAULT 0,
                duration_ms INTEGER DEFAULT 0,
                success BOOLEAN DEFAULT 1,
                error_msg TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON history(created_at DESC)")
        self._conn.commit()

        # 关键 3：Signal 连接到主线程槽
        self.add_requested.connect(self._on_add)

    def request_add(self, source_path: str, fmt: str, md_len: int,
                    duration_ms: int, success: bool, error: str = ""):
        """
        线程安全入口。ConverterWorker 在 QThread 中调这个方法，
        Signal 会把执行切回主线程的 _on_add 槽。
        """
        self.add_requested.emit({
            "source_path": source_path,
            "fmt": fmt,
            "md_len": md_len,
            "duration_ms": duration_ms,
            "success": success,
            "error": error,
        })

    @pyqtSlot(dict)
    def _on_add(self, payload: dict):
        """
        实际写入槽。永远在主线程执行（QObject + Signal 的保证）。
        """
        self._conn.execute(
            "INSERT INTO history (source_path, source_format, markdown_length, duration_ms, success, error_msg) VALUES (?,?,?,?,?,?)",
            (payload["source_path"], payload["fmt"], payload["md_len"],
             payload["duration_ms"], payload["success"], payload["error"])
        )
        self._conn.commit()
        self._trim()

    def list(self, limit: int = 20) -> list[HistoryEntry]:
        """读取。WAL 模式下读不阻塞写，且只在主线程调用所以无需额外保护。"""
        rows = self._conn.execute(
            "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [HistoryEntry(*r) for r in rows]

    def _trim(self):
        self._conn.execute("""
            DELETE FROM history WHERE id NOT IN (
                SELECT id FROM history ORDER BY id DESC LIMIT ?
            )
        """, (self._max,))
        self._conn.commit()

    def close(self):
        """应用退出时调用，清理 WAL 文件 + 关闭连接。"""
        try:
            self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass
        self._conn.close()
```

**ConverterWorker 中的使用示例**（配合任务 1.4）：

```python
class ConverterWorker(QObject):
    finished = pyqtSignal(str, bool, str, int)  # path, success, error, duration_ms

    def __init__(self, history: HistoryManager):
        super().__init__()
        self._history = history  # 持有引用

    def run(self):
        # ... 转换逻辑 ...
        result_md = MarkItDown().convert(self._path)
        duration_ms = int((time.time() - start) * 1000)

        # 关键：调 request_add() 而非 history.add()，让主线程写 DB
        self._history.request_add(
            source_path=self._path,
            fmt=self._fmt,
            md_len=len(result_md.markdown),
            duration_ms=duration_ms,
            success=True,
        )
        self.finished.emit(self._path, True, "", duration_ms)
```

---

## Phase 2: 增强功能

### Task 2.1: 设置对话框

**Objective:** 提供 LLM API、输出目录、主题等配置界面

**Files:** `src/ui/settings_dialog.py`

### Task 2.2: 批量并行转换

**Objective:** 使用 QThreadPool 实现 4 路并行转换

**Files:** `src/core/batch_worker.py` (重构)

### Task 2.3: 历史记录面板

**Objective:** 查看/搜索/重新加载历史转换结果

**Files:** `src/ui/history_panel.py`

### Task 2.4: YouTube URL 输入

**Objective:** 输入 YouTube 链接直接获取字幕

**Files:** `src/ui/main_window.py` (新增 URL 输入栏)

### Task 2.5: 深色模式

**Objective:** 跟随 Windows 系统主题切换

**Files:** `src/ui/styles.py`, `src/app.py`

### Task 2.6: 中文界面

**Objective:** 完整的中文 UI 翻译

**Files:** `src/resources/locales/zh_CN.json`

---

## Phase 3: 打包与交付（v1.0 计划）

### Task 3.1: PyInstaller 打包脚本

```python
# scripts/build.py
import PyInstaller.__main__
import sys
from pathlib import Path

PyInstaller.__main__.run([
    'src/main.py',
    "--name=Lei_MD",
    '--windowed',                     # 无控制台窗口
    '--icon=src/resources/icons/app.ico',
    '--add-data=src/resources/locales:locales',
    '--hidden-import=markitdown',
    '--hidden-import=Pygments',
    '--clean',
    '--onefile',                      # 单文件（大而全）
])
```

### Task 3.2: NSIS 安装包

```nsis
; scripts/installer.nsi
Name "Lei_MD"
OutFile "Lei_MD-Setup-${VERSION}.exe"
InstallDir "$PROGRAMFILES\Lei_MD"
RequestExecutionLevel admin
```

### Task 3.3: GitHub Release 自动化

使用 `release.yml` 工作流，当推送 `v*` 标签时自动构建并发布。

---

## Phase 4: 测试策略

### Task 4.1: 单元测试

```python
# tests/conftest.py
import os
import sys
from pathlib import Path

import pytest

# 确保 src/ 可被 import
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """提供全局 QApplication 实例，供所有 UI 测试复用。"""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()
```

### Task 4.2: 测试清单

| 测试类型 | 覆盖范围 | 工具 |
|---------|----------|------|
| 单元测试 | converter, config, history, worker | pytest |
| UI 测试 | MainWindow, DropArea, 信号/槽 | pytest-qt |
| 集成测试 | 端到端转换流程 | pytest + 样本文件 |
| 性能测试 | 大文件转换时间 | pytest-benchmark |

---

## Phase 5: 最终检查清单（v1.0 收尾）

- [ ] 拖拽 PDF/Word/Excel/PPT/HTML/图片/ZIP 均可成功转换
- [ ] 拖入目录时自动递归展开
- [ ] 拖入音频（mp3/wav）给出明确不支持提示（v1.0 不支持）
- [ ] 批量 10 个文件转换无崩溃
- [ ] 预览窗口正确渲染 Markdown（表格、代码块、图片）
- [ ] 复制到剪贴板正常
- [ ] 导出 .md 文件正常（UTF-8 编码）
- [ ] 深色/浅色模式切换正常
- [ ] 中文界面完整无遗漏
- [ ] 设置持久化（关闭重开不丢失）
- [ ] PyInstaller 打包的 .exe 在干净 Windows 上可运行
- [ ] NSIS 安装包正常安装/卸载

---

## 文件清单

| 文件 | 状态 | 说明 |
|------|------|------|
| `docs/01-requirements.md` | ✅ 已创建 | 需求文档 |
| `docs/02-architecture.md` | ✅ 已创建 | 架构设计 |
| `docs/03-development-plan.md` | ✅ 本文件 | 开发计划 |
| `docs/04-testing-plan.md` | ✅ 已创建 | 测试计划 |
| `docs/05-release-plan.md` | ✅ 已创建 | 发布与维护 |
| `docs/06-dependency-update-strategy.md` | ✅ 已创建 | 依赖更新策略（首次发布后） |
| `CODE_OF_CONDUCT.md` | ✅ 已创建 | 社区行为准则 |
| `pyproject.toml` | 🔜 | 项目配置 |
| `src/` | 🔜 | 源代码 |
| `tests/` | 🔜 | 测试代码 |
