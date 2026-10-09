# Problem Statement: LLM-Powered File System Assistant

## Background

Reviewing resume files manually is time-consuming, especially when the files use different formats or are distributed across folders. Users need a reliable way to ask natural-language questions about local resume collections and have an AI assistant perform the necessary file operations safely and accurately.

## Problem

Develop a Python-based, LLM-powered file system assistant that can read, list, write, and search local files through structured tool calls. The assistant must support common resume formats, return consistent and useful results, handle invalid inputs and file-system errors gracefully, and allow an integrated large language model to select and invoke the correct tools in response to user requests.

The completed system should allow users to perform tasks such as:

- Reading all resumes in a specified folder.
- Finding resumes that mention a skill such as Python.
- Creating a summary file from a selected resume.

## Functional Requirements

### 1. Core File System Tools

Create a Python module named `fs_tools.py` that provides the following functions.

#### `read_file(filepath: str) -> dict`

- Read resume files in PDF, TXT, and DOCX formats.
- Extract the text content from each supported file.
- Return a structured dictionary containing the extracted content and relevant metadata.
- Handle missing files, unsupported formats, permission problems, parsing failures, and other errors gracefully.

#### `list_files(directory: str, extension: str = None) -> list`

- List files in a specified directory.
- Optionally filter files by extension, such as `.pdf` or `.txt`.
- Return metadata for each file, including its name, size, and last-modified date.
- Handle invalid or inaccessible directories gracefully.

#### `write_file(filepath: str, content: str) -> dict`

- Write text content to the specified file.
- Create missing parent directories when necessary.
- Return a structured success or failure response.
- Report write and permission errors clearly.

#### `search_in_file(filepath: str, keyword: str) -> dict`

- Search a supported file's extracted content for a keyword.
- Perform the search without case sensitivity.
- Return every match together with useful surrounding context.
- Return a structured response when there are no matches or when the file cannot be searched.

### 2. LLM Integration

Create a Python module named `llm_file_assistant.py` that:

- Integrates the file-system tools with an LLM provider, such as OpenAI or Anthropic.
- Exposes the tools to the model through structured function or tool definitions.
- Parses and validates tool arguments before execution.
- Allows the model to choose the appropriate tool or sequence of tools from a user's natural-language request.
- Returns clear, user-friendly results based on tool output.
- Handles model, validation, and tool-execution errors gracefully.

## Quality and Safety Requirements

- Use clear, maintainable Python with suitable type hints and documentation.
- Use consistent structured response formats for successful operations and errors.
- Validate file paths, extensions, and required arguments before processing.
- Preserve useful metadata throughout file operations.
- Avoid unhandled exceptions during normal use.

## Required Deliverables

The project submission must include:

1. Documented source code for `fs_tools.py` and `llm_file_assistant.py`.
2. A `requirements.txt` file listing all required dependencies.
3. Five to ten dummy resume files for demonstration and testing.
4. A `README.md` file containing setup, configuration, and usage instructions.
5. A two-to-three-minute demo video showing LLM tool calling in action.
6. A GitHub repository link containing the completed project.

## Acceptance Criteria

The solution is complete when:

- PDF, TXT, and DOCX resumes can be read and converted into text.
- Directory contents can be listed and filtered by extension with correct metadata.
- Files can be written successfully, including when parent directories do not yet exist.
- Keywords can be found case-insensitively with surrounding context.
- The LLM can select and invoke the appropriate tools for representative user queries.
- Invalid inputs and operational failures produce structured, understandable error responses.
- All required source code, documentation, sample data, dependency declarations, demo video, and repository link are provided.

## Expected Outcome

The final product should demonstrate practical understanding of LLM function calling, structured tool interfaces, programmatic file I/O, document parsing and validation, and the orchestration of these capabilities through a conversational assistant.
