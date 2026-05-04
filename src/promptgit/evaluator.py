"""Prompt evaluation engine.

Compares prompt versions against datasets to detect regressions.
Supports rule-based evaluation (no LLM dependency) with optional LLM enhancement.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional, Callable

from promptgit.schema import PromptTemplate


@dataclass
class EvalSample:
    """Single evaluation sample from dataset."""

    input: str
    expected_output: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> EvalSample:
        """Create from dictionary."""
        return cls(
            input=data.get("input", ""),
            expected_output=data.get("expected_output", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SampleResult:
    """Result for a single sample evaluation."""

    input: str
    expected: str
    old_output: str
    new_output: str
    old_match: bool
    new_match: bool
    similarity_delta: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "input": self.input,
            "expected": self.expected,
            "old_output": self.old_output,
            "new_output": self.new_output,
            "old_match": self.old_match,
            "new_match": self.new_match,
            "similarity_delta": self.similarity_delta,
        }


@dataclass
class EvalResult:
    """Complete evaluation result."""

    total_samples: int
    accuracy_old: float
    accuracy_new: float
    accuracy_delta: float
    token_cost_old: int
    token_cost_new: int
    token_cost_delta: float
    consistency_score: float
    passed: bool
    threshold: float
    details: list[SampleResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_samples": self.total_samples,
            "accuracy_old": self.accuracy_old,
            "accuracy_new": self.accuracy_new,
            "accuracy_delta": self.accuracy_delta,
            "token_cost_old": self.token_cost_old,
            "token_cost_new": self.token_cost_new,
            "token_cost_delta": self.token_cost_delta,
            "consistency_score": self.consistency_score,
            "passed": self.passed,
            "threshold": self.threshold,
            "details": [d.to_dict() for d in self.details],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# Type alias for custom render functions
RenderFunction = Callable[[str, dict[str, Any]], str]


def load_dataset(path: Path) -> list[EvalSample]:
    """Load dataset from JSONL file.

    Args:
        path: Path to .jsonl file.

    Returns:
        List of EvalSample instances.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file format is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    samples = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                samples.append(EvalSample.from_dict(data))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON at line {line_num}: {e}") from e

    if not samples:
        raise ValueError(f"Dataset is empty: {path}")

    return samples


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Simple heuristic: ~4 chars per token for English, ~2 for CJK.
    This is a rough estimate; use tiktoken for precise counting.

    Args:
        text: Input text.

    Returns:
        Estimated token count.
    """
    if not text:
        return 0

    # Count CJK characters
    cjk_count = len(re.findall(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]", text))
    ascii_count = len(text) - cjk_count

    # Rough estimate: 4 chars/token for ASCII, 1.5 chars/token for CJK
    return int(ascii_count / 4 + cjk_count / 1.5)


def rule_based_render(template: PromptTemplate, variables: dict[str, Any]) -> str:
    """Render prompt template using rule-based substitution.

    Args:
        template: Prompt template.
        variables: Variable values to substitute.

    Returns:
        Rendered prompt string.
    """
    result = template.user_template

    # Merge default variables with provided ones
    merged_vars = {}
    for var_name, var_def in template.variables.items():
        if isinstance(var_def, dict):
            default = var_def.get("default", "")
        else:
            default = str(var_def)
        merged_vars[var_name] = default

    merged_vars.update(variables)

    # Substitute {{var}} placeholders
    for var_name, var_value in merged_vars.items():
        result = result.replace(f"{{{{{var_name}}}}}", str(var_value))

    # Prepend system prompt
    full_prompt = f"{template.system_prompt}\n\n{result}"
    return full_prompt


def compute_similarity(text1: str, text2: str) -> float:
    """Compute similarity ratio between two texts.

    Args:
        text1: First text.
        text2: Second text.

    Returns:
        Similarity ratio between 0 and 1.
    """
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1, text2).ratio()


def extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text.

    Args:
        text: Input text.

    Returns:
        Set of lowercase keywords.
    """
    # Remove common stop words
    stop_words = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "can",
        "shall",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "and",
        "but",
        "or",
        "not",
        "no",
        "nor",
        "so",
        "yet",
        "both",
        "either",
        "neither",
        "each",
        "every",
        "all",
        "any",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "than",
        "too",
        "very",
        "just",
        "about",
        "的",
        "了",
        "在",
        "是",
        "我",
        "有",
        "和",
        "就",
        "不",
        "人",
        "都",
        "一",
        "一个",
        "上",
        "也",
        "很",
        "到",
        "说",
        "要",
        "去",
        "你",
        "会",
        "着",
        "没有",
        "看",
        "好",
        "自己",
        "这",
        "一种",
    }

    text_lower = text.lower()

    # English words (2+ chars) - extract before removing non-ASCII
    english_words = set(re.findall(r"[a-z]{2,}", text_lower))

    # Remove English words to get pure Chinese text
    text_no_english = re.sub(r"[a-zA-Z]+", " ", text)

    # Chinese: extract 1-4 character segments
    chinese_chars = set(re.findall(r"[\u4e00-\u9fff]{2,4}", text_no_english))

    all_keywords = english_words | chinese_chars
    return {w for w in all_keywords if w not in stop_words and len(w) > 1}


def keyword_based_evaluate(
    rendered_prompt: str,
    expected_output: str,
) -> tuple[str, bool]:
    """Evaluate using keyword matching (rule-based).

    Args:
        rendered_prompt: The rendered prompt text.
        expected_output: Expected output text.

    Returns:
        Tuple of (simulated_output, is_match).
    """
    expected_keywords = extract_keywords(expected_output)

    if not expected_keywords:
        return "", True

    # Simple heuristic: if prompt contains keywords from expected output,
    # assume the model would produce similar output
    prompt_lower = rendered_prompt.lower()
    matched_keywords = {kw for kw in expected_keywords if kw in prompt_lower}

    match_ratio = (
        len(matched_keywords) / len(expected_keywords) if expected_keywords else 0
    )

    # Also check if expected output keywords appear in the prompt context
    # This handles cases where the prompt directly mentions the expected answer
    prompt_keywords = extract_keywords(rendered_prompt)
    overlap = prompt_keywords & expected_keywords
    overlap_ratio = len(overlap) / len(expected_keywords) if expected_keywords else 0

    # Use the better of the two ratios
    best_ratio = max(match_ratio, overlap_ratio)

    # Simulate output based on match ratio
    if best_ratio >= 0.5:
        return expected_output, True
    elif best_ratio >= 0.2:
        # Partial match - return modified version
        words = expected_output.split()
        return " ".join(words[: len(words) // 2]), False
    else:
        return "[no relevant output]", False


def evaluate_prompts(
    old_template: PromptTemplate,
    new_template: PromptTemplate,
    dataset: list[EvalSample],
    threshold: float = 0.05,
    render_fn: Optional[RenderFunction] = None,
) -> EvalResult:
    """Evaluate two prompt versions against a dataset.

    Args:
        old_template: Original prompt template.
        new_template: New prompt template.
        dataset: List of evaluation samples.
        threshold: Accuracy drop threshold for failure.
        render_fn: Optional custom render function (for LLM integration).

    Returns:
        EvalResult with metrics.

    Raises:
        ValueError: If dataset is empty.
    """
    if not dataset:
        raise ValueError("Dataset is empty, cannot evaluate.")

    if render_fn is None:
        render_fn = lambda prompt, vars: rule_based_render(
            old_template if "old" in prompt else new_template, vars
        )

    details = []
    old_correct = 0
    new_correct = 0
    old_total_tokens = 0
    new_total_tokens = 0
    consistency_matches = 0

    for sample in dataset:
        # Extract variables from input (simple heuristic)
        variables = {"input": sample.input, "question": sample.input}

        # Render prompts
        old_rendered = rule_based_render(old_template, variables)
        new_rendered = rule_based_render(new_template, variables)

        # Estimate tokens
        old_tokens = estimate_tokens(old_rendered)
        new_tokens = estimate_tokens(new_rendered)
        old_total_tokens += old_tokens
        new_total_tokens += new_tokens

        # Evaluate
        old_output, old_match = keyword_based_evaluate(
            old_rendered, sample.expected_output
        )
        new_output, new_match = keyword_based_evaluate(
            new_rendered, sample.expected_output
        )

        if old_match:
            old_correct += 1
        if new_match:
            new_correct += 1

        # Consistency: both produce same result
        if old_match == new_match:
            consistency_matches += 1

        similarity_delta = compute_similarity(old_output, new_output)

        details.append(
            SampleResult(
                input=sample.input,
                expected=sample.expected_output,
                old_output=old_output,
                new_output=new_output,
                old_match=old_match,
                new_match=new_match,
                similarity_delta=similarity_delta,
            )
        )

    total = len(dataset)
    accuracy_old = old_correct / total if total > 0 else 0
    accuracy_new = new_correct / total if total > 0 else 0
    accuracy_delta = accuracy_new - accuracy_old
    token_cost_delta = (
        (new_total_tokens - old_total_tokens) / old_total_tokens
        if old_total_tokens > 0
        else 0
    )
    consistency_score = consistency_matches / total if total > 0 else 0

    # Check threshold: fail if accuracy drops more than threshold
    passed = accuracy_delta >= -threshold

    return EvalResult(
        total_samples=total,
        accuracy_old=accuracy_old,
        accuracy_new=accuracy_new,
        accuracy_delta=accuracy_delta,
        token_cost_old=old_total_tokens,
        token_cost_new=new_total_tokens,
        token_cost_delta=token_cost_delta,
        consistency_score=consistency_score,
        passed=passed,
        threshold=threshold,
        details=details,
    )
