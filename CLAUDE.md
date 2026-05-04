# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**prompt-git-manager** is a Git-native prompt version control and CI guardrail tool. It brings software engineering practices (version control, semantic diff, evaluation, CI gates) to prompt engineering. CLI command: `pg`.

## Development Commands

```bash
# Install dependencies (including dev)
uv sync --extra dev

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_diff.py -v

# Run a specific test
uv run pytest tests/test_diff.py::test_function_name -v

# Run with coverage
uv run pytest --cov=promptgit --cov-report=html

# Linting
uv run ruff check src/

# Formatting
uv run ruff format src/

# Type checking
uv run mypy src/

# Build package
python -m build

# Version bump
./scripts/bump_version.sh patch  # or minor, major
```

## Architecture

The source code lives in `src/promptgit/` with these core modules:

- **cli.py** — Typer CLI entry point. Defines the `pg` command and subcommands (`init`, `add`, `commit`, `diff`, `eval`, `ci init`). All user-facing I/O goes through Rich console (stderr) and Typer echo (stdout).
- **schema.py** — Pydantic models: `PromptTemplate` (the prompt file schema with name/version/system_prompt/user_template/variables/constraints/metadata) and `CommitRecord` (commit metadata). `PromptTemplate.from_yaml()` is the standard loader.
- **diff_engine.py** — Semantic diff engine. `diff_prompts()` produces a `DiffResult` with field-level changes, semantic change type (variable/constraint/tone/role shift), and risk level (LOW/MEDIUM/HIGH). Uses `SemanticChangeType` and `RiskLevel` enums.
- **evaluator.py** — Rule-based evaluation (no LLM dependency). `evaluate_prompts()` compares old/new prompt versions against a JSONL dataset. Computes accuracy, token cost, and consistency metrics. Uses keyword matching and text similarity as heuristics.
- **ci_gen.py** — CI/CD config generator. `init_ci()` creates GitHub Actions workflows, pre-commit hooks, and version bump scripts. `CIConfig` and `PreCommitConfig` dataclasses drive the generation.
- **utils.py** — Shared helpers: `get_repo()` (GitPython Repo), `get_prompts_dir()` (.prompts/ path), `render_table()` (Rich tables), `error_exit()`. Error codes: `ERR_SUCCESS=0`, `ERR_ARGS=1`, `ERR_GIT=2`, `ERR_VALIDATION=3`.

## Key Patterns

- Prompts are stored as YAML files in `.prompts/` directory within a Git repo.
- All data validation uses Pydantic v2 (`BaseModel`, `field_validator`, `model_validate`).
- CLI uses Typer with Rich for formatted terminal output (tables, colored text).
- Git operations use GitPython (`Repo`, `Repo.index`, `repo.head.commit`).
- Evaluation works offline via rule-based heuristics (keyword matching + SequenceMatcher similarity). Optional LLM integration via `render_fn` parameter.
- Tests use pytest with fixtures in `conftest.py` that create temporary Git repos (`tmp_git_repo`, `initialized_repo`, etc.).

## Testing

Test files: `tests/test_cli.py`, `tests/test_diff.py`, `tests/test_eval.py`, `tests/test_ci_gen.py`. Fixtures in `tests/conftest.py` provide temporary Git repos with various states (clean, dirty, with history, with branches, with remotes). Test datasets live in `fixtures/`.

## Prompt File Format

```yaml
name: string          # Required, 1-128 chars
version: string       # Semver, default "0.1.0"
system_prompt: string # Required
user_template: string # Required, supports {{variable}} placeholders
variables: {}         # Variable definitions with defaults
constraints: []       # Behavioral constraints
metadata: {}          # Arbitrary metadata
```
