"""Tests for shared tool response contracts."""

from __future__ import annotations

from contracts import ErrorCode, error_response, success_response


def test_success_response_uses_consistent_envelope() -> None:
    response = success_response({"value": 42}, warnings=["example warning"])

    assert response == {
        "success": True,
        "data": {"value": 42},
        "error": None,
        "warnings": ["example warning"],
    }


def test_error_response_uses_machine_readable_code() -> None:
    response = error_response(
        ErrorCode.FILE_NOT_FOUND,
        "The requested file does not exist.",
        details={"path": "missing.txt"},
    )

    assert response["success"] is False
    assert response["data"] is None
    assert response["error"] == {
        "code": "FILE_NOT_FOUND",
        "message": "The requested file does not exist.",
        "details": {"path": "missing.txt"},
    }
    assert response["warnings"] == []


def test_response_builders_copy_mutable_inputs() -> None:
    warnings = ["first"]
    details = {"path": "resume.pdf"}

    success = success_response({}, warnings=warnings)
    failure = error_response(ErrorCode.READ_FAILED, "Read failed.", details=details)
    warnings.append("second")
    details["path"] = "changed.pdf"

    assert success["warnings"] == ["first"]
    assert failure["error"] is not None
    assert failure["error"]["details"] == {"path": "resume.pdf"}
