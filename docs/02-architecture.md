# MarkItDown-GUI 架构设计文档

> **版本：** v0.1.0 | **日期：** 2026-06-01

---

## 1. 技术选型

### 1.1 GUI 框架对比

| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| **PySide6 (Qt)** | 原生外观、拖拽支持好、组件丰富、文档全 | 打包体积 ~80MB | ✅ **首选** |
| Tkinter | Python 内置零依赖 | UI 丑、无现代控件 | ❌ |
| Dear PyGui | GPU 加速、颜值高 | 生态不成熟、打包复杂 | ❌ |
| Electron | 前端技术栈 | 体积 >200MB、Node 依赖重 | ❌ |
| WPF + Python.NET | 最原生 Windows | 技术栈割裂、调试困难 | ❌ |

**结论**：选择 **PySide6**，理由：
1. Qt 是业界最成熟的跨平台 GUI 框架
2. 原生支持文件拖拽、系统托盘、多线程
3. Qt Designer 可加速 UI 开发
4. PyInstaller 打包成熟

### 1.2 技术栈总览

```
┌──────────────────────────────────────────────────┐
│                   用户界面层                       │
│  PySide6 (Qt6)  —  窗口 / 拖拽 / 预览 / 设置       │
├──────────────────────────────────────────────────┤
│                   业务逻辑层                       │
│  Python 3.10+  —  转换编排 / 队列管理 / 历史记录    │
├──────────────────────────────────────────────────┤
│                   数据转换层                       │
│  MarkItDown  —  文件解析 / Markdown 生成           │
├──────────────────────────────────────────────────┤
│                   打包分发层                       │
│  PyInstaller  —  单文件 .exe / NSIS 安装包          │
└──────────────────────────────────────────────────┘
```

### 1.3 关键依赖

```
markitdown[all]>=0.1.0       # 核心转换引擎
PySide6>=6.7                  # Qt GUI 框架
markdown>=3.6                 # Markdown 渲染 (非必须，可用 QTextBrowser)
Pygments>=2.18                # 代码高亮 (预览窗口)
darkdetect>=0.8               # Windows 深色模式检测
```

## 2. 项目结构

```
markitdown-gui/
├── src/
│   ├── __init__.py
│   ├── main.py                 # 程序入口
│   ├── app.py                  # QApplication 初始化
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py      # 主窗口
│   │   ├── drop_area.py        # 文件拖拽区域
│   │   ├── preview_panel.py    # Markdown 预览面板
│   │   ├── file_list.py        # 文件列表组件
│   │   ├── settings_dialog.py  # 设置对话框
│   │   ├── history_panel.py    # 历史记录面板
│   │   └── styles.py           # QSS 样式表
│   ├── core/
│   │   ├── __init__.py
│   │   ├── converter.py        # 转换引擎封装
│   │   ├── batch_worker.py     # 批量转换工作线程
│   │   ├── history.py          # 历史记录管理
│   │   └── config.py           # 配置管理
│   └── resources/
│       ├── icons/              # 应用图标
│       ├── locales/            # 国际化文件 (zh_CN, en_US)
│       └── assets.qrc          # Qt 资源文件
├── tests/
│   ├── __init__.py
│   ├── test_converter.py
│   ├── test_batch_worker.py
│   ├── test_config.py
│   ├── test_ui/                # UI 自动化测试
│   └── fixtures/               # 测试用样本文件
├── scripts/
│   ├── build.py                # PyInstaller 打包脚本
│   ├── installer.nsi            # NSIS 安装包脚本
│   └── bump_version.py         # 版本号管理
├── docs/
│   ├── 01-requirements.md      # 需求文档
│   ├── 02-architecture.md      # 本文件
│   ├── 03-development-plan.md  # 开发计划
│   ├── 04-testing-plan.md      # 测试计划
│   └── 05-release-plan.md      # 发布与维护计划
├── .github/
│   └── workflows/
│       ├── ci.yml              # CI: 测试 + 类型检查
│       └── release.yml         # CD: 自动打包发布
├── pyproject.toml              # 项目配置
├── requirements.txt            # 开发依赖
├── requirements-build.txt      # 打包依赖
├── LICENSE                     # MIT
└── README.md                   # 项目说明
```

## 3. 核心架构设计

### 3.1 组件交互图

```
┌─────────────────────────────────────────────────────┐
│                    MainWindow                        │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ DropArea │  │  PreviewPanel │  │  FileList    │   │
│  │ (拖入文件)│  │  (Markdown   │  │  (待转换列表) │   │
│  │          │  │   渲染预览)    │  │              │   │
│  └────┬─────┘  └──────▲───────┘  └──────┬───────┘   │
│       │               │                 │           │
│       └───────┬───────┴─────────────────┘           │
│               │  信号/槽 (Qt Signals)                │
│       ┌───────▼──────────────────────┐              │
│       │      ConverterWorker         │              │
│       │   (QThread 后台转换线程)       │              │
│       └───────────┬──────────────────┘              │
│                   │                                 │
│       ┌───────────▼──────────────────┐              │
│       │    MarkItDown Engine          │              │
│       │   markitdown.MarkItDown()     │              │
│       └──────────────────────────────┘              │
│                                                     │
│       ┌──────────────────────────────┐              │
│       │    ConfigManager             │              │
│       │   (QSettings / JSON 配置)     │              │
│       └──────────────────────────────┘              │
│                                                     │
│       ┌──────────────────────────────┐              │
│       │    HistoryManager            │              │
│       │   (SQLite 本地历史记录)        │              │
│       └──────────────────────────────┘              │
└─────────────────────────────────────────────────────┘
```

### 3.2 核心流程

```
[用户拖入文件] → [格式检测] → [显示文件列表]
                                    │
                    [点击"开始转换" / 自动开始]
                                    │
                    [ConverterWorker 启动]
                                    │
                    [MarkItDown.convert()]
                                    │
                    [返回 Markdown 文本]
                                    │
                    [更新预览面板] ← [写入历史记录]
                                    │
                    [用户导出/复制]
```

### 3.3 线程模型

```
主线程 (GUI Thread)
  ├── UI 渲染、事件处理
  ├── 预览更新（频率限制 100ms）
  └── 进度条更新

工作线程 (QThread)
  ├── ConverterWorker.run()
  ├── 调用 MarkItDown.convert()
  └── 通过 pyqtSignal 回传结果

批量模式:
  ├── 创建线程池 (QThreadPool)
  ├── 最多 4 个并行转换任务
  └── 结果按完成顺序回传
```

### 3.4 数据模型

```python
# 文件项
@dataclass
class FileItem:
    path: Path
    format: str          # 检测到的格式: pdf, docx, pptx...
    size: int            # 文件大小 (bytes)
    status: str          # pending / converting / done / error
    result: str = ""     # 转换后的 Markdown 文本
    error: str = ""      # 错误信息
    duration: float = 0  # 转换耗时 (秒)

# 历史记录 (SQLite)
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,
    source_format TEXT,
    output_path TEXT,
    markdown_length INTEGER,
    duration_ms INTEGER,
    success BOOLEAN,
    error_msg TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# 配置 (JSON)
{
    "output_dir": "same",           // same | custom_path
    "custom_output_dir": "",
    "auto_convert": true,           // 拖入后自动转换
    "max_history": 50,
    "language": "system",           // system | zh_CN | en_US
    "theme": "system",              // system | light | dark
    "llm": {
        "api_base": "",
        "api_key": "",
        "model": "gpt-4o"
    },
    "batch_concurrency": 4
}
```

## 4. 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| GUI 框架 | PySide6 | 原生控件、拖拽支持、成熟生态 |
| 配置存储 | JSON 文件 (~/.markitdown-gui/) | 简单可读、易于备份 |
| 历史存储 | SQLite | 轻量、支持查询、无需服务 |
| 预览渲染 | QTextBrowser + 自定义 Markdown→HTML | 避免引入 WebEngine (体积大) |
| 打包方案 | PyInstaller + NSIS | 生成独立 .exe + 标准安装包 |
| 版本策略 | SemVer (MAJOR.MINOR.PATCH) | 清晰传达变更影响 |

## 5. 安全考虑

- **输入验证**：限制文件大小上限 500MB，防止恶意大文件
- **路径安全**：输出文件写入前验证路径合法性
- **API 密钥**：LLM API Key 不记录日志，存储在本地 JSON（用户目录）
- **子进程隔离**：转换在子线程中执行，异常不影响主程序
