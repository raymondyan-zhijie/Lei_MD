# 贡献指南

感谢你对 MarkItDown-GUI 的关注！

## 开发环境

```bash
git clone https://github.com/raymondyan/markitdown-gui.git
cd markitdown-gui
pip install -e ".[dev]"
```

## 代码风格

- 遵循 [PEP 8](https://peps.python.org/pep-0008/)
- 使用 `ruff` 自动格式化: `ruff check src/ tests/`
- 类型注解: 所有公共函数需要类型注解
- 命名: 类名 PascalCase, 函数/变量 snake_case

## 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/):

| 前缀 | 用途 |
|------|------|
| `feat:` | 新功能 |
| `fix:` | 缺陷修复 |
| `docs:` | 文档更新 |
| `style:` | 代码格式化 |
| `refactor:` | 重构 |
| `test:` | 测试相关 |
| `chore:` | 构建/工具 |

示例: `feat: add YouTube URL conversion support`

## 开发流程

1. **Fork** 本仓库
2. **创建分支**: `git checkout -b feat/my-feature`
3. **编写测试**: 先写失败的测试
4. **实现功能**: 写最小代码让测试通过
5. **运行测试**: `pytest tests/ -v`
6. **代码检查**: `ruff check src/ tests/`
7. **提交**: `git commit -m "feat: my feature description"`
8. **推送**: `git push origin feat/my-feature`
9. **创建 PR**: 在 GitHub 上打开 Pull Request

## PR 要求

- [ ] 包含相关测试
- [ ] 所有测试通过
- [ ] Ruff 检查通过
- [ ] 更新文档（如需要）
- [ ] 提供清晰的 PR 描述

## 项目结构

```
src/ui/          — GUI 组件 (PySide6)
src/core/        — 业务逻辑
tests/           — 测试代码
docs/            — 项目文档
scripts/         — 构建脚本
```

## 问题反馈

使用 GitHub Issues 报告问题，请提供：
- MarkItDown-GUI 版本号
- Windows 版本
- 复现步骤
- 截图或日志
