# 评估指南 / Evaluation Guide

> prompt-git-manager 评估功能完整参考

---

## 目录

- [概述](#概述)
- [基本用法](#基本用法)
- [命令参考](#命令参考)
- [数据集格式](#数据集格式)
- [评估指标](#评估指标)
- [阈值配置](#阈值配置)
- [评估算法](#评估算法)
- [自定义评估](#自定义评估)
- [CI 集成](#ci-集成)
- [最佳实践](#最佳实践)
- [故障排除](#故障排除)

---

## 概述

### 什么是评估

评估是比较两个 Prompt 版本在同一数据集上的表现差异，用于：
- 检测 Prompt 变更是否导致性能退化
- 量化改进效果
- 在合并前进行质量把关

### 评估流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  数据集      │     │  旧版本      │     │  新版本      │
│  (JSONL)    │     │  (HEAD)     │     │  (Working)  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   评估引擎       │
                  │                 │
                  │ 1. 渲染模板     │
                  │ 2. 关键词匹配   │
                  │ 3. 计算指标     │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   评估结果       │
                  │                 │
                  │ accuracy_delta  │
                  │ token_cost      │
                  │ consistency     │
                  │ passed (bool)   │
                  └─────────────────┘
```

### 评估模式

| 模式 | 说明 | 依赖 |
|------|------|------|
| 规则引擎（默认） | 基于关键词匹配 | 无外部依赖 |
| LLM 增强 | 使用 LLM 评判 | 需要 API Key |

---

## 基本用法

### 快速评估

```bash
# 最简单的评估
pg eval --dataset fixtures/dataset.jsonl

# 指定阈值
pg eval --dataset fixtures/dataset.jsonl --threshold 0.05

# JSON 输出
pg eval --dataset fixtures/dataset.jsonl --json
```

### 比较特定文件

```bash
# 比较两个文件（而非 HEAD vs Working）
pg eval --old .prompts/v1.yaml --new .prompts/v2.yaml -d data.jsonl
```

### 完整工作流

```bash
# 1. 创建数据集
cat > fixtures/dataset.jsonl << 'EOF'
{"input": "What is Python?", "expected_output": "Python is a programming language"}
{"input": "What is Git?", "expected_output": "Git is a version control system"}
EOF

# 2. 运行评估
pg eval --dataset fixtures/dataset.jsonl --threshold 0.05

# 3. 查看结果
# 如果通过：显示 PASSED
# 如果失败：显示 FAILED 并列出失败样本
```

---

## 命令参考

### 语法

```bash
pg eval [OPTIONS]
```

### 必填参数

| 参数 | 短选项 | 说明 |
|------|--------|------|
| `--dataset` | `-d` | 数据集文件路径（JSONL 格式） |

### 可选参数

| 参数 | 短选项 | 默认值 | 说明 |
|------|--------|--------|------|
| `--old` | | HEAD 版本 | 旧 Prompt 文件路径 |
| `--new` | | Working 版本 | 新 Prompt 文件路径 |
| `--threshold` | `-t` | `0.05` | 准确率下降阈值（0-1） |
| `--json` | `-j` | | JSON 格式输出 |

### 示例

```bash
# 基本评估
pg eval -d data.jsonl

# 自定义阈值
pg eval -d data.jsonl -t 0.10

# 比较特定文件
pg eval --old v1.yaml --new v2.yaml -d data.jsonl

# JSON 输出（用于 CI）
pg eval -d data.jsonl --json > result.json

# 组合使用
pg eval -d data.jsonl -t 0.03 --json | jq '.passed'
```

### 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 评估通过 |
| `2` | 评估失败（准确率下降超过阈值） |
| `1` | 参数错误 |
| `3` | 校验错误 |

---

## 数据集格式

### JSONL 格式

每行一个 JSON 对象：

```jsonl
{"input": "问题", "expected_output": "答案", "metadata": {}}
```

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `input` | string | 输入文本（用户问题） |
| `expected_output` | string | 期望输出（标准答案） |

### 可选字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `metadata` | object | 元数据（分类、难度等） |

### 示例数据集

```jsonl
{"input": "What is Python?", "expected_output": "Python is a programming language", "metadata": {"category": "definition", "difficulty": "easy"}}
{"input": "Explain the GIL", "expected_output": "The GIL prevents multiple threads from executing Python bytecode simultaneously", "metadata": {"category": "technical", "difficulty": "hard"}}
{"input": "", "expected_output": "I need a question to help you.", "metadata": {"category": "edge_case"}}
```

### 数据集管理

详见 [数据集指南](dataset-guide.md)。

---

## 评估指标

### accuracy_delta（准确率变化）

新版本与旧版本准确率的差值。

```
accuracy_delta = accuracy_new - accuracy_old
```

| 值 | 含义 |
|----|------|
| > 0 | 新版本更好 |
| = 0 | 无变化 |
| < 0 | 新版本更差 |

### token_cost_delta（Token 消耗变化）

新版本与旧版本 Token 消耗的相对变化。

```
token_cost_delta = (new_tokens - old_tokens) / old_tokens
```

| 值 | 含义 |
|----|------|
| > 0 | 新版本消耗更多 Token |
| = 0 | 无变化 |
| < 0 | 新版本消耗更少 Token |

### consistency_score（一致性分数）

两个版本在相同输入上产生相同结果的比例。

```
consistency_score = 相同结果数 / 总样本数
```

| 值 | 含义 |
|----|------|
| 1.0 | 完全一致 |
| 0.8+ | 高度一致 |
| 0.5-0.8 | 中等一致 |
| < 0.5 | 低一致性 |

### 结果示例

```json
{
  "total_samples": 20,
  "accuracy_old": 0.85,
  "accuracy_new": 0.80,
  "accuracy_delta": -0.05,
  "token_cost_old": 1250,
  "token_cost_new": 1180,
  "token_cost_delta": -0.056,
  "consistency_score": 0.75,
  "passed": true,
  "threshold": 0.05
}
```

---

## 阈值配置

### 阈值含义

阈值定义了允许的准确率下降幅度：

```
如果 accuracy_delta >= -threshold，则通过
```

### 阈值选择指南

| 场景 | 推荐阈值 | 说明 |
|------|---------|------|
| 金融/医疗 | 0.01-0.02 | 极严格 |
| 生产环境 | 0.03-0.05 | 严格 |
| 一般场景 | 0.05-0.10 | 标准 |
| 开发/实验 | 0.10-0.20 | 宽松 |

### 配置方式

**CLI 参数（优先级最高）：**
```bash
pg eval --dataset data.jsonl --threshold 0.10
```

**配置文件：**
```json
// .prompts/config.json
{
  "eval_threshold": 0.05
}
```

**环境变量：**
```bash
export PROMPT_GIT_THRESHOLD=0.10
```

---

## 评估算法

### 规则引擎（默认）

#### 渲染流程

```python
def rule_based_render(template, variables):
    # 1. 提取变量默认值
    merged_vars = {var: def.default for var, def in template.variables.items()}
    
    # 2. 合并传入变量
    merged_vars.update(variables)
    
    # 3. 替换 {{var}} 占位符
    result = template.user_template
    for var, value in merged_vars.items():
        result = result.replace(f"{{{{{var}}}}}", str(value))
    
    # 4. 组合 system_prompt
    return f"{template.system_prompt}\n\n{result}"
```

#### 关键词匹配

```python
def keyword_based_evaluate(rendered_prompt, expected_output):
    # 1. 提取期望输出的关键词
    expected_keywords = extract_keywords(expected_output)
    
    # 2. 检查 prompt 中是否包含这些关键词
    matched = {kw for kw in expected_keywords if kw in rendered_prompt.lower()}
    match_ratio = len(matched) / len(expected_keywords)
    
    # 3. 判断匹配程度
    if match_ratio >= 0.5:
        return expected_output, True   # 完全匹配
    elif match_ratio >= 0.2:
        return partial_output, False   # 部分匹配
    else:
        return "[no output]", False    # 无匹配
```

#### 关键词提取

```python
def extract_keywords(text):
    # 英文：提取 2+ 字符的单词
    english_words = set(re.findall(r"[a-z]{2,}", text.lower()))
    
    # 中文：提取 2-4 字符的片段
    chinese_chars = set(re.findall(r"[\u4e00-\u9fff]{2,4}", text))
    
    # 过滤停用词
    return {w for w in (english_words | chinese_chars) if w not in stop_words}
```

#### Token 估算

```python
def estimate_tokens(text):
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    ascii_count = len(text) - cjk_count
    
    # 启发式：英文 4 字符/token，中文 1.5 字符/token
    return int(ascii_count / 4 + cjk_count / 1.5)
```

### LLM 增强评估（可选）

使用 LLM 作为评判标准，提供更准确的评估结果。

#### 配置方式

**1. 环境变量配置（推荐）**

```bash
# OpenAI
export OPENAI_API_KEY="sk-your-key-here"
export OPENAI_API_BASE="https://api.openai.com/v1"  # 可选，默认值

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Ollama（本地模型）
export OLLAMA_API_BASE="http://localhost:11434"
```

**2. CLI 参数配置**

```bash
# 指定提供商和模型
pg eval --dataset data.jsonl --provider openai --model gpt-4

# 指定自定义 API Base（用于私有部署或代理）
pg eval --dataset data.jsonl --provider openai --model gpt-4 \
  --api-base "https://your-proxy.com/v1"

# 使用 Anthropic
pg eval --dataset data.jsonl --provider anthropic --model claude-3-opus-20240229

# 使用 Ollama 本地模型
pg eval --dataset data.jsonl --provider ollama --model llama2
```

**3. Python API 配置**

```python
from promptgit.llm_evaluator import get_llm_config, evaluate_prompts_with_llm

# 方式 1：自动从环境变量读取 API Key
config = get_llm_config(
    provider="openai",
    model="gpt-4"
)

# 方式 2：显式指定 API Key
config = get_llm_config(
    provider="openai",
    model="gpt-4",
    api_key="sk-your-key-here"
)

# 方式 3：自定义 API Base（私有部署、代理、本地模型）
config = get_llm_config(
    provider="openai",
    model="gpt-4",
    api_key="sk-your-key-here",
    api_base="https://your-proxy.com/v1"
)

# 方式 4：使用 Ollama 本地模型
config = get_llm_config(
    provider="ollama",
    model="llama2",
    api_base="http://localhost:11434"
)
```

#### 支持的提供商

| 提供商 | provider 参数 | 模型示例 | API Key 环境变量 |
|--------|--------------|----------|-----------------|
| OpenAI | `openai` | `gpt-4`, `gpt-3.5-turbo`, `gpt-4-turbo` | `OPENAI_API_KEY` |
| Anthropic | `anthropic` | `claude-3-opus-20240229`, `claude-3-sonnet-20240229` | `ANTHROPIC_API_KEY` |
| Ollama | `ollama` | `llama2`, `mistral`, `codellama` | 无需（本地） |
| Azure OpenAI | `azure` | `gpt-4`, `gpt-35-turbo` | `AZURE_API_KEY` |
| 其他 | LiteLLM 支持的任意提供商 | - | 视提供商而定 |

#### LLM-as-Judge 模式

使用 LLM 作为评判者，更准确地评估输出质量：

```bash
# 启用 LLM-as-judge
pg eval --dataset data.jsonl --provider openai --model gpt-4 --judge

# JSON 输出（用于 CI）
pg eval --dataset data.jsonl --provider openai --model gpt-4 --judge --json
```

**Judge 评分标准：**
- 1.0：完美匹配期望输出
- 0.8-0.9：高度匹配，细节略有不同
- 0.6-0.7：部分匹配，缺少关键信息
- 0.4-0.5：勉强相关，偏差较大
- 0.0-0.3：不相关或完全错误

#### 多模型对比

比较不同模型在同一数据集上的表现：

```bash
# 对比 GPT-3.5 和 GPT-4
pg eval --dataset data.jsonl --compare-models gpt-3.5-turbo,gpt-4

# 对比 OpenAI 和 Anthropic
pg eval --dataset data.jsonl --provider openai --compare-models gpt-4,claude-3-opus-20240229

# JSON 输出
pg eval --dataset data.jsonl --compare-models gpt-3.5-turbo,gpt-4 --json
```

**输出示例：**
```
┌──────────┬─────────────────┬─────────────────┬──────────┐
│ Sample   │ Score (gpt-3.5) │ Score (gpt-4)   │ Winner   │
├──────────┼─────────────────┼─────────────────┼──────────┤
│ Sample 1 │ 0.75            │ 0.92            │ gpt-4    │
│ Sample 2 │ 0.80            │ 0.85            │ gpt-4    │
│ Sample 3 │ 0.90            │ 0.88            │ gpt-3.5  │
└──────────┴─────────────────┴─────────────────┴──────────┘

Summary:
  gpt-3.5-turbo wins: 1
  gpt-4 wins: 2
  Ties: 0

Overall winner: gpt-4
```

#### 使用场景

| 场景 | 推荐配置 |
|------|---------|
| 快速验证 | 规则引擎（默认，无需 API） |
| 准确评估 | `--provider openai --model gpt-4` |
| 最高准确性 | `--provider openai --model gpt-4 --judge` |
| 成本敏感 | `--provider openai --model gpt-3.5-turbo` |
| 隐私敏感 | `--provider ollama --model llama2` |
| 模型选型 | `--compare-models model1,model2` |

#### 成本估算

| 模型 | 每 1000 样本估算成本 | 说明 |
|------|---------------------|------|
| gpt-3.5-turbo | ~$0.50 | 经济实惠 |
| gpt-4 | ~$10-30 | 高准确性 |
| claude-3-sonnet | ~$3 | Anthropic 中端 |
| claude-3-opus | ~$15-45 | Anthropic 高端 |
| Ollama (本地) | $0 | 需要本地 GPU |

**注意：** 实际成本取决于 prompt 长度和输出长度。上述为粗略估算。

---

## 自定义评估

### 自定义渲染函数

```python
from promptgit.evaluator import evaluate_prompts, rule_based_render

def custom_render(template, variables):
    """自定义渲染逻辑"""
    # 基础渲染
    rendered = rule_based_render(template, variables)
    
    # 添加自定义逻辑
    # 例如：调用 LLM、添加上下文等
    
    return rendered

# 使用自定义渲染
result = evaluate_prompts(
    old_template=old_template,
    new_template=new_template,
    dataset=dataset,
    threshold=0.05,
    render_fn=custom_render
)
```

### 自定义评估逻辑

```python
from promptgit.evaluator import EvalSample, SampleResult

def custom_evaluate(rendered_prompt, expected_output):
    """自定义评估逻辑"""
    # 例如：使用语义相似度而非关键词匹配
    from sentence_transformers import SentenceTransformer
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embedding1 = model.encode(rendered_prompt)
    embedding2 = model.encode(expected_output)
    
    similarity = cosine_similarity(embedding1, embedding2)
    return similarity > 0.8
```

### 批量评估

```python
from pathlib import Path
from promptgit.schema import PromptTemplate
from promptgit.evaluator import evaluate_prompts, load_dataset

# 加载数据集
dataset = load_dataset(Path("dataset.jsonl"))

# 评估多个版本
versions = ["v1.yaml", "v2.yaml", "v3.yaml"]
baseline = PromptTemplate.from_yaml(Path("baseline.yaml"))

results = []
for version in versions:
    template = PromptTemplate.from_yaml(Path(version))
    result = evaluate_prompts(baseline, template, dataset)
    results.append((version, result))

# 输出比较表
print(f"{'Version':<10} {'Accuracy':<10} {'Delta':<10} {'Status':<10}")
for version, result in results:
    status = "PASS" if result.passed else "FAIL"
    print(f"{version:<10} {result.accuracy_new:.1%}{'':<4} {result.accuracy_delta:+.1%}{'':<4} {status}")
```

---

## CI 集成

### GitHub Actions

```yaml
name: Prompt Guard

on:
  pull_request:
    paths:
      - '.prompts/**'

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install
        run: uv sync
      
      - name: Evaluate
        run: pg eval --dataset fixtures/dataset.jsonl --threshold 0.05
      
      - name: Comment on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: '❌ Prompt evaluation failed!'
            })
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: prompt-eval
        name: Prompt Evaluation
        entry: pg eval --dataset fixtures/dataset.jsonl --threshold 0.05
        language: system
        files: '\.prompts/.*\.ya?ml$'
        pass_filenames: false
```

### 多数据集评估

```yaml
# 评估多个数据集
jobs:
  evaluate:
    strategy:
      matrix:
        dataset:
          - qa.jsonl
          - code_gen.jsonl
          - ecommerce.jsonl
    steps:
      - run: pg eval --dataset fixtures/${{ matrix.dataset }}
```

---

## 最佳实践

### 1. 数据集设计

```jsonl
// 覆盖多样场景
{"input": "简单问题", "expected_output": "...", "metadata": {"difficulty": "easy"}}
{"input": "复杂问题", "expected_output": "...", "metadata": {"difficulty": "hard"}}
{"input": "边界情况", "expected_output": "...", "metadata": {"category": "edge"}}
{"input": "对抗输入", "expected_output": "...", "metadata": {"category": "adversarial"}}
```

### 2. 阈值选择

```bash
# 开发环境：宽松
pg eval -d data.jsonl -t 0.10

# 生产环境：严格
pg eval -d data.jsonl -t 0.03
```

### 3. 定期评估

```bash
# 每次 Prompt 变更后
pg diff --semantic && pg eval -d data.jsonl

# 定期完整评估
pg eval -d full_dataset.jsonl -t 0.05
```

### 4. 分析失败

```bash
# 查看失败详情
pg eval -d data.jsonl --json | jq '.details[] | select(.new_match == false)'
```

### 5. 记录基线

```bash
# 保存基线结果
pg eval -d data.jsonl --json > baseline.json

# 后续比较
pg eval -d data.jsonl --json | jq '.accuracy_delta'
```

---

## 故障排除

### Q: 评估失败怎么办？

**A:** 检查失败样本：
```bash
pg eval -d data.jsonl --json | jq '.details[] | select(.new_match == false)'
```

可能原因：
1. Prompt 变更导致关键行为改变
2. 数据集期望输出不准确
3. 阈值设置过严

### Q: 如何提高评估准确性？

**A:** 
1. 增加数据集样本数（推荐 20+）
2. 覆盖更多边界情况
3. 使用 LLM 增强评估

### Q: 评估结果不稳定？

**A:** 
1. 检查数据集是否有歧义样本
2. 降低温度参数（如果有）
3. 多次运行取平均值

### Q: 如何评估中文 Prompt？

**A:** 关键词提取已支持中文：
```jsonl
{"input": "什么是Python？", "expected_output": "Python是一种编程语言"}
```

### Q: 数据集格式错误？

**A:** 验证数据集：
```python
import json
with open("data.jsonl") as f:
    for i, line in enumerate(f, 1):
        try:
            json.loads(line)
        except json.JSONDecodeError as e:
            print(f"Line {i}: {e}")
```

---

## 相关文档

- [数据集指南](dataset-guide.md) - 创建评估数据集
- [配置详解](configuration.md) - 阈值配置
- [Python API](python-api.md) - 程序化评估
- [CLI 参考](cli_reference.md) - 命令行用法
- [故障排除](TROUBLESHOOTING.md) - 常见问题
