# Lei_MD 测试计划

> **品牌：** leimengde  
> **版本：** v0.1.0 | **日期：** 2026-06-01

---

## 1. 测试策略

采用 **测试金字塔** 模型：大量单元测试 → 适量集成测试 → 少量 E2E 测试。

```
         ╱  E2E (5%)  ╲
        ╱  集成测试 (20%) ╲
       ╱   单元测试 (75%)   ╲
      ────────────────────────
```

## 2. 测试环境

| 维度 | 配置 |
|------|------|
| 操作系统 | Windows 10 (22H2), Windows 11 (23H2) |
| Python | 3.10, 3.11, 3.12 |
| CI | GitHub Actions `windows-latest` |
| 本地 | 开发者 Windows 11 Pro Workstation |

> 配套 `tests/conftest.py` 提供全局 `qapp` fixture（offscreen 模式），pytest-qt 自动复用。

## 3. 单元测试

### 3.1 转换引擎测试 (`tests/test_converter.py`)

```python
import pytest
from pathlib import Path
from src.core.converter import MarkItDownConverter

class TestConverter:
    def test_init_default(self):
        conv = MarkItDownConverter()
        assert conv is not None

    def test_supported_extensions(self):
        exts = MarkItDownConverter.supported_extensions()
        assert ".pdf" in exts
        assert ".docx" in exts
        assert ".pptx" in exts
        assert ".xlsx" in exts

    @pytest.mark.parametrize("ext,expected_contains", [
        (".txt", True),
        (".pdf", True),
        (".xyz", False),      # 不支持的格式
    ])
    def test_extension_support(self, ext, expected_contains):
        exts = MarkItDownConverter.supported_extensions()
        assert (ext in exts) == expected_contains

    def test_convert_txt(self, tmp_path):
        """基本 TXT 转换"""
        f = tmp_path / "test.txt"
        f.write_text("Hello World", encoding="utf-8")
        conv = MarkItDownConverter()
        result = conv.convert(f)
        assert "Hello World" in result

    def test_convert_nonexistent(self):
        """不存在的文件应抛出异常"""
        conv = MarkItDownConverter()
        with pytest.raises(Exception):
            conv.convert(Path("/nonexistent/file.pdf"))
```

### 3.2 配置管理测试 (`tests/test_config.py`)

```python
class TestConfig:
    def test_default_config(self, tmp_config):
        mgr = ConfigManager(config_dir=tmp_config)
        cfg = mgr.get()
        assert cfg.output_dir == "same"
        assert cfg.auto_convert == True
        assert cfg.language == "system"

    def test_update_and_persist(self, tmp_config):
        mgr = ConfigManager(config_dir=tmp_config)
        mgr.update(output_dir="custom", language="zh_CN")
        cfg = mgr.get()
        assert cfg.output_dir == "custom"
        assert cfg.language == "zh_CN"
        # 重新加载
        mgr2 = ConfigManager(config_dir=tmp_config)
        assert mgr2.get().language == "zh_CN"

    def test_llm_key_not_logged(self, tmp_config):
        """API key 不应出现在日志中"""
        mgr = ConfigManager(config_dir=tmp_config)
        mgr.update(llm_api_key="sk-secret-123")
        cfg = mgr.get()
        assert cfg.llm_api_key == "sk-secret-123"
```

### 3.3 历史记录测试 (`tests/test_history.py`)

```python
class TestHistory:
    def test_add_and_list(self, tmp_db):
        mgr = HistoryManager(db_path=tmp_db)
        mgr.add("/tmp/test.pdf", "pdf", 500, 1200, True)
        entries = mgr.list()
        assert len(entries) == 1
        assert entries[0].source_format == "pdf"

    def test_trim_excess(self, tmp_db):
        mgr = HistoryManager(db_path=tmp_db, max_entries=5)
        for i in range(10):
            mgr.add(f"/tmp/file_{i}.pdf", "pdf", 100, 500, True)
        assert len(mgr.list()) <= 5

    def test_failed_conversion_recorded(self, tmp_db):
        mgr = HistoryManager(db_path=tmp_db)
        mgr.add("/tmp/bad.pdf", "pdf", 0, 200, False, "Corrupted file")
        e = mgr.list()[0]
        assert e.success == False
        assert "Corrupted" in e.error_msg
```

### 3.4 Batch Worker 测试 (`tests/test_batch_worker.py`)

```python
class TestBatchWorker:
    def test_single_file(self, qapp, tmp_path, qtbot):
        f = tmp_path / "test.txt"
        f.write_text("test content")
        worker = ConverterWorker([f])
        
        results = []
        worker.file_done.connect(results.append)
        
        with qtbot.waitSignal(worker.all_done, timeout=10000):
            worker.start()
        
        assert len(results) == 1
        assert results[0].success == True

    def test_mixed_files(self, qapp, tmp_path, qtbot):
        f1 = tmp_path / "good.txt"
        f1.write_text("good")
        f2 = tmp_path / "bad.xyz"
        f2.write_text("bad")
        
        worker = ConverterWorker([f1, f2])
        results = []
        worker.file_done.connect(results.append)
        
        with qtbot.waitSignal(worker.all_done, timeout=15000):
            worker.start()
        
        assert len(results) == 2
        # good.txt 应该成功，bad.xyz 应该失败
        assert any(r.success for r in results)
        assert any(not r.success for r in results)
```

## 4. UI 测试 (`tests/test_ui/`)

### 4.1 MainWindow 测试

```python
class TestMainWindow:
    def test_window_title(self, qapp):
        window = MainWindow()
        assert "MarkItDown" in window.windowTitle()

    def test_initial_button_state(self, qapp):
        window = MainWindow()
        assert not window.btn_convert.isEnabled()
        assert not window.btn_copy.isEnabled()

    def test_drop_area_visible(self, qapp):
        window = MainWindow()
        assert window.drop_area.isVisible()

    def test_clear_resets_state(self, qapp):
        window = MainWindow()
        window.btn_convert.setEnabled(True)
        window.btn_copy.setEnabled(True)
        window.clear_all()
        assert not window.btn_convert.isEnabled()
        assert not window.btn_copy.isEnabled()
```

### 4.2 DropArea 测试

```python
class TestDropArea:
    def test_accepts_drops(self, qapp):
        area = DropArea()
        assert area.acceptDrops()

    def test_files_dropped_signal(self, qapp, tmp_path, qtbot):
        area = DropArea()
        f1 = tmp_path / "test.pdf"
        f1.touch()
        
        received = []
        area.files_dropped.connect(received.append)
        
        # 模拟拖拽
        from PySide6.QtCore import QMimeData, QUrl
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(f1))])
        from PySide6.QtGui import QDropEvent
        event = QDropEvent(
            QPointF(50, 50), Qt.CopyAction,
            mime, Qt.LeftButton, Qt.NoModifier
        )
        area.dropEvent(event)
        
        assert len(received) == 1
```

## 5. 集成测试

### 5.1 端到端转换流程

```python
def test_full_workflow(qapp, tmp_path, qtbot):
    """完整流程：拖入文件 → 转换 → 预览 → 导出"""
    window = MainWindow()
    
    # 1. 创建测试文件
    test_file = tmp_path / "sample.txt"
    test_file.write_text("# Test\n\nHello **World**")
    
    # 2. 模拟拖入文件
    window.on_files_dropped([test_file])
    assert window.btn_convert.isEnabled()
    
    # 3. 执行转换
    window.start_convert()
    with qtbot.waitSignal(window._worker.all_done, timeout=15000):
        pass
    
    # 4. 验证预览
    raw = window.preview.get_raw_markdown()
    assert "Hello" in raw
    
    # 5. 测试导出
    export_path = tmp_path / "output.md"
    # 模拟 QFileDialog
    window.export_markdown()  # 需要 mock file dialog
    
    # 6. 测试复制
    window.copy_markdown()
```

## 6. 性能测试

| 场景 | 指标 | 目标 |
|------|------|------|
| 单文件 TXT <1MB | 转换时间 | < 1s |
| 单文件 PDF <10MB | 转换时间 | < 3s |
| 批量 10 个文件 (混合) | 总时间 | < 30s |
| 大文件 PDF >50MB | 不崩溃 | 显示错误提示 |
| 应用启动 | 冷启动时间 | < 3s |
| 内存占用 | 空闲状态 | < 100MB |

## 7. 安全与错误处理测试

| 场景 | 期望行为 | 错误码 |
|------|----------|--------|
| 空文件 (0 byte) | 跳过，给出友好提示 | `E_FILE_002` |
| 超大文件 (>500MB) | 拒绝并提示文件过大 | `E_FILE_003` |
| 恶意文件名 (路径遍历) | 拒绝，不访问预期外路径 | `E_FILE_004` |
| 密码保护 PDF | 转换失败但 UI 友好提示 | `E_CONVERT_001` |
| 损坏的 Office 文档 | 转换失败，保留 traceback 到 crash.log | `E_CONVERT_002` |
| 拖入目录 | 递归展开所有支持文件 | (正常) |
| 拖入不支持格式 | 跳过，标"❌ 不支持" | `E_FILE_005` |
| 拖入音频 (mp3/wav) | v1.0 明确提示「v1.1+ 支持」 | `E_FILE_006` |
| 无效的 LLM API Key | 不记录日志，返回明确错误 | `E_INTERNAL_001` |
| 配置文件损坏 | 备份 .bak 后重置默认 | (启动恢复) |
| SQLite 损坏 | 备份 .bak 后重建空表 | (启动恢复) |
| 并发 100 个文件拖入 | UI 不冻结，最多处理前 N 个 | (节流) |

## 8. 测试夹具样本文件

```
tests/fixtures/
├── sample.txt           # 纯文本
├── sample.md            # Markdown
├── sample.pdf           # 简单 PDF
├── sample.docx          # Word 文档
├── sample.xlsx          # Excel 表格
├── sample.pptx          # PowerPoint
├── sample.html          # HTML 页面
├── sample.csv           # CSV 数据
├── sample.json          # JSON 数据
├── sample.zip           # ZIP 压缩包（含上述部分文件）
├── sample_dir/          # 目录样本（用于测试递归展开）
│   ├── a.pdf
│   └── subdir/
│       └── b.docx
├── empty.txt            # 空文件
├── large.txt            # 大文本文件 (5MB)
├── invalid.xyz          # 不支持格式
├── locked.pdf           # 被占用的 PDF (Windows 测试用)
└── corrupted.docx       # 损坏的 Word 文档 (用于 E_CONVERT_xxx 测试)
```

## 9. CI 集成

```yaml
# .github/workflows/ci.yml
# 每次 push/PR 自动运行：
# 1. ruff lint
# 2. pytest + pytest-qt + pytest-cov
# 3. PyInstaller build
```

## 10. 缺陷管理

- 使用 GitHub Issues 跟踪缺陷
- 标签：`bug`, `critical`, `enhancement`
- 每个版本发布前完成 P0/P1 缺陷修复
- 严重缺陷要求回归测试
