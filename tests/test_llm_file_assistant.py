"""Tests for the bounded provider-neutral tool-calling loop."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from config import AppConfig, ConfigurationError
from llm_file_assistant import FileAssistant, build_assistant, is_query_in_scope
from providers import ChatMessage, ProviderError, ProviderTurn, ToolCallRequest
from tool_registry import ToolRegistry


class FakeProvider:
    """Return predefined turns and retain request messages for assertions."""

    def __init__(self, turns: list[ProviderTurn | Exception]) -> None:
        self.turns = list(turns)
        self.requests: list[list[ChatMessage]] = []
        self.tool_schemas: list[list[dict[str, Any]]] = []

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
    ) -> ProviderTurn:
        self.requests.append([dict(message) for message in messages])
        self.tool_schemas.append(tools)
        next_turn = self.turns.pop(0)
        if isinstance(next_turn, Exception):
            raise next_turn
        return next_turn


def _final_turn(content: str) -> ProviderTurn:
    return ProviderTurn(
        content=content,
        tool_calls=(),
        assistant_message={"role": "assistant", "content": content},
    )


def _tool_turn(call_id: str, name: str, arguments: str) -> ProviderTurn:
    tool_call = ToolCallRequest(id=call_id, name=name, arguments=arguments)
    return ProviderTurn(
        content=None,
        tool_calls=(tool_call,),
        assistant_message={
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": arguments},
                }
            ],
        },
    )


def _data(response: dict[str, Any]) -> dict[str, Any]:
    assert response["success"] is True
    return cast(dict[str, Any], response["data"])


def _error(response: dict[str, Any]) -> dict[str, Any]:
    assert response["success"] is False
    return cast(dict[str, Any], response["error"])


def test_direct_model_answer_requires_no_tool_calls(tmp_path: Path) -> None:
    provider = FakeProvider([_final_turn("How can I help?")])
    assistant = FileAssistant(provider, ToolRegistry(tmp_path))

    data = _data(assistant.ask("What can you do with resume files?"))

    assert data == {
        "response": "How can I help?",
        "tool_calls_executed": 0,
        "iterations": 1,
    }
    assert {item["function"]["name"] for item in provider.tool_schemas[0]} == {
        "read_file",
        "list_files",
        "write_file",
        "search_in_file",
    }


def test_tool_result_is_returned_to_model_with_matching_call_id(tmp_path: Path) -> None:
    (tmp_path / "resume.txt").write_text("Python", encoding="utf-8")
    provider = FakeProvider(
        [
            _tool_turn("call-1", "read_file", '{"filepath":"resume.txt"}'),
            _final_turn("The resume mentions Python."),
        ]
    )
    assistant = FileAssistant(provider, ToolRegistry(tmp_path))

    data = _data(assistant.ask("Read the resume"))
    tool_message = provider.requests[1][-1]
    tool_result = json.loads(tool_message["content"])

    assert data["response"] == "The resume mentions Python."
    assert data["tool_calls_executed"] == 1
    assert tool_message["role"] == "tool"
    assert tool_message["tool_call_id"] == "call-1"
    assert tool_result["success"] is True
    assert tool_result["data"]["content"] == "Python"


def test_multi_step_folder_search_executes_list_then_parallel_searches(tmp_path: Path) -> None:
    resumes = tmp_path / "resumes"
    resumes.mkdir()
    (resumes / "candidate-a.txt").write_text("Python", encoding="utf-8")
    (resumes / "candidate-b.txt").write_text("Java", encoding="utf-8")
    search_arguments_a = '{"filepath":"resumes/candidate-a.txt","keyword":"Python"}'
    search_arguments_b = '{"filepath":"resumes/candidate-b.txt","keyword":"Python"}'
    search_calls = (
        ToolCallRequest("call-2", "search_in_file", search_arguments_a),
        ToolCallRequest("call-3", "search_in_file", search_arguments_b),
    )
    provider = FakeProvider(
        [
            _tool_turn("call-1", "list_files", '{"directory":"resumes","extension":"txt"}'),
            ProviderTurn(
                content=None,
                tool_calls=search_calls,
                assistant_message={
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {"name": call.name, "arguments": call.arguments},
                        }
                        for call in search_calls
                    ],
                },
            ),
            _final_turn("candidate-a.txt mentions Python."),
        ]
    )
    assistant = FileAssistant(provider, ToolRegistry(tmp_path))

    data = _data(assistant.ask("Find TXT resumes that mention Python"))

    assert data["tool_calls_executed"] == 3
    assert data["iterations"] == 3
    assert data["response"] == "candidate-a.txt mentions Python."
    assert [message["tool_call_id"] for message in provider.requests[2][-2:]] == [
        "call-2",
        "call-3",
    ]


def test_invalid_tool_arguments_are_reported_to_model(tmp_path: Path) -> None:
    provider = FakeProvider(
        [
            _tool_turn("call-bad", "read_file", "{invalid}"),
            _final_turn("I could not read the file because the arguments were invalid."),
        ]
    )
    assistant = FileAssistant(provider, ToolRegistry(tmp_path))

    response = assistant.ask("Read a file")
    tool_result = json.loads(provider.requests[1][-1]["content"])

    assert response["success"] is True
    assert tool_result["error"]["code"] == "TOOL_ARGUMENT_ERROR"


def test_provider_error_becomes_structured_failure(tmp_path: Path) -> None:
    provider = FakeProvider([ProviderError("Groq unavailable.", status_code=503)])
    assistant = FileAssistant(provider, ToolRegistry(tmp_path))

    error = _error(assistant.ask("List files"))

    assert error["code"] == "PROVIDER_ERROR"
    assert error["details"] == {"status_code": 503}


def test_repeated_tool_call_stops_loop(tmp_path: Path) -> None:
    repeated = _tool_turn("call-1", "list_files", '{"directory":"."}')
    provider = FakeProvider([repeated, repeated])
    assistant = FileAssistant(
        provider,
        ToolRegistry(tmp_path),
        max_tool_calls=4,
        max_repeated_calls=1,
    )

    error = _error(assistant.ask("List files forever"))

    assert error["code"] == "TOOL_STEP_LIMIT_REACHED"
    assert error["details"]["reason"] == "repeated tool call detected"
    assert error["details"]["tool_calls_executed"] == 1


def test_total_tool_call_limit_stops_loop(tmp_path: Path) -> None:
    provider = FakeProvider(
        [
            _tool_turn("call-1", "list_files", '{"directory":"."}'),
            _tool_turn("call-2", "list_files", '{"directory":".","extension":"txt"}'),
        ]
    )
    assistant = FileAssistant(provider, ToolRegistry(tmp_path), max_tool_calls=1)

    error = _error(assistant.ask("Keep listing workspace files"))

    assert error["code"] == "TOOL_STEP_LIMIT_REACHED"
    assert error["details"]["reason"] == "tool-call limit reached"


def test_empty_query_is_rejected_without_provider_call(tmp_path: Path) -> None:
    provider = FakeProvider([])
    assistant = FileAssistant(provider, ToolRegistry(tmp_path))

    error = _error(assistant.ask("  "))

    assert error["code"] == "INVALID_ARGUMENT"
    assert provider.requests == []


@pytest.mark.parametrize(
    "query",
    [
        "List all resume files.",
        "Find candidates mentioning Kubernetes.",
        "Summarize resumes/example.pdf.",
        "What skills are present in this document?",
        "How does this project read DOCX files?",
    ],
)
def test_project_queries_are_in_scope(query: str) -> None:
    assert is_query_in_scope(query) is True


@pytest.mark.parametrize(
    "query",
    [
        "Who is Donald Trump?",
        "Who is Donal Trumph?",
        "What is the weather today?",
        "Write a poem about the ocean.",
        "Tell me the latest political news.",
        "Hello",
    ],
)
def test_unrelated_queries_are_out_of_scope(query: str) -> None:
    assert is_query_in_scope(query) is False


def test_out_of_scope_query_is_rejected_before_provider_call(tmp_path: Path) -> None:
    provider = FakeProvider([_final_turn("This should never be used.")])
    assistant = FileAssistant(provider, ToolRegistry(tmp_path))

    error = _error(assistant.ask("Who is Donald Trump?"))

    assert error["code"] == "QUERY_OUT_OF_SCOPE"
    assert error["details"] == {"allowed_scope": "workspace files and resume analysis"}
    assert provider.requests == []


def test_empty_provider_answer_is_rejected(tmp_path: Path) -> None:
    provider = FakeProvider([_final_turn("")])
    assistant = FileAssistant(provider, ToolRegistry(tmp_path))

    assert _error(assistant.ask("Summarize the resume file"))["code"] == "PROVIDER_ERROR"


def test_build_assistant_requires_groq_provider(tmp_path: Path) -> None:
    config = AppConfig.from_environment(
        {
            "LLM_PROVIDER": "other",
            "GROQ_API_KEY": "secret",
            "ASSISTANT_WORKSPACE": str(tmp_path),
        }
    )

    with pytest.raises(ConfigurationError) as error:
        build_assistant(config)

    assert error.value.field == "LLM_PROVIDER"


def test_build_assistant_requires_groq_api_key(tmp_path: Path) -> None:
    config = AppConfig.from_environment({"ASSISTANT_WORKSPACE": str(tmp_path)})

    with pytest.raises(ConfigurationError) as error:
        build_assistant(config)

    assert error.value.field == "GROQ_API_KEY"
