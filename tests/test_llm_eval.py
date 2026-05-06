"""Tests for LLM evaluation module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from promptgit.evaluator import EvalSample
from promptgit.llm_evaluator import (
    LLMConfig,
    LLMJudgeResult,
    LLMCompareResult,
    LLMEvalResult,
    get_llm_config,
    call_llm,
    llm_judge_evaluate,
    llm_generate_output,
    evaluate_prompts_with_llm,
    compare_models,
)
from promptgit.schema import PromptTemplate


# ============================================================
# LLMConfig Tests
# ============================================================


class TestLLMConfig:
    """Tests for LLMConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = LLMConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-3.5-turbo"
        assert config.temperature == 0.0
        assert config.max_tokens == 1024
        assert config.api_key is None
        assert config.api_base is None

    def test_to_litellm_model_openai(self):
        """Test LiteLLM model format for OpenAI."""
        config = LLMConfig(provider="openai", model="gpt-4")
        assert config.to_litellm_model() == "openai/gpt-4"

    def test_to_litellm_model_anthropic(self):
        """Test LiteLLM model format for Anthropic."""
        config = LLMConfig(provider="anthropic", model="claude-2")
        assert config.to_litellm_model() == "anthropic/claude-2"

    def test_to_litellm_model_ollama(self):
        """Test LiteLLM model format for Ollama."""
        config = LLMConfig(provider="ollama", model="llama2")
        assert config.to_litellm_model() == "ollama/llama2"

    def test_to_litellm_model_azure(self):
        """Test LiteLLM model format for Azure."""
        config = LLMConfig(provider="azure", model="gpt-4")
        assert config.to_litellm_model() == "azure/gpt-4"

    def test_to_litellm_model_unknown(self):
        """Test LiteLLM model format for unknown provider."""
        config = LLMConfig(provider="custom", model="my-model")
        # Unknown providers don't get a prefix
        assert config.to_litellm_model() == "my-model"

    def test_custom_config(self):
        """Test custom configuration."""
        config = LLMConfig(
            provider="anthropic",
            model="claude-3-opus",
            temperature=0.5,
            max_tokens=2048,
            api_key="test-key",
            api_base="http://localhost:8080",
        )
        assert config.provider == "anthropic"
        assert config.model == "claude-3-opus"
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
        assert config.api_key == "test-key"
        assert config.api_base == "http://localhost:8080"


# ============================================================
# get_llm_config Tests
# ============================================================


class TestGetLLMConfig:
    """Tests for get_llm_config function."""

    def test_basic_config(self):
        """Test basic configuration creation."""
        config = get_llm_config("openai", "gpt-4")
        assert config.provider == "openai"
        assert config.model == "gpt-4"

    def test_with_explicit_api_key(self):
        """Test with explicit API key."""
        config = get_llm_config("openai", "gpt-4", api_key="my-key")
        assert config.api_key == "my-key"

    def test_with_api_base(self):
        """Test with custom API base."""
        config = get_llm_config("ollama", "llama2", api_base="http://localhost:11434")
        assert config.api_base == "http://localhost:11434"

    def test_env_var_openai(self, monkeypatch):
        """Test auto-detection of OpenAI API key from environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "env-key-123")
        config = get_llm_config("openai", "gpt-4")
        assert config.api_key == "env-key-123"

    def test_env_var_anthropic(self, monkeypatch):
        """Test auto-detection of Anthropic API key from environment."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key-456")
        config = get_llm_config("anthropic", "claude-2")
        assert config.api_key == "env-key-456"

    def test_explicit_key_overrides_env(self, monkeypatch):
        """Test that explicit key overrides environment variable."""
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        config = get_llm_config("openai", "gpt-4", api_key="explicit-key")
        assert config.api_key == "explicit-key"

    def test_env_var_azure(self, monkeypatch):
        """Test auto-detection of Azure API key from environment."""
        monkeypatch.setenv("AZURE_API_KEY", "azure-key-789")
        config = get_llm_config("azure", "gpt-4")
        assert config.api_key == "azure-key-789"


# ============================================================
# LLMJudgeResult Tests
# ============================================================


class TestLLMJudgeResult:
    """Tests for LLMJudgeResult dataclass."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        result = LLMJudgeResult(
            score=0.85,
            reasoning="Good output",
            raw_response='{"score": 0.85}',
        )
        d = result.to_dict()
        assert d["score"] == 0.85
        assert d["reasoning"] == "Good output"
        assert d["raw_response"] == '{"score": 0.85}'


# ============================================================
# LLMCompareResult Tests
# ============================================================


class TestLLMCompareResult:
    """Tests for LLMCompareResult dataclass."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        result = LLMCompareResult(
            model_a="gpt-3.5",
            model_b="gpt-4",
            score_a=0.7,
            score_b=0.9,
            winner="B",
            reasoning="Model B is more accurate",
        )
        d = result.to_dict()
        assert d["model_a"] == "gpt-3.5"
        assert d["model_b"] == "gpt-4"
        assert d["score_a"] == 0.7
        assert d["score_b"] == 0.9
        assert d["winner"] == "B"
        assert d["reasoning"] == "Model B is more accurate"


# ============================================================
# LLMEvalResult Tests
# ============================================================


class TestLLMEvalResult:
    """Tests for LLMEvalResult dataclass."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        result = LLMEvalResult(
            total_samples=10,
            accuracy_old=0.8,
            accuracy_new=0.9,
            accuracy_delta=0.1,
            token_cost_old=100,
            token_cost_new=120,
            token_cost_delta=0.2,
            consistency_score=0.9,
            passed=True,
            threshold=0.05,
        )
        d = result.to_dict()
        assert d["total_samples"] == 10
        assert d["accuracy_old"] == 0.8
        assert d["accuracy_new"] == 0.9
        assert d["accuracy_delta"] == 0.1
        assert d["passed"] is True

    def test_to_json(self):
        """Test JSON serialization."""
        result = LLMEvalResult(
            total_samples=5,
            accuracy_old=0.6,
            accuracy_new=0.8,
            accuracy_delta=0.2,
            token_cost_old=50,
            token_cost_new=60,
            token_cost_delta=0.2,
            consistency_score=0.8,
            passed=True,
            threshold=0.1,
        )
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["total_samples"] == 5
        assert parsed["passed"] is True


# ============================================================
# call_llm Tests (mocked)
# ============================================================


class TestCallLLM:
    """Tests for call_llm function."""

    @patch("litellm.completion")
    def test_call_llm_success(self, mock_completion):
        """Test successful LLM call."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_completion.return_value = mock_response

        config = LLMConfig(provider="openai", model="gpt-3.5-turbo")
        result = call_llm(config, "Test prompt")

        assert result == "Test response"
        mock_completion.assert_called_once()

    @patch("litellm.completion")
    def test_call_llm_with_system_prompt(self, mock_completion):
        """Test LLM call with system prompt."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "System response"
        mock_completion.return_value = mock_response

        config = LLMConfig(provider="openai", model="gpt-4")
        result = call_llm(config, "User prompt", system_prompt="You are helpful")

        assert result == "System response"
        call_args = mock_completion.call_args
        messages = call_args[1]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_call_llm_import_error(self):
        """Test ImportError when litellm is not installed."""
        with patch.dict("sys.modules", {"litellm": None}):
            config = LLMConfig()
            with pytest.raises(ImportError, match="litellm is required"):
                call_llm(config, "Test")


# ============================================================
# llm_judge_evaluate Tests (mocked)
# ============================================================


class TestLLMJudgeEvaluate:
    """Tests for llm_judge_evaluate function."""

    @patch("promptgit.llm_evaluator.call_llm")
    def test_judge_evaluate_success(self, mock_call_llm):
        """Test successful judge evaluation."""
        mock_call_llm.return_value = '{"score": 0.85, "reasoning": "Good output"}'

        config = LLMConfig()
        result = llm_judge_evaluate(
            config,
            "What is Python?",
            "Python is a programming language",
            "Python is a popular programming language",
        )

        assert isinstance(result, LLMJudgeResult)
        assert result.score == 0.85
        assert result.reasoning == "Good output"

    @patch("promptgit.llm_evaluator.call_llm")
    def test_judge_evaluate_invalid_json(self, mock_call_llm):
        """Test judge evaluation with invalid JSON response."""
        mock_call_llm.return_value = "This is not JSON"

        config = LLMConfig()
        result = llm_judge_evaluate(
            config,
            "What is Python?",
            "Python is a programming language",
            "Some output",
        )

        assert result.score == 0.0
        assert "Failed to parse" in result.reasoning

    @patch("promptgit.llm_evaluator.call_llm")
    def test_judge_evaluate_partial_json(self, mock_call_llm):
        """Test judge evaluation with partial JSON."""
        mock_call_llm.return_value = '{"score": 0.7}'

        config = LLMConfig()
        result = llm_judge_evaluate(
            config,
            "What is Python?",
            "Python is a programming language",
            "Some output",
        )

        assert result.score == 0.7
        assert result.reasoning == ""


# ============================================================
# llm_generate_output Tests (mocked)
# ============================================================


class TestLLMGenerateOutput:
    """Tests for llm_generate_output function."""

    @patch("promptgit.llm_evaluator.call_llm")
    def test_generate_output_success(self, mock_call_llm):
        """Test successful output generation."""
        mock_call_llm.return_value = "Python is a programming language"

        config = LLMConfig()
        output, tokens = llm_generate_output(
            config,
            "You are a helpful assistant.",
            "What is Python?",
        )

        assert output == "Python is a programming language"
        assert tokens > 0

    @patch("promptgit.llm_evaluator.call_llm")
    def test_generate_output_error(self, mock_call_llm):
        """Test output generation with error."""
        mock_call_llm.side_effect = Exception("API Error")

        config = LLMConfig()
        output, tokens = llm_generate_output(
            config,
            "You are a helpful assistant.",
            "What is Python?",
        )

        assert "[LLM Error:" in output
        assert tokens == 0


# ============================================================
# evaluate_prompts_with_llm Tests (mocked)
# ============================================================


class TestEvaluatePromptsWithLLM:
    """Tests for evaluate_prompts_with_llm function."""

    def create_sample_templates(self):
        """Create sample prompt templates for testing."""
        old_data = {
            "name": "test-prompt",
            "version": "1.0.0",
            "system_prompt": "You are a helpful assistant.",
            "user_template": "Answer: {{question}}",
            "variables": {"question": {"default": "What?"}},
            "constraints": ["Be concise"],
            "metadata": {},
        }
        new_data = {
            "name": "test-prompt",
            "version": "2.0.0",
            "system_prompt": "You are a code expert.",
            "user_template": "Explain: {{question}}",
            "variables": {"question": {"default": "What?"}},
            "constraints": ["Be detailed"],
            "metadata": {},
        }
        return (
            PromptTemplate(**old_data),
            PromptTemplate(**new_data),
        )

    @patch("promptgit.llm_evaluator.llm_generate_output")
    def test_evaluate_with_llm_basic(self, mock_generate):
        """Test basic LLM evaluation."""
        mock_generate.return_value = ("Python is a language", 5)

        old_template, new_template = self.create_sample_templates()
        dataset = [
            EvalSample(input="What is Python?", expected_output="Python is a language"),
            EvalSample(input="What is Git?", expected_output="Git is a VCS"),
        ]
        config = LLMConfig()

        result = evaluate_prompts_with_llm(
            old_template, new_template, dataset, config
        )

        assert isinstance(result, LLMEvalResult)
        assert result.total_samples == 2
        assert result.accuracy_old >= 0
        assert result.accuracy_new >= 0

    @patch("promptgit.llm_evaluator.llm_generate_output")
    @patch("promptgit.llm_evaluator.llm_judge_evaluate")
    def test_evaluate_with_judge(self, mock_judge, mock_generate):
        """Test LLM evaluation with judge mode."""
        mock_generate.return_value = ("Python is a language", 5)
        mock_judge.return_value = LLMJudgeResult(
            score=0.9,
            reasoning="Good",
            raw_response='{"score": 0.9}',
        )

        old_template, new_template = self.create_sample_templates()
        dataset = [
            EvalSample(input="What is Python?", expected_output="Python is a language"),
        ]
        config = LLMConfig()

        result = evaluate_prompts_with_llm(
            old_template, new_template, dataset, config, use_judge=True
        )

        assert isinstance(result, LLMEvalResult)
        assert len(result.judge_results) > 0

    def test_evaluate_empty_dataset(self):
        """Test evaluation with empty dataset."""
        old_template, new_template = self.create_sample_templates()
        config = LLMConfig()

        with pytest.raises(ValueError, match="Dataset is empty"):
            evaluate_prompts_with_llm(
                old_template, new_template, [], config
            )


# ============================================================
# compare_models Tests (mocked)
# ============================================================


class TestCompareModels:
    """Tests for compare_models function."""

    def create_sample_template(self):
        """Create sample prompt template."""
        data = {
            "name": "test-prompt",
            "version": "1.0.0",
            "system_prompt": "You are a helpful assistant.",
            "user_template": "Answer: {{question}}",
            "variables": {"question": {"default": "What?"}},
            "constraints": ["Be concise"],
            "metadata": {},
        }
        return PromptTemplate(**data)

    @patch("promptgit.llm_evaluator.llm_generate_output")
    @patch("promptgit.llm_evaluator.call_llm")
    def test_compare_models_basic(self, mock_call_llm, mock_generate):
        """Test basic model comparison."""
        mock_generate.return_value = ("Python is a language", 5)
        mock_call_llm.return_value = '{"score_a": 0.7, "score_b": 0.9, "winner": "B", "reasoning": "B is better"}'

        template = self.create_sample_template()
        dataset = [
            EvalSample(input="What is Python?", expected_output="Python is a language"),
        ]
        config_a = LLMConfig(provider="openai", model="gpt-3.5")
        config_b = LLMConfig(provider="openai", model="gpt-4")

        results = compare_models(template, dataset, config_a, config_b)

        assert len(results) == 1
        assert isinstance(results[0], LLMCompareResult)
        assert results[0].winner == "B"

    @patch("promptgit.llm_evaluator.llm_generate_output")
    @patch("promptgit.llm_evaluator.call_llm")
    def test_compare_models_invalid_json(self, mock_call_llm, mock_generate):
        """Test model comparison with invalid JSON response."""
        mock_generate.return_value = ("Python is a language", 5)
        mock_call_llm.return_value = "Invalid JSON"

        template = self.create_sample_template()
        dataset = [
            EvalSample(input="What is Python?", expected_output="Python is a language"),
        ]
        config_a = LLMConfig(provider="openai", model="gpt-3.5")
        config_b = LLMConfig(provider="openai", model="gpt-4")

        results = compare_models(template, dataset, config_a, config_b)

        assert len(results) == 1
        assert results[0].winner == "Tie"
        assert "Failed to parse" in results[0].reasoning

    @patch("promptgit.llm_evaluator.llm_generate_output")
    @patch("promptgit.llm_evaluator.call_llm")
    def test_compare_models_multiple_samples(self, mock_call_llm, mock_generate):
        """Test model comparison with multiple samples."""
        mock_generate.return_value = ("Some output", 3)
        mock_call_llm.return_value = '{"score_a": 0.8, "score_b": 0.8, "winner": "Tie", "reasoning": "Equal"}'

        template = self.create_sample_template()
        dataset = [
            EvalSample(input="Question 1?", expected_output="Answer 1"),
            EvalSample(input="Question 2?", expected_output="Answer 2"),
            EvalSample(input="Question 3?", expected_output="Answer 3"),
        ]
        config_a = LLMConfig(provider="openai", model="gpt-3.5")
        config_b = LLMConfig(provider="openai", model="gpt-4")

        results = compare_models(template, dataset, config_a, config_b)

        assert len(results) == 3


# ============================================================
# Multi-turn LLM Tests
# ============================================================


class TestMultiTurnLLM:
    """Tests for multi-turn conversation LLM support."""

    def create_multi_turn_template(self):
        """Create a template with message history."""
        return PromptTemplate.model_validate({
            "name": "multi-turn",
            "version": "1.0.0",
            "system_prompt": "You are a helpful assistant.",
            "user_template": "{{question}}",
            "variables": {"question": {"default": "What is Python?"}},
            "constraints": [],
            "metadata": {},
            "messages": [
                {"role": "user", "content": "Hi there"},
                {"role": "assistant", "content": "Hello! How can I help?"},
            ],
        })

    def test_build_messages_multi_turn(self):
        """_build_messages returns message list for multi-turn template."""
        from promptgit.llm_evaluator import _build_messages

        template = self.create_multi_turn_template()
        messages = _build_messages(template, {"question": "What is Python?"})

        assert messages is not None
        assert len(messages) == 4  # system + 2 history + user
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"
        assert messages[3]["role"] == "user"
        assert "What is Python?" in messages[3]["content"]

    def test_build_messages_single_turn(self):
        """_build_messages returns None for single-turn template."""
        from promptgit.llm_evaluator import _build_messages

        template = PromptTemplate.model_validate({
            "name": "single",
            "version": "1.0.0",
            "system_prompt": "sys",
            "user_template": "hello",
            "variables": {},
            "constraints": [],
            "metadata": {},
        })
        messages = _build_messages(template, {})
        assert messages is None

    @patch("litellm.completion")
    def test_call_llm_with_messages(self, mock_completion):
        """call_llm passes messages list directly when provided."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_completion.return_value = mock_response

        config = LLMConfig(provider="openai", model="gpt-4")
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "bye"},
        ]
        result = call_llm(config, "ignored", system_prompt="ignored", messages=messages)

        assert result == "Response"
        call_args = mock_completion.call_args
        assert call_args.kwargs["messages"] == messages

    @patch("promptgit.llm_evaluator.call_llm")
    def test_llm_generate_output_with_messages(self, mock_call_llm):
        """llm_generate_output passes messages to call_llm."""
        mock_call_llm.return_value = "output text"

        config = LLMConfig(provider="openai", model="gpt-4")
        messages = [{"role": "user", "content": "hi"}]
        output, tokens = llm_generate_output(config, "sys", "user", messages=messages)

        assert output == "output text"
        assert tokens > 0
        mock_call_llm.assert_called_once_with(
            config, "user", system_prompt="sys", messages=messages
        )

    @patch("promptgit.llm_evaluator.call_llm")
    def test_evaluate_prompts_with_llm_multi_turn(self, mock_call_llm):
        """evaluate_prompts_with_llm works with multi-turn templates."""
        mock_call_llm.return_value = "Python is a programming language."

        template = self.create_multi_turn_template()
        dataset = [
            EvalSample(input="What is Python?", expected_output="Python is a programming language"),
        ]
        config = LLMConfig(provider="openai", model="gpt-4")

        result = evaluate_prompts_with_llm(template, template, dataset, config)

        assert result.total_samples == 1
        assert isinstance(result.passed, bool)
        # Verify call_llm was called with messages (not just prompt string)
        first_call = mock_call_llm.call_args_list[0]
        assert first_call.kwargs.get("messages") is not None or \
               (len(first_call.args) > 3 and first_call.args[3] is not None) or \
               first_call.kwargs.get("messages") is not None
