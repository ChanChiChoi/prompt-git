"""CI/CD configuration generator for prompt-git.

Generates GitHub Actions workflows, pre-commit hooks, and CI configurations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class CIConfig:
    """Configuration for CI generation."""

    # Trigger settings
    branches: list[str] = field(default_factory=lambda: ["main", "dev"])
    paths: list[str] = field(default_factory=lambda: [".prompts/**"])

    # Evaluation settings
    dataset_path: str = "fixtures/dataset.jsonl"
    threshold: float = 0.05
    model_provider: str = "none"  # none, openai, anthropic, local
    model_name: str = "gpt-3.5-turbo"

    # Workflow settings
    python_version: str = "3.10"
    concurrency_group: str = "prompt-guard-${{ github.ref }}"
    cancel_in_progress: bool = True

    # Feature flags
    enable_diff: bool = True
    enable_eval: bool = True
    comment_on_failure: bool = True
    upload_artifact: bool = True

    # Paths
    workflow_path: str = ".github/workflows/prompt-guard.yml"
    pre_commit_path: str = ".pre-commit-config.yaml"


@dataclass
class PreCommitConfig:
    """Configuration for pre-commit hooks."""

    diff_fail_on: str = "high"  # low, med, high
    enable_eval: bool = False
    dataset_path: str = "fixtures/dataset.jsonl"


def generate_workflow(config: CIConfig) -> str:
    """Generate GitHub Actions workflow YAML.

    Args:
        config: CI configuration.

    Returns:
        YAML string for the workflow file.
    """
    workflow = {
        "name": "Prompt Guard",
        "on": {
            "pull_request": {
                "branches": config.branches,
                "paths": config.paths,
            },
        },
        "permissions": {
            "contents": "read",
            "pull-requests": "write",
        },
        "concurrency": {
            "group": config.concurrency_group,
            "cancel-in-progress": config.cancel_in_progress,
        },
        "jobs": {
            "prompt-guard": {
                "runs-on": "ubuntu-latest",
                "steps": _build_steps(config),
            }
        },
    }

    return yaml.dump(workflow, default_flow_style=False, sort_keys=False)


def _build_steps(config: CIConfig) -> list[dict]:
    """Build workflow steps.

    Args:
        config: CI configuration.

    Returns:
        List of step dictionaries.
    """
    steps = []

    # Step 1: Checkout
    steps.append(
        {
            "name": "Checkout code",
            "uses": "actions/checkout@v4",
            "with": {
                "fetch-depth": 0,
            },
        }
    )

    # Step 2: Setup Python
    steps.append(
        {
            "name": "Set up Python",
            "uses": "actions/setup-python@v5",
            "with": {
                "python-version": config.python_version,
            },
        }
    )

    # Step 3: Install uv
    steps.append(
        {
            "name": "Install uv",
            "uses": "astral-sh/setup-uv@v3",
        }
    )

    # Step 4: Install dependencies
    steps.append(
        {
            "name": "Install dependencies",
            "run": "uv sync",
        }
    )

    # Step 5: Run diff (if enabled)
    if config.enable_diff:
        steps.append(
            {
                "name": "Run Prompt Diff",
                "id": "diff",
                "run": "uv run pg diff --semantic --json > diff_report.json",
            }
        )

    # Step 6: Run evaluation (if enabled)
    if config.enable_eval:
        eval_cmd = f"uv run pg eval --dataset {config.dataset_path} --threshold {config.threshold}"
        if config.model_provider != "none":
            eval_cmd += f" --model {config.model_name}"
        eval_cmd += " --json > eval_report.json"

        steps.append(
            {
                "name": "Run Prompt Evaluation",
                "id": "eval",
                "run": eval_cmd,
                "continue-on-error": True,
            }
        )

    # Step 7: Comment on PR (if enabled)
    if config.comment_on_failure:
        steps.append(
            {
                "name": "Comment PR with Report",
                "if": "always()",
                "uses": "actions/github-script@v7",
                "with": {
                    "script": _get_comment_script(config),
                },
            }
        )

    # Step 8: Upload artifacts (if enabled)
    if config.upload_artifact:
        steps.append(
            {
                "name": "Upload Reports",
                "if": "always()",
                "uses": "actions/upload-artifact@v4",
                "with": {
                    "name": "prompt-reports",
                    "path": "*.json",
                    "retention-days": 30,
                },
            }
        )

    # Step 9: Fail if evaluation failed
    if config.enable_eval:
        steps.append(
            {
                "name": "Check evaluation result",
                "if": "steps.eval.outcome == 'failure'",
                "run": "exit 1",
            }
        )

    return steps


def _get_comment_script(config: CIConfig) -> str:
    """Generate GitHub Script for PR comments.

    Args:
        config: CI configuration.

    Returns:
        JavaScript code as string.
    """
    script = r"""const fs = require('fs');

// Read reports
let diffReport = '';
let evalReport = '';

try {
    diffReport = fs.readFileSync('diff_report.json', 'utf8');
    diffReport = JSON.stringify(JSON.parse(diffReport), null, 2);
} catch (e) {
    diffReport = 'No diff report available';
}

try {
    evalReport = fs.readFileSync('eval_report.json', 'utf8');
    evalReport = JSON.stringify(JSON.parse(evalReport), null, 2);
} catch (e) {
    evalReport = 'No evaluation report available';
}

// Determine status
const evalPassed = '${{ steps.eval.outcome }}' !== 'failure';
const statusIcon = evalPassed ? '✅' : '❌';
const statusText = evalPassed ? 'PASSED' : 'FAILED';

// Build comment body
const body = `## ${statusIcon} Prompt Guard Results

### Status: ${statusText}

<details>
<summary>📊 Diff Report</summary>

\`\`\`json
${diffReport}
\`\`\`
</details>

<details>
<summary>📈 Evaluation Report</summary>

\`\`\`json
${evalReport}
\`\`\`
</details>

---
<sub>Generated by <a href="https://github.com/yourusername/prompt-git">prompt-git</a> CI Guard</sub>`;

// Find existing comment
const { data: comments } = await github.rest.issues.listComments({
    owner: context.repo.owner,
    repo: context.repo.repo,
    issue_number: context.issue.number,
});

const marker = '## ✅ Prompt Guard Results';
const failedMarker = '## ❌ Prompt Guard Results';
const existingComment = comments.find(c =>
    c.user.type === 'Bot' && (c.body.includes(marker) || c.body.includes(failedMarker))
);

if (existingComment) {
    await github.rest.issues.updateComment({
        owner: context.repo.owner,
        repo: context.repo.repo,
        comment_id: existingComment.id,
        body: body,
    });
} else {
    await github.rest.issues.createComment({
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: context.issue.number,
        body: body,
    });
}"""
    return script


def generate_pre_commit_config(config: PreCommitConfig) -> str:
    """Generate pre-commit configuration YAML.

    Args:
        config: Pre-commit configuration.

    Returns:
        YAML string for pre-commit config.
    """
    hooks = [
        {
            "id": "prompt-diff",
            "name": "Prompt Diff Check",
            "entry": f"pg diff --fail-on={config.diff_fail_on}",
            "language": "system",
            "files": r"\.prompts/.*\.ya?ml$",
            "pass_filenames": False,
        }
    ]

    if config.enable_eval:
        hooks.append(
            {
                "id": "prompt-eval",
                "name": "Prompt Evaluation",
                "entry": f"pg eval --dataset {config.dataset_path} --threshold 0.05",
                "language": "system",
                "files": r"\.prompts/.*\.ya?ml$",
                "pass_filenames": False,
            }
        )

    pre_commit_config = {
        "repos": [
            {
                "repo": "local",
                "hooks": hooks,
            }
        ]
    }

    return yaml.dump(pre_commit_config, default_flow_style=False, sort_keys=False)


def generate_publish_workflow() -> str:
    """Generate GitHub Actions workflow for PyPI publishing.

    Returns:
        YAML string for the publish workflow.
    """
    workflow = {
        "name": "Publish to PyPI",
        "on": {
            "release": {
                "types": ["published"],
            },
        },
        "permissions": {
            "contents": "write",
            "id-token": "write",
        },
        "jobs": {
            "build": {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {
                        "name": "Checkout code",
                        "uses": "actions/checkout@v4",
                        "with": {
                            "fetch-depth": 0,
                        },
                    },
                    {
                        "name": "Set up Python",
                        "uses": "actions/setup-python@v5",
                        "with": {
                            "python-version": "3.10",
                        },
                    },
                    {
                        "name": "Install build tools",
                        "run": "pip install build twine",
                    },
                    {
                        "name": "Build package",
                        "run": "python -m build",
                    },
                    {
                        "name": "Check package",
                        "run": "twine check dist/*",
                    },
                    {
                        "name": "Upload to PyPI",
                        "env": {
                            "TWINE_USERNAME": "__token__",
                            "TWINE_PASSWORD": "${{ secrets.PYPI_API_TOKEN }}",
                        },
                        "run": "twine upload dist/*",
                    },
                    {
                        "name": "Upload artifacts",
                        "uses": "actions/upload-artifact@v4",
                        "with": {
                            "name": "dist",
                            "path": "dist/",
                        },
                    },
                ],
            }
        },
    }

    return yaml.dump(workflow, default_flow_style=False, sort_keys=False)


def generate_version_bump_script() -> str:
    """Generate version bump script.

    Returns:
        Shell script content.
    """
    return """#!/bin/bash
# Version bump script for prompt-git
# Usage: ./scripts/bump_version.sh [major|minor|patch]

set -e

BUMP_TYPE=${1:-patch}

# Get current version from pyproject.toml
CURRENT_VERSION=$(grep -E '^version = ' pyproject.toml | sed 's/version = "\\(.*\\)"/\\1/')
echo "Current version: $CURRENT_VERSION"

# Parse version components
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Bump version
case $BUMP_TYPE in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
    *)
        echo "Invalid bump type: $BUMP_TYPE"
        echo "Usage: $0 [major|minor|patch]"
        exit 1
        ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
echo "New version: $NEW_VERSION"

# Update pyproject.toml
sed -i "s/version = \\"$CURRENT_VERSION\\"/version = \\"$NEW_VERSION\\"/" pyproject.toml

# Update __init__.py
sed -i "s/__version__ = \\"$CURRENT_VERSION\\"/__version__ = \\"$NEW_VERSION\\"/" src/promptgit/__init__.py

# Create git tag
git add pyproject.toml src/promptgit/__init__.py
git commit -m "chore: bump version to $NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"

echo "Version bumped to $NEW_VERSION"
echo "Run 'git push && git push --tags' to publish"
"""


def init_ci(
    config_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    dry_run: bool = False,
) -> dict[str, Path]:
    """Initialize CI configuration files.

    Args:
        config_path: Path to CI config file (optional).
        output_dir: Output directory (default: current dir).
        dry_run: If True, only show what would be created.

    Returns:
        Dictionary mapping file types to their paths.
    """
    if output_dir is None:
        output_dir = Path.cwd()

    # Load config if provided
    if config_path and config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        ci_config = CIConfig(**config_data)
    else:
        ci_config = CIConfig()

    pre_commit_config = PreCommitConfig()

    # Generate files
    files = {}

    # GitHub Actions workflow
    workflow_dir = output_dir / ".github" / "workflows"
    workflow_path = workflow_dir / "prompt-guard.yml"
    workflow_content = generate_workflow(ci_config)
    files["workflow"] = workflow_path

    # Publish workflow
    publish_path = workflow_dir / "publish.yml"
    publish_content = generate_publish_workflow()
    files["publish"] = publish_path

    # Pre-commit config
    pre_commit_path = output_dir / ".pre-commit-config.yaml"
    pre_commit_content = generate_pre_commit_config(pre_commit_config)
    files["pre_commit"] = pre_commit_path

    # Version bump script
    scripts_dir = output_dir / "scripts"
    bump_path = scripts_dir / "bump_version.sh"
    bump_content = generate_version_bump_script()
    files["bump_script"] = bump_path

    if dry_run:
        print("Files that would be created:")
        for file_type, path in files.items():
            print(f"  {file_type}: {path}")
        return files

    # Write files
    workflow_dir.mkdir(parents=True, exist_ok=True)

    workflow_path.write_text(workflow_content, encoding="utf-8")
    publish_path.write_text(publish_content, encoding="utf-8")
    pre_commit_path.write_text(pre_commit_content, encoding="utf-8")

    scripts_dir.mkdir(exist_ok=True)
    bump_path.write_text(bump_content, encoding="utf-8")
    bump_path.chmod(0o755)  # Make executable

    return files


# CLI entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate CI configuration")
    parser.add_argument("--config", type=Path, help="CI config JSON file")
    parser.add_argument(
        "--output", type=Path, default=Path("."), help="Output directory"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without writing"
    )
    parser.add_argument(
        "--publish-only", action="store_true", help="Only generate publish workflow"
    )

    args = parser.parse_args()

    if args.publish_only:
        content = generate_publish_workflow()
        print(content)
    else:
        files = init_ci(args.config, args.output, args.dry_run)
        if not args.dry_run:
            print("CI configuration generated:")
            for file_type, path in files.items():
                print(f"  ✓ {path}")
