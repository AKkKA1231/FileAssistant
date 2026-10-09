# Project Context

## Product Summary

The LLM-Powered File System Assistant is a Python application that translates natural-language requests into controlled file operations. Its initial domain is resume processing, with support for PDF, TXT, and DOCX files.

## User Need

Resume collections are commonly stored in mixed formats. Finding candidates with a particular skill, reading every document, or generating summaries requires repetitive manual work. The project addresses this problem by combining deterministic file utilities with an LLM that can select those utilities based on user intent.

## Primary Users

- Students demonstrating LLM function calling and tool use.
- Recruiters or hiring-team members working with small local resume collections.
- Developers learning how to expose safe, structured operations to an LLM.

## Core User Journeys

### Inspect a Resume Collection

The user asks the assistant to show resumes in a folder. The assistant calls `list_files`, applies any requested extension filter, and presents file metadata.

### Read Resume Content

The user identifies one or more files. The assistant calls `read_file` for each file and returns or summarizes the extracted content.

### Find Relevant Experience

The user asks for resumes mentioning a skill. The assistant lists appropriate files, calls `search_in_file` for each candidate file, and reports matches with context.

### Produce an Output File

The user requests a summary of a resume. The assistant reads the source, generates the summary, and calls `write_file` to store the result.

## Scope

### In Scope

- Local, text-based file operations.
- PDF, TXT, and DOCX text extraction.
- Non-recursive directory listing for the first release.
- Optional extension filtering.
- Case-insensitive literal keyword search.
- Text-file output with automatic parent-directory creation.
- LLM-driven selection and sequencing of registered tools.
- Structured success and error results.

### Out of Scope for the Initial Release

- Optical character recognition for scanned PDFs.
- Editing PDF or DOCX documents in place.
- Semantic or vector search.
- Remote cloud-storage integrations.
- Multi-user access control and shared workspaces.
- Autonomous deletion, moving, or renaming of files.
- Processing password-protected documents.
- Production-scale indexing of large document collections.

## Assumptions

- The user has legitimate access to the files being processed.
- Resume files are stored within a configured workspace.
- Text-based PDFs contain extractable text.
- The runtime has permission to read input files and write approved outputs.
- An LLM API key is available through environment configuration when live integration is used.
- File names and document content must be treated as untrusted data.

## Constraints

- Tool interfaces must remain simple enough for reliable model invocation.
- The solution must be demonstrable within a short video.
- External API use may introduce cost, latency, rate limits, and transient failures.
- Resume content may contain personal information and must not be logged unnecessarily.
- The model is probabilistic; authorization, path validation, and actual file operations must remain deterministic.

## Success Measures

- Supported documents are parsed consistently.
- Relevant keyword matches are returned with enough context to verify them.
- The model selects the intended tool for the supplied example queries.
- Failures result in clear structured messages rather than process termination.
- A new user can set up and demonstrate the application from the README.

## Related Documents

- `ProblemStatement.md`: source requirements and acceptance criteria.
- `implementation-plan.md`: phased delivery plan.
- `architecture.md`: components and execution flow.
- `edge-cases.md`: expected behavior under unusual conditions.
- `special-strategies.md`: reliability, safety, and testing techniques.
- `role.md`: behavioral contract for the assistant.
- `deployment-plan.md`: packaging and release guidance.
