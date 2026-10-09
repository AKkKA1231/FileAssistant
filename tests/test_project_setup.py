"""Smoke tests for the Phase 1 project foundation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"


class ProjectSetupTests(unittest.TestCase):
    """Verify that the documented foundation is present and importable."""

    def test_required_directories_exist(self) -> None:
        for relative_path in ("Doc", "data/resumes", "output", "src", "tests"):
            with self.subTest(path=relative_path):
                self.assertTrue((PROJECT_ROOT / relative_path).is_dir())

    def test_required_project_files_exist(self) -> None:
        for filename in (".env.example", ".gitignore", "README.md", "pyproject.toml"):
            with self.subTest(file=filename):
                self.assertTrue((PROJECT_ROOT / filename).is_file())

    def test_source_modules_are_importable(self) -> None:
        for module_name in ("fs_tools", "llm_file_assistant"):
            with self.subTest(module=module_name):
                module_path = SRC_DIRECTORY / f"{module_name}.py"
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                self.assertIsNotNone(spec)
                self.assertIsNotNone(spec.loader if spec else None)

    def test_environment_template_has_required_keys(self) -> None:
        template = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
        for key in ("LLM_PROVIDER", "LLM_MODEL", "GROQ_API_KEY", "ASSISTANT_WORKSPACE"):
            with self.subTest(key=key):
                self.assertIn(f"{key}=", template)


if __name__ == "__main__":
    unittest.main()
