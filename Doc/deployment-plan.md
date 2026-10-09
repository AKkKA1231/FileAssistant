# Deployment Plan

## Deployment Objective

Package the assistant as a reproducible Python command-line application suitable for local demonstration and GitHub submission. The initial deployment target is a developer or evaluator workstation, not a public multi-user service.

## Target Environment

- A documented supported Python version.
- Windows, macOS, or Linux with standard local file access.
- Network access for live LLM requests.
- An environment variable containing the selected provider's API key.
- A configured local workspace containing sample resumes and an output directory.

## Packaging Requirements

The repository should include:

```text
.
|-- Doc/
|-- data/resumes/
|-- output/
|-- src/
|-- tests/
|-- .env.example
|-- .gitignore
|-- LICENSE                 # if applicable
|-- README.md
|-- requirements.txt
`-- pyproject.toml          # recommended for tooling and package metadata
```

Pin direct dependency versions for the submitted release, or use bounded compatible versions and retain a tested lock file. Keep development-only tooling separate when practical.

## Environment Configuration

Document variables in `.env.example` without real secrets:

```dotenv
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-20b
GROQ_API_KEY=<set-locally>
ASSISTANT_WORKSPACE=./data
MAX_FILE_SIZE_BYTES=10485760
MAX_TOOL_STEPS=10
LOG_LEVEL=INFO
```

Validate required configuration during startup. The application should explain which variable is missing without displaying any secret values.

## Release Pipeline

### 1. Pre-Release Validation

- Install dependencies in a clean virtual environment.
- Run formatting and lint checks.
- Run the full automated test suite.
- Verify parsing against all sample PDF, TXT, and DOCX files.
- Run mocked end-to-end tool-calling scenarios.
- Run a small live-provider smoke test when credentials are available.
- Scan the repository for secrets and real personal data.

### 2. Build and Version

- Assign a semantic version, beginning with `0.1.0` for the initial submission.
- Record the supported Python version and tested operating systems.
- Generate or verify dependency artifacts.
- Tag the verified commit used for the demo.

### 3. Local Installation Verification

From a clean checkout:

1. Create and activate a virtual environment.
2. Install from `requirements.txt`.
3. Copy `.env.example` to a local `.env` or export variables manually.
4. Add the API key locally.
5. Run tests.
6. Start the assistant and execute the documented example prompts.

### 4. Demo Preparation

Use fictional sample resumes and demonstrate:

1. Listing resumes in the sample folder.
2. Finding resumes that mention Python.
3. Reading one selected resume.
4. Creating and verifying a summary file.
5. Showing one graceful failure, such as an unsupported extension or missing file.

Keep the recorded workflow between two and three minutes and avoid displaying keys, unrelated files, or personal information.

### 5. Publication

- Push the verified source and documentation to the submission repository.
- Confirm the default branch contains all deliverables.
- Add the demo video or a durable video link according to submission constraints.
- Confirm repository visibility matches evaluator requirements.
- Test the README instructions from the published repository.

## Operational Checks

### Startup Check

- Configuration is valid.
- Workspace exists and is accessible.
- Output path is writable.
- Required parser packages import successfully.
- Provider credentials are present for live mode.

### Runtime Check

- Tool calls remain within the configured workspace.
- Retry and step limits are enforced.
- Logs contain operation status but not resume content or credentials.
- Errors are returned in the standard response envelope.

## Rollback Plan

For a local application, rollback consists of checking out the previous tagged release and reinstalling its dependencies in a fresh virtual environment. User-created output files should remain separate from application source so a rollback does not remove them.

## Security Checklist

- No API keys or `.env` files are committed.
- Sample resumes contain fictional data only.
- Paths are resolved and checked against the workspace root.
- Writes use an explicit overwrite policy.
- Dependencies are reviewed for known vulnerabilities.
- Logs omit document content by default.
- Document text is treated as untrusted input.

## Release Acceptance Criteria

- Clean installation succeeds from documented instructions.
- Automated tests pass in the target environment.
- Required example prompts work end to end.
- The application handles at least one representative failure gracefully.
- The repository contains source, dependencies, sample data, documentation, demo evidence, and the required GitHub link.
