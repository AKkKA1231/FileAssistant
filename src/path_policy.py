"""Workspace-bound path validation and file metadata helpers."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from contracts import ErrorCode, FileMetadata, ToolResponse, error_response

SUPPORTED_EXTENSIONS = frozenset({".docx", ".pdf", ".txt"})
_EXTENSION_PATTERN = re.compile(r"^\.[a-z0-9]+$")


class PathValidationError(ValueError):
    """A predictable validation failure that can be converted to a tool response."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})

    def to_response(self) -> ToolResponse:
        """Convert this validation failure to the public response envelope."""

        return error_response(self.code, self.message, details=self.details)


def normalize_extension(extension: str, *, require_supported: bool = True) -> str:
    """Normalize an extension to lowercase with a leading dot.

    Args:
        extension: An extension such as ``pdf`` or ``.PDF``.
        require_supported: Restrict the result to the supported resume formats.

    Raises:
        PathValidationError: If the value is empty, malformed, or unsupported.
    """

    if not isinstance(extension, str):
        raise PathValidationError(
            ErrorCode.INVALID_ARGUMENT,
            "The extension must be a string.",
            details={"argument": "extension"},
        )

    normalized = extension.strip().lower()
    if not normalized:
        raise PathValidationError(
            ErrorCode.INVALID_ARGUMENT,
            "The extension cannot be empty.",
            details={"argument": "extension"},
        )

    if not normalized.startswith("."):
        normalized = f".{normalized}"

    if not _EXTENSION_PATTERN.fullmatch(normalized):
        raise PathValidationError(
            ErrorCode.INVALID_ARGUMENT,
            "The extension must contain only letters and numbers.",
            details={"argument": "extension", "value": extension},
        )

    if require_supported and normalized not in SUPPORTED_EXTENSIONS:
        raise PathValidationError(
            ErrorCode.UNSUPPORTED_FILE_TYPE,
            f"Unsupported file extension: {normalized}",
            details={"extension": normalized, "supported": sorted(SUPPORTED_EXTENSIONS)},
        )

    return normalized


def resolve_workspace_path(
    raw_path: str | Path,
    workspace_root: str | Path,
) -> Path:
    """Resolve a path and verify that it stays within the workspace root."""

    candidate_input = _validate_path_input(raw_path, argument="path")
    root_input = _validate_path_input(workspace_root, argument="workspace_root")

    try:
        root = root_input.expanduser().resolve(strict=False)
        candidate = candidate_input.expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise PathValidationError(
            ErrorCode.INVALID_PATH,
            "The path could not be resolved.",
            details={"path": str(raw_path)},
        ) from exc

    if not resolved.is_relative_to(root):
        raise PathValidationError(
            ErrorCode.PATH_OUTSIDE_WORKSPACE,
            "The requested path is outside the configured workspace.",
            details={"path": str(raw_path)},
        )

    return resolved


def validate_file_path(
    raw_path: str | Path,
    workspace_root: str | Path,
    *,
    must_exist: bool = True,
    require_supported: bool = True,
) -> Path:
    """Validate a file path for a read or write operation."""

    path = resolve_workspace_path(raw_path, workspace_root)

    if must_exist and not path.exists():
        raise PathValidationError(
            ErrorCode.FILE_NOT_FOUND,
            "The requested file does not exist.",
            details={"path": str(raw_path)},
        )

    if path.exists() and not path.is_file():
        raise PathValidationError(
            ErrorCode.NOT_A_FILE,
            "The requested path is not a regular file.",
            details={"path": str(raw_path)},
        )

    if require_supported:
        normalize_extension(path.suffix)

    return path


def validate_directory_path(
    raw_path: str | Path,
    workspace_root: str | Path,
    *,
    must_exist: bool = True,
) -> Path:
    """Validate a directory path within the configured workspace."""

    path = resolve_workspace_path(raw_path, workspace_root)

    if must_exist and not path.exists():
        raise PathValidationError(
            ErrorCode.DIRECTORY_NOT_FOUND,
            "The requested directory does not exist.",
            details={"path": str(raw_path)},
        )

    if path.exists() and not path.is_dir():
        raise PathValidationError(
            ErrorCode.NOT_A_DIRECTORY,
            "The requested path is not a directory.",
            details={"path": str(raw_path)},
        )

    return path


def build_file_metadata(path: Path) -> FileMetadata:
    """Create the standard metadata representation for an existing file."""

    try:
        stat = path.stat()
    except PermissionError as exc:
        raise PathValidationError(
            ErrorCode.PERMISSION_DENIED,
            "Permission was denied while reading file metadata.",
            details={"path": str(path)},
        ) from exc
    except OSError as exc:
        raise PathValidationError(
            ErrorCode.READ_FAILED,
            "File metadata could not be read.",
            details={"path": str(path)},
        ) from exc

    if not path.is_file():
        raise PathValidationError(
            ErrorCode.NOT_A_FILE,
            "Metadata is available only for regular files.",
            details={"path": str(path)},
        )

    return {
        "name": path.name,
        "path": str(path),
        "extension": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
    }


def _validate_path_input(raw_path: str | Path, *, argument: str) -> Path:
    """Validate and convert a public path argument."""

    if not isinstance(raw_path, (str, Path)):
        raise PathValidationError(
            ErrorCode.INVALID_ARGUMENT,
            f"{argument} must be a string or Path.",
            details={"argument": argument},
        )

    if isinstance(raw_path, str) and not raw_path.strip():
        raise PathValidationError(
            ErrorCode.INVALID_PATH,
            f"{argument} cannot be empty.",
            details={"argument": argument},
        )

    return Path(raw_path)


__all__ = [
    "SUPPORTED_EXTENSIONS",
    "PathValidationError",
    "build_file_metadata",
    "normalize_extension",
    "resolve_workspace_path",
    "validate_directory_path",
    "validate_file_path",
]
