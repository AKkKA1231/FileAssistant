"""Tests for workspace path validation and metadata generation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from contracts import ErrorCode
from path_policy import (
    SUPPORTED_EXTENSIONS,
    PathValidationError,
    build_file_metadata,
    normalize_extension,
    resolve_workspace_path,
    validate_directory_path,
    validate_file_path,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("pdf", ".pdf"), (" .TXT ", ".txt"), (".DoCx", ".docx")],
)
def test_normalize_supported_extension(value: str, expected: str) -> None:
    assert normalize_extension(value) == expected


def test_supported_extensions_are_explicit() -> None:
    assert frozenset({".pdf", ".txt", ".docx"}) == SUPPORTED_EXTENSIONS


@pytest.mark.parametrize("value", ["", "   ", ".tar.gz", "../pdf", "doc x"])
def test_normalize_extension_rejects_malformed_values(value: str) -> None:
    with pytest.raises(PathValidationError) as error:
        normalize_extension(value)

    assert error.value.code is ErrorCode.INVALID_ARGUMENT


def test_normalize_extension_rejects_unsupported_type() -> None:
    with pytest.raises(PathValidationError) as error:
        normalize_extension(".csv")

    assert error.value.code is ErrorCode.UNSUPPORTED_FILE_TYPE


def test_normalize_extension_can_allow_other_well_formed_types() -> None:
    assert normalize_extension("csv", require_supported=False) == ".csv"


def test_resolve_workspace_path_resolves_relative_path(tmp_path: Path) -> None:
    resolved = resolve_workspace_path("resumes/candidate.txt", tmp_path)

    assert resolved == (tmp_path / "resumes" / "candidate.txt").resolve()


def test_resolve_workspace_path_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(PathValidationError) as error:
        resolve_workspace_path("../outside.txt", tmp_path)

    assert error.value.code is ErrorCode.PATH_OUTSIDE_WORKSPACE
    assert error.value.to_response()["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"


def test_resolve_workspace_path_rejects_empty_value(tmp_path: Path) -> None:
    with pytest.raises(PathValidationError) as error:
        resolve_workspace_path(" ", tmp_path)

    assert error.value.code is ErrorCode.INVALID_PATH


def test_validate_file_path_and_build_metadata(tmp_path: Path) -> None:
    resume = tmp_path / "Candidate.PDF"
    resume.write_bytes(b"sample")

    validated = validate_file_path("Candidate.PDF", tmp_path)
    metadata = build_file_metadata(validated)

    assert validated == resume.resolve()
    assert metadata["name"] == "Candidate.PDF"
    assert metadata["extension"] == ".pdf"
    assert metadata["size_bytes"] == 6
    assert Path(metadata["path"]) == resume.resolve()
    assert datetime.fromisoformat(metadata["modified_at"]).tzinfo is not None


def test_validate_file_path_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(PathValidationError) as error:
        validate_file_path("missing.txt", tmp_path)

    assert error.value.code is ErrorCode.FILE_NOT_FOUND


def test_validate_file_path_rejects_directory(tmp_path: Path) -> None:
    directory = tmp_path / "resume.txt"
    directory.mkdir()

    with pytest.raises(PathValidationError) as error:
        validate_file_path(directory, tmp_path)

    assert error.value.code is ErrorCode.NOT_A_FILE


def test_validate_new_file_path_for_write(tmp_path: Path) -> None:
    path = validate_file_path("output/summary.txt", tmp_path, must_exist=False)

    assert path == (tmp_path / "output" / "summary.txt").resolve()


def test_validate_directory_path_rejects_file(tmp_path: Path) -> None:
    file_path = tmp_path / "resume.txt"
    file_path.write_text("sample", encoding="utf-8")

    with pytest.raises(PathValidationError) as error:
        validate_directory_path(file_path, tmp_path)

    assert error.value.code is ErrorCode.NOT_A_DIRECTORY


def test_validate_directory_path_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(PathValidationError) as error:
        validate_directory_path("missing", tmp_path)

    assert error.value.code is ErrorCode.DIRECTORY_NOT_FOUND
