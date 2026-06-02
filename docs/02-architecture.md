# Lei_MD 架构设计文档

> 🌐 **Language**: **中文** | [English](02-architecture.en.md)

> **品牌：** leimengde  
> **版本：** 规划期快照（实际实施见 [CHANGELOG](../CHANGELOG.md)） | **日期：** 2026-06-01  
>  
> 本文档为**项目初始规划期**的原始快照。规划 vs v0.3.0 实际实施的对照表见 [IMPLEMENTATION_VS_PLAN.md](IMPLEMENTATION_VS_PLAN.md)。

> **SSOT 索引**：本文档是以下主题的**权威定义**：
> - §1 技术选型（PySide6 + 关键依赖）
> - §3 核心架构设计（线程模型、数据模型）
> - §6 错误处理设计（5 大类错误码体系）
>
> 其他文档出现相关主题时**引用本文档**，不再重复定义。

---

## 1. 技术选型

### 1.1 GUI 框架对比

| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| **PySide6 (Qt)** | 原生外观、拖拽支持好、组件丰富、文档全 | 打包体积 ~120MB | ✅ **首选** |
| Tkinter | Python 内置零依赖 | UI 丑、无现代控件 | ❌ |
| Dear PyGui | GPU 加速、颜值高 | 生态不成熟、打包复杂 | ❌ |
| Electron | 前端技术栈 | 体积 >200MB、Node 依赖重 | ❌ |
| WPF + Python.NET | 最原生 Windows | 技术栈割裂、调试困难 | ❌ |

**结论**：选择 **PySide6**，理由：
1. Qt 是业界最成熟的跨平台 GUI 框架
2. 原生支持文件拖拽、系统托盘、多线程
3. Qt Designer 可加速 UI 开发
4. PyInstaller 打包成熟

### 1.1.1 备选方案评估：QWebEngineView（待评估，v2.0+ 路线图）

> 用户反馈提到「评估引入 QWebEngineView 的可能性」。本节作为**技术雷达登记**，v1.0 不实施，v2.0+ 重新评估。

**QWebEngineView 是什么**：PySide6 自带的 Chromium 嵌入式组件，可渲染完整 HTML/CSS/JS（用于 Markdown 预览会更接近 GitHub 渲染效果）。

| 维度 | 当前方案 `QTextBrowser` | 备选 `QWebEngineView` |
|------|------------------------|----------------------|
| 渲染效果 | 基础 Markdown→HTML（无 JS、无复杂 CSS） | 完整 GitHub-Flavored Markdown 渲染 |
| 打包体积 | PySide6 基线 ~120MB | **+ 80-150MB**（Chromium 内核）→ 总 ~200-270MB |
| 启动时间 | < 1s | + 1-2s（Chromium 初始化） |
| 内存占用 | < 100MB | + 100-200MB |
| 安全风险 | 极低（仅本地 HTML） | **高**（Chromium 历史漏洞多；离线运行原则下需禁用网络，仍需关注渲染引擎 0day） |
| 维护成本 | 低 | 中（Chromium 版本对齐 PySide6 发布周期） |

**v1.0 决定**：**不引入**，保持 QTextBrowser。理由：
1. 违反 NF3「大而全单安装包 ~400-500MB」原则（再 + 100MB = 550-650MB）
2. 违反「完全离线运行」安全姿态（Chromium 即使禁用网络也是攻击面）
3. 当前 QTextBrowser + 自定义 Markdown→HTML 已能满足 80% 用户需求

**v2.0+ 重评估条件**：
- 大量用户反馈「Markdown 渲染效果差」（量化指标：>20% issue 标签 `rendering-quality`）
- PySide6 发布新版本将 QWebEngineView 体积优化至 < 50MB
- 用户接受更大的安装包换取完整 GitHub 渲染

详见 [05 §5.3 长期路线图](05-release-plan.md)。

### 1.2 技术栈总览

```
┌──────────────────────────────────────────────────┐
│                   用户界面层                       │
│  PySide6 (Qt6)  —  窗口 / 拖拽 / 预览 / 设置       │
├──────────────────────────────────────────────────┤
│                   业务逻辑层                       │
│  Python 3.10~3.13  —  转换编排 / 队列管理 / 历史记录    │
├──────────────────────────────────────────────────┤
│                   数据转换层                       │
│  MarkItDown  —  文件解析 / Markdown 生成           │
├──────────────────────────────────────────────────┤
│                   打包分发层                       │
│  PyInstaller  —  单文件 .exe / NSIS 安装包          │
└──────────────────────────────────────────────────┘
```

### 1.3 关键依赖

> 权威版本号与上限约束见 [`pyproject.toml`](../pyproject.toml)。本节仅列职责。

| 依赖 | 职责 |
|------|------|
| `markitdown[all]` | 核心转换引擎（20+ 格式） |
| `PySide6` | Qt6 GUI 框架 |
| `markdown` | Markdown 渲染（备选 QTextBrowser） |
| `Pygments` | 代码高亮（预览窗口） |
| `darkdetect` | Windows 深色模式检测 |

## 2. 项目结构

```
Lei_MD/
├── src/
│   ├── __init__.py
│   ├── main.py                 # 程序入口（v0.4.2 加 logging.basicConfig）
│   ├── app.py                  # QApplication 初始化
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py      # 主窗口
│   │   ├── drop_area.py        # 文件拖拽区域
│   │   ├── preview_panel.py    # Markdown 预览面板
│   │   ├── file_list.py        # 文件列表组件
│   │   ├── settings_dialog.py  # 设置对话框
│   │   ├── history_panel.py    # 历史记录面板
│   │   ├── i18n.py             # 国际化（v0.4.0 加）
│   │   └── styles.py           # QSS 样式表
│   ├── core/
│   │   ├── __init__.py
│   │   ├── converter.py        # 转换引擎封装
│   │   ├── worker.py           # 单文件转换 QThread（v0.4.2 P1 C1 顶层导入）
│   │   ├── batch_worker.py     # 批量转换工作线程（v0.4.2 P0 S3 加 wait_finished）
│   │   ├── history.py          # 历史记录管理（SQLite + WAL）
│   │   ├── config.py           # 配置管理（v0.4.2 P0 S2 max_history 上限 1000）
│   │   ├── errors.py           # 错误码体系（ConversionError / ErrorCode）
│   │   ├── supported.py        # 扩展名 SSOT（v0.4.2 P0 S1 从 drop_area 上提）
│   │   ├── file_item.py        # 文件项 dataclass（v0.4.2 P1 A1 实现）
│   │   └── youtube.py          # YouTube 字幕抓取（v0.4.0 Task 2.4）
│   └── resources/
│       ├── icons/              # 应用图标
│       ├── locales/            # 国际化文件 (zh_CN, en_US)
│       └── assets.qrc          # Qt 资源文件
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # pytest 全局 fixture（qapp offscreen 等）
│   ├── test_converter.py
│   ├── test_batch_worker.py
│   ├── test_config.py
│   ├── test_history.py        # SQLite 并发测试（WAL + Signal）
│   ├── test_ui/                # UI 自动化测试
│   └── fixtures/               # 测试用样本文件
├── scripts/
│   └── build-windows.ps1       # v0.4.1 一键 Windows 打包（PowerShell）
├── installer/
│   └── installer.nsi           # v0.4.1 NSIS 安装包脚本
├── Lei_MD.spec                 # v0.4.1 PyInstaller 配置
├── docs/
│   ├── 01-requirements.md      # 需求文档
│   ├── 02-architecture.md      # 本文件
│   ├── 03-development-plan.md  # 开发计划
│   ├── 04-testing-plan.md      # 测试计划
│   ├── 05-release-plan.md      # 发布与维护计划
│   └── 06-dependency-update-strategy.md  # 依赖更新策略（v1.0 后）
├── .github/
│   └── workflows/
│       ├── ci.yml              # CI: 测试 + 类型检查
│       └── release.yml         # CD: 自动打包发布
├── pyproject.toml              # 项目配置
├── requirements.txt            # 开发依赖
├── requirements-build.txt      # 打包依赖
├── CODE_OF_CONDUCT.md          # 社区行为准则
├── CHANGELOG.md                # 变更日志
├── CONTRIBUTING.md             # 贡献指南
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
│       │    config.json)              │
│       └──────────────────────────────┘              │
│                                                     │
│       ┌──────────────────────────────┐              │
│       │    HistoryManager            │              │
│       │   (SQLite: %APPDATA%\Lei_MD\ │              │
│       │    history.db)               │
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
  ├── 进度条更新
  └── HistoryManager 单例（**所有 SQLite 写操作**）

工作线程 (QThread)
  ├── ConverterWorker.run()
  ├── 调用 MarkItDown.convert()
  └── 通过 pyqtSignal 回传结果

批量模式:
  ├── 创建线程池 (QThreadPool)
  ├── 最多 4 个并行转换任务
  └── 结果按完成顺序回传（**不发 DB**，经 signal 回到主线程写）
```

#### 3.3.1 SQLite 并发策略（**WAL + Signal 串行化**）

**问题背景**：ConverterWorker 跑在 QThread 上，如果直接在同一连接上 `INSERT`，主线程同时 `SELECT`（历史面板刷新）会触发 `database is locked`（SQLite 写锁是数据库级，**所有读阻塞**）。

**解决方案 = WAL 模式 + Signal 写串行化（双保险）**：

| 机制 | 作用 | 缓解比例 |
|------|------|----------|
| **PRAGMA journal_mode=WAL** | 读写并发不再互斥（读者不阻塞写者，反之亦然） | ~90% lock 场景 |
| **`busy_timeout = 5000ms`** | 极端竞争下自动 retry 5s 而非立即抛异常 | ~9% 残余 |
| **所有写操作走 `pyqtSignal` → 主线程执行** | 写操作完全串行化（单写者），消除所有竞态 | 100% 消除已知竞态 |

**为什么双保险**：
- WAL 单独使用已经能解决 99% 场景，但**写者间仍可能短暂冲突**（WAL 模式下写者串行，但写+checkpoint 可能与读短暂互斥）
- Signal 串行化保证**逻辑上只有一个写者**（主线程），从源头消除竞态
- 两者结合：写者绝对无冲突 + 读者与写者完全并发

**实现要点**（详见 [03-development-plan.md](03-development-plan.md) 历史任务 1.9 段落）：

```python
# src/core/history.py
class HistoryManager(QObject):
    # Signal: ConverterWorker 在任何线程 emit，槽永远在主线程执行
    add_requested = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")     # 关键 1
        self._conn.execute("PRAGMA busy_timeout=5000")    # 关键 2
        self._conn.execute("PRAGMA synchronous=NORMAL")   # WAL 推荐
        # ...
        self.add_requested.connect(self._on_add)           # 关键 3

    def request_add(self, **kwargs):
        """线程安全入口：ConverterWorker 调这个，不直接写 DB"""
        self.add_requested.emit(kwargs)

    @pyqtSlot(dict)
    def _on_add(self, kwargs):
        """槽：永远在主线程执行，写 DB"""
        self._conn.execute("INSERT INTO history ...", ...)
        self._conn.commit()
        self._trim()
```

**性能验证**（04 §6 性能测试场景）：
- 批量 10 个文件转换，转换完成时主线程写 10 条历史 → 串行 10 次 INSERT < 5ms
- 用户拖动历史面板滚动 → 主线程读，不阻塞转换
- WAL 文件自动 checkpoint：WAL > 1000 pages 时自动触发（SQLite 默认）

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

# 配置 (JSON) — 需含 schema_version 字段以支持迁移
{
    "config_version": 1,             // 必填，ConfigManager 据此选择加载/迁移策略
    "output_dir": "same",            // same | custom_path
    "custom_output_dir": "",
    "auto_convert": true,            // 拖入后自动转换
    "max_history": 50,
    "language": "system",            // system | zh_CN | en_US
    "theme": "system",               // system | light | dark
    "llm": {
        "api_base": "",
        "api_key": "",               // 不记录日志；详见 02 §5 安全考虑
        "model": "gpt-4o"
    },
    "batch_concurrency": 4
}
```

### 3.4.1 config.json Schema 版本管理

**目标**：配置结构随版本迭代可能变化（新增/废弃/重命名字段），必须保证老用户的 `config.json` 不会因为升级而崩溃。

**Schema 版本约定**：

| 版本 | 范围 | 策略 |
|------|------|------|
| `config_version: 1` | v1.0 ~ v1.x | 基线版本，直接加载 |
| `config_version: 2+` | 未来 | 启动时检测 → 调用 `migrate(old_version, data)` 链式迁移 |
| 缺失字段 | 任何版本 | 视为 `config_version: 0`（v1.0 之前开发期）→ 用默认值补全 |

**迁移函数**（伪代码，详见 [03-development-plan.md](03-development-plan.md) 历史任务 1.8 段落）：

```python
# src/core/config.py
CONFIG_VERSION = 1
MIGRATIONS = {
    # 0 → 1: 添加 batch_concurrency 字段
    # 1 → 2: rename custom_output_dir → output_dir_custom（示例）
    # ...
}

def load_config(path: Path) -> dict:
    data = json.loads(path.read_text()) if path.exists() else {}
    version = data.get("config_version", 0)
    if version < CONFIG_VERSION:
        for old in range(version, CONFIG_VERSION):
            data = MIGRATIONS[old](data)        # 链式迁移
        data["config_version"] = CONFIG_VERSION
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    elif version > CONFIG_VERSION:
        # 新版应用读老配置文件 = 不应发生（用户降级）；备份 + 重置
        backup_corrupt_config(path)
        return DEFAULT_CONFIG
    return data
```

**保护策略**（与 [01 §5.1 E_INTERNAL_003](01-requirements.md) 异常场景对应）：
- 迁移前自动备份原文件为 `config.json.bak.{timestamp}`
- 迁移失败 → 记录 `crash.log` + 重置为默认值 + 通知用户
- 任何迁移都不删除用户原有数据，只**新增**字段和**重命名**字段

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

### 5.1 基本安全项（v1.0 必须）

- **输入验证**：限制文件大小上限 500MB，防止恶意大文件
- **路径安全**：输出文件写入前验证路径合法性（处理 Windows MAX_PATH 260 字符限制）；拒绝 `../` 路径遍历
- **API 密钥**：LLM API Key 不记录日志，存储在 `%APPDATA%\Lei_MD\config.json`（用户目录权限，仅当前用户可读）
- **子进程隔离**：转换在 QThread 中执行，异常不影响主程序
- **音频格式**：v1.0 **不支持** MP3/WAV/OGG/FLAC（[详见 01 F9a](01-requirements.md)，v1.1+ 离线实现）
- **离线运行**：安装后**不联网**，更新通过用户手动下载新安装包

### 5.2 临时文件清理（v1.0 必须）

MarkItDown 转换过程可能产生临时文件（如 PDF→图片→OCR 中间产物），如不清理会占用用户磁盘并泄露内容。

**策略**：
- 所有临时文件统一写入 `%TEMP%\Lei_MD\{session_id}\`
- 每次启动清理：删除 `>= 24 小时`未访问的临时目录
- 每次退出清理：删除当前 session 的临时目录
- 异常退出：下次启动按 24h 规则兜底清理
- 转换成功后立即清理该文件对应的临时目录

### 5.3 STRIDE 威胁模型（v1.0 三大关键威胁）

> 完整 STRIDE 6 维度分析见 [v2.0+ 路线图](#)；v1.0 只对实际威胁最大的 3 项做评估与缓解。

| STRIDE 维度 | 威胁场景 | 影响 | v1.0 缓解措施 | 残余风险 |
|------------|----------|------|---------------|----------|
| **S**poofing（伪装） | 攻击者替换 `Lei_MD.exe` 或劫持其依赖 DLL（Windows 路径劫持 / DLL 注入） | 恶意代码以 Lei_MD 身份执行 | v1.0 接受 SmartScreen 警告（**用户风险**，v1.1+ 评估 EV 代码签名证书）；安装包 SHA256 校验和发布在 GitHub Release | DLL 搜索顺序劫持 — v1.0 不防 |
| **T**ampering（篡改） | 攻击者篡改 `config.json` 注入恶意路径/API endpoint | 数据泄露或命令执行 | 配置文件存用户目录 + 仅当前用户可写；启动时 schema 校验（详见 §3.4.1） | 多用户共享电脑场景下不防 |
| **I**nformation Disclosure（信息泄露） | API Key 写到日志 / crash report / 转储文件 | 凭据泄露 | API Key 永远不写日志（自定义 log filter）；crash.log 自动 redact `api_key=` 字段；`%APPDATA%\Lei_MD\` 目录权限 `700` | 用户主动导出日志含 Key — 文档提示 |

**未在 v1.0 缓解的威胁**（v1.1+ 路线图）：
- **R**epudiation（抵赖）：转换操作审计日志 — v1.0 不实现
- **D**enial of Service（拒绝服务）：恶意大文件 / 大量并发 — v1.0 有 500MB 限制 + 4 并发上限，**基本缓解**
- **E**levation of Privilege（权限提升）：MarkItDown 库自身漏洞 — 依赖上游修复 + Dependabot 自动 PR

### 5.4 DLL 注入防护（v1.0 最小化）

Windows 特有风险：恶意程序可能通过搜索顺序劫持替换 `Qt6*.dll` / `python*.dll`。

**v1.0 缓解**：
- **PyInstaller `--onedir` 模式**（非 `--onefile`）：所有 DLL 在同目录，降低 `PATH` 劫持风险
- NSIS 安装包将 DLL 安装到 `%PROGRAMFILES%\Lei_MD\`（非 system32）
- 启动时 `os.add_dll_directory(app_dir)` 显式限定 DLL 搜索路径

**v1.0 不实现**（v1.1+ 评估）：
- 启用 WinVerifyTrust 签名校验（需要代码签名证书）
- 反调试 / 反注入检测（PyArmor 等工具，体积 + 50MB）

## 6. 错误处理设计

### 6.1 错误分类（5 大类）

**权威错误码 ID 列表**（与 [01 §5.1](01-requirements.md) 异常场景表一一对应）：

| 错误码 | 类别 | 触发场景 | 用户体验 |
|--------|------|----------|----------|
| `E_FILE_001` | 文件级 | 文件不存在/被锁/被拖入后删除 | UI 红条「该文件跳过」+ 悬停看详情 |
| `E_FILE_002` | 文件级 | 0 字节空文件 | UI 红条「文件为空，跳过」 |
| `E_FILE_003` | 文件级 | 超大文件 (>500MB) | 拒绝 + 提示「文件超出 500MB 限制」 |
| `E_FILE_004` | 文件级 | 路径遍历 / 非法文件名 | 拒绝 + 提示「非法文件名」 |
| `E_FILE_005` | 文件级 | 不支持格式 (`.xyz` 等) | 拒绝 + 提示「暂不支持此格式（v1.0 支持 20+ 格式，详见 01 F2）」 |
| `E_FILE_006` | 文件级 | 拖入音频 (mp3/wav) | 明确提示「音频转录 v1.1+ 支持，详见 01 F9a」 |
| `E_CONVERT_001` | 转换级 | 密码保护 PDF / 加密 Office | 文件列表标 ❌ + 提示「文件受密码保护，暂不支持」 |
| `E_CONVERT_002` | 转换级 | 文件格式损坏 (docx 实际 zip 损坏等) | 文件列表标 ❌ + 提示「文件已损坏，无法解析」 |
| `E_SYS_001` | 系统级 | 转换中用户强关 | 下次启动检查 `processing.lock` 清理未完成文件 |
| `E_SYS_002` | 系统级 | 输出路径不可写 (磁盘满/权限不足) | 弹模态对话框 + 「打开输出目录」按钮 |
| `E_SYS_003` | 系统级 | 路径超 Windows MAX_PATH 260 | 自动检测并尝试 `\\?\` 前缀；仍失败则报错 |
| `E_INTERNAL_001` | 内部级 | 转换引擎 Python traceback | 捕获后不退出 + UI 红条 + 写 `crash.log` |
| `E_INTERNAL_002` | 内部级 | SQLite 历史数据库损坏 | 下次启动检测 → 备份原文件 + 重建空库 |
| `E_INTERNAL_003` | 内部级 | config.json 损坏 | 下次启动检测 → 备份原文件 + 重置默认值 |
| `E_UPDATE_001` | 更新级 | 更新文件下载中断 / 校验失败 | 保留旧版本 + 提示重试 |
| `E_UPDATE_002` | 更新级 | 应用内「检查更新」网络失败 | 静默忽略 + 状态栏提示「无法连接服务器」 |

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
