# 配置详解

> prompt-git-manager 配置文件完整参考

---

## 目录

- [项目配置](#项目配置)
- [环境变量](#环境变量)
- [CI 配置](#ci-配置)
- [Pre-commit 配置](#pre-commit-配置)
- [评估配置](#评估配置)

---

## 项目配置

### config.json

位于 `.prompts/config.json`，存储项目级配置。

```json
{
  "version": "0.1.0",
  "created_at": "2026-05-04T10:30:00",
  "eval_threshold": 0.05,
  "model_provider": "openai",
  "default_model": "gpt-3.5-turbo",
  "auto_validate": true,
  "commit_hooks": true
}
```

### 配置项说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `version` | string | `"0.1.0"` | 配置版本 |
| `created_at` | string | 当前时间 | 创建时间（ISO 8601） |
| `eval_threshold` | float | `0.05` | 评估阈值（0-1） |
| `model_provider` | string | `"none"` | LLM 提供商 |
| `default_model` | string | - | 默认模型 |
| `auto_validate` | bool | `true` | 添加时自动验证 |
| `commit_hooks` | bool | `true` | 启用提交钩子 |

### eval_threshold 详解

评估阈值控制允许的准确率下降幅度：

```json
{
  "eval_threshold": 0.05  // 允许准确率下降 5%
}
```

| 阈值 | 严格度 | 适用场景 |
|------|--------|---------|
| 0.01 | 极严格 | 金融、医疗等关键场景 |
| 0.03 | 严格 | 生产环境 |
| 0.05 | 标准 | 一般场景（默认） |
| 0.10 | 宽松 | 开发/实验环境 |
| 0.20 | 很宽松 | 快速迭代 |

### model_provider 选项

| 提供商 | 说明 | 需要 API Key |
|--------|------|-------------|
| `none` | 不使用 LLM（默认） | 否 |
| `openai` | OpenAI GPT | 是 |
| `anthropic` | Anthropic Claude | 是 |
| `local` | 本地模型 | 否 |

---

## 环境变量

### 环境变量列表

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PROMPT_GIT_MODEL` | LLM 模型 | `none` |
| `PROMPT_GIT_THRESHOLD` | 评估阈值 | `0.05` |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `OPENAI_API_BASE` | OpenAI API Base URL | `https://api.openai.com/v1` |
| `ANTHROPIC_API_KEY` | Anthropic API Key | - |
| `OLLAMA_API_BASE` | Ollama API Base URL | `http://localhost:11434` |

### 设置方式

**Linux/macOS:**
```bash
# 临时设置
export PROMPT_GIT_THRESHOLD=0.10

# 永久设置（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export PROMPT_GIT_THRESHOLD=0.10' >> ~/.bashrc
```

**Windows:**
```powershell
# 临时设置
$env:PROMPT_GIT_THRESHOLD=0.10

# 永久设置
[System.Environment]::SetEnvironmentVariable("PROMPT_GIT_THRESHOLD", 0.10, "User")
```

**.env 文件:**
```bash
# 创建 .env 文件
PROMPT_GIT_MODEL=gpt-3.5-turbo
PROMPT_GIT_THRESHOLD=0.05
OPENAI_API_KEY=sk-xxx
```

### 优先级

配置优先级（从高到低）：
1. CLI 参数（`--threshold 0.10`）
2. 环境变量（`PROMPT_GIT_THRESHOLD=0.10`）
3. 配置文件（`config.json` 中的 `eval_threshold`）
4. 默认值（`0.05`）

---

## CI 配置

### CIConfig

CI 生成器的配置对象。

```python
from promptgit.ci_gen import CIConfig

config = CIConfig(
    # 触发设置
    branches=["main", "dev", "release/*"],
    paths=[".prompts/**", "datasets/**"],
    
    # 评估设置
    dataset_path="fixtures/dataset.jsonl",
    threshold=0.05,
    model_provider="openai",
    model_name="gpt-3.5-turbo",
    
    # Workflow 设置
    python_version="3.10",
    concurrency_group="prompt-guard-${{ github.ref }}",
    cancel_in_progress=True,
    
    # 功能开关
    enable_diff=True,
    enable_eval=True,
    comment_on_failure=True,
    upload_artifact=True
)
```

### 配置项说明

#### 触发设置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `branches` | list[str] | `["main", "dev"]` | 触发的分支 |
| `paths` | list[str] | `[".prompts/**"]` | 触发的路径 |

#### 评估设置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `dataset_path` | str | `"fixtures/dataset.jsonl"` | 数据集路径 |
| `threshold` | float | `0.05` | 评估阈值 |
| `model_provider` | str | `"none"` | LLM 提供商 |
| `model_name` | str | `"gpt-3.5-turbo"` | 模型名称 |

#### Workflow 设置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `python_version` | str | `"3.10"` | Python 版本 |
| `concurrency_group` | str | `"prompt-guard-${{ github.ref }}"` | 并发组 |
| `cancel_in_progress` | bool | `true` | 取消进行中的任务 |

#### 功能开关

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable_diff` | bool | `true` | 启用 diff |
| `enable_eval` | bool | `true` | 启用评估 |
| `comment_on_failure` | bool | `true` | 失败时评论 PR |
| `upload_artifact` | bool | `true` | 上传产物 |

### 配置文件方式

创建 `ci_config.json`：

```json
{
  "branches": ["main", "release/*"],
  "paths": [".prompts/**"],
  "dataset_path": "fixtures/dataset.jsonl",
  "threshold": 0.05,
  "model_provider": "openai",
  "model_name": "gpt-4",
  "enable_diff": true,
  "enable_eval": true
}
```

使用配置文件：

```bash
pg ci init --config ci_config.json
```

或 Python API：

```python
from promptgit.ci_gen import init_ci
from pathlib import Path

files = init_ci(config_path=Path("ci_config.json"))
```

---

## Pre-commit 配置

### PreCommitConfig

```python
from promptgit.ci_gen import PreCommitConfig

config = PreCommitConfig(
    diff_fail_on="high",        # 失败级别: low/med/high
    enable_eval=False,          # 是否启用评估
    dataset_path="fixtures/dataset.jsonl"  # 数据集路径
)
```

### 配置项说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `diff_fail_on` | str | `"high"` | 触发失败的风险级别 |
| `enable_eval` | bool | `false` | 是否运行评估 |
| `dataset_path` | str | `"fixtures/dataset.jsonl"` | 数据集路径 |

### diff_fail_on 选项

| 值 | 说明 |
|----|------|
| `low` | 任何变更都失败 |
| `med` | 中等及以上风险失败 |
| `high` | 仅高风险失败（默认） |

### 生成的配置

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: prompt-diff
        name: Prompt Diff Check
        entry: pg diff --fail-on=high
        language: system
        files: '\.prompts/.*\.ya?ml$'
        pass_filenames: false
```

---

## LLM 配置

### 概述

prompt-git-manager 支持使用 LLM 进行增强评估，通过 LiteLLM 实现多提供商支持。

### 配置方式

#### 1. CLI 参数（优先级最高）

```bash
# 指定提供商和模型
pg eval --dataset data.jsonl --provider openai --model gpt-4

# 指定自定义 API Base
pg eval --dataset data.jsonl --provider openai --model gpt-4 \
  --api-base "https://your-proxy.com/v1"
```

#### 2. 环境变量

```bash
# OpenAI
export OPENAI_API_KEY="sk-your-key-here"
export OPENAI_API_BASE="https://api.openai.com/v1"  # 可选

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Ollama（本地模型）
export OLLAMA_API_BASE="http://localhost:11434"
```

#### 3. Python API

```python
from promptgit.llm_evaluator import get_llm_config, evaluate_prompts_with_llm

# 方式 1：自动从环境变量读取 API Key
config = get_llm_config(
    provider="openai",
    model="gpt-4"
)

# 方式 2：显式指定所有参数
config = get_llm_config(
    provider="openai",
    model="gpt-4",
    api_key="sk-your-key-here",
    api_base="https://api.openai.com/v1"
)

# 方式 3：使用 Ollama 本地模型
config = get_llm_config(
    provider="ollama",
    model="llama2",
    api_base="http://localhost:11434"
)

# 运行评估
result = evaluate_prompts_with_llm(
    old_template=old_template,
    new_template=new_template,
    dataset=dataset,
    config=config,
    use_judge=True  # 启用 LLM-as-judge
)
```

### 支持的提供商

| 提供商 | provider 参数 | 环境变量 | 示例模型 |
|--------|--------------|----------|----------|
| OpenAI | `openai` | `OPENAI_API_KEY` | `gpt-4`, `gpt-3.5-turbo` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | `claude-3-opus-20240229` |
| Ollama | `ollama` | 无需 | `llama2`, `mistral` |
| Azure OpenAI | `azure` | `AZURE_API_KEY` | `gpt-4` |

### 自定义 API Base

对于私有部署、代理或本地模型，需要指定自定义 API Base：

```bash
# 使用代理
pg eval --dataset data.jsonl --provider openai --model gpt-4 \
  --api-base "https://your-proxy.com/v1"

# 使用 Ollama 本地模型
pg eval --dataset data.jsonl --provider ollama --model llama2 \
  --api-base "http://localhost:11434"

# 使用 Azure OpenAI
pg eval --dataset data.jsonl --provider azure --model gpt-4 \
  --api-base "https://your-resource.openai.azure.com"
```

### LLM-as-Judge 模式

使用 LLM 作为评判者，更准确地评估输出质量：

```bash
# 启用 LLM-as-judge
pg eval --dataset data.jsonl --provider openai --model gpt-4 --judge
```

**评分标准：**
- 1.0：完美匹配
- 0.8-0.9：高度匹配
- 0.6-0.7：部分匹配
- 0.4-0.5：勉强相关
- 0.0-0.3：不相关

### 多模型对比

比较不同模型的表现：

```bash
# 对比 GPT-3.5 和 GPT-4
pg eval --dataset data.jsonl --compare-models gpt-3.5-turbo,gpt-4
```

### 成本控制

| 模型 | 每 1000 样本估算成本 |
|------|---------------------|
| gpt-3.5-turbo | ~$0.50 |
| gpt-4 | ~$10-30 |
| claude-3-sonnet | ~$3 |
| claude-3-opus | ~$15-45 |
| Ollama (本地) | $0 |

### 故障排除

**问题：API Key 未找到**
```
解决方案：设置环境变量或在 CLI 中显式指定
```

**问题：连接超时**
```
解决方案：检查 API Base URL 是否正确，或使用代理
```

**问题：模型不存在**
```
解决方案：检查模型名称是否正确，参考提供商文档
```

---

## 评估配置

### 评估阈值设置

**CLI 方式：**
```bash
pg eval --dataset data.jsonl --threshold 0.10
```

**Python API：**
```python
from promptgit.evaluator import evaluate_prompts

result = evaluate_prompts(
    old_template=old_template,
    new_template=new_template,
    dataset=dataset,
    threshold=0.10  # 10% 阈值
)
```

**配置文件：**
```json
{
  "eval_threshold": 0.10
}
```

### 自定义渲染函数

```python
from promptgit.evaluator import evaluate_prompts

def llm_render(template, variables):
    """使用 LLM 渲染"""
    # 调用 LLM API
    response = call_llm_api(template, variables)
    return response

result = evaluate_prompts(
    old_template=old_template,
    new_template=new_template,
    dataset=dataset,
    threshold=0.05,
    render_fn=llm_render  # 传入自定义渲染函数
)
```

---

## GitHub Actions 配置

### 完整 Workflow 示例

```yaml
name: Prompt Guard

on:
  pull_request:
    branches: [main, develop]
    paths:
      - '.prompts/**'
      - 'fixtures/**'

permissions:
  contents: read
  pull-requests: write

concurrency:
  group: prompt-guard-${{ github.ref }}
  cancel-in-progress: true

env:
  EVAL_THRESHOLD: 0.05
  DATASET_PATH: fixtures/dataset.jsonl

jobs:
  prompt-guard:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      
      - name: Install dependencies
        run: uv sync
      
      - name: Run diff
        run: pg diff --semantic --json > diff.json
      
      - name: Run evaluation
        run: pg eval --dataset ${{ env.DATASET_PATH }} --threshold ${{ env.EVAL_THRESHOLD }}
        continue-on-error: true
      
      - name: Comment PR
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            // PR 评论脚本
```

### Secrets 配置

在 GitHub 仓库中设置 Secrets：

1. 进入仓库 Settings → Secrets and variables → Actions
2. 添加以下 Secrets：

| Name | Value |
|------|-------|
| `OPENAI_API_KEY` | `sk-xxx` |
| `PYPI_API_TOKEN` | `pypi-xxx` |

### Environment 配置

创建 Environment（用于 PyPI 发布）：

1. 进入仓库 Settings → Environments
2. 创建 `pypi` 环境
3. 配置保护规则（如需要审批）

---

## 最佳实践

### 1. 阈值选择

```bash
# 开发环境：宽松
pg eval --dataset data.jsonl --threshold 0.10

# 测试环境：标准
pg eval --dataset data.jsonl --threshold 0.05

# 生产环境：严格
pg eval --dataset data.jsonl --threshold 0.03
```

### 2. 分支策略

```json
{
  "branches": ["main", "release/*"]
}
```

- `main`：主分支，必须通过检查
- `release/*`：发布分支，严格检查
- `develop`：开发分支，可选检查

### 3. 数据集组织

```
fixtures/
├── dataset.jsonl           # 主数据集
├── datasets/
│   ├── qa.jsonl           # QA 场景
│   ├── code_gen.jsonl     # 代码生成
│   └── ecommerce.jsonl    # 电商场景
└── edge_cases.jsonl       # 边界用例
```

---

## 相关文档

- [快速开始](quickstart.md) - 5 分钟上手
- [CLI 参考](cli_reference.md) - 命令详解
- [Prompt Schema](prompt-schema.md) - 文件格式
- [数据集指南](dataset-guide.md) - 创建数据集
