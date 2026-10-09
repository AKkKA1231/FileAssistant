# Groq Integration

## Overview

The assistant uses Groq Chat Completions with local function calling. Groq decides when a registered tool is needed, while all file access and tool execution remain inside the local Python application.

## Configuration

```dotenv
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-20b
GROQ_API_KEY=<set-locally>
ASSISTANT_WORKSPACE=./data
MAX_TOOL_STEPS=10
```

`GROQ_API_KEY` must be stored in the local `.env` file or operating-system environment. It must never be committed to version control.

## Request Flow

1. The CLI submits the system instruction, user request, and four function schemas to Groq.
2. Groq either returns a final text response or one or more structured tool calls.
3. The application parses each call and validates its name and arguments through `ToolRegistry`.
4. The selected local function executes within `ASSISTANT_WORKSPACE`.
5. The structured result is serialized as a `tool` message using the matching `tool_call_id`.
6. Groq receives the updated conversation and either requests another tool or returns the final answer.

## Registered Tools

- `read_file`
- `list_files`
- `write_file`
- `search_in_file`

The provider cannot supply internal options such as `workspace_root` or file-size limits. The application injects those trusted values after validating public arguments.

## Safety Controls

- Unknown tools are rejected.
- Missing, malformed, incorrectly typed, or additional arguments are rejected.
- Model-generated paths remain subject to canonical workspace-boundary validation.
- Identical calls are limited to prevent loops.
- Total tool calls are capped by `MAX_TOOL_STEPS`.
- Tool errors are returned to the model as structured data instead of terminating the process.
- Document contents are treated as untrusted data and cannot authorize actions.
- Existing files require an explicit `overwrite` argument, and the system prompt permits it only when requested by the user.

## Provider Isolation

`providers/base.py` defines the provider-neutral interface used by the orchestrator. `providers/groq_provider.py` contains Groq SDK behavior and converts Groq responses into normalized assistant turns. This keeps tool execution and orchestration independent of provider-specific response classes.

## Testing Policy

Automated tests use fake provider responses and do not make network calls. They verify multi-turn execution, matching call identifiers, malformed JSON handling, unknown arguments, provider errors, repeated calls, and step limits. A live smoke test is optional and should be run only when a valid local API key is configured.
