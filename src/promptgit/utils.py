"""Utility functions for Git operations, Rich rendering, and path handling."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from git import GitCommandError, InvalidGitRepositoryError, Repo
from rich.console import Console
from rich.table import Table

# Error codes
ERR_SUCCESS = 0
ERR_ARGS = 1
ERR_GIT = 2
ERR_VALIDATION = 3

console = Console(stderr=True)


def get_repo(path: Optional[Path] = None) -> Repo:
    """Get Git repository instance.

    Args:
        path: Directory to search from. Defaults to cwd.

    Returns:
        GitPython Repo instance.

    Raises:
        typer.Exit: If not in a git repository.
    """
    try:
        return Repo(path or Path.cwd(), search_parent_directories=True)
    except InvalidGitRepositoryError:
        console.print(
            "[red]Error:[/red] Not a git repository (or any parent up to root)"
        )
        raise typer.Exit(code=ERR_GIT)


def get_prompts_dir(repo: Repo) -> Path:
    """Get the .prompts directory path within the repo.

    Args:
        repo: Git repository instance.

    Returns:
        Path to .prompts directory.
    """
    return Path(repo.working_dir) / ".prompts"


def ensure_prompts_dir(repo: Repo) -> Path:
    """Ensure .prompts directory exists and return its path.

    Args:
        repo: Git repository instance.

    Returns:
        Path to .prompts directory.
    """
    prompts_dir = get_prompts_dir(repo)
    prompts_dir.mkdir(exist_ok=True)
    return prompts_dir


def render_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
    """Render a Rich table to stderr.

    Args:
        title: Table title.
        columns: Column header names.
        rows: Row data as list of lists.
    """
    table = Table(title=title, show_lines=True)
    for col in columns:
        table.add_column(col, style="cyan")
    for row in rows:
        table.add_row(*row)
    console.print(table)


def render_diff_summary(changes: dict[str, list[str]]) -> None:
    """Render a diff summary with colored status indicators.

    Args:
        changes: Dict mapping status (added/modified/deleted) to file lists.
    """
    table = Table(title="Prompt Changes", show_lines=True)
    table.add_column("Status", style="bold")
    table.add_column("File", style="cyan")

    status_style = {
        "added": "[green]ADDED[/green]",
        "modified": "[yellow]MODIFIED[/yellow]",
        "deleted": "[red]DELETED[/red]",
    }

    for status, files in changes.items():
        for f in files:
            table.add_row(status_style.get(status, status), f)

    console.print(table)


def error_exit(message: str, code: int = ERR_ARGS) -> None:
    """Print error message and exit with error code.

    Args:
        message: Error description.
        code: Exit code.
    """
    console.print(f"[red]Error:[/red] {message}")
    raise typer.Exit(code=code)
