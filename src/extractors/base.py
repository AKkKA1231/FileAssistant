"""Shared contracts for document text extractors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from contracts import ErrorCode


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """Normalized output returned by every document extractor."""

    content: str
    details: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


class ExtractionError(Exception):
    """A controlled document-extraction failure."""

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


__all__ = ["ExtractionError", "ExtractionResult"]
