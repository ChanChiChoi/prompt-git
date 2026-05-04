# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- (upcoming features)

### Changed
- (upcoming changes)

### Fixed
- (upcoming fixes)

---

## [0.2.0] - 2026-05-04

### Added

**LLM Enhanced Evaluation:**
- Integrated LiteLLM for multi-provider support
- Support for OpenAI, Anthropic, Ollama, and local models
- LLM-as-judge evaluation mode (`--judge` flag)
- Multi-model comparison (`--compare-models` flag)
- New `llm_evaluator.py` module with LLMConfig, LLMEvalResult, LLMJudgeResult, LLMCompareResult

**CLI Enhancements:**
- `pg eval --provider <provider>` - Specify LLM provider
- `pg eval --model <model>` - Specify LLM model
- `pg eval --judge` - Enable LLM-as-judge scoring
- `pg eval --compare-models <model1>,<model2>` - Compare multiple models

**Testing:**
- Added 30 new tests for LLM evaluation
- Total test count: 148 tests
- All tests passing

**Documentation:**
- Updated roadmap with v0.2.0 completion
- Updated README with LLM evaluation examples
- Updated README_zh with Chinese LLM documentation

### Changed
- Bumped version to 0.2.0
- Added `litellm>=1.0.0` to dependencies

---

## [0.1.1] - 2026-05-04

### Fixed
- Fixed `Table` import error in `pg eval` command
- Fixed double replacement issue in ci_gen.py

### Changed
- Renamed project from `prompt-git` to `prompt-git-manager`
- Updated all GitHub references to ChanChiChoi

---

## [0.1.0] - 2026-05-04

### Added

**Core Features:**
- `pg init` - Initialize `.prompts/` directory
- `pg add` - Add prompt files to version tracking
- `pg commit` - Commit prompt changes with metadata
- `pg diff` - Show differences between prompt versions
- `pg eval` - Evaluate prompts against datasets
- `pg ci init` - Generate CI/CD configuration

**Diff Engine:**
- Structured field-level diff
- Semantic change detection (variable, constraint, tone, role)
- Risk level assessment (low, medium, high)
- Text diff output

**Evaluator:**
- Rule-based evaluation (no LLM dependency)
- Keyword matching algorithm
- Token cost estimation
- Consistency scoring
- Threshold-based pass/fail

**CI/CD Integration:**
- GitHub Actions workflow generation
- Pre-commit hook configuration
- PyPI publish workflow
- Version bump script

**Schema:**
- PromptTemplate Pydantic model
- CommitRecord model
- YAML/JSON validation

**Documentation:**
- README.md (English)
- README_zh.md (Chinese)
- CLI reference
- Architecture documentation
- Troubleshooting guide
- Quick start guide

**Testing:**
- 118 unit tests
- 74% code coverage
- Tests for all core modules

---

## [0.0.1] - 2026-04-28

### Added
- Initial project setup
- Basic project structure

---

## Release Notes

### How to Update

```bash
# Using uv
uv pip install --upgrade prompt-git-manager

# Using pip
pip install --upgrade prompt-git-manager
```

### Breaking Changes

#### v0.2.0
- No breaking changes

#### v0.1.1
- Package renamed from `prompt-git` to `prompt-git-manager`
- CLI command remains `pg`

#### v0.1.0
- Initial release

---

## Links

- [GitHub Releases](https://github.com/ChanChiChoi/prompt-git-manager/releases)
- [PyPI](https://pypi.org/project/prompt-git-manager/)
- [Full Changelog](https://github.com/ChanChiChoi/prompt-git-manager/compare/v0.1.1...v0.2.0)
