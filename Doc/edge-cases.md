# Edge Cases and Failure Handling

## Purpose

This document defines expected behavior for boundary conditions and failures. All failures should use structured results with a stable error code, readable message, and relevant details. Normal operational errors must not expose stack traces to end users.

## Path and File-System Cases

| Scenario | Expected Behavior |
|---|---|
| Empty or whitespace-only path | Reject as `INVALID_PATH`. |
| Relative path containing `..` | Resolve it and reject it if it escapes the configured workspace. |
| Path does not exist | Return `FILE_NOT_FOUND` or `DIRECTORY_NOT_FOUND`. |
| Path points to a directory when a file is required | Return `NOT_A_FILE`. |
| Path points to a file when a directory is required | Return `NOT_A_DIRECTORY`. |
| Permission denied | Return `PERMISSION_DENIED` without leaking sensitive host details. |
| Broken symbolic link | Treat it as a missing or invalid path. |
| Symbolic link escapes the workspace | Reject after resolving the canonical path. |
| Very long or platform-invalid path | Return a validation or file-system error. |
| Unicode, spaces, or punctuation in a filename | Process normally without shell interpolation. |
| File changes during processing | Return a read error or document that metadata reflects the completed operation. |

## `read_file` Cases

| Scenario | Expected Behavior |
|---|---|
| Unsupported extension | Return `UNSUPPORTED_FILE_TYPE`. |
| Uppercase extension such as `.PDF` | Normalize and process it. |
| Empty file | Return success with empty content and an explicit empty-content indicator. |
| Binary data renamed as TXT | Return `DECODE_ERROR` if safe decoding fails. |
| Non-UTF-8 TXT | Attempt a documented fallback or return a clear decode error. |
| Corrupt PDF or DOCX | Return `PARSE_ERROR`. |
| Password-protected PDF | Return `ENCRYPTED_FILE_UNSUPPORTED`. |
| Scanned/image-only PDF | Return empty or minimal content with an OCR-not-supported warning. |
| PDF with pages that individually fail | Report a partial-read warning or fail consistently according to policy. |
| DOCX containing tables | Extract table text if supported and document the ordering. |
| Extremely large file | Reject using a configurable size limit before loading it fully. |

## `list_files` Cases

| Scenario | Expected Behavior |
|---|---|
| Empty directory | Return an empty list successfully. |
| Filter provided as `pdf` instead of `.pdf` | Normalize it to `.pdf`. |
| Mixed-case extensions | Match case-insensitively. |
| Unknown extension filter | Return an empty list or validation error according to the documented policy. |
| Directory contains subdirectories | Exclude them from a non-recursive result. |
| Hidden or temporary files | Follow a documented inclusion policy; exclude them by default. |
| File disappears while metadata is read | Skip it with a warning or return an item-level error. |
| Large directory | Use iteration and impose a configurable result limit if necessary. |

## `write_file` Cases

| Scenario | Expected Behavior |
|---|---|
| Parent directory is missing | Create it within the allowed workspace. |
| Target already exists | Follow an explicit overwrite policy; do not overwrite silently if confirmation is required. |
| Empty content | Permit it when intentional and report zero bytes written. |
| Target is read-only | Return `PERMISSION_DENIED`. |
| Disk is full | Return `WRITE_FAILED` with an actionable message. |
| Partial write or interrupted process | Prefer atomic write-then-replace behavior. |
| Destination escapes workspace | Reject as `PATH_OUTSIDE_WORKSPACE`. |
| Content is not a string | Reject as `INVALID_ARGUMENT`. |

## `search_in_file` Cases

| Scenario | Expected Behavior |
|---|---|
| Empty keyword | Reject as `INVALID_KEYWORD`. |
| No matches | Return success with `match_count: 0` and an empty match list. |
| Different capitalization | Match successfully. |
| Keyword contains regex symbols | Treat it literally unless regex search is explicitly introduced. |
| Keyword occurs repeatedly or overlaps | Use a documented overlap policy and cap the number of returned matches. |
| Match is near the start or end | Clamp context boundaries without errors. |
| Match spans extracted line boundaries | Preserve readable context and accurate position information where possible. |
| Source file is unreadable | Propagate the structured `read_file` error. |

## LLM and Tool-Calling Cases

| Scenario | Expected Behavior |
|---|---|
| Model requests an unknown tool | Reject it and ask the model to choose from registered tools. |
| Tool arguments fail schema validation | Return a validation result; never call the tool with unchecked values. |
| Model repeats the same tool call | Stop after a configurable repetition or step limit. |
| Model returns malformed JSON | Retry once if supported, then return a controlled error. |
| Several tool calls are needed | Execute them in a bounded sequence and preserve individual results. |
| LLM API times out or is rate-limited | Retry with bounded exponential backoff, then report failure. |
| User request is ambiguous | Ask a concise clarifying question before writing or processing the wrong target. |
| Tool output is too large for the model | Truncate or chunk content and disclose that behavior. |
| Document contains prompt injection text | Treat document text strictly as data, never as instructions. |

## Privacy and Security Cases

- Do not write API keys, resume content, or full tool payloads to logs by default.
- Redact sensitive details from error messages when they are not required for diagnosis.
- Do not execute commands embedded in filenames, user prompts, or document text.
- Do not allow the model to invent file access outside the configured workspace.
- Use fictional identities and data in all sample resumes.

## Minimum Edge-Case Test Set

Automated tests should include missing paths, unsupported types, empty files, corrupt documents, mixed-case extensions, no-match searches, repeated matches, workspace traversal attempts, write permission failures, malformed tool arguments, and simulated LLM timeouts.
