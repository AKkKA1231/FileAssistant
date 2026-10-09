"""Tests for environment-backed application configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from config import AppConfig, ConfigurationError


def test_config_uses_safe_defaults(tmp_path: Path) -> None:
    config = AppConfig.from_environment({}, base_directory=tmp_path)

    assert config.llm_provider == "groq"
    assert config.llm_model == "openai/gpt-oss-20b"
    assert config.groq_api_key is None
    assert config.workspace_root == (tmp_path / "data").resolve()
    assert config.max_file_size_bytes == 10_485_760
    assert config.max_search_matches == 100
    assert config.search_context_characters == 120
    assert config.max_tool_steps == 10
    assert config.log_level == "INFO"


def test_config_normalizes_values(tmp_path: Path) -> None:
    config = AppConfig.from_environment(
        {
            "LLM_PROVIDER": " Groq ",
            "LLM_MODEL": " test-model ",
            "GROQ_API_KEY": " secret ",
            "ASSISTANT_WORKSPACE": "workspace",
            "MAX_FILE_SIZE_BYTES": "2048",
            "MAX_SEARCH_MATCHES": "5",
            "SEARCH_CONTEXT_CHARACTERS": "0",
            "MAX_TOOL_STEPS": "3",
            "LOG_LEVEL": "debug",
        },
        base_directory=tmp_path,
    )

    assert config.llm_provider == "groq"
    assert config.llm_model == "test-model"
    assert config.groq_api_key == "secret"
    assert config.workspace_root == (tmp_path / "workspace").resolve()
    assert config.max_file_size_bytes == 2048
    assert config.max_search_matches == 5
    assert config.search_context_characters == 0
    assert config.max_tool_steps == 3
    assert config.log_level == "DEBUG"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("MAX_FILE_SIZE_BYTES", "0"),
        ("MAX_SEARCH_MATCHES", "-1"),
        ("MAX_TOOL_STEPS", "abc"),
        ("LOG_LEVEL", "verbose"),
        ("ASSISTANT_WORKSPACE", " "),
    ],
)
def test_config_rejects_invalid_values(tmp_path: Path, field: str, value: str) -> None:
    with pytest.raises(ConfigurationError) as error:
        AppConfig.from_environment({field: value}, base_directory=tmp_path)

    assert error.value.field == field
