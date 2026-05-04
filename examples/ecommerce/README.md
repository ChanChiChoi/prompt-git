# E-commerce Prompt Workflow Demo

This example demonstrates a complete prompt engineering workflow for an e-commerce customer service bot.

## Directory Structure

```
examples/ecommerce/
├── README.md                    # This file
├── customer_service.yaml        # Main prompt template
├── customer_service_v2.yaml     # Improved version (for diff demo)
├── dataset.jsonl                # Evaluation dataset (20 samples)
├── workflow_demo.sh             # End-to-end workflow script
└── ci_config.json               # CI configuration
```

## Quick Start

```bash
# Navigate to example directory
cd examples/ecommerce

# Initialize prompt-git-manager
pg init

# Add the prompt
pg add customer_service.yaml

# Commit initial version
pg commit -m "Add e-commerce customer service prompt v1"

# Run evaluation
pg eval --dataset dataset.jsonl --threshold 0.05

# View results
cat eval_report.json
```

## Workflow Steps

### Step 1: Initial Setup

```bash
# Create working directory
mkdir -p ecommerce-workflow
cd ecommerce-workflow

# Initialize git and prompt-git-manager
git init
pg init

# Copy prompt files
cp ../customer_service.yaml .prompts/
cp ../dataset.jsonl .
```

### Step 2: Baseline Evaluation

```bash
# Add and commit baseline prompt
pg add customer_service.yaml
pg commit -m "Baseline: e-commerce CS prompt v1"

# Run baseline evaluation
pg eval --dataset dataset.jsonl --threshold 0.05 --json > baseline_eval.json

# View baseline metrics
python3 -c "
import json
with open('baseline_eval.json') as f:
    data = json.load(f)
print(f'Baseline Accuracy: {data[\"accuracy_old\"]:.1%}')
print(f'Samples: {data[\"total_samples\"]}')
"
```

### Step 3: Prompt Iteration

```bash
# Make improvements to the prompt
# Example: Add VIP handling, improve error responses
vim .prompts/customer_service.yaml

# Review changes with semantic diff
pg diff --semantic

# Output example:
# ┌─────────────────────────────────────────────────┐
# │ Diff: .prompts/customer_service.yaml            │
# ├──────────────┬──────────────────────────────────┤
# │ Risk Level   │ 🟡 MEDIUM                        │
# │ Change Type  │ constraint_change                │
# │ Summary      │ Added 2 constraints              │
# └──────────────┴──────────────────────────────────┘
```

### Step 4: A/B Evaluation

```bash
# Commit new version
pg commit -m "v2: Add VIP handling and improved error responses"

# Run evaluation comparing v1 vs v2
pg eval --dataset dataset.jsonl --threshold 0.05 --json > v2_eval.json

# Compare results
python3 << 'SCRIPT'
import json

with open('baseline_eval.json') as f:
    v1 = json.load(f)
with open('v2_eval.json') as f:
    v2 = json.load(f)

print("=== A/B Comparison ===")
print(f"V1 Accuracy: {v1['accuracy_old']:.1%}")
print(f"V2 Accuracy: {v2['accuracy_new']:.1%}")
print(f"Delta: {v2['accuracy_delta']:+.1%}")
print(f"Consistency: {v2['consistency_score']:.1%}")
print(f"Status: {'PASSED' if v2['passed'] else 'FAILED'}")
SCRIPT
```

### Step 5: CI Integration

```bash
# Generate CI configuration
pg ci init

# This creates:
# - .github/workflows/prompt-guard.yml
# - .pre-commit-config.yaml

# Test locally before pushing
pg diff --semantic --fail-on=high
pg eval --dataset dataset.jsonl --threshold 0.05
```

## Prompt Design Decisions

### Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `message` | Customer's original input | "Where is my order?" |
| `order_id` | Reference for tracking | "#12345" |
| `order_status` | Current state | "shipped" |
| `membership_tier` | VIP handling | "gold" |

### Constraints

1. **Verification**: Always verify order ID before sharing details
2. **Escalation**: Refunds >$100 need supervisor approval
3. **VIP Priority**: Gold+ members get expedited service
4. **Tone**: Acknowledge frustration before problem-solving

### Risk Analysis

| Change Type | Risk | Rationale |
|-------------|------|-----------|
| Variable removal | 🔴 HIGH | May break existing integrations |
| Constraint removal | 🟡 MEDIUM | Could reduce service quality |
| Tone shift | 🟡 MEDIUM | May affect customer satisfaction |
| Metadata change | 🟢 LOW | No behavioral impact |

## Evaluation Metrics

### Accuracy

Measures how well the prompt handles test cases:
- **Match**: Response contains expected keywords/patterns
- **Partial**: Response partially addresses the query
- **Miss**: Response fails to address the query

### Consistency

Measures response stability across runs:
- High consistency (>0.8): Reliable, predictable responses
- Low consistency (<0.6): May need temperature adjustment

### Token Cost

Tracks prompt efficiency:
- Compare input/output tokens between versions
- Optimize for cost without sacrificing quality

## Best Practices

1. **Version Control**: Commit after each meaningful change
2. **Evaluation First**: Always eval before merging
3. **Small Increments**: Make focused, testable changes
4. **Document Rationale**: Explain why changes were made
5. **Review Diffs**: Use semantic diff to understand impact

## Troubleshooting

### Issue: Low Accuracy

```bash
# Check which samples are failing
python3 -c "
import json
with open('eval_report.json') as f:
    data = json.load(f)
for detail in data['details']:
    if not detail['new_match']:
        print(f'FAILED: {detail[\"input\"][:50]}...')
"
```

### Issue: High Token Cost

```bash
# Analyze token usage
python3 -c "
import json
with open('eval_report.json') as f:
    data = json.load(f)
print(f'Old tokens: {data[\"token_cost_old\"]}')
print(f'New tokens: {data[\"token_cost_new\"]}')
print(f'Delta: {data[\"token_cost_delta\"]:+.1%}')
"
```

### Issue: Inconsistent Results

If evaluation results vary between runs:
1. Set lower temperature (0.1-0.3)
2. Increase dataset size
3. Use deterministic sampling for critical paths

## Next Steps

- Add more test cases to `dataset.jsonl`
- Experiment with different system prompts
- Set up automated CI/CD pipeline
- Monitor production performance
