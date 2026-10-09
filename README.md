# LLM-Powered File System Assistant

A Python command-line assistant that lets a Groq-hosted LLM safely list, read,
search, and write local files through validated tools. The reference use case is
resume analysis across PDF, TXT, and DOCX documents.

> Project status: Phases 1 through 6 are implemented. The repository includes
> seventeen fictional resumes, automated tests, and a two-to-three-minute demo guide.

## Features

- Four structured tools: `read_file`, `list_files`, `write_file`, and
  `search_in_file`.
- Text extraction from PDF, TXT, and DOCX files.
- Strict JSON tool schemas and structured success/error responses.
- Workspace-bound path validation, traversal protection, and explicit overwrite
  control.
- Groq local tool calling with bounded iterations and repeat-call detection.
- Fictional sample resumes and mocked integration tests that do not consume API
  credits.
- A deterministic scope guardrail that rejects unrelated and general-knowledge
  questions before they reach the LLM provider.

## Requirements

- Python 3.11 or newer.
- A Groq API key for live assistant requests.
- A local workspace containing the files the assistant may access.

## Project Structure

```text
.
|-- Doc/                       # Requirements, architecture, contracts, and demo guide
|-- data/
|   |-- resumes/               # Seventeen fictional TXT, DOCX, and PDF resumes
|   `-- output/                # Live assistant output; created on demand and ignored
|-- output/                    # Generated files; contents are ignored by Git
|-- scripts/
|   `-- generate_sample_resumes.py
|-- src/
|   |-- config.py              # Validated environment configuration
|   |-- contracts.py           # Shared response and metadata contracts
|   |-- extractors/            # TXT, PDF, and DOCX extraction adapters
|   |-- fs_tools.py            # Core file-system tools
|   |-- llm_file_assistant.py  # LLM orchestration and CLI entry point
|   |-- path_policy.py         # Workspace-bound path validation
|   |-- providers/             # Provider-neutral contract and Groq adapter
|   `-- tool_registry.py       # Strict schemas, validation, and dispatch
|-- tests/                     # Unit and integration tests
|-- .env.example               # Safe configuration template
|-- pyproject.toml             # Package and tooling configuration
`-- requirements.txt           # Runtime and development dependencies
```

## Installation

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Replace the placeholder `GROQ_API_KEY` in `.env` with a Groq credential. Never
commit or share `.env`; it is excluded by `.gitignore`.

For an editable package install that exposes the `llm-file-assistant` command:

```bash
python -m pip install -e .
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `groq` | Provider identifier; this release supports Groq. |
| `LLM_MODEL` | `openai/gpt-oss-20b` | Groq model used for tool selection and responses. |
| `GROQ_API_KEY` | None | Required only for live assistant requests. |
| `ASSISTANT_WORKSPACE` | `./data` | Root boundary for all file-system tools. |
| `MAX_FILE_SIZE_BYTES` | `10485760` | Maximum readable document size. |
| `MAX_SEARCH_MATCHES` | `100` | Maximum matches returned by one search. |
| `SEARCH_CONTEXT_CHARACTERS` | `120` | Context characters shown around each match. |
| `MAX_TOOL_STEPS` | `10` | Maximum tool calls for one assistant request. |
| `LOG_LEVEL` | `INFO` | Application logging threshold. |

Relative workspace paths are resolved from the directory where the application
starts. See `.env.example` for a ready-to-copy configuration.

## Usage

### Web application

Launch the integrated frontend and API:

```bash
python -m web_app
```

Then open `http://127.0.0.1:8000`. The responsive interface provides the
dashboard, file explorer, safe uploads, document viewer, cross-document search,
and live Groq assistant. Interactive API documentation is available at
`http://127.0.0.1:8000/api/docs`.

After an editable package installation, you can also run:

```bash
filepilot-web
```

### Command-line assistant

Run a one-shot request:

```bash
python -m llm_file_assistant "Find resumes mentioning Python experience"
```

Start an interactive session:

```bash
python -m llm_file_assistant
```

With an editable install, the equivalent command is:

```bash
llm-file-assistant "Read all resumes in the resumes folder"
```

Useful demo requests:

- `List all .txt, .pdf, and .docx files in the resumes folder.`
- `Find every resume mentioning Python, regardless of capitalization.`
- `Read resumes/ethan-brooks-machine-learning-engineer.pdf and summarize the candidate.`
- `Create output/python-candidate-summary.md with a concise summary of the Python candidates.`

The model receives the registered tool definitions and returned document content,
but it never receives unrestricted file-system access. Every requested operation is
validated locally and constrained to `ASSISTANT_WORKSPACE`.

## Direct Tool Usage

The Python API returns the envelope documented in
[`Doc/tool-contracts.md`](Doc/tool-contracts.md).

```python
from fs_tools import list_files, read_file, search_in_file, write_file

files = list_files("resumes", extension="pdf", workspace_root="data")
resume = read_file(
    "resumes/ethan-brooks-machine-learning-engineer.pdf",
    workspace_root="data",
)
matches = search_in_file(
    "resumes/ethan-brooks-machine-learning-engineer.pdf",
    "Python",
    workspace_root="data",
)
summary = write_file(
    "candidate-summary.md",
    "# Candidate Summary\n",
    workspace_root="output",
)
```

`write_file` creates missing parent directories. It refuses to replace an existing
file unless `overwrite=True` is explicitly supplied.

## Supported Files and Behavior

| Format | Extension | Extraction behavior |
|---|---|---|
| Plain text | `.txt` | UTF-8 with Windows-1252 fallback. |
| PDF | `.pdf` | Text extraction by page; image-only PDFs may yield no text. |
| Word document | `.docx` | Paragraph and table text extraction. |

Directory listing is non-recursive. Search is literal, case-insensitive, and
non-overlapping. Hidden files and Microsoft Office temporary files are excluded
from listings.

## Testing and Quality Checks

After installing dependencies, run:

```bash
python -m pytest
python -m pytest --cov=src --cov-report=term-missing
python -m ruff check .
python -m ruff format --check .
python -m pip check
```

Regenerate the fictional sample set with:

```bash
python scripts/generate_sample_resumes.py
```

Automated tests use mocked provider responses and make no network calls. A live
CLI request uses the configured Groq API key and may consume provider quota.

## Limitations

- Only Groq is implemented as a live provider in this release.
- PDF extraction does not perform OCR on scanned or image-only documents.
- Directory listing is intentionally non-recursive.
- Search accepts literal text, not regular expressions or semantic similarity.
- The CLI keeps no persistent conversation history between separate processes.
- Generated summaries should be reviewed before use in hiring decisions.

## Troubleshooting

| Problem | Resolution |
|---|---|
| `GROQ_API_KEY is required` | Set the key in the local `.env` file and launch from the project root. |
| `PATH_OUTSIDE_WORKSPACE` | Use a path inside `ASSISTANT_WORKSPACE`; paths are workspace-relative. |
| `FILE_NOT_FOUND` | Confirm the filename, extension, and workspace root. |
| `UNSUPPORTED_FILE_TYPE` | Use a `.pdf`, `.txt`, or `.docx` input file. |
| PDF returns empty text | The PDF may be scanned; convert it with OCR before using this release. |
| `FILE_ALREADY_EXISTS` | Choose a new path or explicitly request an overwrite. |
| Module import error | Activate the virtual environment and reinstall `requirements.txt` or run `pip install -e .`. |
| Groq provider error | Check network access, key validity, model availability, and account quota. |

## Documentation and Submission

- Start with [`Doc/ProblemStatement.md`](Doc/ProblemStatement.md).
- Review the design in [`Doc/architecture.md`](Doc/architecture.md).
- Inspect exact schemas in [`Doc/tool-contracts.md`](Doc/tool-contracts.md).
- Record the assignment demonstration with [`Doc/demo-guide.md`](Doc/demo-guide.md).
- Use [`Doc/submission-readiness.md`](Doc/submission-readiness.md) before submitting.

## Security Notes

- Never commit `.env`, API credentials, generated output, or private resumes.
- Rotate any credential that has been exposed in chat, logs, screenshots, or Git
  history.
- Treat prompts, paths, filenames, and document content as untrusted input.
- Use fictional data in public demonstrations.
- Do not report a file operation as successful until its tool result confirms it.
