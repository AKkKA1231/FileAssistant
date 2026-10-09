"""Validated registry for the file-system tools exposed to the LLM."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from contracts import ErrorCode, ToolResponse, error_response
from fs_tools import list_files, read_file, search_in_file, write_file

ToolFunction = Callable[..., ToolResponse]


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """A callable tool and its provider-facing JSON schema."""

    name: str
    description: str
    parameters: dict[str, Any]
    function: ToolFunction

    def as_provider_schema(self) -> dict[str, Any]:
        """Return a defensive copy of the Groq-compatible function schema."""

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": deepcopy(self.parameters),
            },
        }


_TOOL_DEFINITIONS = (
    ToolDefinition(
        name="read_file",
        description="Read and extract text from one PDF, TXT, or DOCX file.",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Path to the file, relative to the configured workspace.",
                }
            },
            "required": ["filepath"],
            "additionalProperties": False,
        },
        function=read_file,
    ),
    ToolDefinition(
        name="list_files",
        description="List regular files in one directory, optionally filtered by extension.",
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "minLength": 1,
                    "description": (
                        "Non-empty directory path relative to the configured workspace. "
                        "Use 'resumes' for the default document collection or '.' for the "
                        "workspace root; never use an empty string."
                    ),
                },
                "extension": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Optional extension filter such as .pdf, .txt, or .docx.",
                },
            },
            "required": ["directory"],
            "additionalProperties": False,
        },
        function=list_files,
    ),
    ToolDefinition(
        name="write_file",
        description=(
            "Write UTF-8 text to a workspace file. Set overwrite only when the user explicitly "
            "requested replacing an existing file."
        ),
        parameters={
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Destination path relative to the configured workspace.",
                },
                "content": {
                    "type": "string",
                    "description": "Complete text content to write.",
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "Whether to replace an existing file. Defaults to false.",
                },
            },
            "required": ["filepath", "content"],
            "additionalProperties": False,
        },
        function=write_file,
    ),
    ToolDefinition(
        name="search_in_file",
        description="Search one supported file for a literal keyword, ignoring letter case.",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Path to a PDF, TXT, or DOCX file in the workspace.",
                },
                "keyword": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Literal word or phrase to find.",
                },
            },
            "required": ["filepath", "keyword"],
            "additionalProperties": False,
        },
        function=search_in_file,
    ),
)


class ToolRegistry:
    """Expose approved tools and validate model-generated calls before execution."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve(strict=False)
        self._tools = {definition.name: definition for definition in _TOOL_DEFINITIONS}

    @property
    def schemas(self) -> list[dict[str, Any]]:
        """Return provider-facing schemas for all registered tools."""

        return [definition.as_provider_schema() for definition in self._tools.values()]

    def execute(self, name: str, arguments: str | Mapping[str, Any]) -> ToolResponse:
        """Parse, validate, and execute one registered tool call."""

        definition = self._tools.get(name)
        if definition is None:
            return error_response(
                ErrorCode.UNKNOWN_TOOL,
                "The model requested an unknown tool.",
                details={"tool": name, "available_tools": sorted(self._tools)},
            )

        parsed, parse_error = self._parse_arguments(arguments)
        if parse_error is not None:
            return parse_error
        assert parsed is not None

        argument_values = dict(parsed)
        validation_error = _validate_arguments(definition.parameters, argument_values)
        if validation_error is not None:
            return error_response(
                ErrorCode.TOOL_ARGUMENT_ERROR,
                validation_error,
                details={"tool": name},
            )

        try:
            return definition.function(
                **argument_values,
                workspace_root=self.workspace_root,
            )
        except Exception:
            return error_response(
                ErrorCode.INTERNAL_ERROR,
                "The tool failed unexpectedly.",
                details={"tool": name},
            )

    @staticmethod
    def _parse_arguments(
        arguments: str | Mapping[str, Any],
    ) -> tuple[dict[str, Any] | None, ToolResponse | None]:
        if isinstance(arguments, str):
            try:
                parsed: Any = json.loads(arguments)
            except json.JSONDecodeError:
                return (
                    None,
                    error_response(
                        ErrorCode.TOOL_ARGUMENT_ERROR,
                        "Tool arguments are not valid JSON.",
                    ),
                )
        elif isinstance(arguments, Mapping):
            parsed = dict(arguments)
        else:
            return (
                None,
                error_response(
                    ErrorCode.TOOL_ARGUMENT_ERROR,
                    "Tool arguments must be a JSON object.",
                ),
            )

        if not isinstance(parsed, dict):
            return (
                None,
                error_response(
                    ErrorCode.TOOL_ARGUMENT_ERROR,
                    "Tool arguments must decode to a JSON object.",
                ),
            )
        return parsed, None


def _validate_arguments(schema: dict[str, Any], arguments: dict[str, Any]) -> str | None:
    properties = schema["properties"]
    required = set(schema.get("required", []))
    supplied = set(arguments)

    missing = sorted(required - supplied)
    if missing:
        return "Missing required argument(s): " + ", ".join(missing) + "."

    unknown = sorted(supplied - set(properties))
    if unknown:
        return "Unknown argument(s): " + ", ".join(unknown) + "."

    for name, value in arguments.items():
        property_schema = properties[name]
        expected_type = property_schema["type"]
        if expected_type == "string":
            if not isinstance(value, str):
                return f"Argument '{name}' must be a string."
            minimum_length = property_schema.get("minLength", 0)
            if len(value.strip()) < minimum_length:
                return f"Argument '{name}' cannot be empty."
        elif expected_type == "boolean" and not isinstance(value, bool):
            return f"Argument '{name}' must be a boolean."

    return None


__all__ = ["ToolDefinition", "ToolRegistry"]
