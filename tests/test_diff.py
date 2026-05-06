"""Tests for prompt-git-manager diff engine."""

from __future__ import annotations

import pytest
import yaml
from pathlib import Path

from promptgit.diff_engine import (
    DiffResult,
    SemanticChangeType,
    RiskLevel,
    extract_variables,
    detect_tone_shift,
    detect_role_shift,
    compute_structured_diff,
    diff_prompts,
)
from promptgit.schema import PromptTemplate


@pytest.fixture
def base_prompt_data():
    """Base prompt data for testing."""
    return {
        "name": "test-prompt",
        "version": "1.0.0",
        "system_prompt": "You are a helpful assistant.",
        "user_template": "Answer: {{question}}",
        "variables": {"question": {"type": "string", "default": "What is AI?"}},
        "constraints": ["Be concise", "Be polite"],
        "metadata": {"author": "test"},
    }


@pytest.fixture
def create_prompt_file(tmp_path: Path):
    """Factory fixture to create prompt files."""

    def _create(data: dict, name: str = "prompt.yaml") -> Path:
        path = tmp_path / name
        path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
        return path

    return _create


class TestExtractVariables:
    """Tests for variable extraction."""

    def test_single_variable(self):
        """Extract single variable."""
        assert extract_variables("Hello {{name}}") == {"name"}

    def test_multiple_variables(self):
        """Extract multiple variables."""
        result = extract_variables("{{greeting}} {{name}}, your age is {{age}}")
        assert result == {"greeting", "name", "age"}

    def test_no_variables(self):
        """Handle text without variables."""
        assert extract_variables("Hello world") == set()

    def test_duplicate_variables(self):
        """Handle duplicate variables."""
        assert extract_variables("{{x}} and {{x}}") == {"x"}

    def test_chinese_content(self):
        """Handle Chinese content with variables."""
        assert extract_variables("你好 {{name}}，请回答 {{question}}") == {
            "name",
            "question",
        }


class TestToneShiftDetection:
    """Tests for tone shift detection."""

    def test_no_shift(self):
        """No shift when tones are same."""
        has_shift, _ = detect_tone_shift(
            "You are a helpful assistant", "You are a helpful assistant"
        )
        assert not has_shift

    def test_formal_to_casual(self):
        """Detect shift from formal to casual."""
        has_shift, desc = detect_tone_shift(
            "Please ensure you must follow the guidelines", "Hey, just do it ok"
        )
        assert has_shift
        assert "casual" in desc.lower() or "formal" in desc.lower()

    def test_english_to_chinese(self):
        """Detect tone in Chinese text."""
        has_shift, desc = detect_tone_shift("您必须遵守规定", "咱们就按这个来吧")
        assert has_shift

    def test_same_tone_different_content(self):
        """No shift with same tone indicators."""
        has_shift, _ = detect_tone_shift(
            "Please help the user with their request",
            "Please assist the customer with their query",
        )
        assert not has_shift

    def test_empty_texts(self):
        """Handle empty texts."""
        has_shift, _ = detect_tone_shift("", "")
        assert not has_shift


class TestRoleShiftDetection:
    """Tests for role shift detection."""

    def test_no_shift(self):
        """No shift when roles are same."""
        has_shift, _ = detect_role_shift(
            "You are a helpful assistant", "You are a helpful assistant"
        )
        assert not has_shift

    def test_role_change_english(self):
        """Detect English role change."""
        has_shift, desc = detect_role_shift(
            "You are a customer service agent", "You are a code reviewer"
        )
        assert has_shift
        assert "code reviewer" in desc.lower() or "customer service" in desc.lower()

    def test_role_change_chinese(self):
        """Detect Chinese role change."""
        has_shift, desc = detect_role_shift("你是一位客服代表", "你是一位代码审查专家")
        assert has_shift

    def test_no_explicit_role(self):
        """Handle text without explicit role."""
        has_shift, _ = detect_role_shift("Help the user", "Assist the customer")
        assert not has_shift

    def test_empty_system_prompts(self):
        """Handle empty system prompts."""
        has_shift, _ = detect_role_shift("", "")
        assert not has_shift


class TestStructuredDiff:
    """Tests for structured diff computation."""

    def test_identical_dicts(self):
        """No diff for identical dicts."""
        data = {"name": "test", "value": 42}
        added, removed, modified = compute_structured_diff(data, data)
        assert added == []
        assert removed == []
        assert modified == []

    def test_added_field(self):
        """Detect added field."""
        old = {"name": "test"}
        new = {"name": "test", "value": 42}
        added, removed, modified = compute_structured_diff(old, new)
        assert "value" in added
        assert removed == []
        assert modified == []

    def test_removed_field(self):
        """Detect removed field."""
        old = {"name": "test", "value": 42}
        new = {"name": "test"}
        added, removed, modified = compute_structured_diff(old, new)
        assert added == []
        assert "value" in removed
        assert modified == []

    def test_modified_field(self):
        """Detect modified field."""
        old = {"name": "test", "version": "1.0"}
        new = {"name": "test", "version": "2.0"}
        added, removed, modified = compute_structured_diff(old, new)
        assert added == []
        assert removed == []
        assert len(modified) == 1
        assert modified[0].field == "version"
        assert modified[0].old_value == "1.0"
        assert modified[0].new_value == "2.0"

    def test_nested_diff(self):
        """Detect nested field changes."""
        old = {"config": {"debug": False, "level": 1}}
        new = {"config": {"debug": True, "level": 1}}
        added, removed, modified = compute_structured_diff(old, new)
        assert any(m.field == "config.debug" for m in modified)


class TestDiffPrompts:
    """Integration tests for prompt diffing."""

    def test_identical_prompts(self, base_prompt_data, create_prompt_file):
        """No diff for identical prompts."""
        path = create_prompt_file(base_prompt_data)
        result = diff_prompts(path, path)
        assert result.semantic_change_type == SemanticChangeType.NONE
        assert result.risk_level == RiskLevel.LOW

    def test_variable_change(self, base_prompt_data, create_prompt_file):
        """Detect variable addition."""
        old_data = base_prompt_data.copy()
        new_data = base_prompt_data.copy()
        new_data["user_template"] = "Answer: {{question}} about {{topic}}"

        old_path = create_prompt_file(old_data, "old.yaml")
        new_path = create_prompt_file(new_data, "new.yaml")

        result = diff_prompts(old_path, new_path)
        assert (
            SemanticChangeType.VARIABLE_CHANGE in result.semantic_change_type
            or result.semantic_change_type == SemanticChangeType.VARIABLE_CHANGE
        )

    def test_constraint_removal_risk(self, base_prompt_data, create_prompt_file):
        """Constraint removal raises risk level."""
        old_data = base_prompt_data.copy()
        new_data = base_prompt_data.copy()
        new_data["constraints"] = ["Be concise"]  # Removed "Be polite"

        old_path = create_prompt_file(old_data, "old.yaml")
        new_path = create_prompt_file(new_data, "new.yaml")

        result = diff_prompts(old_path, new_path)
        assert result.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]

    def test_role_shift_high_risk(self, base_prompt_data, create_prompt_file):
        """Role change results in high risk."""
        old_data = base_prompt_data.copy()
        new_data = base_prompt_data.copy()
        new_data["system_prompt"] = "You are a code reviewer."

        old_path = create_prompt_file(old_data, "old.yaml")
        new_path = create_prompt_file(new_data, "new.yaml")

        result = diff_prompts(old_path, new_path)
        assert result.risk_level == RiskLevel.HIGH

    def test_json_output(self, base_prompt_data, create_prompt_file):
        """JSON output is valid."""
        import json

        old_data = base_prompt_data.copy()
        new_data = base_prompt_data.copy()
        new_data["version"] = "2.0.0"

        old_path = create_prompt_file(old_data, "old.yaml")
        new_path = create_prompt_file(new_data, "new.yaml")

        result = diff_prompts(old_path, new_path)
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert "semantic_change_type" in parsed
        assert "risk_level" in parsed


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_constraints(self, create_prompt_file):
        """Handle empty constraints lists."""
        old_data = {
            "name": "test",
            "version": "1.0.0",
            "system_prompt": "You are helpful.",
            "user_template": "Help me",
            "variables": {},
            "constraints": [],
            "metadata": {},
        }
        new_data = old_data.copy()
        new_data["constraints"] = ["Be concise"]

        old_path = create_prompt_file(old_data, "old.yaml")
        new_path = create_prompt_file(new_data, "new.yaml")

        result = diff_prompts(old_path, new_path)
        assert (
            SemanticChangeType.CONSTRAINT_CHANGE in result.semantic_change_type
            or result.semantic_change_type == SemanticChangeType.CONSTRAINT_CHANGE
        )

    def test_mixed_changes(self, base_prompt_data, create_prompt_file):
        """Handle multiple change types."""
        old_data = base_prompt_data.copy()
        new_data = base_prompt_data.copy()
        new_data["system_prompt"] = "You are a code expert."
        new_data["user_template"] = "Review: {{code}} for {{language}}"
        new_data["constraints"] = ["Be technical"]

        old_path = create_prompt_file(old_data, "old.yaml")
        new_path = create_prompt_file(new_data, "new.yaml")

        result = diff_prompts(old_path, new_path)
        assert result.semantic_change_type == SemanticChangeType.MIXED

    def test_multilingual_diff(self, create_prompt_file):
        """Handle multilingual prompts."""
        old_data = {
            "name": "zh-prompt",
            "version": "1.0.0",
            "system_prompt": "你是一位客服代表。",
            "user_template": "客户问题：{{question}}",
            "variables": {"question": {"default": "你好"}},
            "constraints": ["保持礼貌"],
            "metadata": {},
        }
        new_data = old_data.copy()
        new_data["system_prompt"] = "你是一位技术专家。"
        new_data["constraints"] = ["保持专业"]

        old_path = create_prompt_file(old_data, "old_zh.yaml")
        new_path = create_prompt_file(new_data, "new_zh.yaml")

        result = diff_prompts(old_path, new_path)
        assert result.semantic_change_type != SemanticChangeType.NONE

    def test_version_only_change(self, base_prompt_data, create_prompt_file):
        """Version-only change is low risk."""
        old_data = base_prompt_data.copy()
        new_data = base_prompt_data.copy()
        new_data["version"] = "2.0.0"

        old_path = create_prompt_file(old_data, "old.yaml")
        new_path = create_prompt_file(new_data, "new.yaml")

        result = diff_prompts(old_path, new_path)
        assert result.risk_level == RiskLevel.LOW


class TestMessageDiff:
    """Tests for multi-turn message diff detection."""

    def test_message_turn_count_change_high_risk(self, base_prompt_data, create_prompt_file):
        """Adding/removing message turns is high risk."""
        old_data = {**base_prompt_data, "messages": [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ]}
        new_data = {**base_prompt_data, "messages": [
            {"role": "user", "content": "Hi"},
        ]}

        old_path = create_prompt_file(old_data, "old.yaml")
        new_path = create_prompt_file(new_data, "new.yaml")

        result = diff_prompts(old_path, new_path)
        assert SemanticChangeType.MESSAGE_CHANGE in result.semantic_change_type.value or \
               result.semantic_change_type == SemanticChangeType.MESSAGE_CHANGE or \
               result.semantic_change_type == SemanticChangeType.MIXED
        assert result.risk_level == RiskLevel.HIGH

    def test_message_content_change_medium_risk(self, base_prompt_data, create_prompt_file):
        """Modifying message content (same turn count) is medium risk."""
        old_data = {**base_prompt_data, "messages": [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a language."},
        ]}
        new_data = {**base_prompt_data, "messages": [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."},
        ]}

        old_path = create_prompt_file(old_data, "old.yaml")
        new_path = create_prompt_file(new_data, "new.yaml")

        result = diff_prompts(old_path, new_path)
        assert result.semantic_change_type != SemanticChangeType.NONE
        assert result.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH)

    def test_message_role_change_high_risk(self, base_prompt_data, create_prompt_file):
        """Changing message role is high risk."""
        old_data = {**base_prompt_data, "messages": [
            {"role": "user", "content": "Hello"},
        ]}
        new_data = {**base_prompt_data, "messages": [
            {"role": "assistant", "content": "Hello"},
        ]}

        old_path = create_prompt_file(old_data, "old.yaml")
        new_path = create_prompt_file(new_data, "new.yaml")

        result = diff_prompts(old_path, new_path)
        assert result.risk_level == RiskLevel.HIGH

    def test_no_messages_no_change(self, base_prompt_data, create_prompt_file):
        """Templates without messages have no message-related changes."""
        old_data = base_prompt_data.copy()
        new_data = base_prompt_data.copy()

        old_path = create_prompt_file(old_data, "old.yaml")
        new_path = create_prompt_file(new_data, "new.yaml")

        result = diff_prompts(old_path, new_path)
        assert SemanticChangeType.MESSAGE_CHANGE.value not in result.semantic_change_type.value

    def test_adding_messages_field(self, base_prompt_data, create_prompt_file):
        """Adding messages to a template that had none."""
        old_data = base_prompt_data.copy()
        new_data = {**base_prompt_data, "messages": [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ]}

        old_path = create_prompt_file(old_data, "old.yaml")
        new_path = create_prompt_file(new_data, "new.yaml")

        result = diff_prompts(old_path, new_path)
        assert result.semantic_change_type != SemanticChangeType.NONE
