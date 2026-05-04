"""Pydantic schema for prompt template validation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class PromptTemplate(BaseModel):
    """Schema for a prompt template file.

    Supports YAML/JSON format with structured fields for
    system prompt, user template, variables, constraints, and metadata.
    """

    name: str = Field(..., min_length=1, max_length=128, description="Prompt name")
    version: str = Field(default="0.1.0", description="Semantic version")
    system_prompt: str = Field(..., min_length=1, description="System prompt text")
    user_template: str = Field(
        ..., min_length=1, description="User message template with {{var}} placeholders"
    )
    variables: dict[str, Any] = Field(
        default_factory=dict, description="Variable definitions with defaults"
    )
    constraints: list[str] = Field(
        default_factory=list, description="Behavioral constraints"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary metadata"
    )

    @field_validator("user_template")
    @classmethod
    def validate_template_vars(cls, v: str) -> str:
        """Ensure all {{var}} in template have matching variable definitions."""
        import re

        placeholders = set(re.findall(r"\{\{(\w+)\}\}", v))
        return v

    @classmethod
    def from_yaml(cls, path: Path) -> PromptTemplate:
        """Load and validate a prompt template from a YAML file.

        Args:
            path: Path to the YAML file.

        Returns:
            Validated PromptTemplate instance.

        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If YAML is invalid or schema validation fails.
        """
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}") from e

        if not isinstance(data, dict):
            raise ValueError(f"Expected a YAML mapping, got {type(data).__name__}")

        try:
            return cls.model_validate(data)
        except Exception as e:
            raise ValueError(f"Schema validation failed for {path}: {e}") from e


class CommitRecord(BaseModel):
    """Record of a prompt commit."""

    hash: str = Field(..., description="Git commit hash")
    timestamp: datetime = Field(default_factory=datetime.now, description="Commit time")
    changed_files: list[str] = Field(
        default_factory=list, description="Changed prompt files"
    )
    validation_status: str = Field(default="pass", description="Validation result")
    message: str = Field(default="", description="Commit message")
