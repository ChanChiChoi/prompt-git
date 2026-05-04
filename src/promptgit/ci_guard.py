"""
CI Guard Logic for prompt-git-manager

This module implements the CI pipeline logic for detecting prompt regressions.
It can be used standalone or integrated with GitHub Actions.

Exit Codes:
    0: All checks passed
    1: Configuration error
    2: Evaluation failed (accuracy dropped below threshold)
    3: High-risk changes detected without approval
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ============================================================
# PSEUDOCODE: CI Guard Logic
# ============================================================

"""
ALGORITHM: PromptCIGuard

INPUT:
    - repo_path: Path to git repository
    - dataset_path: Path to evaluation dataset (.jsonl)
    - threshold: Maximum allowed accuracy drop (default: 0.05)
    - block_high_risk: Whether to block high-risk changes (default: true)
    - require_eval: Whether evaluation is required (default: true)

OUTPUT:
    - exit_code: 0 (pass), 2 (eval fail), 3 (risk fail)
    - report: Markdown report for PR comment

PROCEDURE:

1. INITIALIZATION
   IF NOT exists(.prompts/):
       RETURN error("No .prompts/ directory found")
   
   changed_files = get_changed_prompt_files()
   
   IF changed_files is empty:
       LOG("No prompt changes detected")
       RETURN success()

2. DIFF ANALYSIS
   FOR EACH file IN changed_files:
       old_version = get_from_HEAD(file)
       new_version = get_from_working_tree(file)
       
       diff_result = compute_structured_diff(old_version, new_version)
       semantic_result = analyze_semantic_changes(diff_result)
       
       diffs.append({
           file: file,
           diff: diff_result,
           semantic: semantic_result
       })

3. RISK ASSESSMENT
   max_risk = max(d.semantic.risk_level FOR d IN diffs)
   
   IF block_high_risk AND max_risk == HIGH:
       IF NOT has_approval_label("risk-approved"):
           generate_report(diffs, status="BLOCKED")
           RETURN exit(3)

4. EVALUATION (if dataset provided)
   IF require_eval AND exists(dataset_path):
       dataset = load_dataset(dataset_path)
       
       FOR EACH file IN changed_files:
           old_template = load_template(get_from_HEAD(file))
           new_template = load_template(get_from_working_tree(file))
           
           eval_result = evaluate_prompts(
               old=old_template,
               new=new_template,
               dataset=dataset,
               threshold=threshold
           )
           
           eval_results.append(eval_result)
       
       // Check if any evaluation failed
       failed_evals = [e FOR e IN eval_results IF NOT e.passed]
       
       IF failed_evals:
           generate_report(diffs, eval_results, status="FAILED")
           RETURN exit(2)

5. GENERATE REPORT
   report = generate_markdown_report(diffs, eval_results)
   write_to_file("prompt_diff_report.md", report)
   
   // For GitHub Actions, set output
   set_github_output("report_path", "prompt_diff_report.md")
   set_github_output("risk_level", max_risk)
   set_github_output("eval_passed", len(failed_evals) == 0)
   
   RETURN success()

END PROCEDURE
"""


# ============================================================
# IMPLEMENTATION
# ============================================================


@dataclass
class CIConfig:
    """CI configuration."""

    dataset_path: Path
    threshold: float = 0.05
    block_high_risk: bool = True
    require_eval: bool = True
    report_path: Path = Path("prompt_diff_report.md")


@dataclass
class CIResult:
    """CI execution result."""

    exit_code: int
    risk_level: str
    eval_passed: bool
    report_path: Optional[Path] = None
    message: str = ""


def run_ci_guard(config: CIConfig) -> CIResult:
    """Execute CI guard logic.

    Args:
        config: CI configuration.

    Returns:
        CIResult with execution status.
    """
    from git import Repo, InvalidGitRepositoryError
    from promptgit.diff_engine import diff_prompts, RiskLevel
    from promptgit.evaluator import load_dataset, evaluate_prompts
    from promptgit.schema import PromptTemplate

    # Step 1: Initialization
    try:
        repo = Repo(".", search_parent_directories=True)
    except InvalidGitRepositoryError:
        return CIResult(
            exit_code=1,
            risk_level="unknown",
            eval_passed=False,
            message="Not a git repository",
        )

    prompts_dir = Path(repo.working_dir) / ".prompts"
    if not prompts_dir.exists():
        return CIResult(
            exit_code=1,
            risk_level="unknown",
            eval_passed=False,
            message="No .prompts/ directory found",
        )

    # Step 2: Find changed files
    changed_files = []
    try:
        # Compare with main/master branch
        base_branch = "main"
        try:
            repo.heads.main
        except AttributeError:
            base_branch = "master"

        diff_index = repo.index.diff(f"origin/{base_branch}")

        for diff_item in diff_index:
            if (
                diff_item.a_path
                and diff_item.a_path.startswith(".prompts/")
                and diff_item.a_path.endswith((".yaml", ".yml"))
            ):
                changed_files.append(diff_item.a_path)
    except Exception:
        # Fallback: check all prompts
        for item in prompts_dir.iterdir():
            if item.suffix in (".yaml", ".yml"):
                changed_files.append(str(item.relative_to(repo.working_dir)))

    if not changed_files:
        return CIResult(
            exit_code=0,
            risk_level="none",
            eval_passed=True,
            message="No prompt changes detected",
        )

    # Step 3: Diff Analysis
    diffs = []
    max_risk = RiskLevel.LOW

    for file_path in changed_files:
        new_path = Path(repo.working_dir) / file_path

        try:
            # Get old version from base branch
            old_content = (
                repo.commit(f"origin/{base_branch}").tree[file_path].data_stream.read()
            )

            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".yaml", delete=False
            ) as tmp:
                tmp.write(old_content)
                old_path = Path(tmp.name)

            try:
                diff_result = diff_prompts(old_path, new_path)
                diffs.append({"file": file_path, "diff": diff_result})

                # Track max risk
                if diff_result.risk_level == RiskLevel.HIGH:
                    max_risk = RiskLevel.HIGH
                elif (
                    diff_result.risk_level == RiskLevel.MEDIUM
                    and max_risk != RiskLevel.HIGH
                ):
                    max_risk = RiskLevel.MEDIUM
            finally:
                old_path.unlink(missing_ok=True)

        except KeyError:
            # New file
            from promptgit.diff_engine import DiffResult, SemanticChangeType

            diffs.append(
                {
                    "file": file_path,
                    "diff": DiffResult(
                        added_fields=["<new file>"],
                        semantic_change_type=SemanticChangeType.NONE,
                        risk_level=RiskLevel.LOW,
                        summary="New file added",
                    ),
                }
            )

    # Step 4: Risk Assessment
    if config.block_high_risk and max_risk == RiskLevel.HIGH:
        # Check for approval label in GitHub
        # In real implementation, check PR labels via GitHub API
        has_approval = False  # Placeholder

        if not has_approval:
            report = generate_ci_report(diffs, None, "BLOCKED")
            config.report_path.write_text(report)

            return CIResult(
                exit_code=3,
                risk_level="high",
                eval_passed=False,
                report_path=config.report_path,
                message="High-risk changes blocked. Add 'risk-approved' label to proceed.",
            )

    # Step 5: Evaluation
    eval_passed = True

    if config.require_eval and config.dataset_path.exists():
        try:
            dataset = load_dataset(config.dataset_path)

            for diff_info in diffs:
                file_path = diff_info["file"]
                new_path = Path(repo.working_dir) / file_path

                # Get old template
                try:
                    old_content = (
                        repo.commit(f"origin/{base_branch}")
                        .tree[file_path]
                        .data_stream.read()
                    )
                    import tempfile

                    with tempfile.NamedTemporaryFile(
                        mode="wb", suffix=".yaml", delete=False
                    ) as tmp:
                        tmp.write(old_content)
                        old_path = Path(tmp.name)

                    old_template = PromptTemplate.from_yaml(old_path)
                    new_template = PromptTemplate.from_yaml(new_path)

                    eval_result = evaluate_prompts(
                        old_template, new_template, dataset, config.threshold
                    )

                    diff_info["eval"] = eval_result

                    if not eval_result.passed:
                        eval_passed = False

                    old_path.unlink(missing_ok=True)

                except Exception as e:
                    diff_info["eval_error"] = str(e)

        except Exception as e:
            return CIResult(
                exit_code=1,
                risk_level=max_risk.value,
                eval_passed=False,
                message=f"Evaluation error: {e}",
            )

    # Step 6: Generate Report
    status = "PASSED" if eval_passed else "FAILED"
    report = generate_ci_report(diffs, None, status)
    config.report_path.write_text(report)

    exit_code = 0 if eval_passed else 2

    return CIResult(
        exit_code=exit_code,
        risk_level=max_risk.value,
        eval_passed=eval_passed,
        report_path=config.report_path,
        message=f"CI guard {'passed' if eval_passed else 'failed'}",
    )


def generate_ci_report(
    diffs: list[dict], eval_results: Optional[list], status: str
) -> str:
    """Generate CI report in Markdown format.

    Args:
        diffs: List of diff results.
        eval_results: Optional evaluation results.
        status: Overall status (PASSED/FAILED/BLOCKED).

    Returns:
        Markdown report string.
    """
    from datetime import datetime

    lines = [
        "# Prompt CI Guard Report",
        "",
        f"**Status:** {status}",
        f"**Generated:** {datetime.now().isoformat()}",
        "",
        "## Changes",
        "",
        "| File | Risk | Change Type | Summary |",
        "|------|------|-------------|---------|",
    ]

    for diff_info in diffs:
        file_path = diff_info["file"]
        diff = diff_info["diff"]
        lines.append(
            f"| `{file_path}` | {diff.risk_level.value} | "
            f"{diff.semantic_change_type.value} | {diff.summary[:50]}... |"
        )

    if eval_results:
        lines.extend(
            [
                "",
                "## Evaluation Results",
                "",
                "| File | Accuracy | Delta | Status |",
                "|------|----------|-------|--------|",
            ]
        )

        for diff_info in diffs:
            if "eval" in diff_info:
                eval_r = diff_info["eval"]
                status_icon = "✅" if eval_r.passed else "❌"
                lines.append(
                    f"| `{diff_info['file']}` | {eval_r.accuracy_new:.1%} | "
                    f"{eval_r.accuracy_delta:+.1%} | {status_icon} |"
                )

    lines.extend(
        [
            "",
            "---",
            "*Generated by prompt-git-manager CI Guard*",
        ]
    )

    return "\n".join(lines)


# ============================================================
# CLI ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prompt CI Guard")
    parser.add_argument("--dataset", type=Path, default=Path("fixtures/dataset.jsonl"))
    parser.add_argument("--threshold", type=float, default=0.05)
    parser.add_argument("--block-high-risk", action="store_true", default=True)
    parser.add_argument("--no-eval", action="store_true")
    parser.add_argument("--report", type=Path, default=Path("prompt_diff_report.md"))

    args = parser.parse_args()

    config = CIConfig(
        dataset_path=args.dataset,
        threshold=args.threshold,
        block_high_risk=args.block_high_risk,
        require_eval=not args.no_eval,
        report_path=args.report,
    )

    result = run_ci_guard(config)

    print(f"Exit Code: {result.exit_code}")
    print(f"Risk Level: {result.risk_level}")
    print(f"Eval Passed: {result.eval_passed}")
    print(f"Message: {result.message}")

    if result.report_path:
        print(f"Report: {result.report_path}")

    sys.exit(result.exit_code)
