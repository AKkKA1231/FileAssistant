"""Route-level tests for the local FilePilot web application."""

from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

import pytest
from fastapi.responses import FileResponse, JSONResponse

import web_app
from contracts import success_response


@pytest.fixture
def web_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    workspace = tmp_path / "workspace"
    resumes = workspace / "resumes"
    resumes.mkdir(parents=True)
    (resumes / "candidate.txt").write_text(
        "Candidate Example\nSkills: Python, SQL\nExperience: Five years",
        encoding="utf-8",
    )
    (resumes / "README.md").write_text("Not a supported resume", encoding="utf-8")
    monkeypatch.setenv("ASSISTANT_WORKSPACE", str(workspace))
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    return workspace


def _run(coroutine: Coroutine[Any, Any, JSONResponse]) -> JSONResponse:
    return asyncio.run(coroutine)


def _payload(response: JSONResponse) -> dict[str, Any]:
    return json.loads(bytes(response.body))


def test_health_never_exposes_api_key(web_workspace: Path) -> None:
    del web_workspace
    response = _run(web_app.health())

    assert response.status_code == 200
    payload = _payload(response)
    assert payload["data"]["api_configured"] is True
    assert "test-key" not in bytes(response.body).decode()


def test_list_files_excludes_unsupported_documents(web_workspace: Path) -> None:
    del web_workspace
    response = _run(web_app.files(directory="resumes", extension=None))

    assert response.status_code == 200
    payload = _payload(response)
    assert payload["data"]["count"] == 1
    assert payload["data"]["files"][0]["path"] == "resumes/candidate.txt"
    assert str(Path.cwd()) not in bytes(response.body).decode()


def test_read_rejects_workspace_traversal(web_workspace: Path) -> None:
    del web_workspace
    response = _run(web_app.read(filepath="../secret.txt"))

    assert response.status_code == 403
    assert _payload(response)["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"


def test_raw_file_returns_original_pdf_inline(
    web_workspace: Path,
) -> None:
    pdf = web_workspace / "resumes" / "candidate.pdf"
    original = b"%PDF-1.4\noriginal document bytes\n%%EOF"
    pdf.write_bytes(original)

    response = _run(web_app.raw_file(filepath="resumes/candidate.pdf"))

    assert isinstance(response, FileResponse)
    assert Path(response.path).read_bytes() == original
    assert response.media_type == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline;")


def test_raw_file_rejects_workspace_traversal(web_workspace: Path) -> None:
    del web_workspace
    response = _run(web_app.raw_file(filepath="../secret.pdf"))

    assert isinstance(response, JSONResponse)
    assert response.status_code == 403
    assert _payload(response)["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"


def test_cross_document_search_returns_literal_matches(web_workspace: Path) -> None:
    del web_workspace
    response = _run(web_app.search(directory="resumes", keyword="python"))

    assert response.status_code == 200
    data = _payload(response)["data"]
    assert data["files_checked"] == 1
    assert data["matching_files"] == 1
    assert data["total_matches"] == 1
    assert data["results"][0]["metadata"]["path"] == "resumes/candidate.txt"


def test_upload_validates_type_and_prevents_silent_overwrite(web_workspace: Path) -> None:
    del web_workspace
    encoded = base64.b64encode(b"New candidate").decode("ascii")
    request = web_app.UploadRequest(filename="new-candidate.txt", content_base64=encoded)
    first = _run(web_app.upload(request))
    duplicate = _run(web_app.upload(request))
    unsupported = _run(
        web_app.upload(web_app.UploadRequest(filename="script.html", content_base64=encoded))
    )

    assert first.status_code == 201
    assert _payload(first)["data"]["metadata"]["path"] == "resumes/new-candidate.txt"
    assert duplicate.status_code == 409
    assert unsupported.status_code == 400
    assert _payload(unsupported)["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_write_endpoint_uses_structured_conflict(web_workspace: Path) -> None:
    del web_workspace
    request = web_app.WriteRequest(filepath="output/summary.md", content="# Summary")
    first = _run(web_app.write(request))
    second = _run(web_app.write(request))

    assert first.status_code == 200
    assert _payload(first)["data"]["metadata"]["path"] == "output/summary.md"
    assert second.status_code == 409


def test_assistant_endpoint_uses_bounded_assistant(
    web_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del web_workspace

    class FakeAssistant:
        def ask(self, query: str) -> dict[str, Any]:
            return success_response({"response": f"Confirmed: {query}", "tool_calls_executed": 1})

    monkeypatch.setattr(web_app, "build_assistant", lambda config: FakeAssistant())
    response = _run(web_app.assistant(web_app.AssistantRequest(query="List resumes")))

    assert response.status_code == 200
    assert _payload(response)["data"]["response"] == "Confirmed: List resumes"


def test_static_frontend_files_exist(web_workspace: Path) -> None:
    del web_workspace
    index = web_app.WEB_ROOT / "index.html"
    script = web_app.WEB_ROOT / "app.js"
    stylesheet = web_app.WEB_ROOT / "styles.css"

    assert index.is_file()
    assert script.is_file()
    assert stylesheet.is_file()
    assert "FilePilot Workspace Assistant" in index.read_text(encoding="utf-8")
    assert 'id="theme-toggle"' in index.read_text(encoding="utf-8")
    assert "filepilot-theme" in script.read_text(encoding="utf-8")
    assert ':root[data-theme="dark"]' in stylesheet.read_text(encoding="utf-8")
