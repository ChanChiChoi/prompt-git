# prompt-git-manager 架构文档

## 目录

- [系统概述](#系统概述)
- [模块架构](#模块架构)
- [数据模型](#数据模型)
- [命令流程](#命令流程)
- [数据流动](#数据流动)
- [核心算法](#核心算法)
- [文件结构](#文件结构)
- [依赖关系](#依赖关系)
- [错误处理](#错误处理)
- [扩展点](#扩展点)

---

## 系统概述

prompt-git-manager 是一个 Git 原生的 Prompt 版本控制工具，核心理念是将 Prompt 视为代码进行管理。

### 设计原则

1. **Git 原生**：利用 Git 进行版本管理，Prompt 文件存储在 `.prompts/` 目录
2. **零依赖运行**：核心功能不依赖外部 LLM API，使用规则引擎评估
3. **CI 优先**：专为 GitHub Actions 设计，支持 PR 自动拦截
4. **模块单一职责**：每个模块只负责一个核心功能

### 核心能力

```
┌─────────────────────────────────────────────────────────────┐
│                      prompt-git-manager                              │
├─────────────────────────────────────────────────────────────┤
│  版本管理          语义分析           质量评估           CI 集成  │
│  ─────────        ─────────         ─────────         ────────│
│  pg init          pg diff           pg eval           pg ci   │
│  pg add             │                 │                 │     │
│  pg commit          ▼                 ▼                 ▼     │
│                   DiffResult       EvalResult        Workflow │
└─────────────────────────────────────────────────────────────┘
```

---

## 模块架构

```
┌──────────────────────────────────────────────────────────────────┐
│                            CLI Layer                              │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                         cli.py                               │ │
│  │  Typer App → init / add / commit / diff / eval / ci         │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                              Core Layer                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  schema.py   │  │diff_engine.py│  │ evaluator.py │  │llm_evaluator │ │
│  │              │  │              │  │              │  │              │ │
│  │ PromptTemplate│  │ 结构化 Diff  │  │ 规则评估     │  │ LLM 评估     │ │
│  │ CommitRecord │  │ 语义分析     │  │ 指标计算     │  │ Judge 模式   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                       Utility Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  utils.py    │  │  ci_gen.py   │  │              │           │
│  │              │  │              │  │              │           │
│  │ Git 操作     │  │ YAML 生成    │  │              │           │
│  │ Rich 渲染    │  │ Pre-commit   │  │              │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└──────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                      External Dependencies                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ GitPython│ │  Pydantic│ │   Typer  │ │   Rich   │            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
└──────────────────────────────────────────────────────────────────┘
```

### 模块职责

| 模块 | 职责 | 核心类/函数 |
|------|------|------------|
| `cli.py` | CLI 入口，命令定义，用户交互 | `app`, `init()`, `add()`, `commit()`, `diff()`, `eval()` |
| `schema.py` | 数据模型定义，YAML/JSON 解析验证 | `PromptTemplate`, `CommitRecord` |
| `diff_engine.py` | 结构化 Diff，语义分析，风险评估 | `diff_prompts()`, `DiffResult`, `RiskLevel` |
| `evaluator.py` | 规则评估，数据集加载，模板渲染，指标计算 | `evaluate_prompts()`, `EvalResult`, `rule_based_render()` |
| `llm_evaluator.py` | LLM 评估引擎，Judge 模式，多模型对比 | `evaluate_prompts_with_llm()`, `compare_models()`, `LLMConfig` |
| `ci_gen.py` | GitHub Actions YAML 生成 | `generate_workflow()`, `init_ci()` |
| `utils.py` | Git 操作封装，Rich 输出，错误处理 | `get_repo()`, `render_table()`, `error_exit()` |

---

## 数据模型

### PromptTemplate

```python
class PromptTemplate(BaseModel):
    name: str                    # Prompt 名称（必填）
    version: str = "0.1.0"       # 语义版本
    system_prompt: str           # 系统提示词（必填）
    user_template: str           # 用户模板，支持 {{var}}（必填）
    variables: dict[str, Any]    # 变量定义及默认值
    constraints: list[str]       # 行为约束列表
    metadata: dict[str, Any]     # 任意元数据
    messages: list[dict]         # 可选，多轮对话历史 [{role, content}]
```

**YAML 示例（单轮）：**

```yaml
name: qa-assistant
version: "1.0.0"
system_prompt: "You are a helpful assistant."
user_template: "Answer: {{question}}"
variables:
  question:
    type: string
    default: "What is Python?"
constraints:
  - Be concise
  - Use examples
metadata:
  author: team-name
```

**YAML 示例（多轮）：**

```yaml
name: multi-turn-assistant
version: "1.0.0"
system_prompt: "You are a helpful assistant."
messages:
  - role: user
    content: "What is {{topic}}?"
  - role: assistant
    content: "{{topic}} is a programming language."
user_template: "Tell me more about {{topic}}."
variables:
  topic:
    type: string
    default: "Python"
```

### CommitRecord

```python
class CommitRecord(BaseModel):
    hash: str                    # Git commit hash（前 12 位）
    timestamp: datetime          # 提交时间
    changed_files: list[str]     # 变更文件列表
    validation_status: str       # 校验状态（pass/fail）
    message: str                 # 提交消息
```

### DiffResult

```python
@dataclass
class DiffResult:
    added_fields: list[str]          # 新增字段
    removed_fields: list[str]        # 删除字段
    modified_fields: list[FieldDiff] # 修改字段
    semantic_change_type: SemanticChangeType  # 语义变更类型
    risk_level: RiskLevel            # 风险等级
    summary: str                     # 变更摘要
    text_diff: list[str]             # 原始文本 diff
```

### EvalResult

```python
@dataclass
class EvalResult:
    total_samples: int           # 样本总数
    accuracy_old: float          # 旧版本准确率
    accuracy_new: float          # 新版本准确率
    accuracy_delta: float        # 准确率变化
    token_cost_old: int          # 旧版本 token 消耗
    token_cost_new: int          # 新版本 token 消耗
    token_cost_delta: float      # token 消耗变化
    consistency_score: float     # 一致性分数
    passed: bool                 # 是否通过阈值
    threshold: float             # 阈值设置
    details: list[SampleResult]  # 每个样本的详细结果
```

### LLMConfig

```python
@dataclass
class LLMConfig:
    provider: str = "openai"        # 提供商: openai/anthropic/azure/ollama/vllm/sglang
    model: str = "gpt-3.5-turbo"   # 模型名称
    temperature: float = 0.0
    max_tokens: int = 1024
    api_key: Optional[str] = None
    api_base: Optional[str] = None
```

### LLMJudgeResult

```python
@dataclass
class LLMJudgeResult:
    score: float           # 0.0 - 1.0
    reasoning: str         # 评分理由
    raw_response: str      # LLM 原始响应
```

### LLMEvalResult

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

---

## 命令流程

### `pg init`

```
用户输入                    处理流程                     输出
────────                    ──────────                   ──────
pg init
    │
    ▼
┌─────────────────┐
│ get_repo()      │  ──→ 检查是否在 Git 仓库
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ get_prompts_dir │  ──→ 获取 .prompts/ 路径
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ mkdir()         │  ──→ 创建目录
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 创建 config.json│  ──→ 写入默认配置
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 创建 .gitignore │  ──→ 忽略临时文件
└─────────────────┘
    │
    ▼
  Rich 表格输出
```

### `pg add`

```
用户输入                    处理流程                     输出
────────                    ──────────                   ──────
pg add file.yaml
    │
    ▼
┌─────────────────┐
│ 文件存在检查    │  ──→ FileNotFoundError
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 格式检查        │  ──→ .yaml/.yml/.json
└─────────────────┘
    │
    ▼
┌─────────────────────────┐
│ PromptTemplate.from_yaml│  ──→ Schema 验证
└─────────────────────────┘
    │
    ▼
┌─────────────────┐
│ shutil.copy2()  │  ──→ 复制到 .prompts/
└─────────────────┘
    │
    ▼
  Rich 表格输出
```

### `pg commit`

```
用户输入                    处理流程                     输出
────────                    ──────────                   ──────
pg commit -m "msg"
    │
    ▼
┌─────────────────────────┐
│ 遍历 .prompts/*.yaml    │  ──→ 收集变更文件
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ 逐个验证 PromptTemplate │  ──→ 校验状态
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ repo.index.add()        │  ──→ Git 暂存
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ repo.index.commit()     │  ──→ Git 提交
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ CommitRecord → JSONL    │  ──→ 记录到 commits.jsonl
└─────────────────────────┘
    │
    ▼
  Rich 表格输出
```

### `pg diff`

```
用户输入                    处理流程                     输出
────────                    ──────────                   ──────
pg diff [--semantic]
    │
    ▼
┌─────────────────────────┐
│ 从 Git 获取 HEAD 版本   │  ──→ old_content
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ 读取当前工作区版本      │  ──→ new_content
└─────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                      diff_prompts()                      │
│  ┌───────────────────────────────────────────────────┐ │
│  │ 1. PromptTemplate.from_yaml() × 2                 │ │
│  │    └─→ 解析并验证两个版本                          │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │ 2. compute_structured_diff(old_data, new_data)    │ │
│  │    └─→ 递归比较字段，生成 added/removed/modified   │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │ 3. compute_text_diff(old_text, new_text)          │ │
│  │    └─→ unified diff 输出                          │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │ 4. analyze_semantic_changes()                     │ │
│  │    ├─ extract_variables() → 变量变更检测           │ │
│  │    ├─ detect_tone_shift() → 语气偏移检测           │ │
│  │    └─ detect_role_shift() → 角色偏移检测           │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────┐
│   DiffResult    │
│  ├─ risk_level  │  ──→ LOW / MEDIUM / HIGH
│  ├─ change_type │  ──→ variable / constraint / tone / role
│  └─ summary     │  ──→ 人类可读摘要
└─────────────────┘
    │
    ▼
  Rich 表格 或 JSON 输出
```

### `pg eval`

```
用户输入                    处理流程                     输出
────────                    ──────────                   ──────
pg eval --dataset data.jsonl [--provider openai --model gpt-4 --judge]
    │
    ▼
┌─────────────────────────┐
│ load_dataset()          │  ──→ 解析 JSONL 文件
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ 从 Git 获取 old 版本    │  ──→ old_template
│ 读取当前 new 版本       │  ──→ new_template
└─────────────────────────┘
    │
    ├──────── 无 --provider ──────────────────── 有 --provider ──────┐
    ▼                                                                ▼
┌──────────────────────────────┐              ┌───────────────────────────────┐
│    evaluate_prompts()        │              │  evaluate_prompts_with_llm()  │
│    (规则引擎)                │              │  (LLM 增强)                   │
│                              │              │                               │
│  FOR EACH sample:            │              │  FOR EACH sample:             │
│    1. rule_based_render      │              │    1. rule_based_render       │
│    2. keyword_match          │              │    2. llm_generate_output     │
│    3. estimate_tokens        │              │    3. similarity / judge      │
│                              │              │                               │
│  聚合指标                    │              │  聚合指标                     │
└──────────────────────────────┘              └───────────────────────────────┘
    │                                                │
    └────────────────────┬───────────────────────────┘
                         ▼
              ┌─────────────────┐
              │   EvalResult /  │
              │   LLMEvalResult │
              │  ├─ accuracy    │  ──→ 准确率变化
              │  ├─ token_cost  │  ──→ 成本变化
              │  ├─ consistency │  ──→ 一致性分数
              │  └─ passed      │  ──→ 是否通过阈值
              └─────────────────┘
                         │
                         ▼
               Rich 表格 或 JSON 输出
```

### `pg ci init`

```
用户输入                    处理流程                     输出
────────                    ──────────                   ──────
pg ci init
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                      init_ci()                           │
│                                                          │
│  ┌───────────────────────────────────────────────────┐ │
│  │ 1. generate_workflow(CIConfig)                    │ │
│  │    └─→ .github/workflows/prompt-guard.yml         │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │ 2. generate_publish_workflow()                    │ │
│  │    └─→ .github/workflows/publish.yml              │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │ 3. generate_pre_commit_config(PreCommitConfig)    │ │
│  │    └─→ .pre-commit-config.yaml                    │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │ 4. generate_version_bump_script()                 │ │
│  │    └─→ scripts/bump_version.sh                    │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
    │
    ▼
  4 个文件写入磁盘
```

---

## 数据流动

### 整体数据流

```
                    ┌─────────────────┐
                    │   YAML 文件     │
                    │  (.prompts/)    │
                    └────────┬────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        schema.py                                 │
│  YAML/JSON ──→ yaml.safe_load() ──→ Pydantic.model_validate()   │
│                                  ──→ PromptTemplate              │
└─────────────────────────────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  diff_engine│  │  evaluator  │  │   ci_gen    │
    │             │  │             │  │             │
    │ old + new   │  │ template +  │  │ config →    │
    │      ↓      │  │ dataset     │  │    YAML     │
    │ DiffResult  │  │      ↓      │  │             │
    │             │  │ EvalResult  │  │             │
    └─────────────┘  └─────────────┘  └─────────────┘
              │              │              │
              ▼              ▼              ▼
    ┌─────────────────────────────────────────────┐
    │                   cli.py                     │
    │  结果 → Rich 表格 / JSON 输出               │
    │           ↓                                  │
    │  Exit Code: 0=成功, 1=参数错, 2=Git错, 3=校验错│
    └─────────────────────────────────────────────┘
```

### Git 数据流

```
┌──────────────────────────────────────────────────────────────┐
│                         Git Repository                        │
│                                                               │
│   Working Directory          Staging Area          HEAD       │
│   ─────────────────          ───────────          ─────       │
│   .prompts/                  git add              commit      │
│   ├─ config.json      ───→   .prompts/*.yaml  ───→  hash      │
│   ├─ qa_prompt.yaml                                    │       │
│   └─ commits.jsonl                                     │       │
│                                                        │       │
│   pg diff: ──→ 对比 Working Directory 与 HEAD          │       │
│   pg eval: ──→ 对比 Working Directory 与 HEAD          │       │
└──────────────────────────────────────────────────────────────┘
```

### 评估数据流

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   dataset.jsonl │     │  old_template   │     │  new_template   │
│                 │     │   (from HEAD)   │     │  (from working) │
│  {"input":...}  │     │                 │     │                 │
│  {"input":...}  │     │  system_prompt  │     │  system_prompt  │
│       ...       │     │  user_template  │     │  user_template  │
└────────┬────────┘     │  variables      │     │  variables      │
         │              └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      evaluate_prompts()                          │
│                                                                  │
│  FOR EACH sample:                                                │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │ 1. render(template, {input: sample.input})               │  │
│    │    └─→ "You are helpful.\n\nAnswer: What is Python?"     │  │
│    └─────────────────────────────────────────────────────────┘  │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │ 2. keyword_based_evaluate(rendered, expected)            │  │
│    │    ├─ extract_keywords(expected) → {"python", "language"}│  │
│    │    ├─ 检查关键词是否出现在 rendered 中                   │  │
│    │    └─→ match_ratio ≥ 0.5 → (expected, True)             │  │
│    └─────────────────────────────────────────────────────────┘  │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │ 3. estimate_tokens(rendered) → 15                        │  │
│    └─────────────────────────────────────────────────────────┘  │
│  END FOR                                                         │
│                                                                  │
│  聚合计算:                                                       │
│  ├─ accuracy_old = old_correct / total                          │
│  ├─ accuracy_new = new_correct / total                          │
│  ├─ accuracy_delta = new - old                                  │
│  ├─ token_cost_delta = (new_tokens - old) / old                 │
│  └─ consistency = matches / total                               │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│   EvalResult    │
│                 │
│  passed =       │
│  delta ≥ -threshold
└─────────────────┘
```

---

## 核心算法

### 1. 结构化 Diff 算法

```python
def compute_structured_diff(old_data: dict, new_data: dict, prefix=""):
    added, removed, modified = [], [], []
    
    for key in all_keys:
        if key only in new:
            added.append(key)
        elif key only in old:
            removed.append(key)
        elif old[key] != new[key]:
            if both are dict:
                # 递归比较嵌套结构
                sub_added, sub_removed, sub_modified = recurse()
            else:
                modified.append(FieldDiff(...))
    
    return added, removed, modified
```

**特点：**
- 递归处理嵌套字典
- 生成字段路径（如 `variables.question.default`）
- 区分 added/removed/modified 三种变更类型

### 2. 语义分析算法

```python
def analyze_semantic_changes(old, new):
    change_types = set()
    risk_factors = []
    
    # 1. 变量变更检测
    old_vars = extract_variables(old.user_template)  # regex: \{\{(\w+)\}\}
    new_vars = extract_variables(new.user_template)
    if removed_vars:
        risk_factors.append(HIGH)  # 删除变量可能破坏调用方
    
    # 2. 约束变更检测
    old_constraints = set(old.constraints)
    new_constraints = set(new.constraints)
    if removed_constraints:
        risk_factors.append(MEDIUM)
    
    # 3. 语气偏移检测
    has_tone_shift = detect_tone_shift(old_text, new_text)
    # 检测关键词: formal/casual/technical/friendly
    
    # 4. 角色偏移检测
    has_role_shift = detect_role_shift(old_system, new_system)
    # 正则匹配: "you are a/an ..." / "你是..."
    
    # 风险等级: HIGH > MEDIUM > LOW
    return change_type, risk_level, summary
```

**风险等级判定：**

| 条件 | 风险 |
|------|------|
| 变量删除 | 🔴 HIGH |
| 角色偏移 | 🔴 HIGH |
| 约束删除 | 🟡 MEDIUM |
| 语气偏移 | 🟡 MEDIUM |
| 变量添加 | 🟢 LOW |
| 约束添加 | 🟢 LOW |
| 元数据变更 | 🟢 LOW |

### 3. 关键词评估算法

```python
def keyword_based_evaluate(rendered_prompt, expected_output):
    # 1. 提取期望输出的关键词
    expected_keywords = extract_keywords(expected_output)
    # 英文: [a-z]{2,}，中文: [\u4e00-\u9fff]{2,4}
    
    # 2. 检查 prompt 中是否包含这些关键词
    matched = {kw for kw in expected_keywords if kw in prompt_lower}
    match_ratio = len(matched) / len(expected_keywords)
    
    # 3. 模拟输出
    if match_ratio >= 0.5:
        return expected_output, True      # 完全匹配
    elif match_ratio >= 0.2:
        return partial_output, False      # 部分匹配
    else:
        return "[no relevant output]", False  # 无匹配
```

**关键词提取策略：**
- 英文：正则 `[a-z]{2,}`，过滤停用词
- 中文：正则 `[\u4e00-\u9fff]{2,4}`，过滤单字
- 停用词表：包含常见英文/中文停用词

### 4. Token 估算算法

```python
def estimate_tokens(text):
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    ascii_count = len(text) - cjk_count
    
    # 启发式估算
    tokens = ascii_count / 4 + cjk_count / 1.5
    return int(tokens)
```

---

## 文件结构

### 运行时文件结构

```
project-root/
├── .prompts/                    # Prompt 版本控制目录
│   ├── config.json              # 项目配置
│   ├── .gitignore               # 忽略临时文件
│   ├── commits.jsonl            # 提交记录（自动生成）
│   ├── qa_prompt.yaml           # 被追踪的 Prompt 文件
│   └── code_prompt.yaml
├── fixtures/                    # 测试数据集
│   └── dataset.jsonl
├── .github/workflows/           # CI 配置
│   ├── prompt-guard.yml
│   └── publish.yml
└── .pre-commit-config.yaml      # Pre-commit 钩子
```

### 配置文件格式

**.prompts/config.json:**
```json
{
  "version": "0.2.0",
  "created_at": "2026-05-04T10:30:00",
  "eval_threshold": 0.05,
  "model_provider": "openai",
  "default_model": "gpt-3.5-turbo"
}
```

**commits.jsonl（每行一个记录）:**
```json
{"hash":"abc123def456","timestamp":"2026-05-04T10:30:00","changed_files":[".prompts/qa.yaml"],"validation_status":"pass","message":"Initial commit"}
```

**dataset.jsonl（每行一个样本）:**
```json
{"input":"What is Python?","expected_output":"Python is a programming language","metadata":{"category":"qa"}}
```

---

## 依赖关系

### 模块依赖图

```
cli.py
  ├── schema.py        (PromptTemplate, CommitRecord)
  ├── utils.py         (get_repo, render_table, error_exit)
  ├── diff_engine.py   (diff_prompts, DiffResult)
  ├── evaluator.py     (load_dataset, evaluate_prompts)
  ├── llm_evaluator.py (get_llm_config, evaluate_prompts_with_llm, compare_models)
  └── ci_gen.py        (init_ci)

diff_engine.py
  └── schema.py        (PromptTemplate)

evaluator.py
  └── schema.py        (PromptTemplate)

llm_evaluator.py
  ├── evaluator.py     (EvalSample, EvalResult, compute_similarity, rule_based_render)
  └── schema.py        (PromptTemplate)

ci_gen.py
  └── (无内部依赖)
```

### 外部依赖

| 包 | 用途 | 模块 |
|---|------|------|
| `typer` | CLI 框架 | cli.py |
| `pydantic` | 数据验证 | schema.py |
| `gitpython` | Git 操作 | utils.py, cli.py |
| `rich` | 终端渲染 | utils.py, cli.py |
| `pyyaml` | YAML 解析 | schema.py, ci_gen.py |
| `litellm` | LLM 多提供商调用 | llm_evaluator.py（可选依赖） |

---

## 错误处理

### 错误码定义

```python
ERR_SUCCESS = 0      # 成功
ERR_ARGS = 1         # 参数错误
ERR_GIT = 2          # Git 操作错误
ERR_VALIDATION = 3   # 校验错误
```

### 错误传播路径

```
异常发生
    │
    ▼
error_exit(message, code)
    │
    ▼
console.print(f"[red]Error:[/red] {message}")
    │
    ▼
raise typer.Exit(code=code)
    │
    ▼
CLI 退出，返回错误码
```

### 各模块错误处理

| 模块 | 异常类型 | 处理方式 |
|------|---------|---------|
| schema.py | FileNotFoundError, ValueError | 向上抛出 |
| utils.py | InvalidGitRepositoryError | error_exit(ERR_GIT) |
| cli.py | GitCommandError | error_exit(ERR_GIT) |
| diff_engine.py | FileNotFoundError, ValueError | 向上抛出 |
| evaluator.py | ValueError (空数据集) | 向上抛出 |

---

## 扩展点

### 1. 自定义评估函数

```python
# evaluator.py 支持自定义渲染函数
def evaluate_prompts(
    old_template, new_template, dataset,
    threshold=0.05,
    render_fn: Optional[RenderFunction] = None  # 可注入
):
    if render_fn is None:
        render_fn = rule_based_render  # 默认使用规则引擎
```

**扩展示例：接入 LLM**
```python
def llm_render(template, variables):
    rendered = rule_based_render(template, variables)
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": rendered}]
    )
    return response.choices[0].message.content

result = evaluate_prompts(old, new, dataset, render_fn=llm_render)
```

### 2. 自定义 CI 配置

```python
# ci_gen.py 支持自定义配置
config = CIConfig(
    branches=["main", "release/*"],
    threshold=0.10,
    model_provider="openai",
    enable_eval=True,
)
generate_workflow(config)
```

### 3. 新增语义检测

```python
# diff_engine.py 可扩展检测器
def analyze_semantic_changes(old, new, ...):
    # 现有检测
    ...
    
    # 扩展：新增意图偏移检测
    if detect_intent_shift(old, new):
        change_types.add(SemanticChangeType.INTENT_SHIFT)
```

---

## 性能特征

| 操作 | 时间复杂度 | 瓶颈 |
|------|-----------|------|
| `pg init` | O(1) | 文件 I/O |
| `pg add` | O(1) | Schema 验证 |
| `pg commit` | O(n) | n = prompt 文件数 |
| `pg diff` | O(n*m) | n = 字段数, m = 嵌套深度 |
| `pg eval` | O(n*s) | n = 样本数, s = 模板大小 |

---

## 测试覆盖

```
tests/
├── conftest.py           # Fixtures: Git 仓库、Prompt 文件、数据集等
│
├── test_cli.py           # 14 个测试
│   ├── init: 正常/干跑/非Git/幂等
│   ├── add: 正常/干跑/缺失/无效/格式
│   └── commit: 正常/干跑/无目录/无变更/校验警告
│
├── test_diff.py          # 29 个测试
│   ├── extract_variables: 单变量/多变量/无变量/重复/中文
│   ├── tone_shift: 无偏移/正式→随意/中文/相同/空
│   ├── role_shift: 无偏移/英文/中文/无角色/空
│   ├── structured_diff: 相同/新增/删除/修改/嵌套
│   ├── diff_prompts: 相同/变量变更/约束删除/角色偏移/JSON输出
│   └── edge_cases: 空约束/混合变更/多语言/仅版本
│
├── test_eval.py          # 33 个测试
│   ├── load_dataset: 正常/空/缺失/无效/元数据
│   ├── token_estimation: 英文/中文/空/混合
│   ├── similarity: 相同/完全不同/空/单空/部分
│   ├── keyword_extraction: 英文/中文/空
│   ├── keyword_evaluation: 匹配/不匹配/空期望
│   ├── rule_based_render: 基本/默认/覆盖
│   ├── evaluate_prompts: 相同/阈值失败/空数据集/token/JSON
│   └── edge_cases: 空约束/多语言/变量冲突/长文本/一致性
│
├── test_llm_eval.py      # 32 个测试
│   ├── LLMConfig: 默认值/自定义/提供商前缀/Azure
│   ├── get_llm_config: 基本/API Key/API Base/环境变量/Azure
│   ├── call_llm: 成功/system_prompt/ImportError
│   ├── llm_judge_evaluate: 成功/无效JSON/部分JSON
│   ├── llm_generate_output: 成功/错误
│   ├── evaluate_prompts_with_llm: 基本/judge/空数据集
│   └── compare_models: 基本/无效JSON/多样本
│
└── test_ci_gen.py        # 42 个测试
    ├── workflow_generation: YAML/名称/分支/路径/权限/并发/步骤
    ├── pre_commit: YAML/仓库/钩子/级别/文件模式
    ├── publish_workflow: YAML/触发/权限/步骤/密钥
    ├── version_bump: 内容/sed/git
    ├── init_ci: 干跑/文件/目录/内容/自定义
    └── edge_cases: 空分支/特殊字符/禁用功能/Unicode

总计: 150 个测试
```

---

## 附录：完整数据流图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户工作流                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
    ┌───────────────────────────────┼───────────────────────────────┐
    │                               │                               │
    ▼                               ▼                               ▼
┌────────┐                    ┌────────┐                    ┌────────┐
│ pg init│                    │pg add  │                    │pg commit│
└────┬───┘                    └────┬───┘                    └────┬───┘
     │                             │                             │
     ▼                             ▼                             ▼
┌─────────┐                  ┌─────────┐                  ┌─────────┐
│创建目录  │                  │验证Schema│                  │Git 提交  │
│写入配置  │                  │复制文件  │                  │记录JSONL │
└─────────┘                  └─────────┘                  └─────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
              ┌──────────┐                    ┌──────────┐
              │ pg diff  │                    │ pg eval  │
              └────┬─────┘                    └────┬─────┘
                   │                               │
                   ▼                               ▼
         ┌─────────────────┐             ┌─────────────────┐
         │ 1. 获取 HEAD    │             │ 1. 加载数据集   │
         │ 2. 结构化 Diff  │             │ 2. 渲染模板     │
         │ 3. 语义分析     │             │ 3. 关键词匹配   │
         │ 4. 风险评估     │             │ 4. 计算指标     │
         └────────┬────────┘             └────────┬────────┘
                  │                               │
                  ▼                               ▼
           ┌─────────────┐                ┌─────────────┐
           │ DiffResult  │                │ EvalResult  │
           │ - risk_level│                │ - accuracy  │
           │ - change    │                │ - token_cost│
           │ - summary   │                │ - passed    │
           └─────────────┘                └─────────────┘
                  │                               │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │      CI 集成            │
                    │                         │
                    │  pg ci init             │
                    │  ├─ prompt-guard.yml    │
                    │  ├─ publish.yml         │
                    │  └─ pre-commit-config   │
                    └─────────────────────────┘
```
