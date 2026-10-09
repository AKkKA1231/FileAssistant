# Implementation Plan

## Implementation Status

| Phase | Status |
|---|---|
| Phase 1: Project Foundation | Complete |
| Phase 2: Shared Contracts and Validation | Complete |
| Phase 3: Core File-System Tools | Complete |
| Phase 4: LLM Tool Integration | Complete; mocked integration and live Groq smoke test verified |
| Phase 5: Test Data and Verification | Complete |
| Phase 6: Documentation and Demonstration | Implementation complete; video recording and GitHub URL remain external submission tasks |

## Purpose

This plan translates the requirements in `ProblemStatement.md` into an incremental delivery path for the LLM-Powered File System Assistant.

## Delivery Approach

Build the deterministic file-system layer first, validate it independently, and add LLM orchestration only after the underlying tools are reliable. Each phase must leave the project in a testable state.

## Phase 1: Project Foundation

1. Create the project structure:

   ```text
   .
   |-- Doc/
   |-- data/resumes/
   |-- output/
   |-- src/
   |   |-- fs_tools.py
   |   `-- llm_file_assistant.py
   |-- tests/
   |-- .env.example
   |-- .gitignore
   |-- README.md
   `-- requirements.txt
   ```

2. Select a supported Python version and document it in `README.md`.
3. Define dependencies for PDF extraction, DOCX extraction, environment configuration, LLM access, and testing.
4. Add configuration through environment variables; never commit API keys.
5. Establish formatting, linting, and test commands.

### Exit Criteria

- The environment can be installed from `requirements.txt`.
- Tests can be discovered and run.
- Secrets and generated outputs are excluded from version control.

## Phase 2: Shared Contracts and Validation

1. Define consistent success and error response schemas.
2. Define file metadata fields: name, path, extension, byte size, and modified timestamp.
3. Normalize file extensions and paths in one shared validation layer.
4. Define supported formats as `.pdf`, `.txt`, and `.docx`.
5. Add safe path-handling rules and actionable error codes.

### Exit Criteria

- Every tool follows a documented response contract.
- Invalid arguments fail predictably without uncaught exceptions.

## Phase 3: Core File-System Tools

### `read_file`

1. Validate that the path exists and points to a regular file.
2. Dispatch extraction by normalized extension.
3. Decode TXT files safely, extract text from PDF pages, and extract DOCX paragraphs.
4. Return extracted content and metadata.
5. Return structured errors for unsupported, inaccessible, corrupt, or empty files.

### `list_files`

1. Validate the directory.
2. Normalize the optional extension filter.
3. Return regular files only, with stable ordering and metadata.
4. Specify whether traversal is non-recursive; use non-recursive behavior for the initial release.

### `write_file`

1. Validate the destination and content.
2. Create missing parent directories.
3. Write UTF-8 text.
4. Return the final path and bytes written.
5. Prevent accidental writes outside the configured workspace.

### `search_in_file`

1. Reuse `read_file` instead of duplicating extraction logic.
2. Perform literal, case-insensitive matching.
3. Return match count, position or line information, and bounded surrounding context.
4. Return a successful result with zero matches when appropriate.

### Exit Criteria

- Unit tests cover successful operations and failure paths for all four tools.
- PDF, TXT, and DOCX samples are parsed correctly.

## Phase 4: LLM Tool Integration

1. Define strict JSON schemas for all tool arguments.
2. Create a registry mapping public tool names to Python functions.
3. Implement the conversation loop:
   - Send the user request and tool schemas to the model.
   - Validate each requested tool call.
   - Execute only registered tools.
   - Return serialized tool results to the model.
   - Repeat until the model returns a final response or the step limit is reached.
4. Add a maximum tool-call count to prevent unbounded loops.
5. Separate provider-specific API code from tool execution.
6. Prevent the model from directly accessing the file system outside the tools.

### Exit Criteria

- Representative natural-language requests invoke the correct tools.
- Invalid model-generated arguments are rejected safely.
- Tool failures are explained without crashing the session.

## Phase 5: Test Data and Verification

1. Create five to ten fictional resumes across PDF, TXT, and DOCX.
2. Include varied skills, capitalization, file sizes, and documents with missing fields.
3. Add unit tests for each tool and integration tests for multi-step requests.
4. Test the scenarios listed in `edge-cases.md`.
5. Add mocked LLM tests so most tests do not require network access or API cost.

### Exit Criteria

- All automated tests pass.
- Sample queries produce correct, reproducible results.
- Test data contains no real personal information.

## Phase 6: Documentation and Demonstration

1. Complete the README with installation, configuration, examples, limitations, and troubleshooting.
2. Document response schemas and supported file types.
3. Prepare a two-to-three-minute demo covering listing, searching, reading, and summary creation.
4. Confirm the repository contains the required deliverables and excludes secrets.

## Recommended Work Order

| Priority | Work Item | Depends On |
|---|---|---|
| 1 | Project setup and contracts | None |
| 2 | Path validation and metadata utilities | Project setup |
| 3 | `list_files` and `write_file` | Validation utilities |
| 4 | `read_file` extractors | Validation utilities |
| 5 | `search_in_file` | `read_file` |
| 6 | Unit and integration tests | Core tools |
| 7 | LLM orchestration | Stable tool contracts |
| 8 | Documentation and demo | Verified application |

## Definition of Done

- All acceptance criteria in `ProblemStatement.md` are satisfied.
- Tool behavior and errors are covered by automated tests.
- LLM calls use validated, registered tool interfaces.
- Documentation enables a new developer to install and run the project.
- The demo and GitHub repository are ready for submission.
