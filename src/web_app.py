"""Local FastAPI application for the FilePilot web interface."""

from __future__ import annotations

import asyncio
import base64
import binascii
import os
import tempfile
from pathlib import Path
from typing import Any, cast

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from config import AppConfig, ConfigurationError
from contracts import ErrorCode, ToolResponse, error_response, success_response
from fs_tools import list_files, read_file, search_in_file, write_file
from llm_file_assistant import build_assistant
from path_policy import (
    SUPPORTED_EXTENSIONS,
    PathValidationError,
    build_file_metadata,
    normalize_extension,
    validate_file_path,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "web"
MAX_WEB_QUERY_LENGTH = 2_000
MAX_SEARCH_FILES = 100

app = FastAPI(
    title="FilePilot Workspace Assistant",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
)


class WriteRequest(BaseModel):
    """Validated text-write request."""

    model_config = ConfigDict(populate_by_name=True)

    filepath: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=1_000_000)
    overwrite: bool = False


class AssistantRequest(BaseModel):
    """Validated assistant query."""

    query: str = Field(min_length=1, max_length=MAX_WEB_QUERY_LENGTH)


class UploadRequest(BaseModel):
    """A browser file encoded as base64."""

    filename: str = Field(min_length=1, max_length=255)
    content_base64: str = Field(min_length=1)
    overwrite: bool = False


@app.get("/api/health")
async def health() -> JSONResponse:
    """Return non-secret runtime status for the frontend."""

    try:
        config = _config()
    except ConfigurationError as exc:
        return _json_response(
            error_response(
                ErrorCode.CONFIGURATION_ERROR,
                exc.message,
                details={"field": exc.field},
            )
        )
    return _json_response(
        success_response(
            {
                "status": "ready",
                "provider": config.llm_provider,
                "model": config.llm_model,
                "api_configured": bool(config.groq_api_key),
                "workspace": config.workspace_root.name,
                "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
            }
        )
    )


@app.get("/api/files")
async def files(
    directory: str = Query(default="resumes", min_length=1, max_length=500),
    extension: str | None = Query(default=None, max_length=20),
) -> JSONResponse:
    """List supported documents without exposing absolute server paths."""

    try:
        config = _config()
        normalized = normalize_extension(extension) if extension else None
    except (ConfigurationError, PathValidationError) as exc:
        return _exception_response(exc)

    result = list_files(directory, extension=normalized, workspace_root=config.workspace_root)
    if not result["success"]:
        return _json_response(result)

    data = cast(dict[str, Any], result["data"])
    visible_files = [
        _public_metadata(item, config.workspace_root)
        for item in data["files"]
        if item["extension"] in SUPPORTED_EXTENSIONS
    ]
    data.update(
        {
            "directory": directory,
            "count": len(visible_files),
            "files": visible_files,
        }
    )
    return _json_response(result)


@app.get("/api/files/read")
async def read(filepath: str = Query(min_length=1, max_length=500)) -> JSONResponse:
    """Extract one supported document."""

    try:
        config = _config()
    except ConfigurationError as exc:
        return _exception_response(exc)
    result = read_file(filepath, workspace_root=config.workspace_root)
    if result["success"]:
        data = cast(dict[str, Any], result["data"])
        data["metadata"] = _public_metadata(data["metadata"], config.workspace_root)
    return _json_response(result)


@app.get("/api/files/raw")
async def raw_file(
    filepath: str = Query(min_length=1, max_length=500),
) -> Response:
    """Return an original supported document from the bounded workspace."""

    try:
        config = _config()
        path = validate_file_path(filepath, config.workspace_root)
    except (ConfigurationError, PathValidationError) as exc:
        return _exception_response(exc)

    media_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain; charset=utf-8",
    }
    return FileResponse(
        path,
        media_type=media_types[path.suffix.lower()],
        filename=path.name,
        content_disposition_type="inline",
    )


@app.get("/api/search")
async def search(
    keyword: str = Query(min_length=1, max_length=200),
    directory: str = Query(default="resumes", min_length=1, max_length=500),
) -> JSONResponse:
    """Search all supported documents in a non-recursive directory."""

    if not keyword.strip():
        return _json_response(
            error_response(ErrorCode.INVALID_KEYWORD, "Search text cannot be blank.")
        )
    try:
        config = _config()
    except ConfigurationError as exc:
        return _exception_response(exc)

    listing = list_files(directory, workspace_root=config.workspace_root)
    if not listing["success"]:
        return _json_response(listing)
    listing_data = cast(dict[str, Any], listing["data"])
    candidates = [
        item for item in listing_data["files"] if item["extension"] in SUPPORTED_EXTENSIONS
    ]
    warnings = list(listing["warnings"])
    if len(candidates) > MAX_SEARCH_FILES:
        warnings.append(f"Only the first {MAX_SEARCH_FILES} supported files were searched.")
        candidates = candidates[:MAX_SEARCH_FILES]

    matched_files: list[dict[str, Any]] = []
    failed_files: list[dict[str, str]] = []
    total_matches = 0
    for item in candidates:
        relative_path = _relative_path(item["path"], config.workspace_root)
        result = search_in_file(
            relative_path,
            keyword,
            workspace_root=config.workspace_root,
        )
        if not result["success"]:
            error = result["error"] or {}
            failed_files.append(
                {
                    "path": relative_path,
                    "code": str(error.get("code", ErrorCode.INTERNAL_ERROR.value)),
                }
            )
            continue
        data = cast(dict[str, Any], result["data"])
        if data["match_count"]:
            total_matches += data["match_count"]
            matched_files.append(
                {
                    "metadata": _public_metadata(data["metadata"], config.workspace_root),
                    "match_count": data["match_count"],
                    "matches": data["matches"],
                    "warnings": result["warnings"],
                }
            )

    if failed_files:
        warnings.append(f"{len(failed_files)} file(s) could not be searched.")
    return _json_response(
        success_response(
            {
                "keyword": keyword,
                "directory": directory,
                "files_checked": len(candidates),
                "matching_files": len(matched_files),
                "total_matches": total_matches,
                "results": matched_files,
                "failed_files": failed_files,
            },
            warnings=warnings,
        )
    )


@app.post("/api/files/write")
async def write(request: WriteRequest) -> JSONResponse:
    """Write a UTF-8 text file inside the configured workspace."""

    try:
        config = _config()
    except ConfigurationError as exc:
        return _exception_response(exc)
    result = write_file(
        request.filepath,
        request.content,
        workspace_root=config.workspace_root,
        overwrite=request.overwrite,
    )
    if result["success"]:
        data = cast(dict[str, Any], result["data"])
        data["metadata"] = _public_metadata(data["metadata"], config.workspace_root)
    return _json_response(result)


@app.post("/api/files/upload")
async def upload(request: UploadRequest) -> JSONResponse:
    """Upload one supported document into the resume directory."""

    try:
        config = _config()
        if Path(request.filename).name != request.filename or request.filename in {".", ".."}:
            return _json_response(
                error_response(
                    ErrorCode.INVALID_PATH,
                    "Upload filename must not contain directory components.",
                )
            )
        normalize_extension(Path(request.filename).suffix)
        try:
            content = base64.b64decode(request.content_base64, validate=True)
        except (binascii.Error, ValueError):
            return _json_response(
                error_response(ErrorCode.INVALID_ARGUMENT, "Upload content is not valid base64.")
            )
        if not content:
            return _json_response(
                error_response(ErrorCode.INVALID_ARGUMENT, "Uploaded files cannot be empty.")
            )
        if len(content) > config.max_file_size_bytes:
            return _json_response(
                error_response(
                    ErrorCode.FILE_TOO_LARGE,
                    "The uploaded file exceeds the configured size limit.",
                    details={"max_file_size_bytes": config.max_file_size_bytes},
                )
            )
        relative_path = f"resumes/{request.filename}"
        destination = validate_file_path(
            relative_path,
            config.workspace_root,
            must_exist=False,
        )
        existed = destination.exists()
        if existed and not request.overwrite:
            return _json_response(
                error_response(
                    ErrorCode.FILE_ALREADY_EXISTS,
                    "A file with this name already exists.",
                    details={"path": relative_path},
                )
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            temporary_path.replace(destination)
        finally:
            temporary_path.unlink(missing_ok=True)
        metadata = _public_metadata(build_file_metadata(destination), config.workspace_root)
        return _json_response(
            success_response(
                {
                    "metadata": metadata,
                    "bytes_written": len(content),
                    "overwritten": existed,
                }
            ),
            success_status=201,
        )
    except (ConfigurationError, PathValidationError) as exc:
        return _exception_response(exc)
    except OSError:
        return _json_response(
            error_response(ErrorCode.WRITE_FAILED, "The uploaded file could not be saved.")
        )


@app.post("/api/assistant")
async def assistant(request: AssistantRequest) -> JSONResponse:
    """Run one bounded Groq assistant request without blocking the event loop."""

    if not request.query.strip():
        return _json_response(
            error_response(ErrorCode.INVALID_ARGUMENT, "Assistant query cannot be blank.")
        )
    try:
        runtime_assistant = build_assistant(_config())
    except ConfigurationError as exc:
        return _exception_response(exc)
    result = await asyncio.to_thread(runtime_assistant.ask, request.query)
    return _json_response(result)


def _config() -> AppConfig:
    return AppConfig.from_environment(base_directory=PROJECT_ROOT)


def _relative_path(raw_path: str, workspace_root: Path) -> str:
    path = Path(raw_path).resolve(strict=False)
    return path.relative_to(workspace_root.resolve(strict=False)).as_posix()


def _public_metadata(metadata: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    public = dict(metadata)
    public["path"] = _relative_path(str(metadata["path"]), workspace_root)
    return public


def _exception_response(exc: ConfigurationError | PathValidationError) -> JSONResponse:
    if isinstance(exc, PathValidationError):
        return _json_response(exc.to_response())
    return _json_response(
        error_response(
            ErrorCode.CONFIGURATION_ERROR,
            exc.message,
            details={"field": exc.field},
        )
    )


def _json_response(result: ToolResponse, *, success_status: int = 200) -> JSONResponse:
    status = success_status if result["success"] else _error_status(result)
    return JSONResponse(content=result, status_code=status)


def _error_status(result: ToolResponse) -> int:
    error = result["error"] or {}
    code = error.get("code")
    if code in {ErrorCode.FILE_NOT_FOUND.value, ErrorCode.DIRECTORY_NOT_FOUND.value}:
        return 404
    if code == ErrorCode.FILE_ALREADY_EXISTS.value:
        return 409
    if code in {ErrorCode.FILE_TOO_LARGE.value}:
        return 413
    if code in {ErrorCode.PERMISSION_DENIED.value, ErrorCode.PATH_OUTSIDE_WORKSPACE.value}:
        return 403
    if code == ErrorCode.PROVIDER_ERROR.value:
        return 502
    if code == ErrorCode.INTERNAL_ERROR.value:
        return 500
    return 400


def run() -> None:
    """Launch the local web application."""

    load_dotenv(PROJECT_ROOT / ".env")
    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=False)


if WEB_ROOT.is_dir():
    app.mount("/", StaticFiles(directory=WEB_ROOT, html=True), name="frontend")


if __name__ == "__main__":
    run()


__all__ = ["app", "run"]
