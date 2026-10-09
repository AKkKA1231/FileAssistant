"""Safe, structured file-system tools exposed to the LLM assistant."""

from __future__ import annotations

import os
import re
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any, cast

from config import AppConfig, ConfigurationError
from contracts import ErrorCode, ToolResponse, error_response, success_response
from extractors import ExtractionError, extract_text
from path_policy import (
    PathValidationError,
    build_file_metadata,
    normalize_extension,
    validate_directory_path,
    validate_file_path,
)


def read_file(
    filepath: str,
    *,
    workspace_root: str | Path | None = None,
    max_file_size_bytes: int | None = None,
) -> ToolResponse:
    """Read and extract a PDF, TXT, or DOCX file within the workspace."""

    try:
        config = AppConfig.from_environment()
        root = config.workspace_root if workspace_root is None else workspace_root
        size_limit = (
            config.max_file_size_bytes if max_file_size_bytes is None else max_file_size_bytes
        )
        if not isinstance(size_limit, int) or isinstance(size_limit, bool) or size_limit <= 0:
            return error_response(
                ErrorCode.INVALID_ARGUMENT,
                "max_file_size_bytes must be a positive integer.",
                details={"argument": "max_file_size_bytes"},
            )

        path = validate_file_path(filepath, root)
        metadata = build_file_metadata(path)
        if metadata["size_bytes"] > size_limit:
            return error_response(
                ErrorCode.FILE_TOO_LARGE,
                "The requested file exceeds the configured size limit.",
                details={
                    "path": str(filepath),
                    "size_bytes": metadata["size_bytes"],
                    "max_file_size_bytes": size_limit,
                },
            )

        extraction = extract_text(path)
        return success_response(
            {
                "content": extraction.content,
                "metadata": metadata,
                "extraction": dict(extraction.details),
            },
            warnings=list(extraction.warnings),
        )
    except PathValidationError as exc:
        return exc.to_response()
    except ExtractionError as exc:
        return error_response(exc.code, exc.message, details=exc.details)
    except ConfigurationError as exc:
        return _configuration_error_response(exc)
    except PermissionError:
        return error_response(
            ErrorCode.PERMISSION_DENIED,
            "Permission was denied while reading the file.",
            details={"path": str(filepath)},
        )
    except OSError:
        return error_response(
            ErrorCode.READ_FAILED,
            "The file could not be read.",
            details={"path": str(filepath)},
        )
    except Exception:
        return _internal_error_response("read_file")


def list_files(
    directory: str,
    extension: str | None = None,
    *,
    workspace_root: str | Path | None = None,
) -> ToolResponse:
    """List regular, non-hidden files in a directory using stable ordering."""

    try:
        config = AppConfig.from_environment()
        root = config.workspace_root if workspace_root is None else workspace_root
        path = validate_directory_path(directory, root)
        normalized_extension = (
            normalize_extension(extension, require_supported=False)
            if extension is not None
            else None
        )

        files: list[dict[str, Any]] = []
        warnings: list[str] = []
        for entry in sorted(path.iterdir(), key=lambda item: item.name.casefold()):
            if entry.name.startswith((".", "~$")) or not entry.is_file():
                continue
            if normalized_extension and entry.suffix.lower() != normalized_extension:
                continue
            try:
                files.append(dict(build_file_metadata(entry)))
            except PathValidationError:
                warnings.append(
                    f"Metadata could not be read for {entry.name}; the file was skipped."
                )

        return success_response(
            {
                "directory": str(path),
                "extension": normalized_extension,
                "count": len(files),
                "files": files,
            },
            warnings=warnings,
        )
    except PathValidationError as exc:
        return exc.to_response()
    except ConfigurationError as exc:
        return _configuration_error_response(exc)
    except PermissionError:
        return error_response(
            ErrorCode.PERMISSION_DENIED,
            "Permission was denied while listing the directory.",
            details={"directory": str(directory)},
        )
    except OSError:
        return error_response(
            ErrorCode.READ_FAILED,
            "The directory could not be listed.",
            details={"directory": str(directory)},
        )
    except Exception:
        return _internal_error_response("list_files")


def write_file(
    filepath: str,
    content: str,
    *,
    workspace_root: str | Path | None = None,
    overwrite: bool = False,
) -> ToolResponse:
    """Atomically write UTF-8 text inside the workspace."""

    temporary_path: Path | None = None
    try:
        if not isinstance(content, str):
            return error_response(
                ErrorCode.INVALID_ARGUMENT,
                "content must be a string.",
                details={"argument": "content"},
            )
        if not isinstance(overwrite, bool):
            return error_response(
                ErrorCode.INVALID_ARGUMENT,
                "overwrite must be a boolean.",
                details={"argument": "overwrite"},
            )

        config = AppConfig.from_environment()
        root = config.workspace_root if workspace_root is None else workspace_root
        path = validate_file_path(
            filepath,
            root,
            must_exist=False,
            require_supported=False,
        )
        destination_existed = path.exists()
        if destination_existed and not overwrite:
            return error_response(
                ErrorCode.FILE_ALREADY_EXISTS,
                "The destination file already exists; enable overwrite to replace it.",
                details={"path": str(filepath)},
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        encoded_content = content.encode("utf-8")
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(encoded_content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        temporary_path.replace(path)
        temporary_path = None

        return success_response(
            {
                "metadata": build_file_metadata(path),
                "bytes_written": len(encoded_content),
                "overwritten": destination_existed,
            }
        )
    except PathValidationError as exc:
        return exc.to_response()
    except ConfigurationError as exc:
        return _configuration_error_response(exc)
    except PermissionError:
        return error_response(
            ErrorCode.PERMISSION_DENIED,
            "Permission was denied while writing the file.",
            details={"path": str(filepath)},
        )
    except OSError:
        return error_response(
            ErrorCode.WRITE_FAILED,
            "The file could not be written.",
            details={"path": str(filepath)},
        )
    except Exception:
        return _internal_error_response("write_file")
    finally:
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)


def search_in_file(
    filepath: str,
    keyword: str,
    *,
    workspace_root: str | Path | None = None,
    context_characters: int | None = None,
    max_matches: int | None = None,
    max_file_size_bytes: int | None = None,
) -> ToolResponse:
    """Search file content literally and case-insensitively with bounded context."""

    try:
        if not isinstance(keyword, str) or not keyword.strip():
            return error_response(
                ErrorCode.INVALID_KEYWORD,
                "keyword must be a non-empty string.",
                details={"argument": "keyword"},
            )

        config = AppConfig.from_environment()
        context_limit = (
            config.search_context_characters if context_characters is None else context_characters
        )
        match_limit = config.max_search_matches if max_matches is None else max_matches
        if (
            not isinstance(context_limit, int)
            or isinstance(context_limit, bool)
            or context_limit < 0
        ):
            return error_response(
                ErrorCode.INVALID_ARGUMENT,
                "context_characters must be a non-negative integer.",
                details={"argument": "context_characters"},
            )
        if not isinstance(match_limit, int) or isinstance(match_limit, bool) or match_limit <= 0:
            return error_response(
                ErrorCode.INVALID_ARGUMENT,
                "max_matches must be a positive integer.",
                details={"argument": "max_matches"},
            )

        read_result = read_file(
            filepath,
            workspace_root=workspace_root,
            max_file_size_bytes=max_file_size_bytes,
        )
        if not read_result["success"]:
            return read_result

        read_data = cast(dict[str, Any], read_result["data"])
        content = cast(str, read_data["content"])
        matches: list[dict[str, Any]] = []
        total_matches = 0
        pattern = re.compile(re.escape(keyword), flags=re.IGNORECASE)
        for match in pattern.finditer(content):
            total_matches += 1
            if len(matches) >= match_limit:
                continue
            context_start = max(0, match.start() - context_limit)
            context_end = min(len(content), match.end() + context_limit)
            matches.append(
                {
                    "match": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "line_number": content.count("\n", 0, match.start()) + 1,
                    "context": content[context_start:context_end],
                }
            )

        warnings = list(read_result["warnings"])
        if total_matches > match_limit:
            warnings.append(f"Results were limited to {match_limit} of {total_matches} matches.")

        return success_response(
            {
                "keyword": keyword,
                "match_count": total_matches,
                "returned_match_count": len(matches),
                "matches": matches,
                "metadata": read_data["metadata"],
            },
            warnings=warnings,
        )
    except ConfigurationError as exc:
        return _configuration_error_response(exc)
    except Exception:
        return _internal_error_response("search_in_file")


def _configuration_error_response(exc: ConfigurationError) -> ToolResponse:
    return error_response(
        ErrorCode.CONFIGURATION_ERROR,
        exc.message,
        details={"field": exc.field},
    )


def _internal_error_response(operation: str) -> ToolResponse:
    return error_response(
        ErrorCode.INTERNAL_ERROR,
        "An unexpected internal error occurred.",
        details={"operation": operation},
    )


__all__ = ["list_files", "read_file", "search_in_file", "write_file"]
