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

#### 规则引擎模式（默认）

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
                  │   规则引擎       │
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

#### LLM 增强模式

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
                  │   渲染模板       │
                  │                 │
                  │ 替换 {{变量}}   │
                  │ 组合 prompt     │
                  └────────┬────────┘
                           │
                           ▼
         ┌─────────────────┴─────────────────┐
         │                                   │
         ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│  旧版本 LLM     │                 │  新版本 LLM     │
│                 │                 │                 │
│ 调用 API 生成   │                 │ 调用 API 生成   │
│ 实际输出        │                 │ 实际输出        │
└────────┬────────┘                 └────────┬────────┘
         │                                   │
         └─────────────────┬─────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   比较输出       │
                  │                 │
                  │ vs 期望输出     │
                  │ 计算相似度      │
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

#### LLM-as-Judge 模式

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
                  │   渲染模板       │
                  └────────┬────────┘
                           │
                           ▼
         ┌─────────────────┴─────────────────┐
         │                                   │
         ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│  旧版本 LLM     │                 │  新版本 LLM     │
│  生成实际输出    │                 │  生成实际输出    │
└────────┬────────┘                 └────────┬────────┘
         │                                   │
         └─────────────────┬─────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   LLM Judge     │
                  │                 │
                  │ 评估输出质量    │
                  │ 给出 0-1 评分   │
                  │ 提供评分理由    │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   评估结果       │
                  │                 │
                  │ accuracy_delta  │
                  │ judge_scores    │
                  │ passed (bool)   │
                  └─────────────────┘
```

### 评估模式

| 模式 | 说明 | 依赖 |
|------|------|------|
| 规则引擎（默认） | 基于关键词匹配 | 无外部依赖 |
| LLM 增强 | 使用 LLM 生成输出并评估 | 需要 API Key |
| LLM-as-Judge | 使用 LLM 作为评判者 | 需要 API Key |

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

## 评估原理

### 三种评估模式对比

| 特性 | 规则引擎 | LLM 增强 | LLM-as-Judge |
|------|---------|----------|--------------|
| **输出生成** | 模拟（关键词匹配） | 真实 LLM 调用 | 真实 LLM 调用 |
| **评估方式** | 关键词匹配 | 文本相似度 | LLM 评分 |
| **准确性** | 低（启发式） | 中 | 高 |
| **速度** | 快（<1s） | 慢（10-60s） | 最慢（20-120s） |
| **成本** | 免费 | 按 token 计费 | 按 token 计费 x2 |
| **离线支持** | ✅ | ❌ | ❌ |
| **适用场景** | 快速验证、CI | 正式评估 | 精确评估 |

### 规则引擎原理

规则引擎通过启发式方法模拟 LLM 输出，不实际调用 API：

```python
# 1. 渲染模板
rendered_prompt = render_template(template, variables)

# 2. 提取期望输出的关键词
expected_keywords = extract_keywords(expected_output)
# 例如: "Python is a programming language" -> {"python", "programming", "language"}

# 3. 检查 prompt 中是否包含这些关键词
matched_keywords = {kw for kw in expected_keywords if kw in rendered_prompt.lower()}

# 4. 计算匹配率
match_ratio = len(matched_keywords) / len(expected_keywords)

# 5. 判断匹配程度
if match_ratio >= 0.5:
    return expected_output, True   # 完全匹配
elif match_ratio >= 0.2:
    return partial_output, False   # 部分匹配
else:
    return "[no output]", False    # 无匹配
```

**优点：**
- 无需 API 调用，完全离线
- 执行速度快（<1 秒）
- 结果确定性强

**缺点：**
- 无法真正评估 LLM 输出质量
- 依赖关键词匹配，可能误判
- 无法评估语义相似度

### LLM 增强评估原理

LLM 增强模式实际调用 LLM API 生成输出，然后与期望输出比较：

```python
# 1. 渲染模板
old_prompt = render_template(old_template, variables)
new_prompt = render_template(new_template, variables)

# 2. 调用 LLM API 生成输出
old_output = llm_api.call(old_template.system_prompt, old_prompt)
new_output = llm_api.call(new_template.system_prompt, new_prompt)

# 3. 与期望输出比较（使用文本相似度）
old_similarity = compute_similarity(old_output, expected_output)
new_similarity = compute_similarity(new_output, expected_output)

# 4. 判断是否匹配（阈值 0.7）
old_match = old_similarity >= 0.7
new_match = new_similarity >= 0.7
```

**相似度计算：**
```python
from difflib import SequenceMatcher

def compute_similarity(text1, text2):
    """计算两段文本的相似度（0-1）"""
    return SequenceMatcher(None, text1, text2).ratio()
```

**优点：**
- 真实评估 LLM 输出
- 能发现实际的性能差异
- 结果更可靠

**缺点：**
- 需要 API 调用，有成本
- 执行速度慢（取决于 API 响应）
- 受 LLM 随机性影响

### LLM-as-Judge 原理

LLM-as-Judge 使用另一个 LLM 来评判输出质量，提供更准确的评分：

```python
# 1. 渲染模板并生成输出（同 LLM 增强模式）
old_output = llm_api.call(old_template.system_prompt, old_prompt)
new_output = llm_api.call(new_template.system_prompt, new_prompt)

# 2. 使用 LLM 作为评判者
judge_prompt = f"""
You are an expert evaluator. Please evaluate the quality of the AI's response.

## Original Prompt
{rendered_prompt}

## Expected Output
{expected_output}

## Actual Output
{actual_output}

## Evaluation Criteria
1. Does the actual output convey the same meaning as the expected output?
2. Is the actual output factually accurate?
3. Is the actual output clear and well-structured?

## Response Format
Please respond with a JSON object containing:
- "score": a float between 0.0 and 1.0 (1.0 = perfect match)
- "reasoning": a brief explanation of your evaluation
"""

# 3. 调用 Judge LLM
judge_response = llm_api.call("You are an expert evaluator.", judge_prompt)
result = json.loads(judge_response)

# 4. 解析评分
score = result["score"]  # 0.0 - 1.0
reasoning = result["reasoning"]

# 5. 判断是否匹配（阈值 0.7）
is_match = score >= 0.7
```

**评分标准：**

| 分数 | 含义 | 说明 |
|------|------|------|
| 0.9-1.0 | 完美匹配 | 输出与期望几乎完全一致 |
| 0.8-0.9 | 高度匹配 | 核心信息一致，细节略有不同 |
| 0.6-0.8 | 部分匹配 | 包含关键信息，但缺少部分内容 |
| 0.4-0.6 | 勉强相关 | 有一定相关性，但偏差较大 |
| 0.0-0.4 | 不相关 | 输出与期望无关或完全错误 |

**优点：**
- 最准确的评估方式
- 能理解语义相似度
- 提供评分理由，便于分析

**缺点：**
- 成本最高（两次 API 调用）
- 执行速度最慢
- 评判标准可能因 LLM 而异

### 评估流程变化

使用 LLM 后，评估流程的主要变化：

| 阶段 | 规则引擎 | LLM 增强 | LLM-as-Judge |
|------|---------|----------|--------------|
| 1. 渲染模板 | ✅ 相同 | ✅ 相同 | ✅ 相同 |
| 2. 生成输出 | 模拟 | LLM API | LLM API |
| 3. 评估输出 | 关键词匹配 | 文本相似度 | LLM 评分 |
| 4. 计算指标 | ✅ 相同 | ✅ 相同 | ✅ 相同 |

**关键区别：**
- **步骤 2**：规则引擎模拟输出，LLM 模式实际调用 API
- **步骤 3**：规则引擎用关键词匹配，LLM 模式用相似度或 LLM 评分

### 选择建议

| 场景 | 推荐模式 | 原因 |
|------|---------|------|
| CI/CD 流水线 | 规则引擎 | 快速、免费、确定性强 |
| 开发阶段快速验证 | 规则引擎 | 即时反馈 |
| 正式评估前的预检 | LLM 增强 | 发现实际问题 |
| 最终发布前评估 | LLM-as-Judge | 最准确 |
| 模型选型对比 | LLM-as-Judge | 公平比较 |
| 成本敏感场景 | 规则引擎 | 零成本 |
| 隐私敏感场景 | 规则引擎 | 无需发送数据 |

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

# Azure OpenAI
export AZURE_API_KEY="your-azure-key"

# Ollama（本地/局域网部署）
export OLLAMA_API_KEY="your-key"                      # 可选，局域网认证时使用
export OLLAMA_API_BASE="http://localhost:11434"        # 默认值，局域网改为实际地址

# vLLM（本地/局域网部署）
export VLLM_API_KEY="your-key"                         # 可选，局域网认证时使用
export VLLM_API_BASE="http://localhost:8000/v1"        # 默认值，局域网改为实际地址

# SGLang（本地/局域网部署）
export SGLANG_API_KEY="your-key"                       # 可选，局域网认证时使用
export SGLANG_API_BASE="http://localhost:30000/v1"     # 默认值，局域网改为实际地址
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

# 方式 4：使用 Ollama 本地模型（默认 API Base: http://localhost:11434）
config = get_llm_config(
    provider="ollama",
    model="llama2"
)

# 方式 5：使用 vLLM 本地模型（默认 API Base: http://localhost:8000/v1）
config = get_llm_config(
    provider="vllm",
    model="meta-llama/Llama-2-7b-chat-hf"
)

# 方式 6：使用 SGLang 本地模型（默认 API Base: http://localhost:30000/v1）
config = get_llm_config(
    provider="sglang",
    model="Qwen/Qwen2-7B-Instruct"
)
```

#### evaluate_prompts_with_llm 使用示例

```python
from pathlib import Path
from promptgit.schema import PromptTemplate
from promptgit.evaluator import load_dataset
from promptgit.llm_evaluator import get_llm_config, evaluate_prompts_with_llm

# 1. 加载模板和数据集
old_template = PromptTemplate.from_yaml(Path("prompts/v1.yaml"))
new_template = PromptTemplate.from_yaml(Path("prompts/v2.yaml"))
dataset = load_dataset(Path("fixtures/dataset.jsonl"))

# 2. 创建 LLM 配置
config = get_llm_config("openai", "gpt-3.5-turbo")

# 方式 A：LLM 增强模式（使用文本相似度匹配）
result = evaluate_prompts_with_llm(
    old_template=old_template,
    new_template=new_template,
    dataset=dataset,
    llm_config=config,
    threshold=0.05,
    use_judge=False  # 默认值，使用相似度匹配
)

print(f"准确率变化: {result.accuracy_delta:+.1%}")
print(f"是否通过: {result.passed}")

# 方式 B：LLM-as-Judge 模式（使用同一个模型生成和评判）
result = evaluate_prompts_with_llm(
    old_template=old_template,
    new_template=new_template,
    dataset=dataset,
    llm_config=config,
    threshold=0.05,
    use_judge=True  # 启用 Judge 模式
)

# 方式 C：独立 Judge 模型（推荐：小模型生成，大模型评判）
gen_config = get_llm_config("openai", "gpt-3.5-turbo")
judge_config = get_llm_config("openai", "gpt-4")

result = evaluate_prompts_with_llm(
    old_template=old_template,
    new_template=new_template,
    dataset=dataset,
    llm_config=gen_config,
    threshold=0.05,
    use_judge=True,
    judge_config=judge_config  # 独立的 Judge 模型
)

# 访问 Judge 评分详情
for judge in result.judge_results:
    print(f"分数: {judge.score:.2f}, 理由: {judge.reasoning}")
```

#### 支持的提供商

| 提供商 | provider 参数 | 模型示例 | 默认 API Base | API Key 环境变量 |
|--------|--------------|----------|---------------|-----------------|
| OpenAI | `openai` | `gpt-4`, `gpt-3.5-turbo`, `gpt-4-turbo` | `https://api.openai.com/v1` | `OPENAI_API_KEY` |
| Anthropic | `anthropic` | `claude-3-opus-20240229`, `claude-3-sonnet-20240229` | - | `ANTHROPIC_API_KEY` |
| Azure OpenAI | `azure` | `gpt-4`, `gpt-35-turbo` | - | `AZURE_API_KEY` |
| Ollama | `ollama` | `llama2`, `mistral`, `codellama`, `qwen2` | `http://localhost:11434` | `OLLAMA_API_KEY`（可选，局域网认证） |
| vLLM | `vllm` | `meta-llama/Llama-2-7b-chat-hf`, `Qwen/Qwen2-7B-Instruct` | `http://localhost:8000/v1` | `VLLM_API_KEY`（可选，局域网认证） |
| SGLang | `sglang` | `meta-llama/Llama-2-7b-chat-hf`, `Qwen/Qwen2-7B-Instruct` | `http://localhost:30000/v1` | `SGLANG_API_KEY`（可选，局域网认证） |
| 其他 | LiteLLM 支持的任意提供商 | - | - | 视提供商而定 |

#### LLM-as-Judge 模式

使用 LLM 作为评判者，更准确地评估输出质量。

**重要：建议使用不同的模型进行生成和评判**

最佳实践是使用更强的模型作为 Judge，以避免自我偏见：

```bash
# 使用 gpt-3.5 生成输出，gpt-4 作为 Judge
pg eval --dataset data.jsonl \
  --provider openai --model gpt-3.5-turbo \
  --judge \
  --judge-provider openai --judge-model gpt-4

# 使用本地模型生成，云端模型作为 Judge
pg eval --dataset data.jsonl \
  --provider ollama --model llama2 \
  --judge \
  --judge-provider openai --judge-model gpt-4

# 使用同一个模型（不推荐，但可用于快速测试）
pg eval --dataset data.jsonl --provider openai --model gpt-4 --judge
```

**为什么需要不同的 Judge 模型？**

| 问题 | 说明 |
|------|------|
| 自我偏见 | LLM 可能倾向于给自己的输出打高分 |
| 盲点相似 | 同一模型可能忽略相同的错误模式 |
| 评估公平性 | 用更强的模型能更准确地评估弱模型 |

**推荐的 Judge 模型组合：**

| 生成模型 | 推荐 Judge | 原因 |
|----------|-----------|------|
| gpt-3.5-turbo | gpt-4 | GPT-4 更擅长发现错误 |
| llama2/mistral | gpt-4 或 claude-3 | 云端大模型更可靠 |
| gpt-4 | claude-3-opus | 不同厂商的视角 |
| claude-3-sonnet | claude-3-opus | 更强的同系列模型 |

**CLI 参数：**

| 参数 | 说明 |
|------|------|
| `--judge` | 启用 LLM-as-judge 模式 |
| `--judge-provider` | Judge 模型的提供商（可选，默认与主模型相同） |
| `--judge-model` | Judge 模型名称（可选，默认与主模型相同） |

**Judge 评分标准：**
- 1.0：完美匹配期望输出
- 0.8-0.9：高度匹配，细节略有不同
- 0.6-0.7：部分匹配，缺少关键信息
- 0.4-0.5：勉强相关，偏差较大
- 0.0-0.3：不相关或完全错误

#### 多模型对比

比较不同模型在同一数据集上的表现：

```bash
# 对比同一厂商的模型
pg eval --dataset data.jsonl --compare-models gpt-3.5-turbo,gpt-4

# 对比不同厂商的模型（使用 provider:model 格式）
pg eval --dataset data.jsonl --compare-models openai:gpt-4,anthropic:claude-3-opus-20240229

# 对比本地模型和云端模型
pg eval --dataset data.jsonl --compare-models ollama:llama2,openai:gpt-4

# 对比 vLLM 和 SGLang
pg eval --dataset data.jsonl --compare-models vllm:llama2,sglang:qwen2-7b

# JSON 输出
pg eval --dataset data.jsonl --compare-models openai:gpt-4,anthropic:claude-3-opus-20240229 --json
```

**模型格式说明：**

| 格式 | 示例 | 说明 |
|------|------|------|
| `model` | `gpt-4` | 使用默认 provider（需要指定 `--provider`） |
| `provider:model` | `openai:gpt-4` | 显式指定 provider |
| `provider:model` | `anthropic:claude-3-opus-20240229` | 不同厂商 |

**注意：** 对比不同厂商的模型时，必须使用 `provider:model` 格式，因为每个厂商的 API 地址和认证方式不同。

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
| 隐私敏感（简单） | `--provider ollama --model llama2` |
| 隐私敏感（高性能） | `--provider vllm --model meta-llama/Llama-2-7b-chat-hf` |
| 大规模推理 | `--provider sglang --model Qwen/Qwen2-7B-Instruct` |
| 模型选型 | `--compare-models model1,model2` |

#### 成本估算

| 模型 | 每 1000 样本估算成本 | 说明 |
|------|---------------------|------|
| gpt-3.5-turbo | ~$0.50 | 经济实惠 |
| gpt-4 | ~$10-30 | 高准确性 |
| claude-3-sonnet | ~$3 | Anthropic 中端 |
| claude-3-opus | ~$15-45 | Anthropic 高端 |
| Ollama (本地) | $0 | 需要本地 GPU |
| vLLM (本地) | $0 | 高性能推理，支持连续批处理 |
| SGLang (本地) | $0 | 高吞吐量，支持 RadixAttention |

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
