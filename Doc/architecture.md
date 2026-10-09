# System Architecture

## Architectural Style

Use a layered architecture that separates user interaction, LLM orchestration, deterministic tool execution, document extraction, and file-system access. Dependencies should point inward toward stable domain contracts rather than outward toward a particular LLM provider.

## Component View

```text
User / CLI
    |
    v
Assistant Orchestrator
    |-- Provider Adapter --------> LLM API
    |<-- validated tool request --|
    |
    v
Tool Registry and Argument Validation
    |
    +--> list_files
    +--> read_file -----> Document Extractors
    +--> search_in_file -^    |-- TXT
    +--> write_file           |-- PDF
                              `-- DOCX
    |
    v
Workspace-Safe File-System Layer
    |
    v
Local Input and Output Files
```

## Major Components

### User Interface

Accepts natural-language requests and displays final responses. A command-line interface is sufficient for the initial release and demo.

### Assistant Orchestrator

Maintains the conversation loop, sends tool schemas to the LLM, receives tool requests, dispatches validated calls, supplies results back to the LLM, and enforces step and retry limits.

### Provider Adapter

Encapsulates authentication and the request/response format of the selected LLM provider. It should expose a provider-neutral method to the orchestrator.

### Tool Registry

Maps approved external tool names to implementations. It rejects unknown tool names and validates arguments against schemas before execution.

### File-System Tools

Expose the assignment's four public operations. These functions return structured values and do not depend on the LLM SDK.

### Document Extractors

Provide one extraction implementation per supported format. TXT uses controlled decoding, PDF uses a PDF parsing library, and DOCX uses a DOCX parsing library. Extractors return normalized text plus warnings or parsing metadata.

### Path Policy

Resolves paths, enforces the configured workspace boundary, checks file types and extensions, and provides safe metadata. Both reads and writes pass through this policy.

## Proposed Module Structure

```text
src/
|-- __init__.py
|-- config.py
|-- contracts.py
|-- fs_tools.py
|-- llm_file_assistant.py
|-- tool_registry.py
|-- path_policy.py
|-- providers/
|   |-- __init__.py
|   |-- base.py
|   `-- groq_provider.py
`-- extractors/
    |-- __init__.py
    |-- txt_extractor.py
    |-- pdf_extractor.py
    `-- docx_extractor.py
```

If assignment grading expects `fs_tools.py` and `llm_file_assistant.py` at the repository root, keep thin compatibility entry points there or adopt the required layout explicitly in the README.

## Core Data Contracts

### Success Result

```json
{
  "success": true,
  "data": {
    "content": "...",
    "metadata": {}
  },
  "error": null,
  "warnings": []
}
```

### Error Result

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "FILE_NOT_FOUND",
    "message": "The requested file does not exist.",
    "details": {}
  },
  "warnings": []
}
```

## Main Execution Flows

### Read a File

1. The user asks to read a resume.
2. The LLM requests `read_file` with a path.
3. The registry validates the arguments.
4. The path policy verifies the resolved path.
5. The correct extractor returns text and metadata.
6. The tool result is passed to the model for presentation.

### Search a Folder

1. The LLM calls `list_files` with the folder and optional extension.
2. The orchestrator calls `search_in_file` for each supported candidate within configured limits.
3. Each search reuses the shared extraction pipeline.
4. The LLM summarizes confirmed matches and identifies source files.

### Create a Summary File

1. The LLM calls `read_file` for the source resume.
2. The model generates a summary from returned content.
3. The LLM calls `write_file` with the approved destination and summary.
4. The assistant reports success only after the write result confirms it.

## Security Boundaries

- The LLM cannot directly access the operating system.
- Only registered tools may perform file actions.
- Canonical-path validation guards the workspace boundary.
- Document content is untrusted data and cannot authorize new actions.
- API credentials come from environment configuration and are never passed into tool output.

## Non-Functional Requirements

- Testability: tool code must run without a live LLM.
- Maintainability: provider and parser dependencies remain isolated.
- Reliability: operations use structured errors and bounded retries.
- Portability: use `pathlib` and avoid platform-specific shell commands.
- Observability: record safe operational metrics without resume content.
- Extensibility: new file extractors and model providers can be added behind existing interfaces.

## Architecture Decisions

1. Use direct Python function calls rather than shell commands for file operations.
2. Keep tools stateless; pass paths and content explicitly.
3. Reuse extraction logic for both reading and searching.
4. Keep folder listing non-recursive in the first release.
5. Use literal keyword search initially; semantic search is a future enhancement.
6. Use an explicit tool registry instead of dynamic function lookup.
