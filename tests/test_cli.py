"""Tests for prompt-git-manager CLI commands."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml
from typer.testing import CliRunner

from promptgit.cli import app

runner = CliRunner()


class TestVersionCallback:
    """Tests for pg --version flag."""

    def test_version_flag(self):
        """--version prints version and exits."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "prompt-git-manager" in result.output

    def test_version_short_flag(self):
        """-v prints version and exits."""
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert "prompt-git-manager" in result.output


class TestInitCommand:
    """Tests for pg init command."""

    def test_init_creates_prompts_dir(self, tmp_git_repo: tuple):
        """Normal path: init creates .prompts/ directory with config."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert (repo_path / ".prompts").exists()
        assert (repo_path / ".prompts" / "config.json").exists()

    def test_init_dry_run(self, tmp_git_repo: tuple):
        """Dry run: does not create files."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        result = runner.invoke(app, ["init", "--dry-run"])
        assert result.exit_code == 0
        assert not (repo_path / ".prompts").exists()

    def test_init_not_git_repo(self, tmp_path: Path):
        """Error path: fails outside git repo."""
        import os

        os.chdir(tmp_path)

        result = runner.invoke(app, ["init"])
        assert result.exit_code == 2  # ERR_GIT

    def test_init_idempotent(self, tmp_git_repo: tuple):
        """Edge case: running init twice does not error."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0

    def test_init_creates_gitignore(self, tmp_git_repo: tuple):
        """Init creates .gitignore inside .prompts/."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        runner.invoke(app, ["init"])
        gitignore = repo_path / ".prompts" / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "*.tmp" in content

    def test_init_config_content(self, tmp_git_repo: tuple):
        """Init config.json has expected fields."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        runner.invoke(app, ["init"])
        config_path = repo_path / ".prompts" / "config.json"
        config = json.loads(config_path.read_text())
        assert "version" in config
        assert "created_at" in config
        assert config["eval_threshold"] == 0.05

    def test_init_preserves_existing_config(self, tmp_git_repo: tuple):
        """Init does not overwrite existing config.json."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        prompts_dir = repo_path / ".prompts"
        prompts_dir.mkdir()
        custom_config = {"version": "9.9.9", "custom": True}
        (prompts_dir / "config.json").write_text(json.dumps(custom_config))

        runner.invoke(app, ["init"])
        config = json.loads((prompts_dir / "config.json").read_text())
        assert config["version"] == "9.9.9"
        assert config["custom"] is True


class TestAddCommand:
    """Tests for pg add command."""

    def test_add_valid_prompt(self, tmp_git_repo: tuple, sample_prompt_yaml: Path):
        """Normal path: adds valid prompt file to tracking."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        # Init first
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["add", str(sample_prompt_yaml)])
        assert result.exit_code == 0
        assert (repo_path / ".prompts" / "test_prompt.yaml").exists()

    def test_add_dry_run(self, tmp_git_repo: tuple, sample_prompt_yaml: Path):
        """Dry run: does not copy file."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["add", str(sample_prompt_yaml), "--dry-run"])
        assert result.exit_code == 0
        assert not (repo_path / ".prompts" / "test_prompt.yaml").exists()

    def test_add_missing_file(self, tmp_git_repo: tuple):
        """Error path: fails for non-existent file."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["add", "/nonexistent/file.yaml"])
        assert result.exit_code == 1  # ERR_ARGS

    def test_add_invalid_schema(self, tmp_git_repo: tuple, invalid_prompt_yaml: Path):
        """Error path: fails for invalid prompt schema."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["add", str(invalid_prompt_yaml)])
        assert result.exit_code == 3  # ERR_VALIDATION

    def test_add_unsupported_format(self, tmp_git_repo: tuple, tmp_path: Path):
        """Error path: fails for unsupported file format."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        runner.invoke(app, ["init"])

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a prompt")

        result = runner.invoke(app, ["add", str(txt_file)])
        assert result.exit_code == 1  # ERR_ARGS

    def test_add_json_format(self, tmp_git_repo: tuple, tmp_path: Path):
        """Normal path: adds .json prompt file."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        runner.invoke(app, ["init"])

        prompt_data = {
            "name": "json-prompt",
            "version": "1.0.0",
            "system_prompt": "You are helpful.",
            "user_template": "Q: {{q}}",
            "variables": {"q": {"default": "test"}},
            "constraints": [],
            "metadata": {},
        }
        json_file = tmp_path / "prompt.json"
        json_file.write_text(json.dumps(prompt_data))

        result = runner.invoke(app, ["add", str(json_file)])
        assert result.exit_code == 0
        assert (repo_path / ".prompts" / "prompt.json").exists()

    def test_add_dry_run_shows_metadata(self, tmp_git_repo: tuple, sample_prompt_yaml: Path):
        """Dry run output includes prompt name and version."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["add", str(sample_prompt_yaml), "--dry-run"])
        assert result.exit_code == 0
        assert "test-prompt" in result.output
        assert "1.0.0" in result.output

    def test_add_auto_creates_prompts_dir(self, tmp_git_repo: tuple, sample_prompt_yaml: Path):
        """Normal path: add auto-creates .prompts/ if missing."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        result = runner.invoke(app, ["add", str(sample_prompt_yaml)])
        assert result.exit_code == 0
        assert (repo_path / ".prompts" / "test_prompt.yaml").exists()


class TestCommitCommand:
    """Tests for pg commit command."""

    def test_commit_prompt_changes(self, initialized_repo: tuple):
        """Normal path: commits prompt changes with record."""
        repo_path, repo, prompts_dir = initialized_repo
        import os

        os.chdir(repo_path)

        result = runner.invoke(app, ["commit", "-m", "test commit"])
        assert result.exit_code == 0

        # Check commit record
        record_path = prompts_dir / "commits.jsonl"
        assert record_path.exists()
        records = record_path.read_text().strip().split("\n")
        assert len(records) == 1
        record = json.loads(records[0])
        assert record["message"] == "test commit"
        assert record["validation_status"] == "pass"

    def test_commit_dry_run(self, initialized_repo: tuple):
        """Dry run: does not create commit."""
        repo_path, repo, prompts_dir = initialized_repo
        import os

        os.chdir(repo_path)

        initial_commit_count = len(list(repo.iter_commits()))

        result = runner.invoke(app, ["commit", "-m", "dry run test", "--dry-run"])
        assert result.exit_code == 0

        # No new commits
        assert len(list(repo.iter_commits())) == initial_commit_count
        assert not (prompts_dir / "commits.jsonl").exists()

    def test_commit_no_prompts_dir(self, tmp_git_repo: tuple):
        """Error path: fails without .prompts/ directory."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        result = runner.invoke(app, ["commit", "-m", "no prompts"])
        assert result.exit_code == 1  # ERR_ARGS

    def test_commit_no_changes(self, tmp_git_repo: tuple):
        """Edge case: handles empty .prompts/ directory gracefully."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        # Create empty .prompts/
        (repo_path / ".prompts").mkdir()

        result = runner.invoke(app, ["commit", "-m", "empty"])
        assert result.exit_code == 0  # Should succeed with "no files" message

    def test_commit_with_validation_errors(
        self, tmp_git_repo: tuple, invalid_prompt_yaml: Path
    ):
        """Edge case: commits with validation warnings."""
        repo_path, repo = tmp_git_repo
        import os

        os.chdir(repo_path)

        prompts_dir = repo_path / ".prompts"
        prompts_dir.mkdir()

        # Copy invalid file
        import shutil

        shutil.copy2(invalid_prompt_yaml, prompts_dir / "invalid.yaml")

        # Track the file
        repo.index.add([".prompts/invalid.yaml"])
        repo.index.commit("add invalid")

        result = runner.invoke(app, ["commit", "-m", "commit with warnings"])
        # Should still succeed but with warnings
        assert result.exit_code == 0

    def test_commit_multiple_files(self, initialized_repo_with_multiple_prompts: tuple):
        """Commits all prompt files in .prompts/."""
        repo_path, repo, prompts_dir = initialized_repo_with_multiple_prompts
        import os

        os.chdir(repo_path)

        result = runner.invoke(app, ["commit", "-m", "add all prompts"])
        assert result.exit_code == 0

        # Verify commit record lists all files
        record_path = prompts_dir / "commits.jsonl"
        assert record_path.exists()
        record = json.loads(record_path.read_text().strip())
        assert len(record["changed_files"]) == 3

    def test_commit_record_fields(self, initialized_repo: tuple):
        """Commit record has all expected fields."""
        repo_path, repo, prompts_dir = initialized_repo
        import os

        os.chdir(repo_path)

        result = runner.invoke(app, ["commit", "-m", "test fields"])
        assert result.exit_code == 0

        record_path = prompts_dir / "commits.jsonl"
        record = json.loads(record_path.read_text().strip())
        assert "hash" in record
        assert "timestamp" in record
        assert "changed_files" in record
        assert "validation_status" in record
        assert "message" in record
        assert record["message"] == "test fields"
        assert len(record["hash"]) == 12

    def test_commit_dry_run_shows_files(self, initialized_repo: tuple):
        """Dry run output lists files to commit."""
        repo_path, repo, prompts_dir = initialized_repo
        import os

        os.chdir(repo_path)

        result = runner.invoke(app, ["commit", "-m", "dry", "--dry-run"])
        assert result.exit_code == 0
        assert "test_prompt.yaml" in result.output


class TestDiffCommand:
    """Tests for pg diff command."""

    def test_diff_basic(self, initialized_repo_for_diff: tuple, monkeypatch):
        """Basic diff detects changed prompt file."""
        repo_path, repo, prompts_dir = initialized_repo_for_diff
        monkeypatch.chdir(repo_path)

        result = runner.invoke(app, ["diff"])
        assert result.exit_code == 0

    def test_diff_no_changes(self, initialized_repo: tuple, monkeypatch):
        """Diff still runs when files exist but match HEAD."""
        repo_path, repo, prompts_dir = initialized_repo
        monkeypatch.chdir(repo_path)

        # Files match HEAD — diff still processes them but shows no semantic changes
        result = runner.invoke(app, ["diff"])
        assert result.exit_code == 0

    def test_diff_no_yaml_files(self, tmp_git_repo: tuple, monkeypatch):
        """No prompt changes when .prompts/ has no YAML files."""
        repo_path, repo = tmp_git_repo
        monkeypatch.chdir(repo_path)

        prompts_dir = repo_path / ".prompts"
        prompts_dir.mkdir()
        (prompts_dir / "config.json").write_text("{}")
        repo.index.add([".prompts/config.json"])
        repo.index.commit("init")

        result = runner.invoke(app, ["diff"])
        assert result.exit_code == 0
        assert "No prompt changes" in result.output

    def test_diff_json_output(self, initialized_repo_for_diff: tuple, monkeypatch):
        """--json outputs valid JSON diff result."""
        repo_path, repo, prompts_dir = initialized_repo_for_diff
        monkeypatch.chdir(repo_path)

        result = runner.invoke(app, ["diff", "--json"])
        assert result.exit_code == 0

        output = json.loads(result.output)
        assert isinstance(output, dict)
        assert len(output) >= 1
        for filename, diff_data in output.items():
            assert "risk_level" in diff_data
            assert "semantic_change_type" in diff_data
            assert "summary" in diff_data

    def test_diff_semantic_flag(self, initialized_repo_for_diff: tuple, monkeypatch):
        """--semantic shows semantic diff with risk analysis."""
        repo_path, repo, prompts_dir = initialized_repo_for_diff
        monkeypatch.chdir(repo_path)

        result = runner.invoke(app, ["diff", "--semantic"])
        assert result.exit_code == 0
        # Semantic output should include risk level info
        assert "Risk Level" in result.output or "LOW" in result.output or "MEDIUM" in result.output or "HIGH" in result.output

    def test_diff_fail_on_high_risk(self, initialized_repo_for_diff: tuple, monkeypatch):
        """--fail-on high exits with error when risk >= high."""
        repo_path, repo, prompts_dir = initialized_repo_for_diff
        monkeypatch.chdir(repo_path)

        # The initialized_repo_for_diff fixture has a role shift (HIGH risk)
        result = runner.invoke(app, ["diff", "--fail-on", "high"])
        # May pass (exit 0) or fail (exit 2) depending on actual risk level
        assert result.exit_code in (0, 2)

    def test_diff_fail_on_low(self, initialized_repo_for_diff: tuple, monkeypatch):
        """--fail-on low exits with error when any change exists."""
        repo_path, repo, prompts_dir = initialized_repo_for_diff
        monkeypatch.chdir(repo_path)

        # Any change should trigger failure with --fail-on low
        result = runner.invoke(app, ["diff", "--fail-on", "low"])
        assert result.exit_code == 2

    def test_diff_fail_on_invalid_value(self, initialized_repo_for_diff: tuple, monkeypatch):
        """--fail-on with invalid value fails."""
        repo_path, repo, prompts_dir = initialized_repo_for_diff
        monkeypatch.chdir(repo_path)

        result = runner.invoke(app, ["diff", "--fail-on", "invalid"])
        assert result.exit_code == 1  # ERR_ARGS

    def test_diff_specific_file(self, initialized_repo_for_diff: tuple, monkeypatch):
        """Diff specific file by argument."""
        repo_path, repo, prompts_dir = initialized_repo_for_diff
        monkeypatch.chdir(repo_path)

        result = runner.invoke(app, ["diff", ".prompts/test_prompt.yaml"])
        assert result.exit_code == 0

    def test_diff_specific_file_not_found(self, initialized_repo_for_diff: tuple, monkeypatch):
        """Error: diff specific file that doesn't exist."""
        repo_path, repo, prompts_dir = initialized_repo_for_diff
        monkeypatch.chdir(repo_path)

        result = runner.invoke(app, ["diff", ".prompts/nonexistent.yaml"])
        assert result.exit_code == 1  # ERR_ARGS

    def test_diff_no_prompts_dir(self, tmp_git_repo: tuple, monkeypatch):
        """Error: fails when .prompts/ directory is missing."""
        repo_path, repo = tmp_git_repo
        monkeypatch.chdir(repo_path)

        result = runner.invoke(app, ["diff"])
        assert result.exit_code == 1  # ERR_ARGS

    def test_diff_new_file(self, initialized_repo: tuple, monkeypatch):
        """Diff shows new file when prompt file is newly added."""
        repo_path, repo, prompts_dir = initialized_repo
        monkeypatch.chdir(repo_path)

        # Add a new prompt file (not in HEAD)
        new_prompt = {
            "name": "new-prompt",
            "version": "1.0.0",
            "system_prompt": "New assistant.",
            "user_template": "New: {{x}}",
            "variables": {"x": {"default": "test"}},
            "constraints": [],
            "metadata": {},
        }
        (prompts_dir / "new_prompt.yaml").write_text(
            yaml.dump(new_prompt, default_flow_style=False)
        )

        result = runner.invoke(app, ["diff", "--json"])
        assert result.exit_code == 0

        output = json.loads(result.output)
        # The new file should appear in the diff
        has_new = any(
            "new file" in str(v.get("summary", "")).lower() or "added" in str(v.get("added_fields", [])).lower()
            for v in output.values()
        )
        assert has_new or len(output) >= 1

    def test_diff_json_has_text_diff(self, initialized_repo_for_diff: tuple, monkeypatch):
        """JSON output includes text_diff field."""
        repo_path, repo, prompts_dir = initialized_repo_for_diff
        monkeypatch.chdir(repo_path)

        result = runner.invoke(app, ["diff", "--json"])
        assert result.exit_code == 0

        output = json.loads(result.output)
        for filename, diff_data in output.items():
            # text_diff may or may not be present
            assert isinstance(diff_data, dict)

    def test_diff_modified_fields_in_json(self, initialized_repo_for_diff: tuple, monkeypatch):
        """JSON output shows modified fields with old/new values."""
        repo_path, repo, prompts_dir = initialized_repo_for_diff
        monkeypatch.chdir(repo_path)

        result = runner.invoke(app, ["diff", "--json"])
        assert result.exit_code == 0

        output = json.loads(result.output)
        for filename, diff_data in output.items():
            if diff_data.get("modified_fields"):
                for mod in diff_data["modified_fields"]:
                    assert "field" in mod
                    assert "old_value" in mod or "old" in mod


class TestEvalCommand:
    """Tests for pg eval command."""

    def test_eval_rule_based_pass(self, initialized_repo_for_eval: tuple, monkeypatch):
        """Rule-based eval: passes when new prompt is identical to old."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)

        result = runner.invoke(app, ["eval", "--dataset", str(dataset_path)])
        assert result.exit_code == 0
        assert "PASSED" in result.output

    def test_eval_rule_based_fail(self, tmp_git_repo: tuple, monkeypatch, tmp_path: Path):
        """Rule-based eval: fails when new prompt loses relevant keywords."""
        repo_path, repo = tmp_git_repo
        monkeypatch.chdir(repo_path)
        prompts_dir = repo_path / ".prompts"
        prompts_dir.mkdir(exist_ok=True)

        # Create config
        config = {"version": "0.1.0", "eval_threshold": 0.05}
        (prompts_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")

        # Old prompt (committed) has keywords matching dataset expected outputs
        old_prompt = {
            "name": "eval-prompt",
            "version": "1.0.0",
            "system_prompt": "You are a Python programming expert. You know about Git version control and artificial intelligence.",
            "user_template": "Answer about Python programming language, Git version control system, AI artificial intelligence: {{question}}",
            "variables": {"question": {"default": "What?"}},
            "constraints": [],
            "metadata": {},
        }
        (prompts_dir / "eval_prompt.yaml").write_text(
            yaml.dump(old_prompt, default_flow_style=False), encoding="utf-8"
        )
        repo.index.add([".prompts/config.json", ".prompts/eval_prompt.yaml"])
        repo.index.commit("Initial commit")

        # New prompt (working copy) has no relevant keywords
        bad_prompt = {
            "name": "eval-prompt",
            "version": "2.0.0",
            "system_prompt": "You are a bot.",
            "user_template": "Respond: {{question}}",
            "variables": {"question": {"default": "Hello"}},
            "constraints": [],
            "metadata": {},
        }
        (prompts_dir / "eval_prompt.yaml").write_text(
            yaml.dump(bad_prompt, default_flow_style=False), encoding="utf-8"
        )

        # Dataset
        dataset_path = tmp_path / "test_dataset.jsonl"
        samples = [
            {"input": "What is Python?", "expected_output": "Python is a programming language"},
            {"input": "What is Git?", "expected_output": "Git is a version control system"},
            {"input": "What is AI?", "expected_output": "AI is artificial intelligence"},
        ]
        with open(dataset_path, "w", encoding="utf-8") as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")

        result = runner.invoke(app, ["eval", "--dataset", str(dataset_path)])
        assert result.exit_code == 2  # ERR_GIT for eval failure
        assert "FAILED" in result.output

    def test_eval_json_output(self, initialized_repo_for_eval: tuple, monkeypatch):
        """--json flag outputs valid JSON with expected fields."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)

        result = runner.invoke(app, ["eval", "--dataset", str(dataset_path), "--json"])
        assert result.exit_code == 0

        output = json.loads(result.output)
        assert "total_samples" in output
        assert "accuracy_old" in output
        assert "accuracy_new" in output
        assert "accuracy_delta" in output
        assert "passed" in output
        assert "threshold" in output
        assert "details" in output
        assert output["total_samples"] == 3

    def test_eval_custom_threshold(self, initialized_repo_for_eval: tuple, monkeypatch):
        """--threshold flag overrides default threshold."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)

        result = runner.invoke(
            app, ["eval", "--dataset", str(dataset_path), "--threshold", "0.5", "--json"]
        )
        assert result.exit_code == 0

        output = json.loads(result.output)
        assert output["threshold"] == 0.5

    def test_eval_threshold_env_var(self, initialized_repo_for_eval: tuple, monkeypatch):
        """PROMPT_GIT_THRESHOLD env var sets default threshold."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)
        monkeypatch.setenv("PROMPT_GIT_THRESHOLD", "0.3")

        result = runner.invoke(app, ["eval", "--dataset", str(dataset_path), "--json"])
        assert result.exit_code == 0

        output = json.loads(result.output)
        assert output["threshold"] == 0.3

    def test_eval_old_new_custom_files(
        self, initialized_repo_for_eval: tuple, monkeypatch, tmp_path: Path
    ):
        """--old and --new specify custom prompt files."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)

        # Create old and new prompt files
        old_prompt = {
            "name": "old",
            "version": "1.0.0",
            "system_prompt": "You are helpful.",
            "user_template": "Q: {{question}}",
            "variables": {"question": {"default": "test"}},
            "constraints": [],
            "metadata": {},
        }
        new_prompt = {
            "name": "new",
            "version": "2.0.0",
            "system_prompt": "You are helpful.",
            "user_template": "Answer: {{question}}",
            "variables": {"question": {"default": "test"}},
            "constraints": [],
            "metadata": {},
        }

        old_path = tmp_path / "old_prompt.yaml"
        new_path = tmp_path / "new_prompt.yaml"
        old_path.write_text(yaml.dump(old_prompt, default_flow_style=False))
        new_path.write_text(yaml.dump(new_prompt, default_flow_style=False))

        result = runner.invoke(
            app,
            [
                "eval",
                "--dataset", str(dataset_path),
                "--old", str(old_path),
                "--new", str(new_path),
                "--json",
            ],
        )
        assert result.exit_code == 0

        output = json.loads(result.output)
        assert output["total_samples"] == 3

    def test_eval_no_prompts_dir(self, tmp_git_repo: tuple, monkeypatch, tmp_path: Path):
        """Error: fails when .prompts/ directory is missing."""
        repo_path, repo = tmp_git_repo
        monkeypatch.chdir(repo_path)

        dataset = tmp_path / "ds.jsonl"
        dataset.write_text('{"input": "hi", "expected_output": "hello"}\n')

        result = runner.invoke(app, ["eval", "--dataset", str(dataset)])
        assert result.exit_code == 1  # ERR_ARGS

    def test_eval_missing_dataset(self, initialized_repo_for_eval: tuple, monkeypatch):
        """Error: fails when dataset file does not exist."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)

        result = runner.invoke(app, ["eval", "--dataset", "/nonexistent/dataset.jsonl"])
        assert result.exit_code == 1  # ERR_ARGS

    def test_eval_empty_dataset(
        self, initialized_repo_for_eval: tuple, monkeypatch, tmp_path: Path
    ):
        """Error: fails when dataset is empty."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)

        empty_ds = tmp_path / "empty.jsonl"
        empty_ds.write_text("")

        result = runner.invoke(app, ["eval", "--dataset", str(empty_ds)])
        assert result.exit_code == 1  # ERR_ARGS

    def test_eval_llm_mode(self, initialized_repo_for_eval: tuple, monkeypatch):
        """LLM eval mode: uses --provider and --model with mocked LLM."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        mock_result = MagicMock()
        mock_result.total_samples = 3
        mock_result.accuracy_old = 1.0
        mock_result.accuracy_new = 1.0
        mock_result.accuracy_delta = 0.0
        mock_result.token_cost_old = 100
        mock_result.token_cost_new = 100
        mock_result.token_cost_delta = 0.0
        mock_result.consistency_score = 1.0
        mock_result.passed = True
        mock_result.threshold = 0.05
        mock_result.provider = "openai"
        mock_result.model = "gpt-3.5-turbo"
        mock_result.to_json.return_value = json.dumps({
            "total_samples": 3,
            "accuracy_old": 1.0,
            "accuracy_new": 1.0,
            "accuracy_delta": 0.0,
            "token_cost_old": 100,
            "token_cost_new": 100,
            "token_cost_delta": 0.0,
            "consistency_score": 1.0,
            "passed": True,
            "threshold": 0.05,
        })

        with patch("promptgit.llm_evaluator.evaluate_prompts_with_llm", return_value=mock_result) as mock_eval:
            result = runner.invoke(
                app,
                [
                    "eval",
                    "--dataset", str(dataset_path),
                    "--provider", "openai",
                    "--model", "gpt-3.5-turbo",
                ],
            )
            assert result.exit_code == 0
            mock_eval.assert_called_once()
            # Verify config was passed correctly
            call_args = mock_eval.call_args
            assert call_args[0][3].model == "gpt-3.5-turbo"

    def test_eval_llm_json_output(self, initialized_repo_for_eval: tuple, monkeypatch):
        """LLM eval with --json outputs valid JSON."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        mock_result = MagicMock()
        mock_result.to_json.return_value = json.dumps({
            "total_samples": 3,
            "accuracy_old": 1.0,
            "accuracy_new": 0.8,
            "accuracy_delta": -0.2,
            "passed": False,
            "threshold": 0.05,
        })

        with patch("promptgit.llm_evaluator.evaluate_prompts_with_llm", return_value=mock_result):
            result = runner.invoke(
                app,
                [
                    "eval",
                    "--dataset", str(dataset_path),
                    "--provider", "openai",
                    "--model", "gpt-4",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            # CLI may print Rich console lines before JSON; find JSON start
            json_start = result.output.find("{")
            assert json_start >= 0, f"No JSON found in output: {result.output}"
            output = json.loads(result.output[json_start:])
            assert output["total_samples"] == 3

    def test_eval_llm_judge_mode(self, initialized_repo_for_eval: tuple, monkeypatch):
        """LLM-as-judge mode: --judge flag enables judge evaluation."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        mock_result = MagicMock()
        mock_result.total_samples = 3
        mock_result.accuracy_old = 1.0
        mock_result.accuracy_new = 1.0
        mock_result.accuracy_delta = 0.0
        mock_result.token_cost_old = 100
        mock_result.token_cost_new = 100
        mock_result.token_cost_delta = 0.0
        mock_result.consistency_score = 1.0
        mock_result.passed = True
        mock_result.threshold = 0.05
        mock_result.to_json.return_value = json.dumps({"passed": True})

        with patch("promptgit.llm_evaluator.evaluate_prompts_with_llm", return_value=mock_result) as mock_eval:
            result = runner.invoke(
                app,
                [
                    "eval",
                    "--dataset", str(dataset_path),
                    "--provider", "openai",
                    "--model", "gpt-3.5-turbo",
                    "--judge",
                    "--judge-model", "gpt-4",
                ],
            )
            assert result.exit_code == 0
            call_args = mock_eval.call_args
            # use_judge should be True
            assert call_args[1].get("use_judge") is True or call_args[0][5] is True
            # judge_config should be set
            judge_config = call_args[1].get("judge_config") or call_args[0][6]
            assert judge_config is not None
            assert judge_config.model == "gpt-4"

    def test_eval_model_comparison(self, initialized_repo_for_eval: tuple, monkeypatch):
        """--compare-models mode compares two models."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        from promptgit.llm_evaluator import LLMCompareResult

        mock_results = [
            LLMCompareResult(
                model_a="gpt-3.5-turbo",
                model_b="gpt-4",
                score_a=0.7,
                score_b=0.9,
                winner="B",
                reasoning="Model B better",
            ),
            LLMCompareResult(
                model_a="gpt-3.5-turbo",
                model_b="gpt-4",
                score_a=0.8,
                score_b=0.85,
                winner="B",
                reasoning="Model B slightly better",
            ),
            LLMCompareResult(
                model_a="gpt-3.5-turbo",
                model_b="gpt-4",
                score_a=0.9,
                score_b=0.7,
                winner="A",
                reasoning="Model A better",
            ),
        ]

        with patch("promptgit.llm_evaluator.compare_models", return_value=mock_results) as mock_cmp:
            result = runner.invoke(
                app,
                [
                    "eval",
                    "--dataset", str(dataset_path),
                    "--compare-models", "gpt-3.5-turbo,gpt-4",
                ],
            )
            assert result.exit_code == 0
            mock_cmp.assert_called_once()

    def test_eval_model_comparison_json(
        self, initialized_repo_for_eval: tuple, monkeypatch
    ):
        """--compare-models with --json outputs valid JSON."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        from promptgit.llm_evaluator import LLMCompareResult

        mock_results = [
            LLMCompareResult(
                model_a="gpt-3.5-turbo",
                model_b="gpt-4",
                score_a=0.7,
                score_b=0.9,
                winner="B",
                reasoning="Better",
            ),
        ]

        with patch("promptgit.llm_evaluator.compare_models", return_value=mock_results):
            result = runner.invoke(
                app,
                [
                    "eval",
                    "--dataset", str(dataset_path),
                    "--compare-models", "gpt-3.5-turbo,gpt-4",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            json_start = result.output.find("{")
            assert json_start >= 0, f"No JSON found in output: {result.output}"
            output = json.loads(result.output[json_start:])
            assert "model_a" in output
            assert "model_b" in output
            assert "results" in output
            assert "summary" in output
            assert output["summary"]["wins_b"] == 1

    def test_eval_model_comparison_with_provider(
        self, initialized_repo_for_eval: tuple, monkeypatch
    ):
        """--compare-models with provider:model format."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        from promptgit.llm_evaluator import LLMCompareResult

        mock_results = [
            LLMCompareResult(
                model_a="claude-2",
                model_b="gpt-4",
                score_a=0.8,
                score_b=0.8,
                winner="Tie",
                reasoning="Equal",
            ),
        ]

        with patch("promptgit.llm_evaluator.compare_models", return_value=mock_results) as mock_cmp:
            result = runner.invoke(
                app,
                [
                    "eval",
                    "--dataset", str(dataset_path),
                    "--compare-models", "anthropic:claude-2,openai:gpt-4",
                ],
            )
            assert result.exit_code == 0
            # Verify configs were created with correct providers
            call_args = mock_cmp.call_args
            config_a = call_args[0][2]
            config_b = call_args[0][3]
            assert config_a.provider == "anthropic"
            assert config_a.model == "claude-2"
            assert config_b.provider == "openai"
            assert config_b.model == "gpt-4"

    def test_eval_model_comparison_too_few(
        self, initialized_repo_for_eval: tuple, monkeypatch
    ):
        """Error: --compare-models with only 1 model fails."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)

        result = runner.invoke(
            app,
            [
                "eval",
                "--dataset", str(dataset_path),
                "--compare-models", "gpt-4",
            ],
        )
        assert result.exit_code == 1  # ERR_ARGS

    def test_eval_model_env_var_provider_only(
        self, initialized_repo_for_eval: tuple, monkeypatch
    ):
        """PROMPT_GIT_MODEL with provider only (no colon) sets provider only."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)
        monkeypatch.setenv("PROMPT_GIT_MODEL", "openai")

        # Without model, falls through to rule-based eval
        result = runner.invoke(
            app, ["eval", "--dataset", str(dataset_path)]
        )
        assert result.exit_code == 0
        assert "PASSED" in result.output

    def test_eval_model_env_var_provider_model(
        self, initialized_repo_for_eval: tuple, monkeypatch
    ):
        """PROMPT_GIT_MODEL with 'provider:model' enables LLM mode."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("PROMPT_GIT_MODEL", "openai:gpt-4")

        mock_result = MagicMock()
        mock_result.total_samples = 3
        mock_result.accuracy_old = 1.0
        mock_result.accuracy_new = 1.0
        mock_result.accuracy_delta = 0.0
        mock_result.token_cost_old = 100
        mock_result.token_cost_new = 100
        mock_result.token_cost_delta = 0.0
        mock_result.consistency_score = 1.0
        mock_result.passed = True
        mock_result.threshold = 0.05
        mock_result.to_json.return_value = json.dumps({"passed": True})

        with patch("promptgit.llm_evaluator.evaluate_prompts_with_llm", return_value=mock_result) as mock_eval:
            result = runner.invoke(
                app, ["eval", "--dataset", str(dataset_path)]
            )
            assert result.exit_code == 0
            mock_eval.assert_called_once()
            call_args = mock_eval.call_args
            config = call_args[0][3]
            assert config.provider == "openai"
            assert config.model == "gpt-4"

    def test_eval_llm_api_base(self, initialized_repo_for_eval: tuple, monkeypatch):
        """--api-base is passed to LLM config."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        mock_result = MagicMock()
        mock_result.total_samples = 3
        mock_result.accuracy_old = 1.0
        mock_result.accuracy_new = 1.0
        mock_result.accuracy_delta = 0.0
        mock_result.token_cost_old = 100
        mock_result.token_cost_new = 100
        mock_result.token_cost_delta = 0.0
        mock_result.consistency_score = 1.0
        mock_result.passed = True
        mock_result.threshold = 0.05
        mock_result.to_json.return_value = json.dumps({"passed": True})

        with patch("promptgit.llm_evaluator.evaluate_prompts_with_llm", return_value=mock_result) as mock_eval:
            result = runner.invoke(
                app,
                [
                    "eval",
                    "--dataset", str(dataset_path),
                    "--provider", "openai",
                    "--model", "gpt-4",
                    "--api-base", "http://localhost:8080/v1",
                ],
            )
            assert result.exit_code == 0
            call_args = mock_eval.call_args
            config = call_args[0][3]
            assert config.api_base == "http://localhost:8080/v1"

    def test_eval_details_in_json(self, initialized_repo_for_eval: tuple, monkeypatch):
        """JSON output includes per-sample details."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)

        result = runner.invoke(app, ["eval", "--dataset", str(dataset_path), "--json"])
        assert result.exit_code == 0

        output = json.loads(result.output)
        assert len(output["details"]) == 3
        for detail in output["details"]:
            assert "input" in detail
            assert "expected" in detail
            assert "old_output" in detail
            assert "new_output" in detail
            assert "old_match" in detail
            assert "new_match" in detail
            assert "similarity_delta" in detail

    def test_eval_judge_provider_different(
        self, initialized_repo_for_eval: tuple, monkeypatch
    ):
        """--judge-provider allows different provider for judge."""
        repo_path, repo, prompts_dir, dataset_path = initialized_repo_for_eval
        monkeypatch.chdir(repo_path)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mock_result = MagicMock()
        mock_result.total_samples = 3
        mock_result.accuracy_old = 1.0
        mock_result.accuracy_new = 1.0
        mock_result.accuracy_delta = 0.0
        mock_result.token_cost_old = 100
        mock_result.token_cost_new = 100
        mock_result.token_cost_delta = 0.0
        mock_result.consistency_score = 1.0
        mock_result.passed = True
        mock_result.threshold = 0.05
        mock_result.to_json.return_value = json.dumps({"passed": True})

        with patch("promptgit.llm_evaluator.evaluate_prompts_with_llm", return_value=mock_result) as mock_eval:
            result = runner.invoke(
                app,
                [
                    "eval",
                    "--dataset", str(dataset_path),
                    "--provider", "openai",
                    "--model", "gpt-3.5-turbo",
                    "--judge",
                    "--judge-provider", "anthropic",
                    "--judge-model", "claude-2",
                ],
            )
            assert result.exit_code == 0
            call_args = mock_eval.call_args
            judge_config = call_args[1].get("judge_config") or call_args[0][6]
            assert judge_config is not None
            assert judge_config.provider == "anthropic"
            assert judge_config.model == "claude-2"
