"""Semantic diff engine for prompt templates.

Provides structured diff (field-level) and semantic analysis
(variable changes, constraint shifts, tone/role drift).
"""

from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from promptgit.schema import PromptTemplate


class SemanticChangeType(str, Enum):
    """Types of semantic changes detected."""

    NONE = "none"
    VARIABLE_CHANGE = "variable_change"
    CONSTRAINT_CHANGE = "constraint_change"
    TONE_SHIFT = "tone_shift"
    ROLE_SHIFT = "role_shift"
    INTENT_SHIFT = "intent_shift"
    MIXED = "mixed"


class RiskLevel(str, Enum):
    """Risk level of prompt changes."""

    LOW = "low"
    MEDIUM = "med"
    HIGH = "high"


@dataclass
class FieldDiff:
    """Diff for a single field."""

    field: str
    old_value: Any
    new_value: Any
    change_type: str  # added, removed, modified


@dataclass
class DiffResult:
    """Complete diff result between two prompt versions."""

    added_fields: list[str] = field(default_factory=list)
    removed_fields: list[str] = field(default_factory=list)
    modified_fields: list[FieldDiff] = field(default_factory=list)
    semantic_change_type: SemanticChangeType = SemanticChangeType.NONE
    risk_level: RiskLevel = RiskLevel.LOW
    summary: str = ""
    text_diff: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "added_fields": self.added_fields,
            "removed_fields": self.removed_fields,
            "modified_fields": [
                {
                    "field": f.field,
                    "old": f.old_value,
                    "new": f.new_value,
                    "change_type": f.change_type,
                }
                for f in self.modified_fields
            ],
            "semantic_change_type": self.semantic_change_type.value,
            "risk_level": self.risk_level.value,
            "summary": self.summary,
            "text_diff": self.text_diff,
        }
        return result

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def extract_variables(template: str) -> set[str]:
    """Extract {{variable}} placeholders from template string.

    Args:
        template: Template string with {{var}} placeholders.

    Returns:
        Set of variable names.
    """
    return set(re.findall(r"\{\{(\w+)\}\}", template))


def extract_constraints_keywords(constraints: list[str]) -> dict[str, set[str]]:
    """Extract keywords from constraints for comparison.

    Args:
        constraints: List of constraint strings.

    Returns:
        Dict mapping keyword category to set of keywords.
    """
    keywords = {
        "forbidden": set(),
        "required": set(),
        "limit": set(),
        "tone": set(),
    }

    forbidden_patterns = r"(never|don't|do not|禁止|不得|不可|严禁)"
    required_patterns = r"(must|always|ensure|必须|务必|确保)"
    limit_patterns = r"(max|min|limit|under|over|不超过|至少)"
    tone_patterns = r"(polite|formal|casual|friendly|professional|礼貌|正式|专业)"

    for c in constraints:
        c_lower = c.lower()
        keywords["forbidden"] |= set(re.findall(forbidden_patterns, c_lower))
        keywords["required"] |= set(re.findall(required_patterns, c_lower))
        keywords["limit"] |= set(re.findall(limit_patterns, c_lower))
        keywords["tone"] |= set(re.findall(tone_patterns, c_lower))

    return keywords


def detect_tone_shift(old_text: str, new_text: str) -> tuple[bool, str]:
    """Detect tone/role shift between two texts.

    Args:
        old_text: Original prompt text.
        new_text: New prompt text.

    Returns:
        Tuple of (has_shift, description).
    """
    tone_indicators = {
        "formal": ["you are", "please", "shall", "must", "您", "请", "应当"],
        "casual": ["hey", "just", "let's", "ok", "嗨", "就", "咱们"],
        "technical": [
            "implement",
            "function",
            "parameter",
            "return",
            "实现",
            "函数",
            "参数",
            "返回",
        ],
        "friendly": ["help", "assist", "glad", "happy", "帮助", "协助", "很高兴"],
    }

    old_lower = old_text.lower()
    new_lower = new_text.lower()

    old_tones = {
        t
        for t, keywords in tone_indicators.items()
        if any(k in old_lower for k in keywords)
    }
    new_tones = {
        t
        for t, keywords in tone_indicators.items()
        if any(k in new_lower for k in keywords)
    }

    if old_tones != new_tones:
        added = new_tones - old_tones
        removed = old_tones - new_tones
        parts = []
        if added:
            parts.append(f"added tone: {', '.join(added)}")
        if removed:
            parts.append(f"removed tone: {', '.join(removed)}")
        return True, "; ".join(parts)

    return False, ""


def detect_role_shift(old_system: str, new_system: str) -> tuple[bool, str]:
    """Detect role/persona shift between system prompts.

    Args:
        old_system: Original system prompt.
        new_system: New system prompt.

    Returns:
        Tuple of (has_shift, description).
    """
    role_patterns = [
        (r"you are (?:a |an )?([\w\s]+?)(?:\.|,|$|\n)", "en"),
        (r"你是(?:一位|一名)?(.+?)(?:。|，|\.|,|$)", "zh"),
    ]

    old_roles = set()
    new_roles = set()

    for pattern, lang in role_patterns:
        old_matches = re.findall(pattern, old_system.lower().strip())
        new_matches = re.findall(pattern, new_system.lower().strip())
        old_roles |= {r.strip() for r in old_matches if r.strip()}
        new_roles |= {r.strip() for r in new_matches if r.strip()}

    if old_roles != new_roles:
        added = new_roles - old_roles
        removed = old_roles - new_roles
        parts = []
        if added:
            parts.append(f"new role: {', '.join(added)}")
        if removed:
            parts.append(f"removed role: {', '.join(removed)}")
        return True, "; ".join(parts)

    return False, ""


def compute_text_diff(old_text: str, new_text: str, lineterm: str = "") -> list[str]:
    """Compute unified text diff.

    Args:
        old_text: Original text.
        new_text: New text.
        lineterm: Line terminator for difflib.

    Returns:
        List of diff lines.
    """
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    return list(difflib.unified_diff(old_lines, new_lines, lineterm=lineterm))


def compute_structured_diff(
    old_data: dict, new_data: dict, prefix: str = ""
) -> tuple[list[str], list[str], list[FieldDiff]]:
    """Compute field-level diff between two dictionaries.

    Args:
        old_data: Original data dictionary.
        new_data: New data dictionary.
        prefix: Field path prefix for nested structures.

    Returns:
        Tuple of (added_fields, removed_fields, modified_fields).
    """
    added = []
    removed = []
    modified = []

    all_keys = set(old_data.keys()) | set(new_data.keys())

    for key in sorted(all_keys):
        field_path = f"{prefix}.{key}" if prefix else key

        if key not in old_data:
            added.append(field_path)
        elif key not in new_data:
            removed.append(field_path)
        else:
            old_val = old_data[key]
            new_val = new_data[key]

            if isinstance(old_val, dict) and isinstance(new_val, dict):
                sub_added, sub_removed, sub_modified = compute_structured_diff(
                    old_val, new_val, field_path
                )
                added.extend(sub_added)
                removed.extend(sub_removed)
                modified.extend(sub_modified)
            elif old_val != new_val:
                modified.append(
                    FieldDiff(
                        field=field_path,
                        old_value=old_val,
                        new_value=new_val,
                        change_type="modified",
                    )
                )

    return added, removed, modified


def analyze_semantic_changes(
    old_template: PromptTemplate,
    new_template: PromptTemplate,
    added_fields: list[str],
    removed_fields: list[str],
    modified_fields: list[FieldDiff],
) -> tuple[SemanticChangeType, RiskLevel, str]:
    """Analyze semantic meaning of changes.

    Args:
        old_template: Original prompt template.
        new_template: New prompt template.
        added_fields: List of added field paths.
        removed_fields: List of removed field paths.
        modified_fields: List of field diffs.

    Returns:
        Tuple of (change_type, risk_level, summary).
    """
    change_types = set()
    risk_factors = []
    summary_parts = []

    # Check variable changes
    old_vars = extract_variables(old_template.user_template)
    new_vars = extract_variables(new_template.user_template)
    added_vars = new_vars - old_vars
    removed_vars = old_vars - new_vars

    if added_vars or removed_vars:
        change_types.add(SemanticChangeType.VARIABLE_CHANGE)
        if added_vars:
            summary_parts.append(f"Added variables: {', '.join(added_vars)}")
        if removed_vars:
            summary_parts.append(f"Removed variables: {', '.join(removed_vars)}")
            risk_factors.append(RiskLevel.HIGH)  # Removing vars may break callers

    # Also check variables dict
    old_var_defs = set(old_template.variables.keys())
    new_var_defs = set(new_template.variables.keys())
    if old_var_defs != new_var_defs:
        change_types.add(SemanticChangeType.VARIABLE_CHANGE)
        added_defs = new_var_defs - old_var_defs
        removed_defs = old_var_defs - new_var_defs
        if added_defs:
            summary_parts.append(f"Added variable definitions: {', '.join(added_defs)}")
        if removed_defs:
            summary_parts.append(
                f"Removed variable definitions: {', '.join(removed_defs)}"
            )

    # Check constraint changes
    old_constraints = set(old_template.constraints)
    new_constraints = set(new_template.constraints)
    added_constraints = new_constraints - old_constraints
    removed_constraints = old_constraints - new_constraints

    if added_constraints or removed_constraints:
        change_types.add(SemanticChangeType.CONSTRAINT_CHANGE)
        if added_constraints:
            summary_parts.append(f"Added {len(added_constraints)} constraint(s)")
        if removed_constraints:
            summary_parts.append(f"Removed {len(removed_constraints)} constraint(s)")
            risk_factors.append(RiskLevel.MEDIUM)

    # Check tone shift
    has_tone_shift, tone_desc = detect_tone_shift(
        old_template.system_prompt + " " + old_template.user_template,
        new_template.system_prompt + " " + new_template.user_template,
    )
    if has_tone_shift:
        change_types.add(SemanticChangeType.TONE_SHIFT)
        summary_parts.append(f"Tone shift: {tone_desc}")
        risk_factors.append(RiskLevel.MEDIUM)

    # Check role shift
    has_role_shift, role_desc = detect_role_shift(
        old_template.system_prompt,
        new_template.system_prompt,
    )
    if has_role_shift:
        change_types.add(SemanticChangeType.ROLE_SHIFT)
        summary_parts.append(f"Role shift: {role_desc}")
        risk_factors.append(RiskLevel.HIGH)

    # Determine combined change type
    if len(change_types) == 0:
        change_type = SemanticChangeType.NONE
    elif len(change_types) == 1:
        change_type = change_types.pop()
    else:
        change_type = SemanticChangeType.MIXED

    # Determine risk level
    if RiskLevel.HIGH in risk_factors:
        risk_level = RiskLevel.HIGH
    elif RiskLevel.MEDIUM in risk_factors:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW

    summary = (
        "; ".join(summary_parts) if summary_parts else "No semantic changes detected"
    )

    return change_type, risk_level, summary


def diff_prompts(
    old_path: Path,
    new_path: Path,
    include_text_diff: bool = True,
) -> DiffResult:
    """Compute complete diff between two prompt files.

    Args:
        old_path: Path to original prompt file.
        new_path: Path to new prompt file.
        include_text_diff: Whether to include raw text diff.

    Returns:
        DiffResult with all changes.

    Raises:
        FileNotFoundError: If either file does not exist.
        ValueError: If files fail schema validation.
    """
    old_template = PromptTemplate.from_yaml(old_path)
    new_template = PromptTemplate.from_yaml(new_path)

    # Load raw data for structured diff
    import yaml

    with open(old_path, "r", encoding="utf-8") as f:
        old_data = yaml.safe_load(f)
    with open(new_path, "r", encoding="utf-8") as f:
        new_data = yaml.safe_load(f)

    # Structured diff
    added_fields, removed_fields, modified_fields = compute_structured_diff(
        old_data, new_data
    )

    # Text diff
    text_diff = []
    if include_text_diff:
        old_text = old_path.read_text(encoding="utf-8")
        new_text = new_path.read_text(encoding="utf-8")
        text_diff = compute_text_diff(old_text, new_text)

    # Semantic analysis
    change_type, risk_level, summary = analyze_semantic_changes(
        old_template,
        new_template,
        added_fields,
        removed_fields,
        modified_fields,
    )

    return DiffResult(
        added_fields=added_fields,
        removed_fields=removed_fields,
        modified_fields=modified_fields,
        semantic_change_type=change_type,
        risk_level=risk_level,
        summary=summary,
        text_diff=text_diff,
    )
