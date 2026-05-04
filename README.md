# prompt-git-manager

<p align="center">
  <strong>Git-native prompt version control & CI guardrail tool</strong>
</p>

<p align="center">
  <a href="#installation">Installation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#commands">Commands</a> •
  <a href="#ci-integration">CI Integration</a> •
  <a href="#contributing">Contributing</a> •
  <a href="./README_zh.md">中文</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/tests-passing-brightgreen.svg" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-74%25-yellow.svg" alt="Coverage">
</p>

---

## Why prompt-git-manager?

### The Problem

Prompt engineering is becoming critical to AI applications, but managing prompts is chaotic:

- 🔀 **No version control**: Prompts scattered in code, docs, and chat logs
- 📊 **No metrics**: Can't measure if changes improve or degrade performance
- 🚫 **No guardrails**: Breaking changes ship without detection
- 🔍 **No diff tools**: Text diff is meaningless for structured prompts

### The Solution

**prompt-git-manager** brings software engineering best practices to prompt management:

| Feature | Traditional Approach | prompt-git-manager |
|---------|---------------------|------------|
| Version Control | Copy-paste in docs | Git-native commits |
| Change Detection | Manual review | Semantic diff |
| Quality Gates | Hope for the best | Automated evaluation |
| Rollback | "What was the old prompt?" | `git checkout` |

### Key Differentiators

- **Zero Infrastructure**: No servers, no databases, no SaaS dependencies
- **Git Native**: Prompts are files, versions are commits
- **CI First**: Built for GitHub Actions, pre-commit, and PR workflows
- **Offline Capable**: Works without LLM API access (rule-based evaluation)

---

## Installation

### Using uv (Recommended)

```bash
uv pip install prompt-git-manager
```

### Using pip

```bash
pip install prompt-git-manager
```

### From Source

```bash
git clone https://github.com/ChanChiChoi/prompt-git-manager.git
cd prompt-git-manager
uv sync
```

### Verify Installation

```bash
pg --version
# prompt-git-manager 0.1.0
```

---

## Quick Start

### 1. Initialize a Project

```bash
cd your-project
pg init
```

This creates:
```
.prompts/
├── config.json      # Project settings
└── .gitignore       # Internal files
```

### 2. Add Your Prompts

```bash
# Create a prompt file
cat > qa_prompt.yaml << 'EOF'
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
  author: your-name
EOF

# Add to tracking
pg add qa_prompt.yaml
```

### 3. Commit Changes

```bash
pg commit -m "Initial QA prompt"
```

### 4. Review Changes

```bash
# Make some changes to the prompt...
vim .prompts/qa_prompt.yaml

# See semantic diff
pg diff --semantic
```

### 5. Evaluate Against Dataset

```bash
# Create a test dataset
cat > fixtures/dataset.jsonl << 'EOF'
{"input": "What is Python?", "expected_output": "Python is a programming language"}
{"input": "What is Git?", "expected_output": "Git is a version control system"}
EOF

# Run evaluation
pg eval --dataset fixtures/dataset.jsonl --threshold 0.05
```

---

## Commands

### `pg init`

Initialize prompt-git-manager in your repository.

```bash
pg init [--dry-run]
```

### `pg add`

Add a prompt file to version tracking.

```bash
pg add <file> [--dry-run]
```

**Supported formats:** YAML (.yaml, .yml), JSON (.json)

**Required fields:**
- `name`: Prompt identifier
- `system_prompt`: System message
- `user_template`: User message template with `{{variables}}`

### `pg commit`

Commit prompt changes with structured metadata.

```bash
pg commit -m "message" [--dry-run]
```

**Generates commit record:**
```json
{
  "hash": "abc123",
  "timestamp": "2024-01-15T10:30:00",
  "changed_files": [".prompts/qa_prompt.yaml"],
  "validation_status": "pass",
  "message": "Update QA prompt"
}
```

### `pg diff`

Show differences between prompt versions.

```bash
pg diff [file] [--semantic] [--json]
```

**Semantic Analysis:**
- Variable changes (`{{old_var}}` → `{{new_var}}`)
- Constraint changes (added/removed rules)
- Tone shifts (formal ↔ casual)
- Role shifts (assistant persona changes)

**Risk Levels:**
- 🟢 **LOW**: Minor changes, no semantic impact
- 🟡 **MEDIUM**: Constraint or tone changes
- 🔴 **HIGH**: Role or variable removal

### `pg eval`

Evaluate prompts against a dataset.

```bash
pg eval --dataset <file.jsonl> [--threshold 0.05] [--json]
```

**Dataset Format:**
```jsonl
{"input": "question", "expected_output": "answer", "metadata": {}}
```

**Metrics:**
- `accuracy_delta`: Change in accuracy (-1 to +1)
- `token_cost_delta`: Change in token usage
- `consistency_score`: Agreement between versions (0-1)

### `pg ci init`

Generate CI/CD configuration files.

```bash
pg ci init [--dry-run]
```

**Generates:**
- `.github/workflows/prompt-guard.yml` - GitHub Actions workflow
- `.pre-commit-config.yaml` - Pre-commit hooks
- `scripts/bump_version.sh` - Version management

---

## CI Integration

### GitHub Actions

#### Automatic Setup

```bash
pg ci init
```

#### Manual Setup

Create `.github/workflows/prompt-guard.yml`:

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

      - name: Install prompt-git-manager
        run: pip install prompt-git-manager

      - name: Run diff
        run: pg diff --semantic --json > diff.json

      - name: Run evaluation
        run: pg eval --dataset fixtures/dataset.jsonl --threshold 0.05

      - name: Comment PR
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
              body: `## ❌ Prompt Guard Failed\n\n\`\`\`json\n${diff}\n\`\`\``
            });
```

### Pre-commit Hooks

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

Install hooks:
```bash
pre-commit install
```

### Local CI Script

```bash
#!/bin/bash
# scripts/ci_check.sh

set -e

echo "Running prompt checks..."

# Run diff
pg diff --semantic --json > diff.json

# Run evaluation
pg eval --dataset fixtures/dataset.jsonl --threshold 0.05 --json > eval.json

echo "All checks passed!"
```

---

## Configuration

### Project Config

`.prompts/config.json`:
```json
{
  "version": "0.1.0",
  "eval_threshold": 0.05,
  "model_provider": "openai",
  "default_model": "gpt-3.5-turbo",
  "auto_validate": true
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROMPT_GIT_MODEL` | LLM model for evaluation | `none` |
| `PROMPT_GIT_THRESHOLD` | Default eval threshold | `0.05` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |

---

## Benchmark

### Performance

| Operation | Time | Notes |
|-----------|------|-------|
| `pg init` | <100ms | Creates directory structure |
| `pg add` | <200ms | Validates + copies file |
| `pg commit` | <500ms | Git commit + record |
| `pg diff` | <300ms | Structured diff analysis |
| `pg eval` (20 samples) | <1s | Rule-based evaluation |
| `pg eval` (100 samples) | <5s | Rule-based evaluation |

### Test Coverage

| Module | Coverage |
|--------|----------|
| cli.py | 42% |
| schema.py | 90% |
| diff_engine.py | 90% |
| evaluator.py | 99% |
| ci_gen.py | - |
| **Total** | **74%** |

### Test Count

| Suite | Tests |
|-------|-------|
| test_cli.py | 14 |
| test_diff.py | 29 |
| test_eval.py | 33 |
| test_ci_gen.py | 40+ |
| **Total** | **116+** |

---

## Architecture

```
prompt-git-manager/
├── src/promptgit/
│   ├── __init__.py          # Version
│   ├── cli.py               # Typer CLI entry point
│   ├── schema.py            # Pydantic models
│   ├── diff_engine.py       # Semantic diff engine
│   ├── evaluator.py         # Dataset evaluation
│   ├── ci_gen.py            # CI/CD generator
│   └── utils.py             # Git + Rich helpers
├── tests/
│   ├── conftest.py          # Fixtures
│   ├── test_cli.py
│   ├── test_diff.py
│   ├── test_eval.py
│   └── test_ci_gen.py
├── fixtures/
│   ├── dataset.jsonl        # Test dataset
│   └── prompts/             # Edge case prompts
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

## Contributing

### Development Setup

```bash
# Clone repository
git clone https://github.com/ChanChiChoi/prompt-git-manager.git
cd prompt-git-manager

# Install with dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=promptgit --cov-report=html
```

### Code Style

- Python 3.10+ with type hints
- Pydantic for data validation
- Typer for CLI
- Rich for terminal output
- pytest for testing

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Running Checks

```bash
# Type checking
uv run mypy src/

# Linting
uv run ruff check src/

# Format
uv run ruff format src/

# All tests
uv run pytest -v
```

### Releasing

```bash
# Bump version
./scripts/bump_version.sh patch  # or minor, major

# Push with tags
git push && git push --tags

# GitHub Action will publish to PyPI automatically
```

---

## Quick PR Demo with gh CLI

### Create a PR with Prompt Changes

```bash
# 1. Create feature branch
git checkout -b feature/update-qa-prompt

# 2. Make prompt changes
vim .prompts/qa_prompt.yaml

# 3. Commit with prompt-git-manager
pg commit -m "Improve QA prompt accuracy"

# 4. Push branch
git push -u origin feature/update-qa-prompt

# 5. Create PR with gh CLI
gh pr create \
  --title "Improve QA prompt accuracy" \
  --body "$(cat <<'EOF'
## Summary
- Updated system prompt for better context understanding
- Added few-shot examples to user template
- Adjusted constraints for more consistent outputs

## Prompt Diff
$(pg diff --semantic)

## Evaluation Results
$(pg eval --dataset fixtures/dataset.jsonl --json)

## Checklist
- [x] Semantic diff reviewed
- [x] Evaluation passed (threshold: 5%)
- [ ] Team review
EOF
)"

# 6. View PR
gh pr view --web
```

### Check PR Status

```bash
# List open PRs
gh pr list

# View specific PR
gh pr view 42

# Check CI status
gh pr checks 42

# Merge when ready
gh pr merge 42 --squash
```

---

## FAQ

### Q: Why not use Langfuse/Weights & Biases?

**A:** Those are great runtime monitoring tools. prompt-git-manager focuses on **development-time** workflow:
- Git-native (no new tool to learn)
- CI-first (catches issues before deploy)
- Zero infrastructure (no servers to maintain)

### Q: Can I use this with private prompts?

**A:** Yes! Prompts stay in your private Git repo. No data is sent externally unless you enable LLM evaluation.

### Q: How does rule-based evaluation work?

**A:** Without LLM APIs, we use keyword matching and text similarity as heuristics. It's less accurate but:
- Works offline
- No API costs
- Fast execution
- Deterministic results

### Q: What prompt formats are supported?

**A:** YAML and JSON with this structure:
```yaml
name: string
version: string
system_prompt: string
user_template: string  # with {{variables}}
variables: {}
constraints: []
metadata: {}
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [GitPython](https://gitpython.readthedocs.io/) - Git integration
- [Rich](https://rich.readthedocs.io/) - Terminal formatting

---

<p align="center">
  Made with ❤️ for the AI engineering community
</p>
