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
