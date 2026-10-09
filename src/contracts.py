"""Shared response and metadata contracts for file-system tools."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, TypedDict


class ErrorCode(StrEnum):
    """Stable machine-readable error codes returned by public tools."""

    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    INVALID_PATH = "INVALID_PATH"
    PATH_OUTSIDE_WORKSPACE = "PATH_OUTSIDE_WORKSPACE"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    DIRECTORY_NOT_FOUND = "DIRECTORY_NOT_FOUND"
    NOT_A_FILE = "NOT_A_FILE"
    NOT_A_DIRECTORY = "NOT_A_DIRECTORY"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    FILE_ALREADY_EXISTS = "FILE_ALREADY_EXISTS"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    DECODE_ERROR = "DECODE_ERROR"
    PARSE_ERROR = "PARSE_ERROR"
    ENCRYPTED_FILE_UNSUPPORTED = "ENCRYPTED_FILE_UNSUPPORTED"
    READ_FAILED = "READ_FAILED"
    WRITE_FAILED = "WRITE_FAILED"
    INVALID_KEYWORD = "INVALID_KEYWORD"
    QUERY_OUT_OF_SCOPE = "QUERY_OUT_OF_SCOPE"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    TOOL_ARGUMENT_ERROR = "TOOL_ARGUMENT_ERROR"
    TOOL_STEP_LIMIT_REACHED = "TOOL_STEP_LIMIT_REACHED"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class FileMetadata(TypedDict):
    """Metadata returned for a regular file."""

    name: str
    path: str
    extension: str
    size_bytes: int
    modified_at: str


class ToolError(TypedDict):
    """Serializable details for a failed tool operation."""

    code: str
    message: str
    details: dict[str, Any]


class ToolResponse(TypedDict):
    """Common response envelope used by every public tool."""

    success: bool
    data: Any | None
    error: ToolError | None
    warnings: list[str]


def success_response(data: Any, *, warnings: list[str] | None = None) -> ToolResponse:
    """Build a successful tool response without sharing mutable input lists."""

    return {
        "success": True,
        "data": data,
        "error": None,
        "warnings": list(warnings or []),
    }


def error_response(
    code: ErrorCode,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> ToolResponse:
    """Build a failed tool response with a stable machine-readable error code."""

    return {
        "success": False,
        "data": None,
        "error": {
            "code": code.value,
            "message": message,
            "details": dict(details or {}),
        },
        "warnings": list(warnings or []),
    }


__all__ = [
    "ErrorCode",
    "FileMetadata",
    "ToolError",
    "ToolResponse",
    "error_response",
    "success_response",
]
