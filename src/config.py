"""Validated environment configuration for the file-system assistant."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(ValueError):
    """Raised when application configuration is missing or invalid."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Immutable, validated runtime configuration."""

    llm_provider: str
    llm_model: str
    groq_api_key: str | None
    workspace_root: Path
    max_file_size_bytes: int
    max_search_matches: int
    search_context_characters: int
    max_tool_steps: int
    log_level: str

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
        *,
        base_directory: Path | None = None,
    ) -> AppConfig:
        """Build configuration from environment variables and safe defaults."""

        values = os.environ if environment is None else environment
        base = (base_directory or Path.cwd()).resolve()
        workspace_value = values.get("ASSISTANT_WORKSPACE", "./data").strip()
        if not workspace_value:
            raise ConfigurationError("ASSISTANT_WORKSPACE", "Workspace path cannot be empty.")

        workspace = Path(workspace_value).expanduser()
        if not workspace.is_absolute():
            workspace = base / workspace

        provider = _required_text(values, "LLM_PROVIDER", "groq")
        model = _required_text(values, "LLM_MODEL", "openai/gpt-oss-20b")
        api_key = values.get("GROQ_API_KEY", "").strip() or None
        log_level = _required_text(values, "LOG_LEVEL", "INFO").upper()
        if log_level not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ConfigurationError("LOG_LEVEL", "LOG_LEVEL is not a supported logging level.")

        return cls(
            llm_provider=provider.lower(),
            llm_model=model,
            groq_api_key=api_key,
            workspace_root=workspace.resolve(strict=False),
            max_file_size_bytes=_positive_integer(
                values, "MAX_FILE_SIZE_BYTES", default=10_485_760
            ),
            max_search_matches=_positive_integer(values, "MAX_SEARCH_MATCHES", default=100),
            search_context_characters=_positive_integer(
                values, "SEARCH_CONTEXT_CHARACTERS", default=120, allow_zero=True
            ),
            max_tool_steps=_positive_integer(values, "MAX_TOOL_STEPS", default=10),
            log_level=log_level,
        )


def _required_text(values: Mapping[str, str], field: str, default: str) -> str:
    value = values.get(field, default).strip()
    if not value:
        raise ConfigurationError(field, f"{field} cannot be empty.")
    return value


def _positive_integer(
    values: Mapping[str, str],
    field: str,
    *,
    default: int,
    allow_zero: bool = False,
) -> int:
    raw_value = values.get(field, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(field, f"{field} must be an integer.") from exc

    minimum = 0 if allow_zero else 1
    if value < minimum:
        qualifier = "zero or greater" if allow_zero else "greater than zero"
        raise ConfigurationError(field, f"{field} must be {qualifier}.")
    return value


__all__ = ["AppConfig", "ConfigurationError"]
