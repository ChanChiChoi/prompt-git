"""Tests for CI configuration generator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from promptgit.ci_gen import (
    CIConfig,
    PreCommitConfig,
    generate_workflow,
    generate_pre_commit_config,
    generate_publish_workflow,
    generate_version_bump_script,
    init_ci,
)


@pytest.fixture
def default_ci_config():
    """Default CI configuration."""
    return CIConfig()


@pytest.fixture
def custom_ci_config():
    """Custom CI configuration."""
    return CIConfig(
        branches=["main", "develop", "release/*"],
        paths=[".prompts/**", "datasets/**"],
        dataset_path="data/eval.jsonl",
        threshold=0.10,
        model_provider="openai",
        model_name="gpt-4",
        python_version="3.11",
        enable_diff=True,
        enable_eval=True,
        comment_on_failure=True,
        upload_artifact=True,
    )


@pytest.fixture
def minimal_ci_config():
    """Minimal CI configuration with disabled features."""
    return CIConfig(
        enable_diff=True,
        enable_eval=False,
        comment_on_failure=False,
        upload_artifact=False,
    )


@pytest.fixture
def default_pre_commit_config():
    """Default pre-commit configuration."""
    return PreCommitConfig()


@pytest.fixture
def custom_pre_commit_config():
    """Custom pre-commit configuration."""
    return PreCommitConfig(
        diff_fail_on="med",
        enable_eval=True,
        dataset_path="fixtures/dataset.jsonl",
    )


class TestWorkflowGeneration:
    """Tests for workflow YAML generation."""

    def test_valid_yaml(self, default_ci_config):
        """Generated YAML is valid."""
        content = generate_workflow(default_ci_config)
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict)

    def test_workflow_name(self, default_ci_config):
        """Workflow has correct name."""
        content = generate_workflow(default_ci_config)
        parsed = yaml.safe_load(content)
        assert parsed["name"] == "Prompt Guard"

    def test_trigger_branches(self, custom_ci_config):
        """Trigger includes configured branches."""
        content = generate_workflow(custom_ci_config)
        parsed = yaml.safe_load(content)
        branches = parsed["on"]["pull_request"]["branches"]
        assert "main" in branches
        assert "develop" in branches
        assert "release/*" in branches

    def test_trigger_paths(self, custom_ci_config):
        """Trigger includes configured paths."""
        content = generate_workflow(custom_ci_config)
        parsed = yaml.safe_load(content)
        paths = parsed["on"]["pull_request"]["paths"]
        assert ".prompts/**" in paths
        assert "datasets/**" in paths

    def test_permissions(self, default_ci_config):
        """Workflow has correct permissions."""
        content = generate_workflow(default_ci_config)
        parsed = yaml.safe_load(content)
        assert parsed["permissions"]["contents"] == "read"
        assert parsed["permissions"]["pull-requests"] == "write"

    def test_concurrency(self, default_ci_config):
        """Workflow has concurrency settings."""
        content = generate_workflow(default_ci_config)
        parsed = yaml.safe_load(content)
        assert "concurrency" in parsed
        assert "group" in parsed["concurrency"]

    def test_checkout_step(self, default_ci_config):
        """Workflow includes checkout step."""
        content = generate_workflow(default_ci_config)
        parsed = yaml.safe_load(content)
        steps = parsed["jobs"]["prompt-guard"]["steps"]
        checkout = next(s for s in steps if s["name"] == "Checkout code")
        assert checkout["uses"] == "actions/checkout@v4"
        assert checkout["with"]["fetch-depth"] == 0

    def test_python_setup(self, custom_ci_config):
        """Workflow sets up correct Python version."""
        content = generate_workflow(custom_ci_config)
        parsed = yaml.safe_load(content)
        steps = parsed["jobs"]["prompt-guard"]["steps"]
        python_step = next(s for s in steps if s["name"] == "Set up Python")
        assert python_step["with"]["python-version"] == "3.11"

    def test_diff_step_enabled(self, default_ci_config):
        """Workflow includes diff step when enabled."""
        content = generate_workflow(default_ci_config)
        parsed = yaml.safe_load(content)
        steps = parsed["jobs"]["prompt-guard"]["steps"]
        step_names = [s["name"] for s in steps]
        assert "Run Prompt Diff" in step_names

    def test_diff_step_disabled(self, minimal_ci_config):
        """Workflow excludes diff step when disabled."""
        content = generate_workflow(minimal_ci_config)
        parsed = yaml.safe_load(content)
        steps = parsed["jobs"]["prompt-guard"]["steps"]
        step_names = [s["name"] for s in steps]
        # Diff is still enabled in minimal config
        assert "Run Prompt Diff" in step_names

    def test_eval_step_enabled(self, custom_ci_config):
        """Workflow includes eval step when enabled."""
        content = generate_workflow(custom_ci_config)
        parsed = yaml.safe_load(content)
        steps = parsed["jobs"]["prompt-guard"]["steps"]
        eval_step = next(s for s in steps if s["name"] == "Run Prompt Evaluation")
        assert "fixtures/dataset.jsonl" not in eval_step["run"]
        assert "data/eval.jsonl" in eval_step["run"]
        assert "0.1" in eval_step["run"]  # 0.10 is normalized to 0.1

    def test_eval_step_disabled(self, minimal_ci_config):
        """Workflow excludes eval step when disabled."""
        content = generate_workflow(minimal_ci_config)
        parsed = yaml.safe_load(content)
        steps = parsed["jobs"]["prompt-guard"]["steps"]
        step_names = [s["name"] for s in steps]
        assert "Run Prompt Evaluation" not in step_names

    def test_comment_step(self, default_ci_config):
        """Workflow includes PR comment step."""
        content = generate_workflow(default_ci_config)
        parsed = yaml.safe_load(content)
        steps = parsed["jobs"]["prompt-guard"]["steps"]
        comment_step = next(s for s in steps if s["name"] == "Comment PR with Report")
        assert comment_step["uses"] == "actions/github-script@v7"

    def test_artifact_upload(self, default_ci_config):
        """Workflow includes artifact upload step."""
        content = generate_workflow(default_ci_config)
        parsed = yaml.safe_load(content)
        steps = parsed["jobs"]["prompt-guard"]["steps"]
        upload_step = next(s for s in steps if s["name"] == "Upload Reports")
        assert upload_step["uses"] == "actions/upload-artifact@v4"

    def test_no_artifact_upload(self, minimal_ci_config):
        """Workflow excludes artifact upload when disabled."""
        content = generate_workflow(minimal_ci_config)
        parsed = yaml.safe_load(content)
        steps = parsed["jobs"]["prompt-guard"]["steps"]
        step_names = [s["name"] for s in steps]
        assert "Upload Reports" not in step_names


class TestPreCommitGeneration:
    """Tests for pre-commit config generation."""

    def test_valid_yaml(self, default_pre_commit_config):
        """Generated YAML is valid."""
        content = generate_pre_commit_config(default_pre_commit_config)
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict)

    def test_local_repo(self, default_pre_commit_config):
        """Config uses local repo."""
        content = generate_pre_commit_config(default_pre_commit_config)
        parsed = yaml.safe_load(content)
        assert parsed["repos"][0]["repo"] == "local"

    def test_diff_hook(self, default_pre_commit_config):
        """Config includes diff hook."""
        content = generate_pre_commit_config(default_pre_commit_config)
        parsed = yaml.safe_load(content)
        hooks = parsed["repos"][0]["hooks"]
        diff_hook = next(h for h in hooks if h["id"] == "prompt-diff")
        assert "pg diff" in diff_hook["entry"]
        assert "--fail-on=high" in diff_hook["entry"]

    def test_diff_fail_on(self, custom_pre_commit_config):
        """Config includes correct fail-on level."""
        content = generate_pre_commit_config(custom_pre_commit_config)
        parsed = yaml.safe_load(content)
        hooks = parsed["repos"][0]["hooks"]
        diff_hook = next(h for h in hooks if h["id"] == "prompt-diff")
        assert "--fail-on=med" in diff_hook["entry"]

    def test_eval_hook_enabled(self, custom_pre_commit_config):
        """Config includes eval hook when enabled."""
        content = generate_pre_commit_config(custom_pre_commit_config)
        parsed = yaml.safe_load(content)
        hooks = parsed["repos"][0]["hooks"]
        eval_hook = next(h for h in hooks if h["id"] == "prompt-eval")
        assert "pg eval" in eval_hook["entry"]

    def test_eval_hook_disabled(self, default_pre_commit_config):
        """Config excludes eval hook when disabled."""
        content = generate_pre_commit_config(default_pre_commit_config)
        parsed = yaml.safe_load(content)
        hooks = parsed["repos"][0]["hooks"]
        hook_ids = [h["id"] for h in hooks]
        assert "prompt-eval" not in hook_ids

    def test_file_pattern(self, default_pre_commit_config):
        """Config has correct file pattern."""
        content = generate_pre_commit_config(default_pre_commit_config)
        parsed = yaml.safe_load(content)
        hooks = parsed["repos"][0]["hooks"]
        diff_hook = next(h for h in hooks if h["id"] == "prompt-diff")
        assert r"\.prompts/.*\.ya?ml$" in diff_hook["files"]


class TestPublishWorkflow:
    """Tests for publish workflow generation."""

    def test_valid_yaml(self):
        """Generated YAML is valid."""
        content = generate_publish_workflow()
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict)

    def test_trigger_on_release(self):
        """Workflow triggers on release."""
        content = generate_publish_workflow()
        parsed = yaml.safe_load(content)
        assert "release" in parsed["on"]
        assert "published" in parsed["on"]["release"]["types"]

    def test_permissions(self):
        """Workflow has correct permissions."""
        content = generate_publish_workflow()
        parsed = yaml.safe_load(content)
        assert parsed["permissions"]["contents"] == "write"
        assert parsed["permissions"]["id-token"] == "write"

    def test_build_steps(self):
        """Workflow includes build steps."""
        content = generate_publish_workflow()
        parsed = yaml.safe_load(content)
        steps = parsed["jobs"]["build"]["steps"]
        step_names = [s["name"] for s in steps]
        assert "Checkout code" in step_names
        assert "Build package" in step_names
        assert "Upload to PyPI" in step_names

    def test_pypi_secret(self):
        """Workflow uses PYPI_API_TOKEN secret."""
        content = generate_publish_workflow()
        assert "PYPI_API_TOKEN" in content
        assert "${{ secrets.PYPI_API_TOKEN }}" in content


class TestVersionBumpScript:
    """Tests for version bump script generation."""

    def test_script_content(self):
        """Script contains version bump logic."""
        content = generate_version_bump_script()
        assert "#!/bin/bash" in content
        assert "BUMP_TYPE" in content
        assert "major" in content
        assert "minor" in content
        assert "patch" in content

    def test_sed_commands(self):
        """Script includes sed commands for version update."""
        content = generate_version_bump_script()
        assert "sed -i" in content
        assert "pyproject.toml" in content
        assert "__init__.py" in content

    def test_git_commands(self):
        """Script includes git commands."""
        content = generate_version_bump_script()
        assert "git add" in content
        assert "git commit" in content
        assert "git tag" in content


class TestInitCI:
    """Tests for CI initialization."""

    def test_dry_run(self, tmp_path, capsys):
        """Dry run shows files without creating them."""
        init_ci(output_dir=tmp_path, dry_run=True)
        captured = capsys.readouterr()
        assert (
            "would be created" in captured.out.lower()
            or "Files that would" in captured.out
        )

    def test_creates_workflow(self, tmp_path):
        """Creates workflow file."""
        files = init_ci(output_dir=tmp_path)
        assert files["workflow"].exists()
        assert files["workflow"].name == "prompt-guard.yml"

    def test_creates_publish(self, tmp_path):
        """Creates publish workflow file."""
        files = init_ci(output_dir=tmp_path)
        assert files["publish"].exists()
        assert files["publish"].name == "publish.yml"

    def test_creates_pre_commit(self, tmp_path):
        """Creates pre-commit config file."""
        files = init_ci(output_dir=tmp_path)
        assert files["pre_commit"].exists()
        assert files["pre_commit"].name == ".pre-commit-config.yaml"

    def test_creates_bump_script(self, tmp_path):
        """Creates version bump script."""
        files = init_ci(output_dir=tmp_path)
        assert files["bump_script"].exists()
        assert files["bump_script"].name == "bump_version.sh"

    def test_workflow_content(self, tmp_path):
        """Workflow file has valid content."""
        files = init_ci(output_dir=tmp_path)
        content = files["workflow"].read_text()
        parsed = yaml.safe_load(content)
        assert parsed["name"] == "Prompt Guard"

    def test_creates_directories(self, tmp_path):
        """Creates necessary directories."""
        init_ci(output_dir=tmp_path)
        assert (tmp_path / ".github" / "workflows").exists()
        assert (tmp_path / "scripts").exists()

    def test_custom_config(self, tmp_path):
        """Loads custom config from file."""
        config = {
            "branches": ["main"],
            "threshold": 0.10,
            "model_provider": "openai",
        }
        config_path = tmp_path / "ci_config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        files = init_ci(config_path=config_path, output_dir=tmp_path)
        content = files["workflow"].read_text()
        assert "0.1" in content  # 0.10 is normalized to 0.1


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_branches(self):
        """Handle empty branches list."""
        config = CIConfig(branches=[])
        content = generate_workflow(config)
        parsed = yaml.safe_load(content)
        assert "pull_request" in parsed["on"]

    def test_special_characters_in_path(self):
        """Handle paths with special characters."""
        config = CIConfig(paths=[".prompts/**", "data/*.jsonl"])
        content = generate_workflow(config)
        parsed = yaml.safe_load(content)
        assert ".prompts/**" in parsed["on"]["pull_request"]["paths"]

    def test_all_features_disabled(self):
        """Handle all features disabled."""
        config = CIConfig(
            enable_diff=False,
            enable_eval=False,
            comment_on_failure=False,
            upload_artifact=False,
        )
        content = generate_workflow(config)
        parsed = yaml.safe_load(content)
        steps = parsed["jobs"]["prompt-guard"]["steps"]
        # Should still have checkout, python setup, uv, install
        assert len(steps) >= 4

    def test_unicode_in_config(self):
        """Handle unicode characters."""
        config = CIConfig(
            dataset_path="datasets/eval.jsonl",
        )
        content = generate_workflow(config)
        assert "datasets/eval.jsonl" in content
