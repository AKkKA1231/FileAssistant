"""PDF text extraction."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from contracts import ErrorCode
from extractors.base import ExtractionError, ExtractionResult


def extract_pdf(path: Path) -> ExtractionResult:
    """Extract text from each PDF page while preserving partial-read warnings."""

    try:
        reader = PdfReader(path, strict=False)
        if reader.is_encrypted and not reader.decrypt(""):
            raise ExtractionError(
                ErrorCode.ENCRYPTED_FILE_UNSUPPORTED,
                "Password-protected PDF files are not supported.",
                details={"path": str(path)},
            )

        page_text: list[str] = []
        warnings: list[str] = []
        failed_pages: list[int] = []
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                page_text.append(page.extract_text() or "")
            except Exception:  # A malformed page must not discard readable pages.
                page_text.append("")
                failed_pages.append(page_number)

        if failed_pages:
            warnings.append(
                "Text could not be extracted from page(s): "
                + ", ".join(str(page) for page in failed_pages)
                + "."
            )

        content = "\n\n".join(page_text)
        if not content.strip():
            warnings.append("No extractable text was found; the PDF may be empty or image-based.")

        return ExtractionResult(
            content=content,
            details={"format": "pdf", "page_count": len(reader.pages)},
            warnings=tuple(warnings),
        )
    except ExtractionError:
        raise
    except PdfReadError as exc:
        raise ExtractionError(
            ErrorCode.PARSE_ERROR,
            "The PDF file is corrupt or could not be parsed.",
            details={"path": str(path)},
        ) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise ExtractionError(
            ErrorCode.PARSE_ERROR,
            "The PDF file could not be parsed.",
            details={"path": str(path)},
        ) from exc


__all__ = ["extract_pdf"]
