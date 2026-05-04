# Troubleshooting Guide

## Table of Contents

- [Installation Issues](#installation-issues)
- [Git-Related Issues](#git-related-issues)
- [Prompt Validation Errors](#prompt-validation-errors)
- [Evaluation Issues](#evaluation-issues)
- [CI/CD Integration Issues](#cicd-integration-issues)
- [Performance Issues](#performance-issues)

---

## Installation Issues

### Issue: `command not found: pg`

**Symptoms:**
```bash
$ pg init
bash: pg: command not found
```

**Solutions:**

1. **Check if package is installed:**
   ```bash
   pip list | grep prompt-git
   # or
   uv pip list | grep prompt-git
   ```

2. **Install the package:**
   ```bash
   uv pip install prompt-git
   # or
   pip install prompt-git
   ```

3. **Check PATH:**
   ```bash
   # Find where pg was installed
   which pg || find ~/.local -name "pg" 2>/dev/null
   
   # Add to PATH if needed
   export PATH="$HOME/.local/bin:$PATH"
   ```

4. **Use uv run as alternative:**
   ```bash
   uv run pg init
   ```

---

### Issue: `ModuleNotFoundError: No module named 'promptgit'`

**Symptoms:**
```python
ModuleNotFoundError: No module named 'promptgit'
```

**Solutions:**

1. **Install in development mode:**
   ```bash
   cd prompt-git
   uv sync
   ```

2. **Check Python environment:**
   ```bash
   which python
   python -c "import promptgit; print(promptgit.__version__)"
   ```

3. **Use correct Python version:**
   ```bash
   uv run python -c "import promptgit"
   ```

---

### Issue: Dependency conflicts

**Symptoms:**
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed
```

**Solutions:**

1. **Use uv for dependency resolution:**
   ```bash
   uv sync --resolution highest
   ```

2. **Create fresh virtual environment:**
   ```bash
   uv venv .venv --python 3.10
   uv sync
   ```

3. **Check conflicting packages:**
   ```bash
   uv pip check
   ```

---

## Git-Related Issues

### Issue: `Not a git repository`

**Symptoms:**
```bash
$ pg init
Error: Not a git repository (or any parent up to root)
```

**Solutions:**

1. **Initialize git first:**
   ```bash
   git init
   pg init
   ```

2. **Navigate to git repository:**
   ```bash
   cd /path/to/your/repo
   pg init
   ```

---

### Issue: `Permission denied` when committing

**Symptoms:**
```bash
$ pg commit -m "test"
Error: Git operation failed: Permission denied
```

**Solutions:**

1. **Configure git user:**
   ```bash
   git config user.name "Your Name"
   git config user.email "your@email.com"
   ```

2. **Check file permissions:**
   ```bash
   ls -la .prompts/
   chmod 644 .prompts/*.yaml
   ```

---

### Issue: Merge conflicts in `.prompts/`

**Symptoms:**
```
CONFLICT (content): Merge conflict in .prompts/customer_service.yaml
```

**Solutions:**

1. **View the conflict:**
   ```bash
   pg diff .prompts/customer_service.yaml
   ```

2. **Resolve manually and test:**
   ```bash
   # Edit file to resolve conflict
   vim .prompts/customer_service.yaml
   
   # Validate the resolved file
   pg diff --semantic
   
   # Commit resolution
   git add .prompts/customer_service.yaml
   pg commit -m "Resolve merge conflict"
   ```

3. **Use semantic diff to understand changes:**
   ```bash
   pg diff --semantic --json | jq '.risk_level'
   ```

---

## Prompt Validation Errors

### Issue: `Missing required field: system_prompt`

**Symptoms:**
```
Error: Schema validation failed: Field required [type=missing]
```

**Solutions:**

1. **Check YAML structure:**
   ```yaml
   name: my-prompt
   version: "1.0.0"
   system_prompt: "You are a helpful assistant."  # Required!
   user_template: "Help me with {{task}}"          # Required!
   ```

2. **Validate before adding:**
   ```bash
   pg add my_prompt.yaml --dry-run
   ```

3. **Use the schema as reference:**
   ```python
   from promptgit.schema import PromptTemplate
   
   # This will show detailed validation errors
   template = PromptTemplate.from_yaml("my_prompt.yaml")
   ```

---

### Issue: `Invalid YAML syntax`

**Symptoms:**
```
Error: Invalid YAML: while scanning a quoted scalar
```

**Solutions:**

1. **Check indentation (use spaces, not tabs):**
   ```yaml
   # Correct
   system_prompt: |
     Line 1
     Line 2
   
   # Wrong (mixed tabs/spaces)
   system_prompt: |
   	Line 1
   	Line 2
   ```

2. **Escape special characters:**
   ```yaml
   # Correct
   user_template: "Answer: {{question}}"
   
   # May cause issues
   user_template: Answer: {{question}}
   ```

3. **Validate YAML online or with tool:**
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('my_prompt.yaml'))"
   ```

---

### Issue: `Variable in template not defined`

**Symptoms:**
```
Warning: Variable {{topic}} in template but not in variables dict
```

**Solutions:**

1. **Add missing variable definition:**
   ```yaml
   user_template: "Discuss {{topic}} in {{language}}"
   variables:
     topic:
       type: string
       default: "general"
     language:
       type: string
       default: "English"
   ```

2. **Remove unused template variables:**
   ```yaml
   # If you don't need {{language}}, remove it from template
   user_template: "Discuss {{topic}}"
   ```

---

## Evaluation Issues

### Issue: `Dataset file not found`

**Symptoms:**
```
Error: Dataset not found: fixtures/dataset.jsonl
```

**Solutions:**

1. **Check file path:**
   ```bash
   ls -la fixtures/dataset.jsonl
   ```

2. **Use absolute path:**
   ```bash
   pg eval --dataset /full/path/to/dataset.jsonl
   ```

3. **Create dataset if missing:**
   ```bash
   mkdir -p fixtures
   cat > fixtures/dataset.jsonl << 'EOF'
   {"input": "test question", "expected_output": "test answer"}
   EOF
   ```

---

### Issue: `Invalid JSON in dataset`

**Symptoms:**
```
Error: Invalid JSON at line 3: Expecting value
```

**Solutions:**

1. **Validate JSONL format:**
   ```bash
   python3 -c "
   import json
   with open('dataset.jsonl') as f:
       for i, line in enumerate(f, 1):
           try:
               json.loads(line)
           except json.JSONDecodeError as e:
               print(f'Line {i}: {e}')
   "
   ```

2. **Common issues:**
   - Missing quotes around strings
   - Trailing commas
   - Multiline JSON (each line must be complete JSON)

3. **Fix and revalidate:**
   ```bash
   # Fix the file, then validate
   pg eval --dataset dataset.jsonl --dry-run
   ```

---

### Issue: `Evaluation failed - accuracy dropped`

**Symptoms:**
```
Error: Evaluation FAILED: accuracy dropped 8.5% (threshold: 5.0%)
```

**Solutions:**

1. **Review failed samples:**
   ```bash
   pg eval --dataset dataset.jsonl --json | python3 -c "
   import json, sys
   data = json.load(sys.stdin)
   for d in data['details']:
       if not d['new_match']:
           print(f'Input: {d[\"input\"]}')
           print(f'Expected: {d[\"expected\"]}')
           print(f'Got: {d[\"new_output\"]}')
           print()
   "
   ```

2. **Increase threshold (if acceptable):**
   ```bash
   pg eval --dataset dataset.jsonl --threshold 0.10
   ```

3. **Investigate the changes:**
   ```bash
   pg diff --semantic
   # Look for high-risk changes that may affect accuracy
   ```

4. **Rollback if needed:**
   ```bash
   git checkout HEAD~1 .prompts/
   pg commit -m "Revert: restore previous prompt version"
   ```

---

### Issue: `Empty dataset error`

**Symptoms:**
```
Error: Dataset is empty, cannot evaluate
```

**Solutions:**

1. **Check file content:**
   ```bash
   wc -l fixtures/dataset.jsonl
   cat fixtures/dataset.jsonl
   ```

2. **Add test cases:**
   ```bash
   cat > fixtures/dataset.jsonl << 'EOF'
   {"input": "What is Python?", "expected_output": "Python is a programming language"}
   EOF
   ```

---

## CI/CD Integration Issues

### Issue: GitHub Action not triggering

**Symptoms:**
PR changes `.prompts/` but workflow doesn't run.

**Solutions:**

1. **Check workflow file location:**
   ```bash
   ls -la .github/workflows/
   # Should contain prompt-guard.yml or similar
   ```

2. **Verify trigger paths:**
   ```yaml
   on:
     pull_request:
       paths:
         - '.prompts/**'  # Must match your directory structure
   ```

3. **Check branch configuration:**
   ```yaml
   on:
     pull_request:
       branches: [main, develop]  # Must match your base branch
   ```

4. **Review GitHub Actions logs:**
   - Go to Actions tab in GitHub
   - Check if workflow appears
   - Review any error messages

---

### Issue: `Comment PR with Report` step fails

**Symptoms:**
```
Error: Resource not accessible by integration
```

**Solutions:**

1. **Add write permissions:**
   ```yaml
   permissions:
     contents: read
     pull-requests: write  # Required for comments
   ```

2. **Use GitHub App token (for forks):**
   ```yaml
   - uses: actions/github-script@v7
     with:
       github-token: ${{ secrets.GITHUB_TOKEN }}
   ```

3. **Check repository settings:**
   - Settings → Actions → General
   - Ensure "Allow GitHub Actions to create and approve pull requests" is enabled

---

### Issue: `uv sync` fails in CI

**Symptoms:**
```
Error: Failed to build `prompt-git`
```

**Solutions:**

1. **Pin Python version:**
   ```yaml
   - uses: actions/setup-python@v5
     with:
       python-version: '3.10'  # Use specific version
   ```

2. **Add caching:**
   ```yaml
   - uses: actions/setup-python@v5
     with:
       python-version: '3.10'
       cache: 'pip'
   ```

3. **Use requirements.txt fallback:**
   ```yaml
   - name: Install dependencies
     run: |
       uv sync || pip install -r requirements.txt
   ```

---

## Performance Issues

### Issue: Evaluation is slow

**Symptoms:**
Evaluation takes >5 minutes for large datasets.

**Solutions:**

1. **Use rule-based evaluation (default):**
   ```bash
   pg eval --dataset dataset.jsonl
   # Uses fast keyword matching by default
   ```

2. **Reduce dataset size for quick checks:**
   ```bash
   head -20 dataset.jsonl > dataset_quick.jsonl
   pg eval --dataset dataset_quick.jsonl
   ```

3. **Run in parallel (for multiple datasets):**
   ```bash
   pg eval --dataset ds1.jsonl &
   pg eval --dataset ds2.jsonl &
   wait
   ```

4. **Use sampling for large datasets:**
   ```bash
   shuf -n 50 dataset.jsonl > dataset_sample.jsonl
   pg eval --dataset dataset_sample.jsonl
   ```

---

### Issue: High memory usage

**Symptoms:**
Process killed or out-of-memory errors.

**Solutions:**

1. **Process large datasets in chunks:**
   ```python
   import json
   
   def process_chunk(input_file, chunk_size=1000):
       with open(input_file) as f:
           chunk = []
           for line in f:
               chunk.append(json.loads(line))
               if len(chunk) >= chunk_size:
                   yield chunk
                   chunk = []
           if chunk:
               yield chunk
   ```

2. **Increase system limits (if possible):**
   ```bash
   ulimit -v unlimited
   ```

---

## FAQ

### General Questions

**Q: What Python versions are supported?**

A: Python 3.10 and above. We recommend 3.10 or 3.11 for best compatibility.

---

**Q: Can I use prompt-git with private repositories?**

A: Yes! prompt-git works entirely locally. No data is sent to external servers unless you explicitly enable LLM evaluation.

---

**Q: Does prompt-git require an internet connection?**

A: No. Rule-based evaluation works completely offline. Only LLM-enhanced evaluation requires API access.

---

**Q: How is prompt-git different from Langfuse?**

A: See the comparison table:

| Feature | prompt-git | Langfuse |
|---------|------------|----------|
| Setup | `pip install` | Docker/Cloud |
| Storage | Git | Database |
| Workflow | CI/CD | Dashboard |
| Cost | Free | Paid tiers |
| Focus | Development | Monitoring |

---

### Prompt Management

**Q: What prompt formats are supported?**

A: YAML (.yaml, .yml) and JSON (.json) with this structure:

```yaml
name: string           # Required
version: string        # Optional
system_prompt: string  # Required
user_template: string  # Required, supports {{variables}}
variables: {}          # Optional
constraints: []        # Optional
metadata: {}           # Optional
```

---

**Q: Can I use Markdown in prompts?**

A: Yes! Use YAML block scalars:

```yaml
system_prompt: |
  You are a helpful assistant.
  
  ## Guidelines
  - Be concise
  - Use examples
```

---

**Q: How do I handle multilingual prompts?**

A: Use Unicode directly in YAML:

```yaml
system_prompt: |
  你是一位专业的客服代表。
  You are a professional customer service agent.
```

---

### Evaluation

**Q: How does rule-based evaluation work?**

A: Without LLM APIs, we use:
- Keyword matching between expected and actual output
- Text similarity scoring (SequenceMatcher)
- Pattern matching for common responses

It's less accurate than LLM evaluation but:
- Works offline
- No API costs
- Fast execution
- Deterministic results

---

**Q: What dataset format is required?**

A: JSONL (one JSON object per line):

```jsonl
{"input": "question", "expected_output": "answer", "metadata": {}}
```

Required fields: `input`, `expected_output`
Optional fields: `metadata` (any JSON object)

---

**Q: How do I create a good evaluation dataset?**

A: Follow these guidelines:

1. **Diverse inputs**: Cover edge cases, different phrasings
2. **Clear expected outputs**: Specific, verifiable answers
3. **Categorize**: Use metadata for grouping
4. **Balance**: Include easy, medium, hard cases
5. **Size**: Start with 20-50 samples, grow over time

Example:
```jsonl
{"input": "What is Python?", "expected_output": "Python is a high-level programming language", "metadata": {"category": "definition", "difficulty": "easy"}}
{"input": "Explain Python's GIL", "expected_output": "The Global Interpreter Lock prevents multiple threads from executing Python bytecode simultaneously", "metadata": {"category": "technical", "difficulty": "hard"}}
```

---

**Q: What is a good accuracy threshold?**

A: Depends on your use case:
- **Conservative (3%)**: For critical applications (finance, healthcare)
- **Standard (5%)**: For most production systems
- **Relaxed (10%)**: For experimental/development prompts

---

### CI/CD Integration

**Q: Which CI platforms are supported?**

A: Official support for:
- GitHub Actions (primary)
- GitLab CI (via custom scripts)
- CircleCI (via custom config)
- Jenkins (via shell scripts)

---

**Q: How do I skip CI for documentation changes?**

A: Use path filters:

```yaml
on:
  pull_request:
    paths:
      - '.prompts/**'
      - '!*.md'  # Exclude markdown files
```

---

**Q: Can I run prompt-git in a monorepo?**

A: Yes! Use path filters and working directory:

```yaml
jobs:
  prompt-guard:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./prompts-service
    steps:
      - uses: actions/checkout@v4
      - run: pg diff --semantic
```

---

**Q: How do I handle secrets for LLM evaluation?**

A: Use GitHub Secrets:

1. Go to Settings → Secrets → Actions
2. Add `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
3. Reference in workflow:

```yaml
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

---

### Advanced Usage

**Q: Can I customize the diff algorithm?**

A: Currently, the diff algorithm uses fixed heuristics. For custom logic:

```python
from promptgit.diff_engine import diff_prompts

# Use the API directly
result = diff_prompts(old_path, new_path)

# Customize analysis
if result.semantic_change_type == "variable_change":
    # Your custom logic
    pass
```

---

**Q: How do I integrate with external tools?**

A: Use JSON output:

```bash
# Export to JSON
pg diff --json > diff.json
pg eval --dataset data.jsonl --json > eval.json

# Process with Python
python3 << 'SCRIPT'
import json

with open('eval.json') as f:
    data = json.load(f)

# Send to monitoring system
import requests
requests.post('https://monitoring.example.com/api', json=data)
SCRIPT
```

---

**Q: Can I use prompt-git with Jupyter notebooks?**

A: Yes! Use the Python API:

```python
from promptgit.schema import PromptTemplate
from promptgit.evaluator import evaluate_prompts, load_dataset

# Load template
template = PromptTemplate.from_yaml("my_prompt.yaml")

# Load dataset
dataset = load_dataset("dataset.jsonl")

# Evaluate
result = evaluate_prompts(old_template, new_template, dataset)
print(f"Accuracy delta: {result.accuracy_delta:.1%}")
```

---

**Q: How do I contribute to prompt-git?**

A: See [CONTRIBUTING.md](../CONTRIBUTING.md) for details:

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit pull request

---

## Getting Help

If your issue isn't covered here:

1. **Search existing issues**: [GitHub Issues](https://github.com/yourusername/prompt-git/issues)
2. **Check discussions**: [GitHub Discussions](https://github.com/yourusername/prompt-git/discussions)
3. **Create new issue**: Include:
   - prompt-git version (`pg --version`)
   - Python version (`python --version`)
   - Operating system
   - Full error message
   - Steps to reproduce

---

*Last updated: 2024-01-15*
