# Tool Contracts

## Purpose

This document defines the stable data contract shared by every public file-system tool. Tool implementations may add operation-specific fields inside `data`, but they must not change the top-level response envelope.

## Success Response

```json
{
  "success": true,
  "data": {},
  "error": null,
  "warnings": []
}
```

- `success` is `true` only when the requested operation completed.
- `data` contains the operation-specific result.
- `error` is always `null` on success.
- `warnings` contains non-fatal conditions, including partial extraction or empty text.

## Error Response

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "FILE_NOT_FOUND",
    "message": "The requested file does not exist.",
    "details": {
      "path": "resumes/missing.pdf"
    }
  },
  "warnings": []
}
```

- `success` is `false` for a failed operation.
- `data` is always `null` on failure.
- `error.code` is a stable machine-readable value.
- `error.message` is safe and understandable to a user.
- `error.details` contains structured diagnostic context and must not contain secrets.

## File Metadata

Every file listing or read result uses these fields:

| Field | Type | Description |
|---|---|---|
| `name` | string | Base filename, including its extension. |
| `path` | string | Canonical path accepted by the application. |
| `extension` | string | Lowercase extension with a leading dot. |
| `size_bytes` | integer | File size in bytes. |
| `modified_at` | string | Timezone-aware ISO 8601 modification timestamp in UTC. |

## Supported Extensions

The initial release supports `.pdf`, `.txt`, and `.docx`. Extension input is trimmed, lowercased, and given a leading dot when omitted. Malformed or unsupported extensions return a controlled validation failure.

## Path Policy

- Relative paths are resolved against the configured workspace root.
- Absolute paths are accepted only when they remain inside the workspace.
- Canonical resolution is applied before the workspace boundary check.
- Empty paths and traversal outside the workspace are rejected.
- A read path must exist and have the expected file-system type.
- A write target may be absent, but its resolved location must remain in the workspace.
- Symbolic links are evaluated through canonical resolution to prevent boundary escapes.

## Validation Errors

Internal validators raise `PathValidationError`, which includes an `ErrorCode`, a safe message, and structured details. Public tools catch this exception and convert it with `to_response()` so validation failures never become uncaught user-facing exceptions.

Core path-related codes include:

- `INVALID_ARGUMENT`
- `INVALID_PATH`
- `PATH_OUTSIDE_WORKSPACE`
- `FILE_NOT_FOUND`
- `DIRECTORY_NOT_FOUND`
- `NOT_A_FILE`
- `NOT_A_DIRECTORY`
- `UNSUPPORTED_FILE_TYPE`
- `PERMISSION_DENIED`

Parsing, file operations, orchestration, and provider failures have additional codes defined in `src/contracts.py`.

## Core Tool Results

### `read_file`

Returns `content`, standard file `metadata`, and format-specific `extraction` details. TXT files use UTF-8 with a Windows-1252 fallback. PDF results include page count, and DOCX results include paragraph and table counts.

Arguments:

```json
{
  "filepath": "resumes/example.pdf"
}
```

Representative result data:

```json
{
  "content": "Extracted document text",
  "metadata": {
    "name": "example.pdf",
    "path": "resumes/example.pdf",
    "extension": ".pdf",
    "size_bytes": 2048,
    "modified_at": "2026-10-07T08:30:00+00:00"
  },
  "extraction": {
    "format": "pdf",
    "page_count": 1
  }
}
```

### `list_files`

Returns the canonical `directory`, normalized extension filter, result `count`, and a stably sorted `files` array. Listing is non-recursive and excludes dotfiles and Office temporary files beginning with `~$`.

Arguments:

```json
{
  "directory": "resumes",
  "extension": ".docx"
}
```

`extension` is optional. Each item in `files` follows the standard metadata schema.

### `write_file`

Returns destination `metadata`, `bytes_written`, and whether an existing file was `overwritten`. Writes are UTF-8 and use a temporary file followed by atomic replacement. Existing files require `overwrite=True`.

Arguments:

```json
{
  "filepath": "summaries/example.md",
  "content": "# Candidate Summary\n\nSummary text.",
  "overwrite": false
}
```

`overwrite` is optional and defaults to `false`. The public tool writes text; it
does not create binary PDF or DOCX output.

### `search_in_file`

Returns the `keyword`, total `match_count`, `returned_match_count`, source metadata, and bounded `matches`. Each match contains the exact matched text, start and end character offsets, one-based line number, and surrounding context. Search is literal, case-insensitive, non-overlapping, and capped by configuration.

Arguments:

```json
{
  "filepath": "resumes/example.pdf",
  "keyword": "Python"
}
```

Representative match:

```json
{
  "matched_text": "python",
  "start": 148,
  "end": 154,
  "line": 8,
  "context": "Built production services with python and SQL."
}
```

No matches is a successful operation with `match_count` and
`returned_match_count` set to zero.

## Provider-Facing Validation

The LLM may supply only the arguments shown above. All schemas set
`additionalProperties` to `false`; internal controls such as `workspace_root`,
file-size limits, context length, and match limits are injected by trusted local
code. Unknown tool names, invalid JSON, missing values, extra values, and incorrect
types produce structured errors rather than invoking a function.
