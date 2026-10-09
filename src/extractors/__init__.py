"""Format-specific document extraction dispatcher."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from contracts import ErrorCode
from extractors.base import ExtractionError, ExtractionResult
from extractors.docx_extractor import extract_docx
from extractors.pdf_extractor import extract_pdf
from extractors.txt_extractor import extract_txt

Extractor = Callable[[Path], ExtractionResult]
_EXTRACTORS: dict[str, Extractor] = {
    ".docx": extract_docx,
    ".pdf": extract_pdf,
    ".txt": extract_txt,
}


def extract_text(path: Path) -> ExtractionResult:
    """Dispatch a validated file to its format-specific extractor."""

    extractor = _EXTRACTORS.get(path.suffix.lower())
    if extractor is None:
        raise ExtractionError(
            ErrorCode.UNSUPPORTED_FILE_TYPE,
            f"Unsupported file extension: {path.suffix.lower() or '<none>'}",
            details={"path": str(path), "supported": sorted(_EXTRACTORS)},
        )
    return extractor(path)


__all__ = ["ExtractionError", "ExtractionResult", "extract_text"]
