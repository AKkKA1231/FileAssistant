"""Verification for the fictional multi-format resume fixture set."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from fs_tools import list_files, read_file, search_in_file
from scripts.generate_sample_resumes import generate_all
from tool_registry import ToolRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESUME_DIRECTORY = PROJECT_ROOT / "data" / "resumes"

EXPECTED_RESUMES = {
    "aisha-khan-data-engineer.txt": "Aisha Khan",
    "liam-chen-frontend-developer.txt": "Liam Chen",
    "sofia-martinez-project-coordinator.txt": "Sofia Martinez",
    "noah-williams-devops-engineer.docx": "Noah Williams",
    "priya-sharma-business-analyst.docx": "Priya Sharma",
    "ethan-brooks-machine-learning-engineer.pdf": "Ethan Brooks",
    "maya-patel-java-engineer.pdf": "Maya Patel",
    "olivia-reed-clinical-nurse.txt": "Olivia Reed",
    "marcus-green-financial-analyst.txt": "Marcus Green",
    "emma-wilson-digital-marketing-manager.txt": "Emma Wilson",
    "aarav-mehta-hospitality-operations-manager.txt": "Aarav Mehta",
    "zoe-turner-cybersecurity-analyst.docx": "Zoe Turner",
    "daniel-kim-secondary-teacher.docx": "Daniel Kim",
    "leila-hassan-ux-designer.docx": "Leila Hassan",
    "victor-alvarez-compliance-specialist.pdf": "Victor Alvarez",
    "grace-okafor-supply-chain-manager.pdf": "Grace Okafor",
    "lucas-morgan-renewable-energy-engineer.pdf": "Lucas Morgan",
}

PYTHON_MATCHES = {
    "aisha-khan-data-engineer.txt",
    "noah-williams-devops-engineer.docx",
    "ethan-brooks-machine-learning-engineer.pdf",
    "maya-patel-java-engineer.pdf",
}


def _data(response: dict[str, Any]) -> dict[str, Any]:
    assert response["success"] is True
    return cast(dict[str, Any], response["data"])


def test_fixture_set_contains_seventeen_resumes_in_all_supported_formats() -> None:
    fixture_names = {
        path.name
        for path in RESUME_DIRECTORY.iterdir()
        if path.suffix.lower() in {".pdf", ".txt", ".docx"}
    }

    assert set(EXPECTED_RESUMES) <= fixture_names
    assert sum(name.endswith(".txt") for name in EXPECTED_RESUMES) == 7
    assert sum(name.endswith(".docx") for name in EXPECTED_RESUMES) == 5
    assert sum(name.endswith(".pdf") for name in EXPECTED_RESUMES) == 5


def test_generator_recreates_readable_fixture_set(tmp_path: Path) -> None:
    generated = generate_all(tmp_path / "resumes")

    assert {path.name for path in generated} == set(EXPECTED_RESUMES)
    for path in generated:
        result = read_file(path.name, workspace_root=path.parent)
        assert result["success"] is True
        assert _data(result)["content"].strip()


@pytest.mark.parametrize(("filename", "candidate_name"), EXPECTED_RESUMES.items())
def test_every_sample_resume_can_be_read(filename: str, candidate_name: str) -> None:
    result = read_file(filename, workspace_root=RESUME_DIRECTORY)
    data = _data(result)

    assert candidate_name in data["content"]
    assert len(data["content"].strip()) > 100
    assert data["metadata"]["size_bytes"] > 0
    assert "@example.com" in data["content"]


def test_python_search_matches_expected_resumes_case_insensitively() -> None:
    matched: set[str] = set()
    for filename in EXPECTED_RESUMES:
        result = search_in_file(filename, "python", workspace_root=RESUME_DIRECTORY)
        if _data(result)["match_count"]:
            matched.add(filename)

    assert matched == PYTHON_MATCHES


def test_kubernetes_search_finds_devops_and_security_experience() -> None:
    matched: set[str] = set()
    for filename in EXPECTED_RESUMES:
        result = search_in_file(filename, "KUBERNETES", workspace_root=RESUME_DIRECTORY)
        if _data(result)["match_count"]:
            matched.add(filename)

    assert matched == {
        "noah-williams-devops-engineer.docx",
        "zoe-turner-cybersecurity-analyst.docx",
    }


def test_fixture_set_includes_documents_with_missing_optional_sections() -> None:
    sofia = _data(
        read_file("sofia-martinez-project-coordinator.txt", workspace_root=RESUME_DIRECTORY)
    )
    priya = _data(read_file("priya-sharma-business-analyst.docx", workspace_root=RESUME_DIRECTORY))

    assert "EDUCATION" not in sofia["content"].upper()
    assert "+1" not in priya["content"]


def test_format_filtered_listing_returns_correct_counts() -> None:
    assert _data(list_files(".", "txt", workspace_root=RESUME_DIRECTORY))["count"] >= 7
    assert _data(list_files(".", "docx", workspace_root=RESUME_DIRECTORY))["count"] >= 5
    assert _data(list_files(".", "pdf", workspace_root=RESUME_DIRECTORY))["count"] >= 5


def test_end_to_end_list_search_write_and_read_workflow(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    resumes = workspace / "resumes"
    resumes.mkdir(parents=True)
    (resumes / "candidate-a.txt").write_text("Python and SQL", encoding="utf-8")
    (resumes / "candidate-b.txt").write_text("TypeScript and React", encoding="utf-8")
    registry = ToolRegistry(workspace)

    listed = _data(registry.execute("list_files", {"directory": "resumes", "extension": "txt"}))
    matching_names: list[str] = []
    for metadata in listed["files"]:
        searched = _data(
            registry.execute(
                "search_in_file",
                {"filepath": f"resumes/{metadata['name']}", "keyword": "Python"},
            )
        )
        if searched["match_count"]:
            matching_names.append(metadata["name"])

    summary_content = "Python matches:\n" + "\n".join(matching_names)
    written = registry.execute(
        "write_file",
        {"filepath": "output/python-matches.txt", "content": summary_content},
    )
    reread = registry.execute("read_file", {"filepath": "output/python-matches.txt"})

    assert written["success"] is True
    assert _data(reread)["content"] == "Python matches:\ncandidate-a.txt"
