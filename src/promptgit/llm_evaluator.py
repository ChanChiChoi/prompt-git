"""LLM-enhanced evaluation engine.

Provides LLM-as-judge evaluation mode using LiteLLM for multi-provider support.
Supports OpenAI, Anthropic, and local models.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from promptgit.evaluator import (
    EvalSample,
    EvalResult,
    SampleResult,
    compute_similarity,
    estimate_tokens,
    rule_based_render,
)
from promptgit.schema import PromptTemplate


@dataclass
class LLMConfig:
    """Configuration for LLM evaluation."""

    provider: str = "openai"
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.0
    max_tokens: int = 1024
    api_key: Optional[str] = None
    api_base: Optional[str] = None

    def to_litellm_model(self) -> str:
        """Convert to LiteLLM model format."""
        provider_prefixes = {
            "openai": "openai/",
            "anthropic": "anthropic/",
            "ollama": "ollama/",
            "vllm": "openai/",  # vLLM uses OpenAI-compatible API
            "sglang": "openai/",  # SGLang uses OpenAI-compatible API
            "azure": "azure/",
            "huggingface": "huggingface/",
        }
        prefix = provider_prefixes.get(self.provider, "")
        return f"{prefix}{self.model}"


@dataclass
class LLMJudgeResult:
    """Result from LLM-as-judge evaluation."""

    score: float
    reasoning: str
    raw_response: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "reasoning": self.reasoning,
            "raw_response": self.raw_response,
        }


@dataclass
class LLMCompareResult:
    """Result from multi-model comparison."""

    model_a: str
    model_b: str
    score_a: float
    score_b: float
    winner: str
    reasoning: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_a": self.model_a,
            "model_b": self.model_b,
            "score_a": self.score_a,
            "score_b": self.score_b,
            "winner": self.winner,
            "reasoning": self.reasoning,
        }


@dataclass
class LLMEvalResult:
    """Complete LLM evaluation result."""

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
    judge_results: list[LLMJudgeResult] = field(default_factory=list)
    compare_results: list[LLMCompareResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
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
            "judge_results": [j.to_dict() for j in self.judge_results],
            "compare_results": [c.to_dict() for c in self.compare_results],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def get_llm_config(
    provider: str = "openai",
    model: str = "gpt-3.5-turbo",
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
) -> LLMConfig:
    """Create LLM configuration from provider and model.

    Args:
        provider: LLM provider name (openai, anthropic, ollama, vllm, sglang, etc.)
        model: Model name
        api_key: API key (optional, can use env vars)
        api_base: API base URL (optional, for local models)

    Returns:
        LLMConfig instance
    """
    # Default API base URLs for local providers
    default_api_bases = {
        "ollama": "http://localhost:11434",
        "vllm": "http://localhost:8000/v1",
        "sglang": "http://localhost:30000/v1",
    }

    # Use default API base if not specified
    if api_base is None and provider in default_api_bases:
        api_base = default_api_bases[provider]

    # Auto-detect API key from environment
    if api_key is None:
        env_keys = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "ollama": "OLLAMA_API_KEY",
            "vllm": "VLLM_API_KEY",
            "sglang": "SGLANG_API_KEY",
            "azure": "AZURE_API_KEY",
        }
        env_var = env_keys.get(provider)
        if env_var:
            api_key = os.environ.get(env_var)

    # For local providers, use a dummy API key if not set
    if api_key is None and provider in ("ollama", "vllm", "sglang"):
        api_key = "dummy"

    return LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        api_base=api_base,
    )


def call_llm(
    config: LLMConfig,
    prompt: str,
    system_prompt: Optional[str] = None,
) -> str:
    """Call LLM using LiteLLM.

    Args:
        config: LLM configuration
        prompt: User prompt
        system_prompt: System prompt (optional)

    Returns:
        LLM response text

    Raises:
        ImportError: If litellm is not installed
        Exception: If LLM call fails
    """
    try:
        from litellm import completion
    except ImportError:
        raise ImportError(
            "litellm is required for LLM evaluation. "
            "Install it with: pip install litellm"
        )

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Prepare kwargs
    kwargs = {
        "model": config.to_litellm_model(),
        "messages": messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }

    if config.api_key:
        kwargs["api_key"] = config.api_key
    if config.api_base:
        kwargs["api_base"] = config.api_base

    response = completion(**kwargs)
    return response.choices[0].message.content


def llm_judge_evaluate(
    config: LLMConfig,
    rendered_prompt: str,
    expected_output: str,
    actual_output: str,
) -> LLMJudgeResult:
    """Use LLM as judge to evaluate output quality.

    Args:
        config: LLM configuration
        rendered_prompt: The rendered prompt sent to model
        expected_output: Expected output
        actual_output: Actual output from model

    Returns:
        LLMJudgeResult with score and reasoning
    """
    judge_prompt = f"""You are an expert evaluator. Please evaluate the quality of the AI's response.

## Original Prompt
{rendered_prompt}

## Expected Output
{expected_output}

## Actual Output
{actual_output}

## Evaluation Criteria
1. Does the actual output convey the same meaning as the expected output?
2. Is the actual output factually accurate?
3. Is the actual output clear and well-structured?

## Response Format
Please respond with a JSON object containing:
- "score": a float between 0.0 and 1.0 (1.0 = perfect match)
- "reasoning": a brief explanation of your evaluation

Example:
{{"score": 0.85, "reasoning": "The output is mostly correct but missing some details."}}
"""

    try:
        response = call_llm(config, judge_prompt, system_prompt="You are an expert evaluator. Respond only with valid JSON.")

        # Parse JSON response
        result = json.loads(response)
        return LLMJudgeResult(
            score=float(result.get("score", 0.0)),
            reasoning=result.get("reasoning", ""),
            raw_response=response,
        )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        return LLMJudgeResult(
            score=0.0,
            reasoning=f"Failed to parse LLM response: {e}",
            raw_response=response if 'response' in locals() else "",
        )


def llm_generate_output(
    config: LLMConfig,
    system_prompt: str,
    user_prompt: str,
) -> tuple[str, int]:
    """Generate output using LLM.

    Args:
        config: LLM configuration
        system_prompt: System prompt
        user_prompt: User prompt

    Returns:
        Tuple of (output_text, estimated_tokens)
    """
    try:
        output = call_llm(config, user_prompt, system_prompt=system_prompt)
        tokens = estimate_tokens(output)
        return output, tokens
    except Exception as e:
        return f"[LLM Error: {e}]", 0


def evaluate_prompts_with_llm(
    old_template: PromptTemplate,
    new_template: PromptTemplate,
    dataset: list[EvalSample],
    config: LLMConfig,
    threshold: float = 0.05,
    use_judge: bool = False,
    judge_config: Optional[LLMConfig] = None,
) -> LLMEvalResult:
    """Evaluate prompts using LLM.

    Args:
        old_template: Original prompt template
        new_template: New prompt template
        dataset: List of evaluation samples
        config: LLM configuration for generating outputs
        threshold: Accuracy drop threshold
        use_judge: Whether to use LLM-as-judge for scoring
        judge_config: Optional separate LLM config for judge (if None, uses config)

    Returns:
        LLMEvalResult with metrics
    """
    if not dataset:
        raise ValueError("Dataset is empty, cannot evaluate.")

    # Use separate judge config if provided, otherwise use same config
    judge_llm_config = judge_config if judge_config else config

    details = []
    judge_results = []
    old_correct = 0
    new_correct = 0
    old_total_tokens = 0
    new_total_tokens = 0
    consistency_matches = 0

    for sample in dataset:
        variables = {"input": sample.input, "question": sample.input}

        # Render prompts
        old_rendered = rule_based_render(old_template, variables)
        new_rendered = rule_based_render(new_template, variables)

        # Generate outputs using LLM
        old_output, old_tokens = llm_generate_output(
            config, old_template.system_prompt, old_rendered
        )
        new_output, new_tokens = llm_generate_output(
            config, new_template.system_prompt, new_rendered
        )

        old_total_tokens += old_tokens
        new_total_tokens += new_tokens

        # Evaluate match
        if use_judge:
            # Use LLM-as-judge (potentially different model)
            old_judge = llm_judge_evaluate(judge_llm_config, old_rendered, sample.expected_output, old_output)
            new_judge = llm_judge_evaluate(judge_llm_config, new_rendered, sample.expected_output, new_output)

            old_match = old_judge.score >= 0.7
            new_match = new_judge.score >= 0.7

            judge_results.extend([old_judge, new_judge])
        else:
            # Use similarity-based matching
            old_similarity = compute_similarity(old_output, sample.expected_output)
            new_similarity = compute_similarity(new_output, sample.expected_output)

            old_match = old_similarity >= 0.7
            new_match = new_similarity >= 0.7

        if old_match:
            old_correct += 1
        if new_match:
            new_correct += 1

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

    passed = accuracy_delta >= -threshold

    return LLMEvalResult(
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
        judge_results=judge_results,
    )


def compare_models(
    template: PromptTemplate,
    dataset: list[EvalSample],
    config_a: LLMConfig,
    config_b: LLMConfig,
) -> list[LLMCompareResult]:
    """Compare two models on the same dataset.

    Args:
        template: Prompt template to use
        dataset: List of evaluation samples
        config_a: Configuration for model A
        config_b: Configuration for model B

    Returns:
        List of LLMCompareResult for each sample
    """
    results = []

    for sample in dataset:
        variables = {"input": sample.input, "question": sample.input}
        rendered = rule_based_render(template, variables)

        # Generate outputs from both models
        output_a, _ = llm_generate_output(config_a, template.system_prompt, rendered)
        output_b, _ = llm_generate_output(config_b, template.system_prompt, rendered)

        # Compare using LLM-as-judge
        judge_prompt = f"""Compare these two AI responses and determine which is better.

## Original Prompt
{rendered}

## Expected Output
{sample.expected_output}

## Model A ({config_a.model})
{output_a}

## Model B ({config_b.model})
{output_b}

## Response Format
Please respond with a JSON object containing:
- "score_a": float between 0.0 and 1.0
- "score_b": float between 0.0 and 1.0
- "winner": "A", "B", or "Tie"
- "reasoning": brief explanation

Example:
{{"score_a": 0.8, "score_b": 0.9, "winner": "B", "reasoning": "Model B provided more accurate information."}}
"""

        try:
            response = call_llm(
                config_a,
                judge_prompt,
                system_prompt="You are an expert evaluator. Respond only with valid JSON.",
            )
            result = json.loads(response)

            results.append(
                LLMCompareResult(
                    model_a=config_a.model,
                    model_b=config_b.model,
                    score_a=float(result.get("score_a", 0.5)),
                    score_b=float(result.get("score_b", 0.5)),
                    winner=result.get("winner", "Tie"),
                    reasoning=result.get("reasoning", ""),
                )
            )
        except (json.JSONDecodeError, ValueError, KeyError):
            results.append(
                LLMCompareResult(
                    model_a=config_a.model,
                    model_b=config_b.model,
                    score_a=0.5,
                    score_b=0.5,
                    winner="Tie",
                    reasoning="Failed to parse comparison result",
                )
            )

    return results
