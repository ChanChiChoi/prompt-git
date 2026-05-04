# Python API 文档

> 使用 Python 代码调用 prompt-git-manager 功能

---

## 目录

- [安装](#安装)
- [Schema API](#schema-api)
- [Diff Engine API](#diff-engine-api)
- [Evaluator API](#evaluator-api)
- [CI Generator API](#ci-generator-api)
- [完整示例](#完整示例)

---

## 安装

```bash
pip install prompt-git-manager
```

或

```bash
uv add prompt-git-manager
```

---

## Schema API

### PromptTemplate

Prompt 模板的数据模型。

```python
from promptgit.schema import PromptTemplate

# 从 YAML 文件加载
template = PromptTemplate.from_yaml("path/to/prompt.yaml")

# 访问字段
print(template.name)           # str
print(template.version)        # str
print(template.system_prompt)  # str
print(template.user_template)  # str
print(template.variables)      # dict
print(template.constraints)    # list
print(template.metadata)       # dict
```

### 从字典创建

```python
from promptgit.schema import PromptTemplate

data = {
    "name": "test-prompt",
    "version": "1.0.0",
    "system_prompt": "You are a helpful assistant.",
    "user_template": "Answer: {{question}}",
    "variables": {
        "question": {"type": "string", "default": "What is Python?"}
    },
    "constraints": ["Be concise"],
    "metadata": {"author": "test"}
}

template = PromptTemplate.model_validate(data)
```

### CommitRecord

提交记录模型。

```python
from promptgit.schema import CommitRecord
from datetime import datetime

record = CommitRecord(
    hash="abc123def456",
    timestamp=datetime.now(),
    changed_files=[".prompts/qa.yaml"],
    validation_status="pass",
    message="Update QA prompt"
)

# 序列化为 JSON
json_str = record.model_dump_json()
```

---

## Diff Engine API

### diff_prompts

比较两个 prompt 文件的差异。

```python
from pathlib import Path
from promptgit.diff_engine import diff_prompts

# 比较两个文件
result = diff_prompts(
    old_path=Path("old_prompt.yaml"),
    new_path=Path("new_prompt.yaml"),
    include_text_diff=True  # 是否包含文本 diff
)

# 访问结果
print(result.risk_level)           # RiskLevel.LOW/MEDIUM/HIGH
print(result.semantic_change_type) # SemanticChangeType
print(result.summary)              # str
print(result.added_fields)         # list[str]
print(result.removed_fields)       # list[str]
print(result.modified_fields)      # list[FieldDiff]
print(result.text_diff)            # list[str]
```

### DiffResult

```python
from promptgit.diff_engine import DiffResult, RiskLevel, SemanticChangeType

# 检查风险等级
if result.risk_level == RiskLevel.HIGH:
    print("⚠️ High risk changes detected!")

# 检查变更类型
if result.semantic_change_type == SemanticChangeType.VARIABLE_CHANGE:
    print("Variable changes detected")

# 转换为字典
data = result.to_dict()

# 转换为 JSON
json_str = result.to_json()
```

### 辅助函数

```python
from promptgit.diff_engine import (
    extract_variables,
    detect_tone_shift,
    detect_role_shift,
    compute_text_diff,
    compute_structured_diff
)

# 提取模板变量
vars = extract_variables("Answer: {{question}} about {{topic}}")
# {'question', 'topic'}

# 检测语气偏移
has_shift, description = detect_tone_shift(
    "Please help the user",
    "Hey, just do it"
)
# has_shift=True, description="added tone: casual"

# 检测角色偏移
has_shift, description = detect_role_shift(
    "You are a helpful assistant",
    "You are a code reviewer"
)
# has_shift=True, description="new role: code reviewer"

# 文本 diff
diff_lines = compute_text_diff("old text", "new text")

# 结构化 diff
added, removed, modified = compute_structured_diff(
    {"name": "old", "version": "1.0"},
    {"name": "new", "version": "2.0", "extra": "field"}
)
```

---

## Evaluator API

### load_dataset

加载 JSONL 数据集。

```python
from pathlib import Path
from promptgit.evaluator import load_dataset

# 加载数据集
samples = load_dataset(Path("fixtures/dataset.jsonl"))

# 访问样本
for sample in samples:
    print(sample.input)           # str
    print(sample.expected_output) # str
    print(sample.metadata)        # dict
```

### evaluate_prompts

评估两个 prompt 版本。

```python
from promptgit.evaluator import evaluate_prompts, load_dataset
from promptgit.schema import PromptTemplate

# 加载模板
old_template = PromptTemplate.from_yaml(Path("old.yaml"))
new_template = PromptTemplate.from_yaml(Path("new.yaml"))

# 加载数据集
dataset = load_dataset(Path("dataset.jsonl"))

# 运行评估
result = evaluate_prompts(
    old_template=old_template,
    new_template=new_template,
    dataset=dataset,
    threshold=0.05  # 准确率下降阈值
)

# 访问结果
print(result.total_samples)     # int
print(result.accuracy_old)      # float (0-1)
print(result.accuracy_new)      # float (0-1)
print(result.accuracy_delta)    # float (-1 to 1)
print(result.token_cost_old)    # int
print(result.token_cost_new)    # int
print(result.token_cost_delta)  # float
print(result.consistency_score) # float (0-1)
print(result.passed)            # bool
print(result.threshold)         # float

# 访问详细结果
for detail in result.details:
    print(detail.input)           # str
    print(detail.expected)        # str
    print(detail.old_output)      # str
    print(detail.new_output)      # str
    print(detail.old_match)       # bool
    print(detail.new_match)       # bool
    print(detail.similarity_delta)# float

# 转换为 JSON
json_str = result.to_json()
```

### 自定义渲染函数

```python
from promptgit.evaluator import evaluate_prompts, rule_based_render

def custom_render(template, variables):
    """自定义渲染函数（例如接入 LLM）"""
    # 先用规则渲染
    rendered = rule_based_render(template, variables)

    # 然后调用 LLM
    # response = call_llm(rendered)
    # return response

    return rendered

# 使用自定义渲染
result = evaluate_prompts(
    old_template=old_template,
    new_template=new_template,
    dataset=dataset,
    threshold=0.05,
    render_fn=custom_render  # 传入自定义函数
)
```

### 自定义评估函数

```python
from promptgit.evaluator import evaluate_prompts, extract_keywords

def custom_evaluate(rendered_prompt, expected_output):
    """自定义评估函数，替换默认的 keyword_based_evaluate。

    签名要求: (rendered_prompt: str, expected_output: str) -> (output: str, is_match: bool)
    """
    # 示例：使用更严格的关键词匹配（90% 命中率）
    expected_kw = extract_keywords(expected_output)
    prompt_kw = extract_keywords(rendered_prompt)
    if not expected_kw:
        return rendered_prompt, True
    matched = expected_kw & prompt_kw
    is_match = len(matched) / len(expected_kw) >= 0.9
    return rendered_prompt, is_match

result = evaluate_prompts(
    old_template=old_template,
    new_template=new_template,
    dataset=dataset,
    threshold=0.05,
    evaluate_fn=custom_evaluate  # 传入自定义评估函数
)
```

### 同时使用自定义渲染和评估

```python
from promptgit.llm_evaluator import get_llm_config, llm_generate_output

config = get_llm_config("openai", "gpt-4")

def llm_render(template, variables):
    """用 LLM 生成输出"""
    return llm_generate_output(config, template, variables)

def strict_match(rendered_prompt, expected_output):
    """严格匹配"""
    from promptgit.evaluator import extract_keywords
    expected_kw = extract_keywords(expected_output)
    prompt_kw = extract_keywords(rendered_prompt)
    if not expected_kw:
        return rendered_prompt, True
    matched = expected_kw & prompt_kw
    is_match = len(matched) / len(expected_kw) >= 0.9
    return rendered_prompt, is_match

result = evaluate_prompts(
    old_template=old_template,
    new_template=new_template,
    dataset=dataset,
    threshold=0.05,
    render_fn=llm_render,
    evaluate_fn=strict_match,
)
```

### 辅助函数

```python
from promptgit.evaluator import (
    estimate_tokens,
    compute_similarity,
    extract_keywords,
    rule_based_render
)

# 估算 token 数
tokens = estimate_tokens("Hello, how are you?")
# 约 5-6

# 计算文本相似度
similarity = compute_similarity("hello world", "hello there")
# 约 0.6

# 提取关键词
keywords = extract_keywords("Python is a programming language")
# {'python', 'programming', 'language'}

# 规则渲染
from promptgit.schema import PromptTemplate
template = PromptTemplate.model_validate({...})
rendered = rule_based_render(template, {"question": "What is Python?"})
```

---

## LLM Evaluator API

### get_llm_config

创建 LLM 配置对象。

```python
from promptgit.llm_evaluator import get_llm_config

# OpenAI
config = get_llm_config(provider="openai", model="gpt-4")

# Anthropic
config = get_llm_config(provider="anthropic", model="claude-3-opus-20240229")

# Ollama 本地模型（自动设置 api_base=http://localhost:11434）
config = get_llm_config(provider="ollama", model="llama2")

# vLLM 本地模型（自动设置 api_base=http://localhost:8000/v1）
config = get_llm_config(provider="vllm", model="meta-llama/Llama-2-7b-chat-hf")

# SGLang 本地模型（自动设置 api_base=http://localhost:30000/v1）
config = get_llm_config(provider="sglang", model="Qwen/Qwen2-7B-Instruct")

# Azure OpenAI
config = get_llm_config(provider="azure", model="gpt-4")

# 自定义 API Base（代理或私有部署）
config = get_llm_config(
    provider="openai",
    model="gpt-4",
    api_base="https://your-proxy.com/v1",
    api_key="sk-xxx"
)
```

### evaluate_prompts_with_llm

使用 LLM 评估两个 prompt 版本。

```python
from promptgit.llm_evaluator import get_llm_config, evaluate_prompts_with_llm
from promptgit.evaluator import load_dataset
from promptgit.schema import PromptTemplate
from pathlib import Path

old_template = PromptTemplate.from_yaml(Path("old.yaml"))
new_template = PromptTemplate.from_yaml(Path("new.yaml"))
dataset = load_dataset(Path("dataset.jsonl"))

# 基本 LLM 评估（使用相似度匹配）
config = get_llm_config("openai", "gpt-3.5-turbo")
result = evaluate_prompts_with_llm(
    old_template, new_template, dataset, config, threshold=0.05
)

# LLM-as-judge 评估（更准确）
result = evaluate_prompts_with_llm(
    old_template, new_template, dataset, config,
    threshold=0.05, use_judge=True
)

# 使用独立的 Judge 模型（推荐：小模型生成，大模型评判）
gen_config = get_llm_config("openai", "gpt-3.5-turbo")
judge_config = get_llm_config("openai", "gpt-4")
result = evaluate_prompts_with_llm(
    old_template, new_template, dataset, gen_config,
    threshold=0.05, use_judge=True, judge_config=judge_config
)

# 访问结果
print(result.accuracy_delta)
print(result.passed)
print(len(result.judge_results))  # Judge 评分详情
```

### compare_models

对比两个模型在同一数据集上的表现。

```python
from promptgit.llm_evaluator import get_llm_config, compare_models
from promptgit.evaluator import load_dataset
from promptgit.schema import PromptTemplate
from pathlib import Path

template = PromptTemplate.from_yaml(Path("prompt.yaml"))
dataset = load_dataset(Path("dataset.jsonl"))

# 同提供商对比
config_a = get_llm_config("openai", "gpt-3.5-turbo")
config_b = get_llm_config("openai", "gpt-4")
results = compare_models(template, dataset, config_a, config_b)

# 跨提供商对比
config_a = get_llm_config("openai", "gpt-4")
config_b = get_llm_config("anthropic", "claude-3-opus-20240229")
results = compare_models(template, dataset, config_a, config_b)

# 访问结果
for r in results:
    print(f"{r.model_a}: {r.score_a:.2f} vs {r.model_b}: {r.score_b:.2f} → Winner: {r.winner}")
```

### LLMConfig

```python
from promptgit.llm_evaluator import LLMConfig

config = LLMConfig(
    provider="openai",       # 提供商
    model="gpt-4",           # 模型名
    temperature=0.0,         # 温度
    max_tokens=1024,         # 最大 token
    api_key="sk-xxx",        # API Key（可选，自动从环境变量读取）
    api_base="https://...",  # API Base（可选，本地模型自动设置）
)

# 转换为 LiteLLM 格式
litellm_model = config.to_litellm_model()  # "openai/gpt-4"
```

### 类型定义

```python
from promptgit.llm_evaluator import (
    LLMConfig,          # LLM 配置
    LLMJudgeResult,     # Judge 评分结果: score, reasoning, raw_response
    LLMCompareResult,   # 模型对比结果: model_a/b, score_a/b, winner, reasoning
    LLMEvalResult,      # LLM 评估结果: accuracy, token_cost, judge_results 等
)
```

---

## CI Generator API

### generate_workflow

生成 GitHub Actions workflow YAML。

```python
from promptgit.ci_gen import CIConfig, generate_workflow

# 创建配置
config = CIConfig(
    branches=["main", "develop"],
    paths=[".prompts/**"],
    dataset_path="fixtures/dataset.jsonl",
    threshold=0.05,
    enable_diff=True,
    enable_eval=True,
    comment_on_failure=True
)

# 生成 YAML
yaml_content = generate_workflow(config)
print(yaml_content)
```

### generate_pre_commit_config

生成 pre-commit 配置。

```python
from promptgit.ci_gen import PreCommitConfig, generate_pre_commit_config

config = PreCommitConfig(
    diff_fail_on="high",
    enable_eval=True,
    dataset_path="fixtures/dataset.jsonl"
)

yaml_content = generate_pre_commit_config(config)
```

### init_ci

初始化 CI 配置文件。

```python
from pathlib import Path
from promptgit.ci_gen import init_ci

# 生成文件
files = init_ci(
    config_path=Path("ci_config.json"),  # 可选
    output_dir=Path("."),                # 输出目录
    dry_run=False                        # 是否预览
)

# 返回生成的文件路径
for file_type, path in files.items():
    print(f"{file_type}: {path}")
```

---

## 完整示例

### 批量评估多个 Prompt

```python
from pathlib import Path
from promptgit.schema import PromptTemplate
from promptgit.evaluator import evaluate_prompts, load_dataset

# 加载数据集
dataset = load_dataset(Path("dataset.jsonl"))

# 加载基准模板
baseline = PromptTemplate.from_yaml(Path("prompts/baseline.yaml"))

# 评估多个版本
versions = ["v1.yaml", "v2.yaml", "v3.yaml"]
results = []

for version in versions:
    template = PromptTemplate.from_yaml(Path(f"prompts/{version}"))
    result = evaluate_prompts(baseline, template, dataset, threshold=0.05)
    results.append((version, result))

# 输出比较结果
print(f"{'Version':<10} {'Accuracy':<10} {'Delta':<10} {'Status':<10}")
print("-" * 40)
for version, result in results:
    status = "PASS" if result.passed else "FAIL"
    print(f"{version:<10} {result.accuracy_new:.1%}{'':<4} {result.accuracy_delta:+.1%}{'':<4} {status:<10}")
```

### 自动化 Diff 检查

```python
from pathlib import Path
from promptgit.diff_engine import diff_prompts, RiskLevel

def check_prompt_changes(prompt_dir: Path) -> dict:
    """检查 prompt 目录中的变更"""
    results = {}
    
    for prompt_file in prompt_dir.glob("*.yaml"):
        # 比较当前版本与备份
        backup_path = prompt_dir / "backup" / prompt_file.name
        if backup_path.exists():
            diff = diff_prompts(backup_path, prompt_file)
            results[prompt_file.name] = {
                "risk_level": diff.risk_level,
                "changes": diff.summary
            }
    
    return results

# 使用
changes = check_prompt_changes(Path(".prompts"))
for file, info in changes.items():
    if info["risk_level"] == RiskLevel.HIGH:
        print(f"⚠️ {file}: {info['changes']}")
```

### 生成评估报告

```python
import json
from pathlib import Path
from promptgit.evaluator import evaluate_prompts, load_dataset
from promptgit.schema import PromptTemplate

def generate_report(old_path: Path, new_path: Path, dataset_path: Path) -> str:
    """生成评估报告"""
    old = PromptTemplate.from_yaml(old_path)
    new = PromptTemplate.from_yaml(new_path)
    dataset = load_dataset(dataset_path)
    
    result = evaluate_prompts(old, new, dataset)
    
    report = []
    report.append("# Evaluation Report\n")
    report.append(f"## Summary")
    report.append(f"- Total Samples: {result.total_samples}")
    report.append(f"- Accuracy Delta: {result.accuracy_delta:+.1%}")
    report.append(f"- Token Cost Delta: {result.token_cost_delta:+.1%}")
    report.append(f"- Consistency: {result.consistency_score:.1%}")
    report.append(f"- Status: {'PASSED' if result.passed else 'FAILED'}\n")
    
    report.append("## Failed Samples")
    for detail in result.details:
        if not detail.new_match:
            report.append(f"- Input: {detail.input}")
            report.append(f"  Expected: {detail.expected}")
            report.append(f"  Got: {detail.new_output}")
    
    return "\n".join(report)

# 使用
report = generate_report(
    Path("old.yaml"),
    Path("new.yaml"),
    Path("dataset.jsonl")
)
print(report)
```

---

## 类型定义

```python
from promptgit.diff_engine import (
    SemanticChangeType,  # Enum: NONE, VARIABLE_CHANGE, CONSTRAINT_CHANGE, TONE_SHIFT, ROLE_SHIFT, MIXED
    RiskLevel,           # Enum: LOW, MEDIUM, HIGH
    FieldDiff,           # Dataclass: field, old_value, new_value, change_type
    DiffResult,          # Dataclass: 完整 diff 结果
)

from promptgit.evaluator import (
    EvalSample,     # Dataclass: input, expected_output, metadata
    SampleResult,   # Dataclass: 单个样本结果
    EvalResult,     # Dataclass: 完整评估结果
    RenderFunction, # Type: Callable[[str, dict], str]
)

from promptgit.llm_evaluator import (
    LLMConfig,          # Dataclass: LLM 配置
    LLMJudgeResult,     # Dataclass: Judge 评分结果
    LLMCompareResult,   # Dataclass: 模型对比结果
    LLMEvalResult,      # Dataclass: LLM 评估完整结果
)
```

---

## 相关文档

- [快速开始](quickstart.md) - 5 分钟上手
- [CLI 参考](cli_reference.md) - 命令行使用
- [Prompt Schema](prompt-schema.md) - 文件格式
- [架构文档](architecture.md) - 内部实现
