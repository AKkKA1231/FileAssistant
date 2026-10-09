# Phase 5 Verification Report

## Scope

Phase 5 adds reproducible fictional resume fixtures, collection-level verification, edge-case coverage, and multi-step assistant tests. All automated tests run without a live Groq request.

## Sample Resume Set

| Format | Files | Coverage Purpose |
|---|---:|---|
| TXT | 3 | UTF-8 extraction, optional sections, and non-Python resumes |
| DOCX | 2 | Paragraph extraction, mixed capitalization, and missing telephone data |
| PDF | 2 | Page extraction, machine-learning content, and lowercase keyword matching |

All identities, employers, schools, telephone numbers, and experience descriptions are fictional. Email addresses use `example.com`, and telephone numbers use the fictional 555 range.

The generator is stored at `scripts/generate_sample_resumes.py`. Automated verification recreates the full set in a temporary directory and confirms that every generated file can be parsed.

## Search Expectations

A case-insensitive search for `python` must match exactly four fixtures:

- `aisha-khan-data-engineer.txt`
- `noah-williams-devops-engineer.docx`
- `ethan-brooks-machine-learning-engineer.pdf`
- `maya-patel-java-engineer.pdf`

The remaining three fixtures must return zero matches.

## Automated Coverage

The final Phase 5 run completed 98 tests with 83 percent statement coverage across `src`.

The test suite verifies:

- TXT, DOCX, and PDF extraction.
- Directory listing and extension filtering.
- Case-insensitive literal search.
- Atomic writes and explicit overwrite behavior.
- Workspace traversal prevention.
- Missing and unsupported files.
- Empty TXT and PDF files.
- Corrupt PDF and DOCX files.
- Password-protected PDF rejection.
- File-size limits and malformed content.
- Strict tool schema validation.
- Unknown tools and malformed JSON arguments.
- Groq response normalization without network calls.
- Multi-turn and multi-tool orchestration.
- Provider errors, repeated calls, and total call limits.
- Prompt-injection isolation instructions.
- An end-to-end list, search, write, and reread workflow.

## Visual Verification

The two DOCX fixtures and two PDF fixtures were rendered to one PNG page each. Every page was inspected at full resolution. The final files have readable typography, consistent section hierarchy, complete content, and no clipping, overlap, broken bullets, or unintended title borders.

The bundled DOCX renderer could not find LibreOffice in the available runtime. Microsoft Word exported the DOCX files to temporary PDFs as a local fallback, and bundled Poppler rasterized those PDFs for inspection. The PDF fixtures were rendered directly with bundled Poppler.

## Commands

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python scripts/generate_sample_resumes.py
```

## Live Provider Verification

A live Groq smoke test completed successfully after local configuration. Groq
selected the directory-listing tool, the application executed it inside the
configured workspace, and the model returned the confirmed file count. The API key
remains local and is excluded from version control.

The regular automated suite continues to use mocked provider responses so tests are
deterministic and do not consume API credits or require network access.
