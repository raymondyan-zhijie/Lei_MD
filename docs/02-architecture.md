# Lei_MD 架构设计文档

> **品牌：** leimengde  
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
Lei_MD/
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
│       │   (JSON: %APPDATA%\Lei_MD\  │              │
│       └──────────────────────────────┘              │
│                                                     │
│       ┌──────────────────────────────┐              │
│       │    HistoryManager            │              │
│       │   (SQLite: %APPDATA%\Lei_MD\ │              │
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
| 配置存储 | **JSON** (`%APPDATA%\Lei_MD\config.json`) | 简单可读、易于备份、跨平台友好 |
| 历史存储 | **SQLite** (`%APPDATA%\Lei_MD\history.db`) | 轻量、支持查询、无需服务 |
| 预览渲染 | QTextBrowser + 自定义 Markdown→HTML | 避免引入 WebEngine (体积大) |
| 打包方案 | PyInstaller + NSIS | 生成独立 .exe + 标准安装包 |
| 版本策略 | SemVer (MAJOR.MINOR.PATCH) | 清晰传达变更影响 |

## 5. 安全考虑

- **输入验证**：限制文件大小上限 500MB，防止恶意大文件
- **路径安全**：输出文件写入前验证路径合法性（处理 Windows MAX_PATH 260 字符限制）
- **API 密钥**：LLM API Key 不记录日志，存储在 `%APPDATA%\Lei_MD\config.json`（用户目录权限）
- **子进程隔离**：转换在 QThread 中执行，异常不影响主程序
- **音频格式**：v1.0 **不支持** MP3/WAV/OGG/FLAC，UI 拖入时给出明确提示（计划 v1.1+ 离线实现）
- **离线运行**：安装后**不联网**，更新通过用户手动下载新安装包

## 6. 错误处理设计

### 6.1 错误分类（5 大类）

| 错误码前缀 | 类别 | 触发场景 | 用户体验 |
|------------|------|----------|----------|
| `E_FILE_xxx` | 文件级 | 文件不存在/被锁/0字节/格式损坏/超 500MB | UI 红条提示「该文件跳过」+ 继续处理其他 |
| `E_CONVERT_xxx` | 转换级 | MarkItDown 抛异常（密码保护 PDF、加密 Office） | 文件列表标 ❌ 失败，悬停看错误详情 |
| `E_SYS_xxx` | 系统级 | 磁盘满、权限不足、路径太长（Windows MAX_PATH 260） | 弹模态对话框 + "打开输出目录" 按钮 |
| `E_INTERNAL_xxx` | 内部级 | Python 异常、QThread crash | 写 `crash.log`，UI 友好提示「附日志发 issue」 |
| `E_UPDATE_xxx` | 更新级 | GitHub API 失败、checksum 不匹配、下载中断 | 不阻塞使用，更新页面显示失败原因 |

### 6.2 错误信息规范

**规则**：
- ❌ 永远不向用户显示 Python traceback
- ✅ 永远提供下一步可执行动作（「重试」/「跳过」/「打开日志」/「复制错误码」）
- 错误码示例：`E_FILE_001`「无法读取 test.pdf：文件被其他程序占用，请关闭后重试」

### 6.3 错误信息国际化

错误信息存放在 `src/resources/locales/errors.json`：

```json
{
  "E_FILE_001": {
    "zh_CN": "无法读取 {filename}：文件被其他程序占用",
    "en_US": "Cannot read {filename}: file is locked by another process"
  }
}
```

### 6.4 崩溃恢复

| 场景 | 策略 |
|------|------|
| 转换中途用户强关 | 下次启动检查 `%APPDATA%\Lei_MD\processing.lock`，清理未完成文件 |
| SQLite 历史损坏 | 启动时 `PRAGMA integrity_check`，坏则备份+重建 |
| 配置文件损坏 | 备份为 `config.json.bak`，重置为默认 |
