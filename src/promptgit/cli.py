"""Typer CLI entry point for prompt-git."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from git import GitCommandError
from rich.console import Console

from promptgit import __version__
from promptgit.schema import CommitRecord, PromptTemplate
from promptgit.utils import (
    ERR_ARGS,
    ERR_GIT,
    ERR_SUCCESS,
    ERR_VALIDATION,
    console,
    ensure_prompts_dir,
    error_exit,
    get_prompts_dir,
    get_repo,
    render_diff_summary,
    render_table,
)

app = typer.Typer(
    name="pg",
    help="Git-native prompt version control & CI guardrail tool.",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"prompt-git {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """prompt-git: Git-native prompt version control & CI guardrail tool."""


@app.command()
def init(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview without creating files."
    ),
) -> None:
    """Initialize .prompts/ directory and metadata in the current Git repo.

    Creates the directory structure and a default config file.
    """
    repo = get_repo()
    prompts_dir = get_prompts_dir(repo)

    if dry_run:
        console.print(f"[yellow]DRY RUN:[/yellow] Would create {prompts_dir}/")
        console.print(
            f"[yellow]DRY RUN:[/yellow] Would create {prompts_dir}/config.json"
        )
        raise typer.Exit(code=ERR_SUCCESS)

    try:
        prompts_dir.mkdir(exist_ok=True)
        config_path = prompts_dir / "config.json"
        if not config_path.exists():
            config = {
                "version": __version__,
                "created_at": datetime.now().isoformat(),
                "eval_threshold": 0.05,
                "model_provider": "openai",
            }
            config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

        # Ensure .prompts is tracked by git
        gitignore_path = prompts_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text(
                "# Prompt-git internal files\n*.tmp\n", encoding="utf-8"
            )

        console.print(f"[green]✓[/green] Initialized prompt-git in {prompts_dir}")
        render_table(
            "Initialized",
            ["Item", "Path"],
            [
                ["Directory", str(prompts_dir)],
                ["Config", str(config_path)],
            ],
        )
    except OSError as e:
        error_exit(f"Failed to initialize: {e}", ERR_GIT)


@app.command()
def add(
    file: Path = typer.Argument(..., help="Prompt file to add (YAML/JSON/MD)."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview without copying file."
    ),
) -> None:
    """Add a prompt file to version tracking.

    Validates the file against the PromptTemplate schema and copies it
    into the .prompts/ directory.
    """
    repo = get_repo()
    prompts_dir = ensure_prompts_dir(repo)

    # Resolve and validate source file
    source = file.resolve()
    if not source.exists():
        error_exit(f"File not found: {source}", ERR_ARGS)

    if source.suffix.lower() not in {".yaml", ".yml", ".json"}:
        error_exit(
            f"Unsupported file format: {source.suffix}. Use .yaml, .yml, or .json",
            ERR_ARGS,
        )

    # Validate prompt schema
    try:
        template = PromptTemplate.from_yaml(source)
    except (FileNotFoundError, ValueError) as e:
        error_exit(str(e), ERR_VALIDATION)

    dest = prompts_dir / source.name

    if dry_run:
        console.print(
            f"[yellow]DRY RUN:[/yellow] Would add {source.name} to {prompts_dir}"
        )
        console.print(f"[yellow]DRY RUN:[/yellow] Validation: PASS")
        console.print(f"  Name: {template.name}")
        console.print(f"  Version: {template.version}")
        console.print(f"  Variables: {list(template.variables.keys())}")
        raise typer.Exit(code=ERR_SUCCESS)

    try:
        import shutil

        shutil.copy2(source, dest)
        console.print(f"[green]✓[/green] Added {source.name} to prompt tracking")
        render_table(
            "Added Prompt",
            ["Field", "Value"],
            [
                ["Name", template.name],
                ["Version", template.version],
                ["Variables", ", ".join(template.variables.keys()) or "(none)"],
                ["Constraints", str(len(template.constraints))],
                ["Path", str(dest)],
            ],
        )
    except OSError as e:
        error_exit(f"Failed to add file: {e}", ERR_GIT)


@app.command()
def commit(
    message: str = typer.Option(..., "--message", "-m", help="Commit message."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview commit without executing."
    ),
) -> None:
    """Commit prompt changes with a structured record.

    Records hash, timestamp, changed files, and validation status.
    """
    repo = get_repo()
    prompts_dir = get_prompts_dir(repo)

    if not prompts_dir.exists():
        error_exit("No .prompts/ directory found. Run 'pg init' first.", ERR_ARGS)

    # Collect changed prompt files (exclude config.json and internal files)
    changed_files = []
    for item in prompts_dir.iterdir():
        if item.is_file() and item.suffix.lower() in {".yaml", ".yml"}:
            # Only track YAML/YML files as prompts, skip config and JSONL
            rel_path = str(item.relative_to(repo.working_dir))
            changed_files.append(rel_path)

    if not changed_files:
        console.print("[yellow]No prompt files to commit.[/yellow]")
        raise typer.Exit(code=ERR_SUCCESS)

    # Validate all prompt files
    validation_errors = []
    for f in changed_files:
        try:
            PromptTemplate.from_yaml(Path(repo.working_dir) / f)
        except (FileNotFoundError, ValueError) as e:
            validation_errors.append(f"{f}: {e}")

    validation_status = "pass" if not validation_errors else "fail"

    if dry_run:
        console.print(
            f"[yellow]DRY RUN:[/yellow] Would commit {len(changed_files)} file(s)"
        )
        render_table(
            "Dry Run Commit",
            ["File", "Validation"],
            [[f, "✓" if f not in validation_errors else "✗"] for f in changed_files],
        )
        if validation_errors:
            console.print("[red]Validation errors:[/red]")
            for err in validation_errors:
                console.print(f"  - {err}")
        raise typer.Exit(code=ERR_SUCCESS)

    # Stage and commit
    try:
        for f in changed_files:
            repo.index.add([f])

        commit_obj = repo.index.commit(message)

        record = CommitRecord(
            hash=commit_obj.hexsha[:12],
            timestamp=datetime.fromtimestamp(commit_obj.committed_date),
            changed_files=changed_files,
            validation_status=validation_status,
            message=message,
        )

        # Save commit record
        record_path = prompts_dir / "commits.jsonl"
        with open(record_path, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

        console.print(f"[green]✓[/green] Committed {len(changed_files)} prompt file(s)")
        render_table(
            "Commit Record",
            ["Field", "Value"],
            [
                ["Hash", record.hash],
                ["Timestamp", record.timestamp.isoformat()],
                ["Files", str(len(changed_files))],
                ["Validation", validation_status],
                ["Message", message],
            ],
        )

        if validation_errors:
            console.print("[yellow]⚠ Some files had validation warnings:[/yellow]")
            for err in validation_errors:
                console.print(f"  - {err}")

    except GitCommandError as e:
        error_exit(f"Git operation failed: {e}", ERR_GIT)


@app.command()
def diff(
    file: Optional[str] = typer.Argument(None, help="Specific prompt file to diff."),
    semantic: bool = typer.Option(
        False, "--semantic", "-s", help="Show semantic diff with risk analysis."
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="Output diff as JSON."
    ),
) -> None:
    """Show diff between current prompts and HEAD.

    With --semantic, shows variable/constraint/intent changes with risk level.
    With --json, outputs structured diff result.
    """
    from promptgit.diff_engine import diff_prompts, RiskLevel

    repo = get_repo()
    prompts_dir = get_prompts_dir(repo)

    if not prompts_dir.exists():
        error_exit("No .prompts/ directory found. Run 'pg init' first.", ERR_ARGS)

    try:
        # Get changed files from git
        changed_files = []

        if file:
            # Diff specific file
            file_path = Path(repo.working_dir) / file
            if not file_path.exists():
                error_exit(f"File not found: {file}", ERR_ARGS)
            changed_files.append(file)
        else:
            # Find all changed prompt files
            diff_output = repo.index.diff(None)
            for d in diff_output:
                if (
                    d.a_path
                    and d.a_path.startswith(".prompts/")
                    and d.a_path.endswith((".yaml", ".yml"))
                ):
                    changed_files.append(d.a_path)

            # Also check unstaged and untracked
            if not changed_files:
                for item in prompts_dir.iterdir():
                    if item.is_file() and item.suffix.lower() in {".yaml", ".yml"}:
                        rel = str(item.relative_to(repo.working_dir))
                        try:
                            repo.head.commit.tree[rel]
                            changed_files.append(rel)
                        except (KeyError, ValueError):
                            changed_files.append(rel)

        if not changed_files:
            console.print("[green]No prompt changes detected.[/green]")
            raise typer.Exit(code=ERR_SUCCESS)

        # Get HEAD versions for comparison
        results = []
        for f in changed_files:
            new_path = Path(repo.working_dir) / f

            # Try to get old version from HEAD
            try:
                old_blob = repo.head.commit.tree[f]
                old_content = old_blob.data_stream.read()

                # Write to temp file for comparison
                import tempfile

                with tempfile.NamedTemporaryFile(
                    mode="wb", suffix=".yaml", delete=False
                ) as tmp:
                    tmp.write(old_content)
                    old_path = Path(tmp.name)

                try:
                    result = diff_prompts(old_path, new_path)
                    results.append((f, result))
                finally:
                    old_path.unlink(missing_ok=True)

            except (KeyError, Exception):
                # New file, no previous version
                from promptgit.diff_engine import (
                    DiffResult,
                    SemanticChangeType,
                    RiskLevel,
                )

                results.append(
                    (
                        f,
                        DiffResult(
                            added_fields=["<new file>"],
                            semantic_change_type=SemanticChangeType.NONE,
                            risk_level=RiskLevel.LOW,
                            summary="New file added",
                        ),
                    )
                )

        # Output results
        if json_output:
            output = {f: r.to_dict() for f, r in results}
            typer.echo(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            from rich.table import Table

            for f, result in results:
                table = Table(title=f"Diff: {f}", show_lines=True)
                table.add_column("Field", style="cyan", min_width=20)
                table.add_column("Value", style="white")

                table.add_row("Risk Level", _risk_style(result.risk_level))
                table.add_row("Change Type", result.semantic_change_type.value)
                table.add_row("Summary", result.summary)

                if result.added_fields:
                    table.add_row("Added Fields", ", ".join(result.added_fields))
                if result.removed_fields:
                    table.add_row("Removed Fields", ", ".join(result.removed_fields))
                if result.modified_fields:
                    mods = [
                        f"{m.field}: {m.old_value} → {m.new_value}"
                        for m in result.modified_fields
                    ]
                    table.add_row("Modified", "\n".join(mods))

                console.print(table)

                if semantic and result.text_diff:
                    console.print("\n[bold]Text Diff:[/bold]")
                    for line in result.text_diff[:50]:  # Limit output
                        if line.startswith("+"):
                            console.print(f"[green]{line}[/green]")
                        elif line.startswith("-"):
                            console.print(f"[red]{line}[/red]")
                        else:
                            console.print(line)

    except GitCommandError as e:
        error_exit(f"Git diff failed: {e}", ERR_GIT)


def _risk_style(risk) -> str:
    """Apply color to risk level."""
    from promptgit.diff_engine import RiskLevel

    styles = {
        RiskLevel.LOW: "[green]LOW[/green]",
        RiskLevel.MEDIUM: "[yellow]MEDIUM[/yellow]",
        RiskLevel.HIGH: "[red]HIGH[/red]",
    }
    return styles.get(risk, risk.value)


@app.command()
def eval(
    dataset: Path = typer.Option(
        ..., "--dataset", "-d", help="Path to dataset JSONL file."
    ),
    old_file: Optional[str] = typer.Option(
        None, "--old", help="Old prompt file (default: HEAD version)."
    ),
    new_file: Optional[str] = typer.Option(
        None, "--new", help="New prompt file (default: current version)."
    ),
    threshold: float = typer.Option(
        0.05, "--threshold", "-t", help="Accuracy drop threshold (0-1)."
    ),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """Evaluate prompt versions against a dataset.

    Compares old and new prompt versions, computing accuracy, token cost,
    and consistency metrics. Fails if accuracy drops more than threshold.
    """
    from promptgit.evaluator import load_dataset, evaluate_prompts

    repo = get_repo()
    prompts_dir = get_prompts_dir(repo)

    if not prompts_dir.exists():
        error_exit("No .prompts/ directory found. Run 'pg init' first.", ERR_ARGS)

    # Resolve prompt files
    if not new_file:
        # Find first YAML in .prompts/
        yaml_files = list(prompts_dir.glob("*.yaml")) + list(prompts_dir.glob("*.yml"))
        if not yaml_files:
            error_exit("No prompt files found in .prompts/", ERR_ARGS)
        new_file = str(yaml_files[0])

    new_path = (
        Path(new_file) if Path(new_file).is_absolute() else prompts_dir / new_file
    )

    if not old_file:
        # Get from HEAD
        try:
            rel_path = str(new_path.relative_to(repo.working_dir))
            old_blob = repo.head.commit.tree[rel_path]
            old_content = old_blob.data_stream.read()

            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".yaml", delete=False
            ) as tmp:
                tmp.write(old_content)
                old_path = Path(tmp.name)
        except (KeyError, Exception):
            error_exit(f"No previous version found for {new_file}", ERR_ARGS)
    else:
        old_path = (
            Path(old_file) if Path(old_file).is_absolute() else prompts_dir / old_file
        )

    # Load dataset
    try:
        samples = load_dataset(dataset)
    except (FileNotFoundError, ValueError) as e:
        error_exit(str(e), ERR_ARGS)

    # Load templates
    try:
        old_template = PromptTemplate.from_yaml(old_path)
        new_template = PromptTemplate.from_yaml(new_path)
    except (FileNotFoundError, ValueError) as e:
        error_exit(str(e), ERR_VALIDATION)

    # Run evaluation
    result = evaluate_prompts(old_template, new_template, samples, threshold)

    # Cleanup temp file
    if not old_file:
        old_path.unlink(missing_ok=True)

    # Output
    if json_output:
        typer.echo(result.to_json())
    else:
        table = Table(title="Evaluation Results", show_lines=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Total Samples", str(result.total_samples))
        table.add_row("Accuracy (Old)", f"{result.accuracy_old:.1%}")
        table.add_row("Accuracy (New)", f"{result.accuracy_new:.1%}")

        delta_color = "green" if result.accuracy_delta >= 0 else "red"
        table.add_row(
            "Accuracy Delta",
            f"[{delta_color}]{result.accuracy_delta:+.1%}[/{delta_color}]",
        )

        table.add_row("Token Cost (Old)", str(result.token_cost_old))
        table.add_row("Token Cost (New)", str(result.token_cost_new))
        table.add_row("Token Cost Delta", f"{result.token_cost_delta:+.1%}")
        table.add_row("Consistency Score", f"{result.consistency_score:.1%}")

        status = "[green]PASSED[/green]" if result.passed else "[red]FAILED[/red]"
        table.add_row("Status", status)
        table.add_row("Threshold", f"{result.threshold:.1%}")

        console.print(table)

        # Show failed samples
        if not result.passed:
            console.print(
                f"\n[red]✗ Evaluation FAILED: accuracy dropped {abs(result.accuracy_delta):.1%} (threshold: {threshold:.1%})[/red]"
            )
            raise typer.Exit(code=ERR_GIT)
        else:
            console.print(f"\n[green]✓ Evaluation PASSED[/green]")


if __name__ == "__main__":
    app()
