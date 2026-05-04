# prompt-git-manager CLI Reference

> Git-native prompt version control & CI guardrail tool.

## Installation

```bash
# Using uv (recommended)
uv pip install prompt-git-manager

# Using pip
pip install prompt-git-manager

# From source
git clone https://github.com/ChanChiChoi/prompt-git-manager.git
cd prompt-git-manager
uv sync
```

## Global Options

```bash
pg [OPTIONS] COMMAND [ARGS]...
```

| Option | Short | Description |
|--------|-------|-------------|
| `--version` | `-v` | Show version and exit |
| `--help` | `-h` | Show help message and exit |

## Commands

### `pg init`

Initialize `.prompts/` directory and metadata in the current Git repository.

```bash
pg init [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview without creating files |
| `--help` | Show help message |

**Examples:**

```bash
# Initialize in current directory
pg init

# Preview what would be created
pg init --dry-run
```

**Output:**

```
✓ Initialized prompt-git-manager in /path/to/.prompts
┌───────────┬───────────────────────────────────┐
│ Item      │ Path                              │
├───────────┼───────────────────────────────────┤
│ Directory │ /path/to/.prompts                 │
│ Config    │ /path/to/.prompts/config.json     │
└───────────┴───────────────────────────────────┘
```

---

### `pg add`

Add a prompt file to version tracking.

```bash
pg add [OPTIONS] FILE
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `FILE` | Yes | Prompt file to add (YAML/JSON) |

**Options:**

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview without copying file |
| `--help` | Show help message |

**Examples:**

```bash
# Add a prompt file
pg add my_prompt.yaml

# Preview what would be added
pg add my_prompt.yaml --dry-run
```

**Validation:**

The file must conform to the PromptTemplate schema:
- `name` (required): Prompt name
- `version` (optional): Semantic version
- `system_prompt` (required): System prompt text
- `user_template` (required): User message template
- `variables` (optional): Variable definitions
- `constraints` (optional): Behavioral constraints
- `metadata` (optional): Arbitrary metadata

**Output:**

```
✓ Added my_prompt.yaml to prompt tracking
┌─────────────┬────────────────────────┐
│ Field       │ Value                  │
├─────────────┼────────────────────────┤
│ Name        │ my-prompt              │
│ Version     │ 1.0.0                  │
│ Variables   │ question, context      │
│ Constraints │ 3                      │
│ Path        │ .prompts/my_prompt.yaml│
└─────────────┴────────────────────────┘
```

---

### `pg commit`

Commit prompt changes with a structured record.

```bash
pg commit [OPTIONS]
```

**Options:**

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--message` | `-m` | Yes | Commit message |
| `--dry-run` | | | Preview commit without executing |
| `--help` | | | Show help message |

**Examples:**

```bash
# Commit with message
pg commit -m "Update QA prompt v2"

# Preview commit
pg commit -m "Test changes" --dry-run
```

**Commit Record:**

Each commit generates a structured record in `.prompts/commits.jsonl`:

```json
{
  "hash": "abc123def456",
  "timestamp": "2026-05-04T10:30:00",
  "changed_files": [".prompts/qa_prompt.yaml"],
  "validation_status": "pass",
  "message": "Update QA prompt v2"
}
```

**Output:**

```
✓ Committed 1 prompt file(s)
┌──────────────┬─────────────────────────┐
│ Field        │ Value                   │
├──────────────┼─────────────────────────┤
│ Hash         │ abc123def456            │
│ Timestamp    │ 2026-05-04T10:30:00     │
│ Files        │ 1                       │
│ Validation   │ pass                    │
│ Message      │ Update QA prompt v2     │
└──────────────┴─────────────────────────┘
```

---

### `pg diff`

Show diff between current prompts and HEAD.

```bash
pg diff [OPTIONS] [FILE]
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `FILE` | No | Specific prompt file to diff |

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--semantic` | `-s` | Show semantic diff with risk analysis |
| `--json` | `-j` | Output diff as JSON |
| `--fail-on` | | Exit with error if risk level >= this value (`low`/`med`/`high`) |
| `--help` | | Show help message |

**Examples:**

```bash
# Show all prompt changes
pg diff

# Show semantic diff with risk analysis
pg diff --semantic

# Diff specific file
pg diff .prompts/qa_prompt.yaml

# JSON output for CI integration
pg diff --json > diff_result.json

# Fail on high-risk changes (for CI/pre-commit)
pg diff --fail-on=high

# Fail on medium or high-risk changes
pg diff --fail-on=med
```

**Semantic Analysis:**

The `--semantic` flag analyzes:
- **Variable changes**: Added/removed `{{variables}}`
- **Constraint changes**: Added/removed behavioral constraints
- **Tone shifts**: Formal ↔ Casual, Technical ↔ Friendly
- **Role shifts**: Assistant persona changes

**Risk Levels:**

| Level | Description | Action |
|-------|-------------|--------|
| 🟢 LOW | Minor changes, no semantic impact | Standard review |
| 🟡 MEDIUM | Constraint or tone changes | Review + evaluation |
| 🔴 HIGH | Role or variable removal | Manual approval required |

**Output (Semantic):**

```
┌─────────────────────────────────────────────────┐
│ Diff: .prompts/qa_prompt.yaml                   │
├──────────────┬──────────────────────────────────┤
│ Risk Level   │ 🟡 MEDIUM                        │
│ Change Type  │ constraint_change                │
│ Summary      │ Removed 1 constraint             │
│ Added Fields │                                  │
│ Removed Fields │ constraints[1]                 │
│ Modified     │ version: 1.0.0 → 2.0.0          │
└──────────────┴──────────────────────────────────┘
```

---

### `pg eval`

Evaluate prompt versions against a dataset.

```bash
pg eval [OPTIONS]
```

**Options:**

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--dataset` | `-d` | Yes | Path to dataset JSONL file |
| `--old` | | No | Old prompt file (default: HEAD version) |
| `--new` | | No | New prompt file (default: current version) |
| `--threshold` | `-t` | No | Accuracy drop threshold (default: env `PROMPT_GIT_THRESHOLD` or `0.05`) |
| `--json` | `-j` | No | Output as JSON |
| `--provider` | `-p` | No | LLM provider (openai, anthropic, azure, ollama, vllm, sglang) |
| `--model` | `-m` | No | LLM model name (e.g., gpt-4, claude-3-opus-20240229) |
| `--api-base` | | No | Custom API base URL (for proxies or local models) |
| `--judge` | | No | Enable LLM-as-judge evaluation mode |
| `--judge-provider` | | No | Judge LLM provider (if different from main provider) |
| `--judge-model` | | No | Judge LLM model (e.g., gpt-4 for judging gpt-3.5 outputs) |
| `--compare-models` | `-c` | No | Compare models. Format: 'model1,model2' or 'provider1:model1,provider2:model2' |
| `--help` | | No | Show help message |

**Examples:**

```bash
# Rule-based evaluation (offline, no API needed)
pg eval --dataset fixtures/dataset.jsonl

# LLM-enhanced evaluation
pg eval --dataset data.jsonl --provider openai --model gpt-4

# LLM-as-judge evaluation (more accurate)
pg eval --dataset data.jsonl --provider openai --model gpt-4 --judge

# LLM-as-judge with separate judge model (recommended)
pg eval --dataset data.jsonl --provider openai --model gpt-3.5-turbo --judge --judge-model gpt-4

# Local model with cloud judge
pg eval --dataset data.jsonl --provider ollama --model llama2 --judge --judge-provider openai --judge-model gpt-4

# Custom API base (proxy, private deployment)
pg eval --dataset data.jsonl --provider openai --model gpt-4 \
  --api-base "https://your-proxy.com/v1"

# Use Anthropic
pg eval --dataset data.jsonl --provider anthropic --model claude-3-opus-20240229

# Use Ollama local model
pg eval --dataset data.jsonl --provider ollama --model llama2

# Compare models from same provider
pg eval --dataset data.jsonl --compare-models gpt-3.5-turbo,gpt-4

# Compare models from different providers (use provider:model format)
pg eval --dataset data.jsonl --compare-models openai:gpt-4,anthropic:claude-3-opus-20240229

# Compare local and cloud models
pg eval --dataset data.jsonl --compare-models ollama:llama2,openai:gpt-4

# Custom threshold
pg eval -d data.jsonl -t 0.10

# Compare specific files
pg eval --old .prompts/v1.yaml --new .prompts/v2.yaml -d data.jsonl

# JSON output
pg eval -d data.jsonl --json > eval_result.json
```

**Dataset Format:**

```jsonl
{"input": "What is Python?", "expected_output": "Python is a programming language", "metadata": {"category": "qa"}}
{"input": "Explain Git", "expected_output": "Git is a version control system", "metadata": {"category": "tech"}}
```

**Metrics:**

| Metric | Description |
|--------|-------------|
| `accuracy_old` | Accuracy with old prompt |
| `accuracy_new` | Accuracy with new prompt |
| `accuracy_delta` | Change in accuracy (-1 to +1) |
| `token_cost_old` | Estimated tokens with old prompt |
| `token_cost_new` | Estimated tokens with new prompt |
| `token_cost_delta` | Change in token cost |
| `consistency_score` | Agreement between old/new (0-1) |

**Exit Codes:**

| Code | Status | Description |
|------|--------|-------------|
| 0 | PASSED | Accuracy within threshold |
| 2 | FAILED | Accuracy dropped below threshold |

**Output (Rule-based):**

```
┌────────────────────┬────────────────┐
│ Metric             │ Value          │
├────────────────────┼────────────────┤
│ Total Samples      │ 20             │
│ Accuracy (Old)     │ 85.0%          │
│ Accuracy (New)     │ 80.0%          │
│ Accuracy Delta     │ -5.0%          │
│ Token Cost (Old)   │ 1250           │
│ Token Cost (New)   │ 1180           │
│ Token Cost Delta   │ -5.6%          │
│ Consistency Score  │ 75.0%          │
│ Status             │ ✅ PASSED      │
│ Threshold          │ 5.0%           │
└────────────────────┴────────────────┘
```

**Output (LLM-enhanced):**

```
┌────────────────────┬────────────────┐
│ Metric             │ Value          │
├────────────────────┼────────────────┤
│ Total Samples      │ 20             │
│ Accuracy (Old)     │ 90.0%          │
│ Accuracy (New)     │ 85.0%          │
│ Accuracy Delta     │ -5.0%          │
│ Token Cost (Old)   │ 1500           │
│ Token Cost (New)   │ 1450           │
│ Token Cost Delta   │ -3.3%          │
│ Consistency Score  │ 80.0%          │
│ Status             │ ✅ PASSED      │
│ Threshold          │ 5.0%           │
│ Provider           │ openai         │
│ Model              │ gpt-4          │
│ Judge Mode         │ LLM-as-judge   │
└────────────────────┴────────────────┘
```

**Output (Model Comparison):**

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

---

## Error Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 0 | Success | Command completed successfully |
| 1 | Argument error | Invalid arguments, missing files |
| 2 | Git error | Not a git repo, git operation failed |
| 3 | Validation error | Invalid prompt schema |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROMPT_GIT_MODEL` | LLM model for evaluation | `none` |
| `PROMPT_GIT_THRESHOLD` | Default eval threshold | `0.05` |
| `PROMPT_GIT_EDITOR` | Editor for commit messages | `$EDITOR` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `OPENAI_API_BASE` | OpenAI API base URL | `https://api.openai.com/v1` |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `OLLAMA_API_BASE` | Ollama API base URL | `http://localhost:11434` |
| `VLLM_API_BASE` | vLLM API base URL | `http://localhost:8000/v1` |
| `SGLANG_API_BASE` | SGLang API base URL | `http://localhost:30000/v1` |

---

## Configuration

The `.prompts/config.json` file stores project settings:

```json
{
  "version": "0.2.0",
  "created_at": "2026-05-04T10:30:00",
  "eval_threshold": 0.05,
  "model_provider": "openai",
  "default_model": "gpt-3.5-turbo",
  "auto_validate": true,
  "commit_hooks": true
}
```

---

## CI/CD Integration

### GitHub Actions

```yaml
- name: Prompt Guard
  run: |
    uv run pg diff --semantic --json > diff.json
    uv run pg eval -d fixtures/dataset.jsonl --threshold 0.05
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: prompt-guard
        name: Prompt Guard
        entry: pg eval -d fixtures/dataset.jsonl
        language: system
        files: '\.prompts/.*\.yaml$'
```

---

## Examples

### Basic Workflow

```bash
# 1. Initialize
pg init

# 2. Add prompts
pg add examples/qa_prompt.yaml
pg add examples/code_prompt.yaml

# 3. Commit
pg commit -m "Initial prompt setup"

# 4. Make changes
vim .prompts/qa_prompt.yaml

# 5. Review changes
pg diff --semantic

# 6. Evaluate
pg eval -d fixtures/dataset.jsonl

# 7. Commit if passed
pg commit -m "Update QA prompt v2"
```

### CI Pipeline

```bash
# In CI environment
pg diff --json > diff_report.json
pg eval -d fixtures/dataset.jsonl --json --threshold 0.05
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo "Prompt evaluation failed!"
  exit 1
fi
```

---

## See Also

- [README](../README.md) - Project overview
- [Architecture](architecture.md) - System design
- [Examples](../examples/) - Example prompts
