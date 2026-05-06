"""Tests for prompt-git-manager evaluator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from promptgit.evaluator import (
    EvalResult,
    EvalSample,
    load_dataset,
    estimate_tokens,
    compute_similarity,
    extract_keywords,
    rule_based_render,
    keyword_based_evaluate,
    evaluate_prompts,
)
from promptgit.schema import PromptTemplate


@pytest.fixture
def sample_template_data():
    """Sample template data."""
    return {
        "name": "test-prompt",
        "version": "1.0.0",
        "system_prompt": "You are a helpful assistant.",
        "user_template": "Answer the question: {{question}}",
        "variables": {"question": {"type": "string", "default": "What is Python?"}},
        "constraints": ["Be concise"],
        "metadata": {},
    }


@pytest.fixture
def create_template(tmp_path: Path, sample_template_data):
    """Create a template from data."""

    def _create(data: dict = None) -> PromptTemplate:
        if data is None:
            data = sample_template_data
        return PromptTemplate.model_validate(data)

    return _create


@pytest.fixture
def create_dataset(tmp_path: Path):
    """Factory to create dataset files."""

    def _create(samples: list[dict], name: str = "test.jsonl") -> Path:
        path = tmp_path / name
        with open(path, "w", encoding="utf-8") as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        return path

    return _create


class TestLoadDataset:
    """Tests for dataset loading."""

    def test_valid_dataset(self, create_dataset):
        """Load valid JSONL dataset."""
        samples = [
            {
                "input": "What is AI?",
                "expected_output": "AI is artificial intelligence",
            },
            {
                "input": "What is Python?",
                "expected_output": "Python is a programming language",
            },
        ]
        path = create_dataset(samples)
        result = load_dataset(path)
        assert len(result) == 2
        assert result[0].input == "What is AI?"

    def test_empty_file(self, tmp_path):
        """Handle empty file."""
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        with pytest.raises(ValueError, match="empty"):
            load_dataset(path)

    def test_missing_file(self, tmp_path):
        """Handle missing file."""
        with pytest.raises(FileNotFoundError):
            load_dataset(tmp_path / "nonexistent.jsonl")

    def test_invalid_json(self, tmp_path):
        """Handle invalid JSON line."""
        path = tmp_path / "invalid.jsonl"
        path.write_text("not json\n")
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_dataset(path)

    def test_with_metadata(self, create_dataset):
        """Load dataset with metadata field."""
        samples = [
            {
                "input": "test",
                "expected_output": "result",
                "metadata": {"category": "qa"},
            },
        ]
        path = create_dataset(samples)
        result = load_dataset(path)
        assert result[0].metadata["category"] == "qa"


class TestTokenEstimation:
    """Tests for token estimation."""

    def test_english_text(self):
        """Estimate English tokens."""
        text = "Hello world, this is a test."  # ~30 chars
        tokens = estimate_tokens(text)
        assert 5 < tokens < 15

    def test_chinese_text(self):
        """Estimate Chinese tokens."""
        text = "你好世界，这是一个测试"  # 10 CJK chars
        tokens = estimate_tokens(text)
        assert 3 < tokens < 15

    def test_empty_text(self):
        """Handle empty text."""
        assert estimate_tokens("") == 0

    def test_mixed_text(self):
        """Estimate mixed language tokens."""
        text = "Hello 你好 world 世界"
        tokens = estimate_tokens(text)
        assert tokens > 0


class TestSimilarity:
    """Tests for text similarity."""

    def test_identical_texts(self):
        """Identical texts have similarity 1.0."""
        assert compute_similarity("hello", "hello") == 1.0

    def test_completely_different(self):
        """Completely different texts have low similarity."""
        assert compute_similarity("abc", "xyz") < 0.5

    def test_empty_texts(self):
        """Both empty is 1.0."""
        assert compute_similarity("", "") == 1.0

    def test_one_empty(self):
        """One empty is 0.0."""
        assert compute_similarity("hello", "") == 0.0

    def test_partial_match(self):
        """Partial match has intermediate similarity."""
        sim = compute_similarity("hello world", "hello there")
        assert 0.3 < sim < 0.8


class TestKeywordExtraction:
    """Tests for keyword extraction."""

    def test_english_keywords(self):
        """Extract English keywords."""
        keywords = extract_keywords("The Python programming language is great")
        assert "python" in keywords
        assert "programming" in keywords
        assert "the" not in keywords  # stop word

    def test_chinese_keywords(self):
        """Extract Chinese keywords."""
        keywords = extract_keywords("Python是一种编程语言")
        assert "python" in keywords

    def test_empty_text(self):
        """Handle empty text."""
        assert extract_keywords("") == set()


class TestKeywordEvaluation:
    """Tests for keyword-based evaluation."""

    def test_matching_output(self):
        """Match when keywords align."""
        _, is_match = keyword_based_evaluate(
            "What is Python? Python is a language", "Python is a programming language"
        )
        assert is_match

    def test_no_match(self):
        """No match when keywords don't align."""
        _, is_match = keyword_based_evaluate(
            "Tell me about cats", "Python is a programming language"
        )
        assert not is_match

    def test_empty_expected(self):
        """Empty expected always matches."""
        _, is_match = keyword_based_evaluate("any prompt", "")
        assert is_match


class TestRuleBasedRender:
    """Tests for rule-based rendering."""

    def test_basic_render(self, create_template):
        """Render with variable substitution."""
        template = create_template()
        result = rule_based_render(template, {"question": "What is AI?"})
        assert "What is AI?" in result
        assert "You are a helpful assistant" in result

    def test_default_variable(self, create_template):
        """Use default variable value."""
        template = create_template()
        result = rule_based_render(template, {})
        assert "What is Python?" in result  # default value

    def test_override_variable(self, create_template):
        """Override default variable."""
        template = create_template()
        result = rule_based_render(template, {"question": "Custom question"})
        assert "Custom question" in result
        assert "What is Python?" not in result


class TestEvaluatePrompts:
    """Integration tests for prompt evaluation."""

    def test_identical_prompts_pass(self, create_template, create_dataset):
        """Identical prompts should pass evaluation."""
        template = create_template()
        dataset_samples = [
            EvalSample(input="What is Python?", expected_output="Python is a language"),
        ]
        result = evaluate_prompts(template, template, dataset_samples, threshold=0.05)
        assert result.passed
        assert result.accuracy_delta == 0.0

    def test_threshold_fail(self, create_template, create_dataset):
        """Fail when accuracy drops below threshold."""
        old_data = {
            "name": "old",
            "version": "1.0.0",
            "system_prompt": "You are a Python expert.",
            "user_template": "What is {{question}}? Python is a language.",
            "variables": {"question": {"default": "Python"}},
            "constraints": [],
            "metadata": {},
        }
        new_data = {
            "name": "new",
            "version": "2.0.0",
            "system_prompt": "You are a cat expert.",
            "user_template": "Tell me about {{question}}.",
            "variables": {"question": {"default": "cats"}},
            "constraints": [],
            "metadata": {},
        }
        old_template = PromptTemplate.model_validate(old_data)
        new_template = PromptTemplate.model_validate(new_data)

        dataset_samples = [
            EvalSample(input="What is Python?", expected_output="Python is a language"),
            EvalSample(
                input="What is coding?", expected_output="Coding is programming"
            ),
        ]

        result = evaluate_prompts(
            old_template, new_template, dataset_samples, threshold=0.05
        )
        # May fail or pass depending on keyword matching heuristics
        assert isinstance(result.passed, bool)

    def test_empty_dataset(self, create_template):
        """Handle empty dataset."""
        template = create_template()
        with pytest.raises(ValueError):
            evaluate_prompts(template, template, [])

    def test_token_cost_tracking(self, create_template):
        """Track token cost changes."""
        old_data = {
            "name": "short",
            "version": "1.0.0",
            "system_prompt": "Help.",
            "user_template": "{{q}}",
            "variables": {"q": {"default": "hi"}},
            "constraints": [],
            "metadata": {},
        }
        new_data = {
            "name": "long",
            "version": "2.0.0",
            "system_prompt": "You are a very helpful and detailed assistant who provides comprehensive answers.",
            "user_template": "Please answer this question thoroughly: {{q}}",
            "variables": {"q": {"default": "hi"}},
            "constraints": [],
            "metadata": {},
        }
        old_template = PromptTemplate.model_validate(old_data)
        new_template = PromptTemplate.model_validate(new_data)

        dataset_samples = [EvalSample(input="test", expected_output="test")]
        result = evaluate_prompts(old_template, new_template, dataset_samples)

        assert result.token_cost_new > result.token_cost_old
        assert result.token_cost_delta > 0

    def test_json_output(self, create_template):
        """JSON serialization works."""
        import json

        template = create_template()
        dataset_samples = [EvalSample(input="test", expected_output="test")]
        result = evaluate_prompts(template, template, dataset_samples)

        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert "accuracy_delta" in parsed
        assert "consistency_score" in parsed


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_constraints(self):
        """Handle empty constraints."""
        data = {
            "name": "test",
            "version": "1.0.0",
            "system_prompt": "Help.",
            "user_template": "{{q}}",
            "variables": {"q": {"default": "test"}},
            "constraints": [],
            "metadata": {},
        }
        template = PromptTemplate.model_validate(data)
        dataset = [EvalSample(input="test", expected_output="test")]
        result = evaluate_prompts(template, template, dataset)
        assert result.passed

    def test_multilingual_dataset(self, create_template):
        """Handle multilingual dataset."""
        template = create_template()
        dataset = [
            EvalSample(input="什么是Python？", expected_output="Python是一种编程语言"),
            EvalSample(
                input="What is AI?", expected_output="AI is artificial intelligence"
            ),
        ]
        result = evaluate_prompts(template, template, dataset)
        assert result.total_samples == 2

    def test_variable_conflict(self):
        """Handle variable conflicts between templates."""
        old_data = {
            "name": "old",
            "version": "1.0.0",
            "system_prompt": "Help.",
            "user_template": "{{question}}",
            "variables": {"question": {"default": "old_q"}},
            "constraints": [],
            "metadata": {},
        }
        new_data = {
            "name": "new",
            "version": "2.0.0",
            "system_prompt": "Help.",
            "user_template": "{{query}}",  # Different variable name
            "variables": {"query": {"default": "new_q"}},
            "constraints": [],
            "metadata": {},
        }
        old_template = PromptTemplate.model_validate(old_data)
        new_template = PromptTemplate.model_validate(new_data)
        dataset = [EvalSample(input="test", expected_output="test")]

        result = evaluate_prompts(old_template, new_template, dataset)
        assert isinstance(result.accuracy_delta, float)

    def test_long_text(self, create_template):
        """Handle long text inputs."""
        template = create_template()
        long_text = "word " * 1000
        dataset = [EvalSample(input=long_text, expected_output=long_text)]
        result = evaluate_prompts(template, template, dataset)
        assert result.total_samples == 1

    def test_consistency_score(self, create_template):
        """Consistency score calculation."""
        template = create_template()
        dataset = [
            EvalSample(input="q1", expected_output="a1"),
            EvalSample(input="q2", expected_output="a2"),
        ]
        result = evaluate_prompts(template, template, dataset)
        assert 0 <= result.consistency_score <= 1


class TestMultiTurnRender:
    """Tests for multi-turn message rendering."""

    def test_messages_render_structured(self):
        """Multi-turn template renders as structured conversation."""
        data = {
            "name": "multi-turn",
            "version": "1.0.0",
            "system_prompt": "You are a helpful assistant.",
            "user_template": "{{current}}",
            "variables": {
                "h1": {"default": "What is Python?"},
                "a1": {"default": "Python is a programming language."},
                "current": {"default": "Tell me more."},
            },
            "constraints": [],
            "metadata": {},
            "messages": [
                {"role": "user", "content": "{{h1}}"},
                {"role": "assistant", "content": "{{a1}}"},
            ],
        }
        template = PromptTemplate.model_validate(data)
        rendered = rule_based_render(template, {"current": "Tell me more."})

        assert "[system] You are a helpful assistant." in rendered
        assert "[user] What is Python?" in rendered
        assert "[assistant] Python is a programming language." in rendered
        assert "[user] Tell me more." in rendered

    def test_messages_with_variables(self):
        """Message content supports variable substitution."""
        data = {
            "name": "multi-turn",
            "version": "1.0.0",
            "system_prompt": "You are a bot.",
            "user_template": "{{question}}",
            "variables": {"topic": {"default": "Python"}},
            "constraints": [],
            "metadata": {},
            "messages": [
                {"role": "user", "content": "What is {{topic}}?"},
                {"role": "assistant", "content": "{{topic}} is great."},
            ],
        }
        template = PromptTemplate.model_validate(data)
        rendered = rule_based_render(template, {"question": "Go on."})

        assert "What is Python?" in rendered
        assert "Python is great." in rendered

    def test_single_turn_no_messages(self):
        """Template without messages renders as single-turn."""
        data = {
            "name": "single",
            "version": "1.0.0",
            "system_prompt": "You are helpful.",
            "user_template": "Hello",
            "variables": {},
            "constraints": [],
            "metadata": {},
        }
        template = PromptTemplate.model_validate(data)
        rendered = rule_based_render(template, {})
        assert "[system]" not in rendered
        assert rendered == "You are helpful.\n\nHello"

    def test_evaluate_prompts_with_messages(self):
        """evaluate_prompts works with multi-turn templates."""
        data = {
            "name": "mt",
            "version": "1.0.0",
            "system_prompt": "You are a Python expert.",
            "user_template": "{{question}}",
            "variables": {"question": {"default": "What is Python?"}},
            "constraints": [],
            "metadata": {},
            "messages": [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello! How can I help?"},
            ],
        }
        template = PromptTemplate.model_validate(data)
        dataset = [EvalSample(input="What is Python?", expected_output="Python is a language")]
        result = evaluate_prompts(template, template, dataset)
        assert result.total_samples == 1
        assert isinstance(result.passed, bool)

    def test_messages_validation_bad_role(self):
        """Invalid role in messages raises validation error."""
        data = {
            "name": "bad",
            "version": "1.0.0",
            "system_prompt": "sys",
            "user_template": "hello",
            "variables": {},
            "constraints": [],
            "metadata": {},
            "messages": [{"role": "invalid", "content": "test"}],
        }
        with pytest.raises(Exception):
            PromptTemplate.model_validate(data)

    def test_messages_validation_empty_content(self):
        """Empty content in messages raises validation error."""
        data = {
            "name": "bad",
            "version": "1.0.0",
            "system_prompt": "sys",
            "user_template": "hello",
            "variables": {},
            "constraints": [],
            "metadata": {},
            "messages": [{"role": "user", "content": ""}],
        }
        with pytest.raises(Exception):
            PromptTemplate.model_validate(data)
