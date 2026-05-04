"""Tests for prompt-git-manager CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from promptgit.cli import app

runner = CliRunner()


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
