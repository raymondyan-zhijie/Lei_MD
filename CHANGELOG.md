# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 项目初始化：文档驱动的完整规划
  - 需求文档 (`docs/01-requirements.md`)
  - 架构设计文档 (`docs/02-architecture.md`)
  - 开发计划 (`docs/03-development-plan.md`)，含 15 个具体任务
  - 测试计划 (`docs/04-testing-plan.md`)
  - 发布与维护计划 (`docs/05-release-plan.md`)
  - 依赖更新策略 (`docs/06-dependency-update-strategy.md`)
- 项目骨架: `pyproject.toml`, `.gitignore`, `LICENSE`, `README.md`, `CONTRIBUTING.md`
- 社区准则: `CODE_OF_CONDUCT.md` (Contributor Covenant v2.0)
- 错误处理设计：5 大类错误码体系（E_FILE/E_CONVERT/E_SYS/E_INTERNAL/E_UPDATE）
- 配置路径：统一到 `%APPDATA%\Lei_MD\`（Windows）+ `~/.config/Lei_MD/`（v2.0+ 跨平台）
- 离线 + 大而全 + 传统安装包路线（400-500MB 单安装包）
- 应用内「检查更新」+ GitHub Releases 主渠道
- SemVer + Dependabot 自动依赖更新策略
