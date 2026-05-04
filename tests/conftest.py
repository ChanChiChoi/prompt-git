"""Pytest fixtures for prompt-git-manager tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Generator

import pytest
import yaml
from git import Repo


# ============================================================
# Git Repository Fixtures
# ============================================================


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Generator[tuple[Path, Repo], None, None]:
    """Create a temporary Git repository for testing.

    Yields:
        Tuple of (repo_path, Repo instance).
    """
    repo = Repo.init(tmp_path)
    # Configure git user for commits
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")

    yield tmp_path, repo


@pytest.fixture
def tmp_git_repo_with_history(
    tmp_path: Path,
) -> Generator[tuple[Path, Repo], None, None]:
    """Create a temporary Git repository with initial commit history.

    Yields:
        Tuple of (repo_path, Repo instance).
    """
    repo = Repo.init(tmp_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")

    # Create initial files
    readme = tmp_path / "README.md"
    readme.write_text("# Test Repository", encoding="utf-8")

    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(".venv/\n__pycache__/\n*.pyc\n", encoding="utf-8")

    repo.index.add(["README.md", ".gitignore"])
    repo.index.commit("Initial commit")

    yield tmp_path, repo


@pytest.fixture
def tmp_git_repo_with_branches(
    tmp_path: Path,
) -> Generator[tuple[Path, Repo], None, None]:
    """Create a temporary Git repository with main and feature branches.

    Yields:
        Tuple of (repo_path, Repo instance) - on the feature branch.
    """
    repo = Repo.init(tmp_path, initial_branch="main")
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")

    # Initial commit on main
    readme = tmp_path / "README.md"
    readme.write_text("# Main Branch", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit on main")

    # Create and switch to feature branch
    feature_branch = repo.create_head("feature/prompt-v2")
    feature_branch.checkout()

    yield tmp_path, repo


@pytest.fixture
def tmp_git_repo_dirty(tmp_path: Path) -> Generator[tuple[Path, Repo], None, None]:
    """Create a temporary Git repository with uncommitted changes.

    Yields:
        Tuple of (repo_path, Repo instance).
    """
    repo = Repo.init(tmp_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")

    # Create and commit initial file
    file1 = tmp_path / "committed.txt"
    file1.write_text("committed content", encoding="utf-8")
    repo.index.add(["committed.txt"])
    repo.index.commit("Initial commit")

    # Create uncommitted changes
    file2 = tmp_path / "uncommitted.txt"
    file2.write_text("uncommitted content", encoding="utf-8")

    # Modify committed file
    file1.write_text("modified content", encoding="utf-8")

    yield tmp_path, repo


@pytest.fixture
def tmp_bare_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary bare Git repository (simulates remote).

    Yields:
        Path to bare repository.
    """
    bare_path = tmp_path / "bare.git"
    Repo.init(bare_path, bare=True)

    yield bare_path


@pytest.fixture
def tmp_git_repo_with_remote(
    tmp_path: Path,
) -> Generator[tuple[Path, Repo], None, None]:
    """Create a temporary Git repository with a local remote.

    Yields:
        Tuple of (repo_path, Repo instance).
    """
    # Create bare remote
    bare_path = tmp_path / "remote.git"
    Repo.init(bare_path, bare=True)

    # Create working repo
    work_path = tmp_path / "work"
    work_path.mkdir()
    repo = Repo.init(work_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")

    # Add remote
    repo.create_remote("origin", bare_path)

    # Initial commit and push
    readme = work_path / "README.md"
    readme.write_text("# Test", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    repo.remote("origin").push("main")

    yield work_path, repo


# ============================================================
# Prompt File Fixtures
# ============================================================


@pytest.fixture
def sample_prompt_yaml(tmp_path: Path) -> Path:
    """Create a sample valid prompt YAML file.

    Returns:
        Path to the created YAML file.
    """
    prompt_data = {
        "name": "test-prompt",
        "version": "1.0.0",
        "system_prompt": "You are a helpful assistant.",
        "user_template": "Answer the following question: {{question}}",
        "variables": {"question": {"type": "string", "default": "What is AI?"}},
        "constraints": ["Be concise", "Use simple language"],
        "metadata": {"author": "test", "category": "qa"},
    }
    path = tmp_path / "test_prompt.yaml"
    path.write_text(yaml.dump(prompt_data, default_flow_style=False), encoding="utf-8")
    return path


@pytest.fixture
def invalid_prompt_yaml(tmp_path: Path) -> Path:
    """Create an invalid prompt YAML file (missing required fields).

    Returns:
        Path to the created YAML file.
    """
    prompt_data = {
        "name": "invalid-prompt",
        # Missing system_prompt and user_template
        "variables": {},
    }
    path = tmp_path / "invalid_prompt.yaml"
    path.write_text(yaml.dump(prompt_data, default_flow_style=False), encoding="utf-8")
    return path


@pytest.fixture
def sample_prompt_data() -> dict:
    """Return sample prompt data as dictionary.

    Returns:
        Dictionary with prompt template data.
    """
    return {
        "name": "test-prompt",
        "version": "1.0.0",
        "system_prompt": "You are a helpful assistant.",
        "user_template": "Answer the following question: {{question}}",
        "variables": {"question": {"type": "string", "default": "What is AI?"}},
        "constraints": ["Be concise", "Use simple language"],
        "metadata": {"author": "test", "category": "qa"},
    }


@pytest.fixture
def create_prompt_file(tmp_path: Path):
    """Factory fixture to create prompt files from data.

    Returns:
        Callable that creates a prompt file.
    """

    def _create(data: dict, name: str = "prompt.yaml") -> Path:
        path = tmp_path / name
        path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
        return path

    return _create


# ============================================================
# Initialized Repository Fixtures
# ============================================================


@pytest.fixture
def initialized_repo(tmp_git_repo: tuple, sample_prompt_yaml: Path):
    """Create a repo with .prompts/ directory initialized.

    Yields:
        Tuple of (repo_path, Repo instance, prompts_dir).
    """
    repo_path, repo = tmp_git_repo
    prompts_dir = repo_path / ".prompts"
    prompts_dir.mkdir(exist_ok=True)

    # Create config
    config = {"version": "0.1.0", "eval_threshold": 0.05}
    (prompts_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")

    # Copy sample prompt
    shutil.copy2(sample_prompt_yaml, prompts_dir / "test_prompt.yaml")

    # Initial commit
    repo.index.add([".prompts/config.json", ".prompts/test_prompt.yaml"])
    repo.index.commit("Initial commit")

    return repo_path, repo, prompts_dir


@pytest.fixture
def initialized_repo_with_history(tmp_git_repo_with_history: tuple):
    """Create a repo with .prompts/ and commit history.

    Yields:
        Tuple of (repo_path, Repo instance, prompts_dir).
    """
    repo_path, repo = tmp_git_repo_with_history
    prompts_dir = repo_path / ".prompts"
    prompts_dir.mkdir(exist_ok=True)

    # Create config
    config = {
        "version": "0.1.0",
        "eval_threshold": 0.05,
        "model_provider": "openai",
        "created_at": "2024-01-01T00:00:00",
    }
    (prompts_dir / "config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )

    # Create prompt v1
    prompt_v1 = {
        "name": "qa-prompt",
        "version": "1.0.0",
        "system_prompt": "You are a helpful assistant.",
        "user_template": "Answer: {{question}}",
        "variables": {"question": {"type": "string", "default": "What is Python?"}},
        "constraints": ["Be concise"],
        "metadata": {},
    }
    (prompts_dir / "qa_prompt.yaml").write_text(
        yaml.dump(prompt_v1, default_flow_style=False), encoding="utf-8"
    )

    # Commit v1
    repo.index.add([".prompts/config.json", ".prompts/qa_prompt.yaml"])
    repo.index.commit("Add QA prompt v1")

    return repo_path, repo, prompts_dir


@pytest.fixture
def initialized_repo_with_multiple_prompts(tmp_git_repo: tuple):
    """Create a repo with multiple prompt files.

    Yields:
        Tuple of (repo_path, Repo instance, prompts_dir).
    """
    repo_path, repo = tmp_git_repo
    prompts_dir = repo_path / ".prompts"
    prompts_dir.mkdir(exist_ok=True)

    # Create config
    config = {"version": "0.1.0", "eval_threshold": 0.05}
    (prompts_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")

    # Create multiple prompts
    prompts = [
        {
            "name": "qa-prompt",
            "version": "1.0.0",
            "system_prompt": "You are a QA assistant.",
            "user_template": "Question: {{question}}",
            "variables": {"question": {"default": "What?"}},
            "constraints": ["Be concise"],
            "metadata": {"category": "qa"},
        },
        {
            "name": "code-prompt",
            "version": "1.0.0",
            "system_prompt": "You are a code assistant.",
            "user_template": "Write {{language}} code for: {{task}}",
            "variables": {
                "language": {"default": "python"},
                "task": {"default": "hello world"},
            },
            "constraints": ["Use type hints", "Add docstrings"],
            "metadata": {"category": "code"},
        },
        {
            "name": "translate-prompt",
            "version": "1.0.0",
            "system_prompt": "You are a translator.",
            "user_template": "Translate to {{target_lang}}: {{text}}",
            "variables": {
                "target_lang": {"default": "en"},
                "text": {"default": "Hello"},
            },
            "constraints": ["Preserve meaning"],
            "metadata": {"category": "translation"},
        },
    ]

    files = [".prompts/config.json"]
    for i, prompt in enumerate(prompts):
        filename = f".prompts/prompt_{i + 1}.yaml"
        (repo_path / filename).write_text(
            yaml.dump(prompt, default_flow_style=False), encoding="utf-8"
        )
        files.append(filename)

    repo.index.add(files)
    repo.index.commit("Add multiple prompts")

    return repo_path, repo, prompts_dir


@pytest.fixture
def initialized_repo_for_diff(tmp_git_repo: tuple):
    """Create a repo ready for diff testing with old and new versions.

    Yields:
        Tuple of (repo_path, Repo instance, prompts_dir).
    """
    repo_path, repo = tmp_git_repo
    prompts_dir = repo_path / ".prompts"
    prompts_dir.mkdir(exist_ok=True)

    # Create config
    config = {"version": "0.1.0", "eval_threshold": 0.05}
    (prompts_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")

    # Create prompt v1
    prompt_v1 = {
        "name": "test-prompt",
        "version": "1.0.0",
        "system_prompt": "You are a helpful assistant.",
        "user_template": "Answer: {{question}}",
        "variables": {"question": {"default": "What?"}},
        "constraints": ["Be concise", "Be polite"],
        "metadata": {},
    }
    (prompts_dir / "test_prompt.yaml").write_text(
        yaml.dump(prompt_v1, default_flow_style=False), encoding="utf-8"
    )

    # Commit v1
    repo.index.add([".prompts/config.json", ".prompts/test_prompt.yaml"])
    repo.index.commit("Initial prompt version")

    # Update to v2 (uncommitted changes for diff)
    prompt_v2 = {
        "name": "test-prompt",
        "version": "2.0.0",
        "system_prompt": "You are a code expert.",  # Role shift
        "user_template": "Review: {{code}} for {{language}}",  # Variable change
        "variables": {
            "code": {"default": "print()"},
            "language": {"default": "python"},
        },
        "constraints": ["Be technical"],  # Constraint change
        "metadata": {},
    }
    (prompts_dir / "test_prompt.yaml").write_text(
        yaml.dump(prompt_v2, default_flow_style=False), encoding="utf-8"
    )

    return repo_path, repo, prompts_dir


@pytest.fixture
def initialized_repo_for_eval(tmp_git_repo: tuple, tmp_path: Path):
    """Create a repo and dataset ready for evaluation testing.

    Yields:
        Tuple of (repo_path, Repo instance, prompts_dir, dataset_path).
    """
    repo_path, repo = tmp_git_repo
    prompts_dir = repo_path / ".prompts"
    prompts_dir.mkdir(exist_ok=True)

    # Create config
    config = {"version": "0.1.0", "eval_threshold": 0.05}
    (prompts_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")

    # Create prompt
    prompt = {
        "name": "eval-prompt",
        "version": "1.0.0",
        "system_prompt": "You are a helpful assistant.",
        "user_template": "Answer: {{question}}",
        "variables": {"question": {"default": "What is Python?"}},
        "constraints": ["Be concise"],
        "metadata": {},
    }
    (prompts_dir / "eval_prompt.yaml").write_text(
        yaml.dump(prompt, default_flow_style=False), encoding="utf-8"
    )

    # Commit
    repo.index.add([".prompts/config.json", ".prompts/eval_prompt.yaml"])
    repo.index.commit("Initial commit")

    # Create dataset
    dataset_path = tmp_path / "test_dataset.jsonl"
    samples = [
        {
            "input": "What is Python?",
            "expected_output": "Python is a programming language",
        },
        {"input": "What is Git?", "expected_output": "Git is a version control system"},
        {"input": "What is AI?", "expected_output": "AI is artificial intelligence"},
    ]
    with open(dataset_path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    return repo_path, repo, prompts_dir, dataset_path


# ============================================================
# Dataset Fixtures
# ============================================================


@pytest.fixture
def sample_dataset(tmp_path: Path) -> Path:
    """Create a sample dataset JSONL file.

    Returns:
        Path to the created dataset file.
    """
    samples = [
        {
            "input": "What is Python?",
            "expected_output": "Python is a programming language",
        },
        {"input": "What is Git?", "expected_output": "Git is a version control system"},
    ]
    path = tmp_path / "dataset.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    return path


@pytest.fixture
def empty_dataset(tmp_path: Path) -> Path:
    """Create an empty dataset JSONL file.

    Returns:
        Path to the empty dataset file.
    """
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    return path


@pytest.fixture
def large_dataset(tmp_path: Path) -> Path:
    """Create a larger dataset JSONL file for performance testing.

    Returns:
        Path to the created dataset file.
    """
    samples = []
    for i in range(100):
        samples.append(
            {
                "input": f"Question {i}: What is topic {i}?",
                "expected_output": f"Topic {i} is a concept in domain {i % 10}",
                "metadata": {"index": i, "category": f"cat_{i % 5}"},
            }
        )

    path = tmp_path / "large_dataset.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    return path


# ============================================================
# Helper Fixtures
# ============================================================


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set mock environment variables for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-12345")
    monkeypatch.setenv("PROMPT_GIT_MODEL", "gpt-3.5-turbo")


@pytest.fixture
def capture_stdout(capsys):
    """Capture stdout for assertion.

    Returns:
        Callable that returns captured output.
    """

    def _capture():
        captured = capsys.readouterr()
        return captured.out

    return _capture


@pytest.fixture
def assert_exit_code():
    """Helper to assert exit codes.

    Returns:
        Callable that asserts exit code.
    """

    def _assert(result, expected_code):
        assert result.exit_code == expected_code, (
            f"Expected exit code {expected_code}, got {result.exit_code}. "
            f"Output: {result.output}"
        )

    return _assert
