# Demonstration Guide

## Goal

Record a two-to-three-minute demonstration proving that Groq can select and call
the local file-system tools to list, search, read, and write resume content.

## Before Recording

1. Activate the project virtual environment.
2. Install dependencies with `python -m pip install -r requirements.txt`.
3. Confirm `.env` contains a valid `GROQ_API_KEY` and is ignored by Git.
4. Keep the `.env` file and terminal environment variables out of the recording.
5. Run `python -m pytest` and confirm the suite passes.
6. Remove any existing `data/output/python-candidate-summary.md`, or use a fresh
   output filename. The assistant intentionally refuses silent overwrites.

## Suggested Recording Script

### 0:00-0:20 — Introduce the project

Show the repository tree and briefly state:

- The assistant uses Groq function calling.
- All actual file access stays local.
- Supported resume formats are PDF, TXT, and DOCX.
- Operations are restricted to the configured `data` workspace.

### 0:20-0:50 — List files

Run:

```powershell
python -m llm_file_assistant "List all .txt, .pdf, and .docx files in the resumes folder, group them by extension, and report the total."
```

Point out that the response comes from filtered `list_files` calls and includes the
seventeen fictional fixtures. The directory also contains a documentation README, which
is intentionally excluded by the requested extension filters.

### 0:50-1:25 — Search across varied formats

Run:

```powershell
python -m llm_file_assistant "Find every resume in the resumes folder that mentions Python, ignoring capitalization."
```

The expected matching files are:

- `aisha-khan-data-engineer.txt`
- `ethan-brooks-machine-learning-engineer.pdf`
- `maya-patel-java-engineer.pdf`
- `noah-williams-devops-engineer.docx`

This demonstrates case-insensitive extraction and search across all three formats.

### 1:25-1:55 — Read and summarize

Run:

```powershell
python -m llm_file_assistant "Read resumes/ethan-brooks-machine-learning-engineer.pdf and give me a three-bullet summary grounded only in the resume."
```

Show that the answer is based on text returned by `read_file`.

### 1:55-2:30 — Create a summary file

Run:

```powershell
python -m llm_file_assistant "Create output/python-candidate-summary.md containing a short Markdown summary of the resumes that mention Python."
```

Because the configured workspace is `./data`, this creates
`data/output/python-candidate-summary.md`. Open the generated file and show its
content. Mention that writes create parent directories and require explicit
permission to overwrite an existing file.

### 2:30-2:50 — Close with verification

Show the test command and summarize the safeguards:

```powershell
python -m pytest
```

- Strict schemas reject malformed tool calls.
- Canonical path checks prevent workspace escape.
- Tool and repeat limits prevent unbounded loops.
- `.env` and generated output are excluded from version control.

## Recording Checklist

- The API key is never visible.
- The terminal begins in the repository root.
- Commands and responses are readable at the recorded resolution.
- All four required operations appear: list, search, read, and write.
- The final video is between two and three minutes.
- The video link is accessible to the evaluator without requesting permission.

## Fallback

If the live provider is unavailable during recording, show the passing mocked
integration tests and explain the outage. Re-record the live calls before final
submission; mocked tests alone do not demonstrate live Groq tool selection.
