# prompt-git

<p align="center">
  <strong>Git 原生的 Prompt 版本控制与 CI 防退化工具</strong>
</p>

<p align="center">
  <a href="#安装">安装</a> •
  <a href="#快速开始">快速开始</a> •
  <a href="#命令">命令</a> •
  <a href="#ci-集成">CI 集成</a> •
  <a href="#贡献">贡献</a> •
  <a href="./README.md">English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/tests-passing-brightgreen.svg" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-74%25-yellow.svg" alt="Coverage">
</p>

---

## 为什么需要 prompt-git？

### 问题所在

Prompt 工程对 AI 应用至关重要，但管理 Prompt 的方式却混乱不堪：

- 🔀 **没有版本控制**：Prompt 散落在代码、文档和聊天记录中
- 📊 **没有指标**：无法衡量变更是提升还是降低了性能
- 🚫 **没有防护**：破坏性变更未经检测就上线
- 🔍 **没有 Diff 工具**：文本 Diff 对结构化 Prompt 毫无意义

### 解决方案

**prompt-git** 将软件工程最佳实践引入 Prompt 管理：

| 功能 | 传统方式 | prompt-git |
|------|---------|------------|
| 版本控制 | 文档中复制粘贴 | Git 原生提交 |
| 变更检测 | 人工审查 | 语义 Diff |
| 质量门禁 | 听天由命 | 自动化评估 |
| 回滚 | "之前的 prompt 是什么？" | `git checkout` |

### 核心优势

- **零基础设施**：无需服务器、数据库或 SaaS 依赖
- **Git 原生**：Prompt 即文件，版本即提交
- **CI 优先**：专为 GitHub Actions、pre-commit 和 PR 工作流设计
- **离线可用**：无需 LLM API 也能工作（基于规则的评估）

---

## 安装

### 使用 uv（推荐）

```bash
uv pip install prompt-git
```

### 使用 pip

```bash
pip install prompt-git
```

### 从源码安装

```bash
git clone https://github.com/yourusername/prompt-git.git
cd prompt-git
uv sync
```

### 验证安装

```bash
pg --version
# prompt-git 0.1.0
```

---

## 快速开始

### 1. 初始化项目

```bash
cd your-project
pg init
```

这将创建：
```
.prompts/
├── config.json      # 项目配置
└── .gitignore       # 内部文件
```

### 2. 添加 Prompt

```bash
# 创建 prompt 文件
cat > qa_prompt.yaml << 'EOF'
name: qa-assistant
version: "1.0.0"
system_prompt: "你是一个有帮助的助手。"
user_template: "回答：{{question}}"
variables:
  question:
    type: string
    default: "什么是 Python？"
constraints:
  - 简洁明了
  - 使用示例
metadata:
  author: your-name
EOF

# 添加到版本追踪
pg add qa_prompt.yaml
```

### 3. 提交变更

```bash
pg commit -m "初始 QA prompt"
```

### 4. 查看变更

```bash
# 修改 prompt...
vim .prompts/qa_prompt.yaml

# 查看语义 diff
pg diff --semantic
```

### 5. 数据集评估

```bash
# 创建测试数据集
cat > fixtures/dataset.jsonl << 'EOF'
{"input": "什么是 Python？", "expected_output": "Python 是一种编程语言"}
{"input": "什么是 Git？", "expected_output": "Git 是一个版本控制系统"}
EOF

# 运行评估
pg eval --dataset fixtures/dataset.jsonl --threshold 0.05
```

---

## 命令

### `pg init`

在仓库中初始化 prompt-git。

```bash
pg init [--dry-run]
```

### `pg add`

添加 prompt 文件到版本追踪。

```bash
pg add <file> [--dry-run]
```

**支持格式：** YAML (.yaml, .yml), JSON (.json)

**必填字段：**
- `name`：Prompt 标识符
- `system_prompt`：系统消息
- `user_template`：用户消息模板，支持 `{{variables}}`

### `pg commit`

提交 prompt 变更并记录结构化元数据。

```bash
pg commit -m "message" [--dry-run]
```

**生成提交记录：**
```json
{
  "hash": "abc123",
  "timestamp": "2024-01-15T10:30:00",
  "changed_files": [".prompts/qa_prompt.yaml"],
  "validation_status": "pass",
  "message": "更新 QA prompt"
}
```

### `pg diff`

显示 Prompt 版本之间的差异。

```bash
pg diff [file] [--semantic] [--json]
```

**语义分析：**
- 变量变更（`{{old_var}}` → `{{new_var}}`）
- 约束变更（添加/删除规则）
- 语气偏移（正式 ↔ 随意）
- 角色偏移（助手人设变更）

**风险等级：**
- 🟢 **低风险**：小幅变更，无语义影响
- 🟡 **中风险**：约束或语气变更
- 🔴 **高风险**：角色或变量删除

### `pg eval`

对数据集评估 Prompt。

```bash
pg eval --dataset <file.jsonl> [--threshold 0.05] [--json]
```

**数据集格式：**
```jsonl
{"input": "问题", "expected_output": "答案", "metadata": {}}
```

**指标：**
- `accuracy_delta`：准确率变化（-1 到 +1）
- `token_cost_delta`：Token 消耗变化
- `consistency_score`：版本间一致性（0-1）

### `pg ci init`

生成 CI/CD 配置文件。

```bash
pg ci init [--dry-run]
```

**生成文件：**
- `.github/workflows/prompt-guard.yml` - GitHub Actions 工作流
- `.pre-commit-config.yaml` - Pre-commit 钩子
- `scripts/bump_version.sh` - 版本管理脚本

---

## CI 集成

### GitHub Actions

#### 自动配置

```bash
pg ci init
```

#### 手动配置

创建 `.github/workflows/prompt-guard.yml`：

```yaml
name: Prompt Guard

on:
  pull_request:
    paths:
      - '.prompts/**'

jobs:
  prompt-guard:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: 安装 prompt-git
        run: pip install prompt-git

      - name: 运行 diff
        run: pg diff --semantic --json > diff.json

      - name: 运行评估
        run: pg eval --dataset fixtures/dataset.jsonl --threshold 0.05

      - name: 评论 PR
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const diff = fs.readFileSync('diff.json', 'utf8');
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: `## ❌ Prompt Guard 失败\n\n\`\`\`json\n${diff}\n\`\`\``
            });
```

### Pre-commit 钩子

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: prompt-diff
        name: Prompt Diff 检查
        entry: pg diff --fail-on=high
        language: system
        files: '\.prompts/.*\.ya?ml$'
        pass_filenames: false
```

安装钩子：
```bash
pre-commit install
```

### 本地 CI 脚本

```bash
#!/bin/bash
# scripts/ci_check.sh

set -e

echo "运行 Prompt 检查..."

# 运行 diff
pg diff --semantic --json > diff.json

# 运行评估
pg eval --dataset fixtures/dataset.jsonl --threshold 0.05 --json > eval.json

echo "所有检查通过！"
```

---

## 配置

### 项目配置

`.prompts/config.json`：
```json
{
  "version": "0.1.0",
  "eval_threshold": 0.05,
  "model_provider": "openai",
  "default_model": "gpt-3.5-turbo",
  "auto_validate": true
}
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PROMPT_GIT_MODEL` | 评估用 LLM 模型 | `none` |
| `PROMPT_GIT_THRESHOLD` | 默认评估阈值 | `0.05` |
| `OPENAI_API_KEY` | OpenAI API 密钥 | - |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | - |

---

## 性能基准

### 响应时间

| 操作 | 耗时 | 说明 |
|------|------|------|
| `pg init` | <100ms | 创建目录结构 |
| `pg add` | <200ms | 验证 + 复制文件 |
| `pg commit` | <500ms | Git 提交 + 记录 |
| `pg diff` | <300ms | 结构化 Diff 分析 |
| `pg eval`（20 样本） | <1s | 基于规则的评估 |
| `pg eval`（100 样本） | <5s | 基于规则的评估 |

### 测试覆盖

| 模块 | 覆盖率 |
|------|--------|
| cli.py | 42% |
| schema.py | 90% |
| diff_engine.py | 90% |
| evaluator.py | 99% |
| ci_gen.py | - |
| **总计** | **74%** |

### 测试数量

| 测试套件 | 测试数 |
|---------|--------|
| test_cli.py | 14 |
| test_diff.py | 29 |
| test_eval.py | 33 |
| test_ci_gen.py | 40+ |
| **总计** | **116+** |

---

## 架构

```
prompt-git/
├── src/promptgit/
│   ├── __init__.py          # 版本号
│   ├── cli.py               # Typer CLI 入口
│   ├── schema.py            # Pydantic 模型
│   ├── diff_engine.py       # 语义 Diff 引擎
│   ├── evaluator.py         # 数据集评估
│   ├── ci_gen.py            # CI/CD 生成器
│   └── utils.py             # Git + Rich 工具函数
├── tests/
│   ├── conftest.py          # Fixtures
│   ├── test_cli.py
│   ├── test_diff.py
│   ├── test_eval.py
│   └── test_ci_gen.py
├── fixtures/
│   ├── dataset.jsonl        # 测试数据集
│   └── prompts/             # 边界用例 Prompt
├── examples/
│   ├── customer_service.yaml
│   ├── code_generation.yaml
│   └── data_extraction.yaml
├── docs/
│   ├── cli_reference.md
│   └── architecture.md
└── .github/
    └── workflows/
        ├── prompt-guard.yml
        └── publish.yml
```

---

## 贡献

### 开发环境搭建

```bash
# 克隆仓库
git clone https://github.com/yourusername/prompt-git.git
cd prompt-git

# 安装开发依赖
uv sync --extra dev

# 运行测试
uv run pytest

# 运行覆盖率报告
uv run pytest --cov=promptgit --cov-report=html
```

### 代码风格

- Python 3.10+，使用类型注解
- Pydantic 用于数据验证
- Typer 用于 CLI
- Rich 用于终端输出
- pytest 用于测试

### Pull Request 流程

1. Fork 仓库
2. 创建功能分支（`git checkout -b feature/amazing-feature`）
3. 提交变更（`git commit -m '添加新功能'`）
4. 推送到分支（`git push origin feature/amazing-feature`）
5. 创建 Pull Request

### 运行检查

```bash
# 类型检查
uv run mypy src/

# 代码检查
uv run ruff check src/

# 格式化
uv run ruff format src/

# 运行所有测试
uv run pytest -v
```

### 发布

```bash
# 版本号递增
./scripts/bump_version.sh patch  # 或 minor, major

# 推送标签
git push && git push --tags

# GitHub Action 会自动发布到 PyPI
```

---

## gh CLI 快速提 PR 演示

### 创建包含 Prompt 变更的 PR

```bash
# 1. 创建功能分支
git checkout -b feature/update-qa-prompt

# 2. 修改 prompt
vim .prompts/qa_prompt.yaml

# 3. 使用 prompt-git 提交
pg commit -m "提升 QA prompt 准确率"

# 4. 推送分支
git push -u origin feature/update-qa-prompt

# 5. 使用 gh CLI 创建 PR
gh pr create \
  --title "提升 QA prompt 准确率" \
  --body "$(cat <<'EOF'
## 概述
- 更新系统提示词以更好地理解上下文
- 在用户模板中添加 few-shot 示例
- 调整约束以获得更一致的输出

## Prompt Diff
$(pg diff --semantic)

## 评估结果
$(pg eval --dataset fixtures/dataset.jsonl --json)

## 检查清单
- [x] 语义 diff 已审查
- [x] 评估通过（阈值：5%）
- [ ] 团队审查
EOF
)"

# 6. 查看 PR
gh pr view --web
```

### 检查 PR 状态

```bash
# 列出打开的 PR
gh pr list

# 查看特定 PR
gh pr view 42

# 检查 CI 状态
gh pr checks 42

# 准备好后合并
gh pr merge 42 --squash
```

---

## 常见问题

### Q: 为什么不用 Langfuse/Weights & Biases？

**A：** 那些是优秀的运行时监控工具。prompt-git 专注于**开发时**工作流：
- Git 原生（无需学习新工具）
- CI 优先（部署前捕获问题）
- 零基础设施（无需维护服务器）

### Q: 可以用于私有 Prompt 吗？

**A：** 当然！Prompt 保存在你的私有 Git 仓库中。除非启用 LLM 评估，否则不会向外部发送数据。

### Q: 基于规则的评估如何工作？

**A：** 在没有 LLM API 的情况下，我们使用关键词匹配和文本相似度作为启发式方法。准确度较低但：
- 可离线工作
- 无 API 成本
- 执行快速
- 结果确定

### Q: 支持哪些 Prompt 格式？

**A：** YAML 和 JSON，结构如下：
```yaml
name: string           # 必填
version: string        # 可选
system_prompt: string  # 必填
user_template: string  # 必填，支持 {{variables}}
variables: {}          # 可选
constraints: []        # 可选
metadata: {}           # 可选
```

---

## 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE)

---

## 致谢

- [Typer](https://typer.tiangolo.com/) - CLI 框架
- [Pydantic](https://docs.pydantic.dev/) - 数据验证
- [GitPython](https://gitpython.readthedocs.io/) - Git 集成
- [Rich](https://rich.readthedocs.io/) - 终端格式化

---

<p align="center">
  为 AI 工程社区用心打造 ❤️
</p>
