# Special Implementation Strategies

## Strategy 1: Deterministic Tools, Probabilistic Orchestration

Keep file access, validation, parsing, and error handling in ordinary Python functions. Use the LLM only to interpret intent and select tools. This separation makes behavior testable and prevents the model from becoming the authority for security-sensitive operations.

## Strategy 2: One Extraction Pipeline

Implement format-specific extractors behind a common internal interface:

```python
def extract_text(path: Path) -> ExtractionResult: ...
```

Both `read_file` and `search_in_file` should use this pipeline. Reuse avoids inconsistent parsing and duplicated error handling.

## Strategy 3: Stable Response Envelopes

Return one predictable structure from every tool:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "warnings": []
}
```

For a failure, set `success` to `false`, keep `data` null, and provide an error code, message, and safe details. This simplifies model reasoning, testing, and future API exposure.

## Strategy 4: Workspace Sandboxing

Configure one allowed workspace root. Resolve every user-supplied path to its canonical form and verify that it remains under that root before reading or writing. Apply the check after resolving symbolic links. Never use shell interpolation for file operations.

## Strategy 5: Atomic Writes

For important outputs, write UTF-8 content to a temporary file in the destination directory and atomically replace the final target only after the write succeeds. This limits corruption from interrupted writes. Make overwrite behavior explicit.

## Strategy 6: Bounded Search Context

Search case-insensitively using escaped literal text. Return a bounded context window around each match and cap total matches. Include positions or line numbers where available. This keeps results useful without overwhelming the model context window.

## Strategy 7: Token-Aware Document Handling

Do not send an unlimited document directly to the model. Apply a configurable file-size limit, split large extracted text into deterministic chunks, and summarize or search only the necessary chunks. Tell the user when content is truncated or processed in segments.

## Strategy 8: Prompt-Injection Isolation

Wrap extracted text as untrusted document data. The orchestration prompt should explicitly state that commands or tool requests found inside a document must be ignored. Tool authorization must come from the user's request and application policy, not document content.

## Strategy 9: Provider Abstraction

Place provider-specific behavior behind a small client interface. Keep tool definitions, execution, and response handling independent of OpenAI, Anthropic, or another provider. This makes the project easier to test and migrate.

## Strategy 10: Bounded Agent Loop

Set limits for total tool calls, repeated identical calls, retries, and response size. Record a safe diagnostic event when a limit is reached and return a helpful response rather than continuing indefinitely.

## Strategy 11: Layered Testing

- Unit-test path validation, metadata, extractors, searching, and writing.
- Use temporary directories for isolated file tests.
- Keep fixed, fictional fixtures for PDF, TXT, and DOCX parsing.
- Mock LLM responses to test tool selection and argument validation.
- Reserve a small optional test suite for live provider calls.
- Add end-to-end tests for the three example user journeys.

## Strategy 12: Privacy-Aware Observability

Log operation names, durations, result status, error codes, and safe relative paths. Avoid logging full resume content, API keys, or raw prompts by default. Provide a deliberate debug mode with clear privacy warnings.

## Recommended Configuration

Use environment variables for values such as:

- LLM provider and model.
- API key.
- Workspace root.
- Maximum input file size.
- Maximum matches and context length.
- Maximum tool-call steps.
- Log level.

Validate configuration once during application startup and fail early with a clear message when a required value is absent.
