"""Plain-text document extraction."""

from __future__ import annotations

from pathlib import Path

from contracts import ErrorCode
from extractors.base import ExtractionError, ExtractionResult


def extract_txt(path: Path) -> ExtractionResult:
    """Extract text using UTF-8 with a documented Windows-1252 fallback."""

    content_bytes = path.read_bytes()
    if b"\x00" in content_bytes:
        raise ExtractionError(
            ErrorCode.DECODE_ERROR,
            "The TXT file appears to contain binary data.",
            details={"path": str(path)},
        )

    warnings: list[str] = []
    try:
        content = content_bytes.decode("utf-8-sig")
        encoding = "utf-8"
    except UnicodeDecodeError:
        try:
            content = content_bytes.decode("cp1252")
            encoding = "cp1252"
            warnings.append("The file was decoded using the Windows-1252 fallback encoding.")
        except UnicodeDecodeError as exc:
            raise ExtractionError(
                ErrorCode.DECODE_ERROR,
                "The TXT file could not be decoded as UTF-8 or Windows-1252.",
                details={"path": str(path)},
            ) from exc

    if not content:
        warnings.append("The file is empty.")

    return ExtractionResult(
        content=content,
        details={"format": "txt", "encoding": encoding},
        warnings=tuple(warnings),
    )


__all__ = ["extract_txt"]
