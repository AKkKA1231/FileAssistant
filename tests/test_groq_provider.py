"""Tests for normalization performed by the Groq provider adapter."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from providers.groq_provider import GroqProvider


class FakeCompletions:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.arguments: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> Any:
        self.arguments = kwargs
        return self.response


class FakeGroqClient:
    def __init__(self, response: Any) -> None:
        self.completions = FakeCompletions(response)
        self.chat = SimpleNamespace(completions=self.completions)


def test_groq_provider_normalizes_tool_calls() -> None:
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=None,
                    tool_calls=[
                        SimpleNamespace(
                            id="call-123",
                            function=SimpleNamespace(
                                name="list_files",
                                arguments='{ "directory": "resumes" }',
                            ),
                        )
                    ],
                )
            )
        ]
    )
    client = FakeGroqClient(response)
    provider = GroqProvider("test-key", "test-model", client=client)

    turn = provider.complete(
        [{"role": "user", "content": "List resumes"}],
        [{"type": "function", "function": {"name": "list_files"}}],
    )

    assert turn.content is None
    assert turn.tool_calls[0].id == "call-123"
    assert turn.tool_calls[0].name == "list_files"
    assert turn.assistant_message["tool_calls"][0]["function"]["name"] == "list_files"
    assert client.completions.arguments["model"] == "test-model"
    assert client.completions.arguments["tool_choice"] == "auto"
    assert client.completions.arguments["parallel_tool_calls"] is True


def test_groq_provider_normalizes_final_text() -> None:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Done", tool_calls=None))]
    )
    provider = GroqProvider("test-key", "test-model", client=FakeGroqClient(response))

    turn = provider.complete([], [])

    assert turn.content == "Done"
    assert turn.tool_calls == ()
    assert turn.assistant_message == {"role": "assistant", "content": "Done"}
