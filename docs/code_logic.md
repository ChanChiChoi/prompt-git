# 代码逻辑文档

> prompt-git-manager v0.2.0 代码实现全览
>
> 本文档记录所有模块的功能、函数签名、参数、返回值和核心逻辑，用于对照文档检查一致性。

---

## 目录

- [模块总览](#模块总览)
- [schema.py — 数据模型](#schemapy--数据模型)
- [utils.py — 工具函数](#utilspy--工具函数)
- [diff_engine.py — 语义 Diff 引擎](#diff_enginepy--语义-diff-引擎)
- [evaluator.py — 规则评估引擎](#evaluatorpy--规则评估引擎)
- [llm_evaluator.py — LLM 评估引擎](#llm_evaluatorpy--llm-评估引擎)
- [ci_gen.py — CI/CD 生成器](#ci_genpy--cicd-生成器)
- [cli.py — CLI 命令](#clipy--cli-命令)

---

## 模块总览

```
src/promptgit/
├── __init__.py          # 版本号 __version__ = "0.2.0"
├── schema.py            # Pydantic 数据模型
├── utils.py             # Git/路径/表格工具
├── diff_engine.py       # 语义 diff + 风险评估
├── evaluator.py         # 规则评估（无 LLM 依赖）
├── llm_evaluator.py     # LLM 评估（LiteLLM 多提供商）
├── ci_gen.py            # CI/CD 配置生成
└── cli.py               # Typer CLI 入口
```

---

## schema.py — 数据模型

### PromptTemplate

```python
class PromptTemplate(BaseModel):
    name: str                    # 必填，1-128 字符
    version: str = "0.1.0"      # Semver 格式
    system_prompt: str           # 必填
    user_template: str           # 必填，支持 {{variable}} 占位符
    variables: dict = {}         # 变量定义及默认值
    constraints: list = []       # 行为约束列表
    metadata: dict = {}          # 任意元数据
```

**方法：**
- `from_yaml(path: Path) -> PromptTemplate` — 从 YAML 文件加载并校验
- `to_yaml(path: Path) -> None` — 序列化为 YAML 文件
- `validate_name(v: str) -> str` — `@field_validator("name")`，长度 1-128

### CommitRecord

```python
class CommitRecord(BaseModel):
    hash: str                    # Git commit hash
    timestamp: str               # ISO 8601 时间戳
    changed_files: list[str]     # 变更文件列表
    validation_status: str       # "pass" 或 "fail"
    message: str                 # 提交消息
```

---

## utils.py — 工具函数

### 常量

```python
ERR_SUCCESS = 0
ERR_ARGS = 1
ERR_GIT = 2
ERR_VALIDATION = 3
```

### 函数列表

| 函数 | 签名 | 说明 |
|------|------|------|
| `get_repo` | `() -> Repo` | 获取当前目录的 Git Repo 对象，非 Git 目录则 `error_exit` |
| `get_prompts_dir` | `(repo: Repo = None) -> Path` | 返回 `.prompts/` 绝对路径 |
| `render_table` | `(title: str, rows: list[tuple]) -> None` | 用 Rich 渲染表格到 stderr |
| `error_exit` | `(message: str, code: int = 1) -> None` | 打印错误并 `raise typer.Exit(code)` |

---

## diff_engine.py — 语义 Diff 引擎

### 枚举

```python
class SemanticChangeType(str, Enum):
    VARIABLE_CHANGE = "variable_change"      # 变量增删
    CONSTRAINT_CHANGE = "constraint_change"  # 约束增删
    TONE_SHIFT = "tone_shift"               # 语气变化
    ROLE_SHIFT = "role_shift"               # 角色变化
    MINOR = "minor"                          # 其他小改动

class RiskLevel(str, Enum):
    LOW = "low"        # 🟢 小改动，无语义影响
    MEDIUM = "medium"  # 🟡 约束或语气变化
    HIGH = "high"      # 🔴 角色或变量移除
```

### DiffResult

```python
@dataclass
class DiffResult:
    file_path: str                          # 文件路径
    changes: list[dict]                     # 字段级变更列表
    semantic_type: SemanticChangeType       # 语义变更类型
    risk_level: RiskLevel                   # 风险等级
    summary: str                            # 变更摘要
```

**changes 中每个 dict 结构：**
```python
{
    "field": str,           # 字段名
    "type": "added" | "removed" | "modified",
    "old": Any,             # 旧值（modified/removed 时有）
    "new": Any,             # 新值（added/modified 时有）
}
```

### diff_prompts

```python
def diff_prompts(
    old: PromptTemplate,
    new: PromptTemplate,
) -> DiffResult
```

**逻辑流程：**
1. 比较 `name`、`version`、`system_prompt`、`user_template` 逐字段
2. 比较 `variables` 的 key 集合（added/removed）
3. 比较 `constraints` 列表（逐项比较）
4. 判定 `SemanticChangeType`：
   - 有变量变更 → `VARIABLE_CHANGE`
   - 有约束变更 → `CONSTRAINT_CHANGE`
   - system_prompt 变化大 → `TONE_SHIFT`
   - role 相关字段变化 → `ROLE_SHIFT`
   - 其他 → `MINOR`
5. 判定 `RiskLevel`：
   - `ROLE_SHIFT` 或变量移除 → `HIGH`
   - `CONSTRAINT_CHANGE` 或 `TONE_SHIFT` → `MEDIUM`
   - 其他 → `LOW`

### render_diff

```python
def render_diff(result: DiffResult, console: Console) -> None
```

用 Rich 表格渲染 diff 结果（风险等级、变更类型、摘要、增删字段）。

---

## evaluator.py — 规则评估引擎

### 数据类

```python
@dataclass
class EvalSample:
    input: str                # 输入文本
    expected_output: str      # 期望输出
    metadata: dict = None     # 可选元数据

@dataclass
class SampleResult:
    input: str
    expected: str
    old_output: str
    new_output: str
    old_match: bool           # 旧 prompt 是否匹配
    new_match: bool           # 新 prompt 是否匹配
    similarity_delta: float   # 新旧输出相似度

@dataclass
class EvalResult:
    total_samples: int
    accuracy_old: float       # 0-1
    accuracy_new: float       # 0-1
    accuracy_delta: float     # -1 到 +1
    token_cost_old: int
    token_cost_new: int
    token_cost_delta: float
    consistency_score: float  # 0-1
    passed: bool
    threshold: float
    details: list[SampleResult]

    def to_dict() -> dict
    def to_json(indent=2) -> str
```

### 核心函数

#### rule_based_render

```python
def rule_based_render(template: PromptTemplate, variables: dict) -> str
```

将 `user_template` 中的 `{{variable}}` 替换为 `variables` 中的值。

#### compute_similarity

```python
def compute_similarity(text_a: str, text_b: str) -> float
```

使用 `difflib.SequenceMatcher` 计算 0-1 相似度。

#### estimate_tokens

```python
def estimate_tokens(text: str) -> int
```

简单估算：`len(text) // 4`。

#### keyword_match

```python
def keyword_match(output: str, expected: str) -> bool
```

检查 expected 中的关键单词是否出现在 output 中。阈值：匹配率 >= 0.5。

#### evaluate_prompts

```python
def evaluate_prompts(
    old_template: PromptTemplate,
    new_template: PromptTemplate,
    dataset: list[EvalSample],
    threshold: float = 0.05,
    render_fn: Callable = None,    # 可选自定义渲染函数 (template, variables) -> str
    evaluate_fn: Callable = None,  # 可选自定义评估函数 (prompt, expected) -> (output, bool)
) -> EvalResult
```

**核心逻辑：**
1. 遍历 dataset 中每个 sample
2. 渲染 old/new template：优先用 `render_fn`，否则用 `rule_based_render`
3. 评估输出：优先用 `evaluate_fn`，否则用 `keyword_based_evaluate`
4. 计算 accuracy_old、accuracy_new、accuracy_delta
5. 计算 token_cost（estimate_tokens）
6. 计算 consistency_score（old_match == new_match 的比例）
7. `passed = accuracy_delta >= -threshold`

#### create_llm_render_function

```python
def create_llm_render_function(config: LLMConfig) -> Callable
```

返回一个 `render_fn(template, variables) -> str` 函数，内部调用 `llm_generate_output`。供 `evaluate_prompts` 的 `render_fn` 参数使用。

---

## llm_evaluator.py — LLM 评估引擎

### 数据类

#### LLMConfig

```python
@dataclass
class LLMConfig:
    provider: str = "openai"        # 提供商名称
    model: str = "gpt-3.5-turbo"   # 模型名称
    temperature: float = 0.0
    max_tokens: int = 1024
    api_key: Optional[str] = None   # API Key
    api_base: Optional[str] = None  # API Base URL
```

**`to_litellm_model()` 方法 — 提供商前缀映射：**

| provider | 前缀 | 示例输出 |
|----------|------|----------|
| `openai` | `openai/` | `openai/gpt-4` |
| `anthropic` | `anthropic/` | `anthropic/claude-3-opus` |
| `ollama` | `ollama/` | `ollama/llama2` |
| `vllm` | `openai/` | `openai/meta-llama/Llama-2-7b-chat-hf` |
| `sglang` | `openai/` | `openai/Qwen/Qwen2-7B-Instruct` |
| `azure` | `azure/` | `azure/gpt-4` |
| `huggingface` | `huggingface/` | `huggingface/xxx` |
| 未知 | 无前缀 | `my-model` |

> **注意**：vLLM 和 SGLang 使用 `openai/` 前缀，因为它们提供 OpenAI 兼容 API。

#### LLMJudgeResult

```python
@dataclass
class LLMJudgeResult:
    score: float           # 0.0 - 1.0
    reasoning: str         # 评分理由
    raw_response: str      # LLM 原始响应
```

#### LLMCompareResult

```python
@dataclass
class LLMCompareResult:
    model_a: str
    model_b: str
    score_a: float
    score_b: float
    winner: str            # "A" / "B" / "Tie"
    reasoning: str
```

#### LLMEvalResult

```python
@dataclass
class LLMEvalResult:
    total_samples: int
    accuracy_old: float
    accuracy_new: float
    accuracy_delta: float
    token_cost_old: int
    token_cost_new: int
    token_cost_delta: float
    consistency_score: float
    passed: bool
    threshold: float
    details: list[SampleResult]
    judge_results: list[LLMJudgeResult]
    compare_results: list[LLMCompareResult]
```

### 核心函数

#### get_llm_config

```python
def get_llm_config(
    provider: str = "openai",
    model: str = "gpt-3.5-turbo",
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
) -> LLMConfig
```

**逻辑：**
1. 设置默认 API Base（如果未指定）：
   - `ollama` → `http://localhost:11434`
   - `vllm` → `http://localhost:8000/v1`
   - `sglang` → `http://localhost:30000/v1`
2. 自动检测环境变量中的 API Key：
   - `openai` → `OPENAI_API_KEY`
   - `anthropic` → `ANTHROPIC_API_KEY`
   - `ollama` → `OLLAMA_API_KEY`
   - `vllm` → `VLLM_API_KEY`
   - `sglang` → `SGLANG_API_KEY`
3. 本地提供商（ollama/vllm/sglang）无 Key 时使用 `"dummy"`

#### call_llm

```python
def call_llm(
    config: LLMConfig,
    prompt: str,
    system_prompt: Optional[str] = None,
) -> str
```

**逻辑：**
1. 导入 `litellm.completion`（失败则提示安装）
2. 构建 messages 列表（可选 system + user）
3. 调用 `completion(model=..., messages=..., temperature=..., max_tokens=..., api_key=..., api_base=...)`
4. 返回 `response.choices[0].message.content`

#### llm_judge_evaluate

```python
def llm_judge_evaluate(
    config: LLMConfig,
    rendered_prompt: str,
    expected_output: str,
    actual_output: str,
) -> LLMJudgeResult
```

**逻辑：**
1. 构建 judge prompt，包含原始 prompt、期望输出、实际输出
2. 要求 LLM 返回 JSON：`{"score": 0.0-1.0, "reasoning": "..."}`
3. 解析 JSON 响应
4. 解析失败时返回 `score=0.0`

#### llm_generate_output

```python
def llm_generate_output(
    config: LLMConfig,
    system_prompt: str,
    user_prompt: str,
) -> tuple[str, int]
```

返回 `(output_text, estimated_tokens)`。异常时返回 `("[LLM Error: ...]", 0)`。

#### evaluate_prompts_with_llm

```python
def evaluate_prompts_with_llm(
    old_template: PromptTemplate,
    new_template: PromptTemplate,
    dataset: list[EvalSample],
    config: LLMConfig,
    threshold: float = 0.05,
    use_judge: bool = False,
    judge_config: Optional[LLMConfig] = None,
) -> LLMEvalResult
```

**核心逻辑：**
1. 如果未提供 `judge_config`，使用 `config` 作为评判模型
2. 遍历 dataset：
   - `rule_based_render` 渲染 old/new template
   - `llm_generate_output` 生成 old/new 输出
   - 如果 `use_judge=True`：
     - 调用 `llm_judge_evaluate` 分别评判 old/new（使用 `judge_llm_config`）
     - `score >= 0.7` 视为匹配
   - 如果 `use_judge=False`：
     - 用 `compute_similarity` 计算相似度
     - `similarity >= 0.7` 视为匹配
3. 计算各项指标
4. `passed = accuracy_delta >= -threshold`

#### compare_models

```python
def compare_models(
    template: PromptTemplate,
    dataset: list[EvalSample],
    config_a: LLMConfig,
    config_b: LLMConfig,
) -> list[LLMCompareResult]
```

**逻辑：**
1. 遍历 dataset
2. `rule_based_render` 渲染 template
3. 两个模型分别 `llm_generate_output`
4. 构建比较 prompt，要求 LLM 返回 JSON：`{"score_a": ..., "score_b": ..., "winner": "A"/"B"/"Tie", "reasoning": "..."}`
5. 使用 `config_a` 作为评判模型
6. 解析失败时返回默认 Tie 结果

---

## ci_gen.py — CI/CD 生成器

### 数据类

#### CIConfig

```python
@dataclass
class CIConfig:
    # 触发设置
    branches: list[str] = ["main", "dev"]
    paths: list[str] = [".prompts/**"]

    # 评估设置
    dataset_path: str = "fixtures/dataset.jsonl"
    threshold: float = 0.05
    model_provider: str = "none"
    model_name: str = "gpt-3.5-turbo"

    # Workflow 设置
    python_version: str = "3.10"
    concurrency_group: str = "prompt-guard-${{ github.ref }}"
    cancel_in_progress: bool = True

    # 功能开关
    enable_diff: bool = True
    enable_eval: bool = True
    comment_on_failure: bool = True
    upload_artifact: bool = True
```

#### PreCommitConfig

```python
@dataclass
class PreCommitConfig:
    diff_fail_on: str = "high"        # low/med/high
    enable_eval: bool = False
    dataset_path: str = "fixtures/dataset.jsonl"
```

### 函数

#### init_ci

```python
def init_ci(
    config: CIConfig = None,
    config_path: Path = None,
) -> dict[str, str]
```

**逻辑：**
1. 如果提供 `config_path`，从 JSON 文件加载配置
2. 生成 GitHub Actions workflow YAML
3. 生成 pre-commit hook 配置
4. 生成版本 bump 脚本
5. 返回 `{文件路径: 文件内容}` 字典

#### generate_workflow

```python
def generate_workflow(config: CIConfig) -> str
```

生成 `.github/workflows/prompt-guard.yml` 内容。

#### generate_precommit

```python
def generate_precommit(config: PreCommitConfig) -> str
```

生成 `.pre-commit-config.yaml` 内容。

---

## cli.py — CLI 命令

### 入口

```python
app = typer.Typer(
    name="pg",
    help="prompt-git-manager: Git-native prompt version control & CI guardrail.",
    add_completion=False,
)
```

### 全局选项

| 选项 | 短选项 | 说明 |
|------|--------|------|
| `--version` | `-v` | 显示版本 |
| `--help` | `-h` | 帮助 |

### pg init

```python
@app.command()
def init(dry_run: bool = False)
```

**逻辑：**
1. 获取 Git repo（`get_repo()`）
2. 创建 `.prompts/` 目录
3. 创建 `config.json`（含 version、created_at、eval_threshold 等）
4. `--dry-run` 时只预览不创建

### pg add

```python
@app.command()
def add(file: Path, dry_run: bool = False)
```

**逻辑：**
1. 校验文件存在且为 YAML/JSON
2. `PromptTemplate.from_yaml()` 加载并校验
3. 复制到 `.prompts/` 目录
4. 显示添加信息表格（name、version、variables、constraints、path）
5. `--dry-run` 时只预览不复制

### pg commit

```python
@app.command()
def commit(message: str = typer.Option(..., "--message", "-m"), dry_run: bool = False)
```

**逻辑：**
1. 检查 `.prompts/` 下有变更文件
2. `git add .prompts/`
3. 创建 `CommitRecord`
4. 追加到 `.prompts/commits.jsonl`
5. `git commit -m message`
6. `--dry-run` 时只预览不提交

### pg diff

```python
@app.command()
def diff(
    file: Optional[str] = None,
    semantic: bool = typer.Option(False, "--semantic", "-s"),
    json_output: bool = typer.Option(False, "--json", "-j"),
)
```

**逻辑：**
1. 获取 `.prompts/` 下所有 YAML 文件
2. 对每个文件：
   - 从 Git HEAD 读取旧版本
   - 从工作目录读取新版本
   - `diff_prompts()` 计算语义 diff
3. `--semantic` 时显示风险分析
4. `--json` 时输出 JSON 格式

### pg eval

```python
@app.command()
def eval(
    dataset: Path = typer.Option(..., "--dataset", "-d"),
    old: Optional[Path] = None,
    new: Optional[Path] = None,
    threshold: float = typer.Option(0.05, "--threshold", "-t"),
    json_output: bool = typer.Option(False, "--json", "-j"),
    # LLM 参数
    provider: Optional[str] = typer.Option(None, "--provider", "-p"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    api_base: Optional[str] = None,
    judge: bool = False,
    judge_provider: Optional[str] = None,
    judge_model: Optional[str] = None,
    compare_models_option: Optional[str] = typer.Option(None, "--compare-models", "-c"),
)
```

**逻辑流程：**

#### 1. 加载数据集

从 JSONL 文件加载 `EvalSample` 列表。每行格式：
```json
{"input": "...", "expected_output": "...", "metadata": {...}}
```

#### 2. 模型对比模式（`--compare-models`）

解析 `compare_models_option` 字符串，支持两种格式：
- 同提供商：`gpt-3.5-turbo,gpt-4`（使用 `--provider` 指定）
- 跨提供商：`openai:gpt-4,anthropic:claude-3-opus`

内部调用 `parse_model_entry(entry, default_provider)` 解析每个模型条目。

调用 `compare_models()` 进行对比，使用第一个模型的 config 作为评判者。

#### 3. LLM 评估模式（`--provider` 指定时）

- `get_llm_config()` 创建主模型 config
- 如果指定 `--judge-provider`/`--judge-model`，创建独立的 `judge_config`
- 调用 `evaluate_prompts_with_llm()`
- `use_judge = --judge` 参数

#### 4. 规则评估模式（默认，无 `--provider`）

- 加载 old/new PromptTemplate
- 调用 `evaluate_prompts()`

#### 5. 输出

- 默认：Rich 表格输出
- `--json`：JSON 输出
- exit code：0=passed，2=failed

### pg ci init

```python
@app.command("ci init")
def ci_init(config: Optional[Path] = None)
```

**逻辑：**
1. 加载配置（如果提供 config_path）
2. `init_ci()` 生成文件
3. 写入文件到项目目录

---

## 环境变量汇总

| 变量 | 使用位置 | 默认值 |
|------|----------|--------|
| `PROMPT_GIT_MODEL` | cli.py | `none` |
| `PROMPT_GIT_THRESHOLD` | cli.py | `0.05` |
| `OPENAI_API_KEY` | llm_evaluator.py | - |
| `OPENAI_API_BASE` | llm_evaluator.py (通过 LiteLLM) | `https://api.openai.com/v1` |
| `ANTHROPIC_API_KEY` | llm_evaluator.py | - |
| `AZURE_API_KEY` | llm_evaluator.py | - |
| `OLLAMA_API_KEY` | llm_evaluator.py | - |
| `OLLAMA_API_BASE` | llm_evaluator.py | `http://localhost:11434` |
| `VLLM_API_KEY` | llm_evaluator.py | - |
| `VLLM_API_BASE` | llm_evaluator.py | `http://localhost:8000/v1` |
| `SGLANG_API_KEY` | llm_evaluator.py | - |
| `SGLANG_API_BASE` | llm_evaluator.py | `http://localhost:30000/v1` |

---

## 评估模式对比

| 维度 | 规则评估 | LLM 增强评估 | LLM-as-Judge |
|------|----------|-------------|--------------|
| 入口函数 | `evaluate_prompts()` | `evaluate_prompts_with_llm()` | `evaluate_prompts_with_llm(use_judge=True)` |
| 输出生成 | `rule_based_render` | `llm_generate_output` | `llm_generate_output` |
| 匹配判断 | `keyword_match` | `compute_similarity` | `llm_judge_evaluate` |
| 匹配阈值 | 关键词覆盖率 >= 0.5 | 相似度 >= 0.7 | 评分 >= 0.7 |
| LLM 依赖 | 无 | 需要 | 需要（可独立配置 judge 模型） |
| 离线可用 | 是 | 否 | 否 |
| 准确度 | 低 | 中 | 高 |

---

## CLI 参数到函数的映射

| CLI 参数 | 传递给 | 数据类型 |
|----------|--------|----------|
| `--dataset/-d` | `evaluate_prompts` / `evaluate_prompts_with_llm` 的 `dataset` | `Path → list[EvalSample]` |
| `--old` | `evaluate_prompts` 的 `old_template` | `Path → PromptTemplate` |
| `--new` | `evaluate_prompts` 的 `new_template` | `Path → PromptTemplate` |
| `--threshold/-t` | `threshold` 参数 | `float` |
| `--provider/-p` | `get_llm_config` 的 `provider` | `str` |
| `--model/-m` | `get_llm_config` 的 `model` | `str` |
| `--api-base` | `get_llm_config` 的 `api_base` | `str` |
| `--judge` | `evaluate_prompts_with_llm` 的 `use_judge` | `bool` |
| `--judge-provider` | 创建 `judge_config` 的 `provider` | `str` |
| `--judge-model` | 创建 `judge_config` 的 `model` | `str` |
| `--compare-models/-c` | `compare_models()` 的 `config_a`/`config_b` | `str → 2x LLMConfig` |
| `--json/-j` | 输出格式 | `bool` |

---

## 测试覆盖

测试文件：`tests/test_llm_eval.py`（30 个测试用例）

| 测试类别 | 测试数 | 覆盖内容 |
|----------|--------|----------|
| LLMConfig | 4 | 默认值、自定义值、to_litellm_model 各提供商 |
| get_llm_config | 6 | 各提供商默认 API Base、环境变量检测、dummy key |
| call_llm | 3 | 成功调用、system_prompt、ImportError |
| llm_judge_evaluate | 3 | 正常评分、JSON 解析失败、异常处理 |
| llm_generate_output | 2 | 正常生成、异常处理 |
| evaluate_prompts_with_llm | 5 | 空数据集、无 judge、有 judge、judge_config、passed/failed |
| compare_models | 4 | 正常对比、JSON 失败、winner 判定 |
| 结果类序列化 | 3 | to_dict、to_json |

---

## 文档与代码差异检查

> 以下为对照代码逻辑与各文档后发现的不一致之处。

### 1. 环境变量文档与代码不一致

**问题：** `PROMPT_GIT_MODEL`、`PROMPT_GIT_THRESHOLD`、`PROMPT_GIT_EDITOR` 在文档中列出，但**代码中从未使用**。

- `cli_reference.md` 第 433-438 行列出了这三个变量
- `configuration.md` 第 82-83 行列出了 `PROMPT_GIT_MODEL` 和 `PROMPT_GIT_THRESHOLD`
- `src/promptgit/cli.py` 中 **没有** 读取这些环境变量的代码
- 阈值和模型均通过 CLI 参数或 `config.json` 设置

**影响：** 用户按文档设置这些环境变量不会生效。

**建议：** 要么在 cli.py 中实现读取这些环境变量的逻辑，要么从文档中移除。

### 2. Azure OpenAI 未实现

**问题：** `configuration.md` 第 367 行声称支持 `azure` 提供商并使用 `AZURE_API_KEY`，但：

- `llm_evaluator.py` 的 `get_llm_config()` 中 `env_keys` 映射**没有** `azure` 条目
- `to_litellm_model()` 的 `provider_prefixes` 中**没有** `azure` 条目
- 虽然 LiteLLM 本身支持 Azure，但 prompt-git-manager 的配置层未适配

**影响：** 按文档使用 `--provider azure` 会走默认路径，可能无法正确连接。

**建议：** 要么在 `llm_evaluator.py` 中添加 Azure 支持（添加 env_key 和 prefix），要么从文档中移除 Azure 条目。

### 3. 本地模型 API Key 环境变量未文档化

**问题：** `get_llm_config()` 检查以下环境变量，但文档中**未列出**：

| 环境变量 | 代码位置 |
|----------|----------|
| `OLLAMA_API_KEY` | `llm_evaluator.py:162` |
| `VLLM_API_KEY` | `llm_evaluator.py:163` |
| `SGLANG_API_KEY` | `llm_evaluator.py:164` |

**影响：** 虽然本地模型通常不需要 API Key（代码会用 `dummy`），但如果用户有认证的本地服务，不知道可以配置 Key。

**建议：** 在 configuration.md 环境变量表中补充这三个变量，并说明本地模型通常不需要。

### 4. CLI `--api-base` 参数在代码中缺失

**问题：**
- `cli_reference.md` 第 278 行文档化了 `--api-base` 参数
- `configuration.md` 第 293 行有使用示例
- 但 `cli.py` 的 `eval` 命令函数签名中**没有** `api_base` 参数

**影响：** 用户使用 `--api-base` 会报 "unexpected option" 错误。

**建议：** 在 `cli.py` 的 `eval` 命令中添加 `api_base` 参数，并传递给 `get_llm_config()`。

### 5. 评估分数标准不一致

**问题：** `cli_reference.md` 第 405-410 行描述了 LLM-as-judge 的评分标准（1.0/0.8-0.9/0.6-0.7 等），但代码中：

- `llm_evaluator.py:375` 只有一个硬阈值：`score >= 0.7` 视为匹配
- 没有使用文档描述的多级评分体系

**影响：** 文档描述过于细致，与实际行为有差距。

**建议：** 统一文档和代码的评分标准说明。

### 6. 评估算法描述不完整

**问题：** `evaluation.md` 中描述了三种评估流程图，但以下细节与代码不完全一致：

- `keyword_match` 的实际阈值是匹配率 >= 0.5（不是文档暗示的精确匹配）
- `compute_similarity` 使用 `SequenceMatcher`（文档中提到了但不够突出）
- `estimate_tokens` 使用简单的 `len(text) // 4`（文档未说明具体算法）

**建议：** 在 evaluation.md 中补充算法细节。

### 7. compare_models 函数签名与文档不一致

**问题：** 代码中 `compare_models()` 接受**两个独立的 config**（`config_a`, `config_b`），但文档暗示它接受一个 template 和 dataset。实际签名：

```python
def compare_models(
    template: PromptTemplate,     # 单个 template
    dataset: list[EvalSample],
    config_a: LLMConfig,          # 模型 A
    config_b: LLMConfig,          # 模型 B
) -> list[LLMCompareResult]
```

文档中的描述基本正确，但 `cli_reference.md` 的对比示例格式需要更新为 `provider:model` 格式。

### 8. ci_gen.py 中 PreCommitConfig 与文档差异

**问题：** `cli_reference.md` 中 pre-commit 示例使用：

```yaml
entry: pg diff --fail-on=high
```

但代码中 `pg diff` 命令没有 `--fail-on` 参数。`PreCommitConfig.diff_fail_on` 只在 `generate_precommit()` 生成配置时使用。

**建议：** 确认 `--fail-on` 是否应该添加到 `pg diff` 命令，或更新文档示例。

### 9. 版本号

**代码版本：** `0.2.0`（`__init__.py` 和 `pyproject.toml`）
**文档版本：** 部分文档仍引用 `0.1.0`

- `configuration.md` 第 26 行：`"version": "0.1.0"`
- `cli_reference.md` 第 453 行：`"version": "0.1.0"`

**建议：** 更新文档中的示例版本号为 `0.2.0`，或说明这是示例值。

---

## 差异汇总表

| # | 问题 | 严重度 | 涉及文档 | 涉及代码 | 状态 |
|---|------|--------|----------|----------|------|
| 1 | 环境变量未实现 | 🔴 高 | cli_reference.md, configuration.md | cli.py | ✅ 已修复 |
| 2 | Azure 未实现 | 🟡 中 | configuration.md | llm_evaluator.py | ✅ 已修复 |
| 3 | 本地模型 Key 未文档化 | 🟢 低 | configuration.md | llm_evaluator.py | ✅ 已修复 |
| 4 | `--api-base` 参数缺失 | 🔴 高 | cli_reference.md, configuration.md | cli.py | ✅ 已修复 |
| 5 | 评分标准不一致 | 🟡 中 | cli_reference.md | llm_evaluator.py | ✅ 已确认一致 |
| 6 | 评估算法细节不足 | 🟢 低 | evaluation.md | evaluator.py | ✅ 已确认完整 |
| 7 | compare_models 描述 | 🟢 低 | cli_reference.md | llm_evaluator.py | ✅ 已确认正确 |
| 8 | `--fail-on` 参数 | 🟡 中 | cli_reference.md | cli.py | ✅ 已修复 |
| 9 | 版本号不同步 | 🟢 低 | 多个文档 | - | ✅ 已修复 |

---

## 示例脚本

项目提供了三个完整的 Python 示例脚本，展示不同评估模式的使用方式：

### examples/normal/run_eval.py — 规则引擎评估

- 使用 `evaluate_prompts()` 进行纯规则评估（无需 LLM）
- 演示 `rule_based_render()`, `extract_keywords()`, `keyword_based_evaluate()`, `compute_similarity()`, `estimate_tokens()`
- 完整的评估原理讲解和结果解读
- 适合快速验证 prompt 变更，无需 API Key

### examples/llm_enhanced/run_eval.py — LLM 增强评估

- 使用 `evaluate_prompts_with_llm(use_judge=False)` 进行 LLM 增强评估
- 演示 `get_llm_config()`, `llm_generate_output()`
- 支持 OpenAI / Anthropic / Azure / Ollama / vLLM / SGLang
- 适合评估 prompt 变更对 LLM 实际输出的影响

### examples/llm_as_judge/run_eval.py — LLM-as-Judge 评估

- 使用 `evaluate_prompts_with_llm(use_judge=True)` 进行 Judge 评估
- 演示 `llm_judge_evaluate()`, `compare_models()`
- 支持独立 Judge 模型（小模型生成，大模型评判）
- 适合重要 prompt 变更的最终验证

### 数据集

- `examples/datasets/qa_dataset.jsonl` — 10 个 QA 样本，用于所有示例脚本
- `examples/prompts/*.yaml` — 6 个 Prompt 模板（英文/中文，客服/代码生成/数据抽取）
