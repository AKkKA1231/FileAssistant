"""Tests for strict tool schemas, argument validation, and dispatch."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from tool_registry import ToolRegistry


def _error_code(response: dict[str, Any]) -> str:
    error = cast(dict[str, Any], response["error"])
    return cast(str, error["code"])


def test_registry_exposes_only_approved_strict_schemas(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)

    schemas = registry.schemas
    names = {schema["function"]["name"] for schema in schemas}

    assert names == {"read_file", "list_files", "write_file", "search_in_file"}
    assert all(
        schema["function"]["parameters"]["additionalProperties"] is False for schema in schemas
    )


def test_schema_results_are_defensive_copies(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)
    first = registry.schemas
    first[0]["function"]["name"] = "changed"

    assert registry.schemas[0]["function"]["name"] == "read_file"


def test_registry_executes_valid_tool_call_inside_workspace(tmp_path: Path) -> None:
    (tmp_path / "resume.txt").write_text("Python", encoding="utf-8")
    registry = ToolRegistry(tmp_path)

    response = registry.execute("read_file", '{"filepath":"resume.txt"}')

    assert response["success"] is True
    data = cast(dict[str, Any], response["data"])
    assert data["content"] == "Python"


def test_registry_accepts_mapping_arguments(tmp_path: Path) -> None:
    registry = ToolRegistry(tmp_path)

    response = registry.execute(
        "write_file",
        {"filepath": "output/summary.txt", "content": "summary"},
    )

    assert response["success"] is True
    assert (tmp_path / "output" / "summary.txt").read_text(encoding="utf-8") == "summary"


def test_registry_rejects_unknown_tool(tmp_path: Path) -> None:
    response = ToolRegistry(tmp_path).execute("delete_file", "{}")

    assert _error_code(response) == "UNKNOWN_TOOL"


def test_registry_rejects_malformed_json(tmp_path: Path) -> None:
    response = ToolRegistry(tmp_path).execute("read_file", "{not-json}")

    assert _error_code(response) == "TOOL_ARGUMENT_ERROR"


def test_registry_rejects_non_object_json(tmp_path: Path) -> None:
    response = ToolRegistry(tmp_path).execute("read_file", "[]")

    assert _error_code(response) == "TOOL_ARGUMENT_ERROR"


def test_registry_rejects_missing_arguments(tmp_path: Path) -> None:
    response = ToolRegistry(tmp_path).execute("search_in_file", '{"filepath":"resume.txt"}')

    assert _error_code(response) == "TOOL_ARGUMENT_ERROR"


def test_registry_rejects_unknown_arguments(tmp_path: Path) -> None:
    response = ToolRegistry(tmp_path).execute(
        "read_file",
        '{"filepath":"resume.txt","workspace_root":"C:/"}',
    )

    assert _error_code(response) == "TOOL_ARGUMENT_ERROR"


def test_registry_rejects_wrong_argument_type(tmp_path: Path) -> None:
    response = ToolRegistry(tmp_path).execute("read_file", '{"filepath":42}')

    assert _error_code(response) == "TOOL_ARGUMENT_ERROR"


def test_registry_rejects_empty_required_string(tmp_path: Path) -> None:
    response = ToolRegistry(tmp_path).execute("read_file", '{"filepath":"  "}')

    assert _error_code(response) == "TOOL_ARGUMENT_ERROR"
