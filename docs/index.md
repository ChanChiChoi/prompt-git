# prompt-git-manager 文档目录

> 完整的文档导航

---

## 📚 文档列表

### 核心文档

| 文档 | 说明 | 适合人群 |
|------|------|---------|
| [快速开始](quickstart.md) | 5 分钟上手指南 | 新用户 |
| [CLI 参考](cli_reference.md) | 所有命令详解 | 日常使用 |
| [Prompt Schema](prompt-schema.md) | Prompt 文件格式规范 | 编写 Prompt |
| [评估指南](evaluation.md) | 评估功能完整参考 | 质量保证 |
| [配置详解](configuration.md) | 配置文件完整参考 | 配置调整 |

### 开发文档

| 文档 | 说明 | 适合人群 |
|------|------|---------|
| [Python API](python-api.md) | Python 代码调用 | 程序化使用 |
| [架构文档](architecture.md) | 内部实现原理 | 贡献者/深度用户 |
| [数据集指南](dataset-guide.md) | 创建评估数据集 | 评估功能 |

### 指南文档

| 文档 | 说明 | 适合人群 |
|------|------|---------|
| [最佳实践](best-practices.md) | Prompt 管理建议 | 所有用户 |
| [迁移指南](migration.md) | 从其他工具迁移 | 迁移用户 |
| [故障排除](TROUBLESHOOTING.md) | 常见问题解决 | 遇到问题时 |
| [代码逻辑](code_logic.md) | 代码实现全览（内部参考） | 贡献者 |

### 项目文档

| 文档 | 说明 | 适合人群 |
|------|------|---------|
| [贡献指南](../CONTRIBUTING.md) | 如何参与开发 | 贡献者 |
| [更新日志](../CHANGELOG.md) | 版本变更记录 | 所有用户 |
| [路线图](roadmap.md) | 发展规划 | 关注未来 |
| [安全策略](../SECURITY.md) | 漏洞报告流程 | 安全研究 |

---

## 🚀 快速导航

### 我是新用户

1. [安装指南](quickstart.md#1-安装)
2. [初始化项目](quickstart.md#2-初始化项目)
3. [创建第一个 Prompt](quickstart.md#3-创建-prompt-文件)
4. [数据集评估](quickstart.md#7-数据集评估)

### 我想了解命令

- [pg init](cli_reference.md#pg-init) - 初始化项目
- [pg add](cli_reference.md#pg-add) - 添加 Prompt
- [pg commit](cli_reference.md#pg-commit) - 提交变更
- [pg diff](cli_reference.md#pg-diff) - 查看差异
- [pg eval](cli_reference.md#pg-eval) - 评估 Prompt
- [pg ci init](cli_reference.md#pg-ci-init) - 生成 CI 配置

### 我想编写 Prompt

- [文件格式](prompt-schema.md#文件格式) - YAML/JSON 格式
- [字段说明](prompt-schema.md#字段说明) - 必填/可选字段
- [变量定义](prompt-schema.md#变量定义) - 如何使用变量
- [约束语法](prompt-schema.md#约束语法) - 如何定义约束

### 我想创建数据集

- [数据集格式](dataset-guide.md#数据集格式) - JSONL 格式
- [样本结构](dataset-guide.md#样本结构) - 字段定义
- [边界样本](dataset-guide.md#边界样本) - 测试边界情况
- [对抗样本](dataset-guide.md#对抗样本) - 测试安全性

### 我想了解评估

- [评估概述](evaluation.md#概述) - 什么是评估
- [基本用法](evaluation.md#基本用法) - 快速开始
- [评估指标](evaluation.md#评估指标) - 指标详解
- [阈值配置](evaluation.md#阈值配置) - 如何设置阈值
- [自定义评估](evaluation.md#自定义评估) - 扩展评估逻辑

### 我想集成到 CI/CD

- [GitHub Actions 集成](cli_reference.md#github-actions)
- [Pre-commit 钩子](cli_reference.md#pre-commit-hooks)
- [配置详解](configuration.md#ci-配置)

### 我想用 Python 调用

- [Schema API](python-api.md#schema-api) - 数据模型
- [Diff Engine API](python-api.md#diff-engine-api) - Diff 功能
- [Evaluator API](python-api.md#evaluator-api) - 评估功能

### 我遇到了问题

- [安装问题](TROUBLESHOOTING.md#installation-issues)
- [Git 问题](TROUBLESHOOTING.md#git-related-issues)
- [验证错误](TROUBLESHOOTING.md#prompt-validation-errors)
- [评估问题](TROUBLESHOOTING.md#evaluation-issues)
- [CI 问题](TROUBLESHOOTING.md#cicd-integration-issues)

### 我想深入了解

- [系统概述](architecture.md#系统概述)
- [模块架构](architecture.md#模块架构)
- [数据模型](architecture.md#数据模型)
- [核心算法](architecture.md#核心算法)
- [数据流动](architecture.md#数据流动)

### 我想贡献代码

- [开发环境](../CONTRIBUTING.md#开发环境)
- [代码规范](../CONTRIBUTING.md#代码规范)
- [提交规范](../CONTRIBUTING.md#提交规范)
- [PR 流程](../CONTRIBUTING.md#pull-request-流程)

---

## 📖 示例

| 示例 | 说明 |
|------|------|
| [E-commerce 工作流](../examples/ecommerce/) | 完整的电商客服 Prompt 开发流程 |
| [基础 Prompt 模板](../examples/) | 客服/代码生成/数据抽取场景 |

---

## 🔗 外部链接

- [GitHub 仓库](https://github.com/ChanChiChoi/prompt-git-manager)
- [PyPI 包](https://pypi.org/project/prompt-git-manager/)
- [问题反馈](https://github.com/ChanChiChoi/prompt-git-manager/issues)
- [功能讨论](https://github.com/ChanChiChoi/prompt-git-manager/discussions)

---

## 📝 文档贡献

发现文档问题？欢迎提交 PR！

```bash
# 克隆仓库
git clone https://github.com/ChanChiChoi/prompt-git-manager.git

# 编辑文档
vim docs/quickstart.md

# 提交更改
git add docs/
git commit -m "docs: improve quickstart guide"
git push
```

---

## 📊 文档统计

| 类别 | 数量 |
|------|------|
| 核心文档 | 5 |
| 开发文档 | 3 |
| 指南文档 | 4 |
| 项目文档 | 4 |
| **总计** | **16** |
