"""Groq SDK adapter for local function calling."""

from __future__ import annotations

from typing import Any

from groq import APIConnectionError, APIStatusError, Groq

from providers.base import (
    ChatMessage,
    ProviderError,
    ProviderTurn,
    ToolCallRequest,
)


class GroqProvider:
    """Translate Groq Chat Completions responses into provider-neutral turns."""

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        client: Any | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not api_key.strip():
            raise ValueError("A Groq API key is required.")
        if not model.strip():
            raise ValueError("A Groq model name is required.")

        self.model = model.strip()
        self._client = client or Groq(
            api_key=api_key.strip(),
            max_retries=2,
            timeout=timeout_seconds,
        )

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
    ) -> ProviderTurn:
        """Request one non-streaming Groq turn with local tools enabled."""

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                parallel_tool_calls=True,
                temperature=0,
                max_completion_tokens=2_048,
            )
        except APIStatusError as exc:
            raise ProviderError(
                "Groq rejected the request.",
                status_code=exc.status_code,
            ) from exc
        except APIConnectionError as exc:
            raise ProviderError("The Groq API could not be reached.") from exc
        except Exception as exc:
            raise ProviderError("The Groq request failed unexpectedly.") from exc

        if not response.choices:
            raise ProviderError("Groq returned a response without any choices.")

        message = response.choices[0].message
        content = message.content if isinstance(message.content, str) else None
        tool_calls: list[ToolCallRequest] = []
        serialized_tool_calls: list[dict[str, Any]] = []
        for tool_call in message.tool_calls or []:
            arguments = tool_call.function.arguments or "{}"
            tool_calls.append(
                ToolCallRequest(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments=arguments,
                )
            )
            serialized_tool_calls.append(
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": arguments,
                    },
                }
            )

        assistant_message: ChatMessage = {
            "role": "assistant",
            "content": content,
        }
        if serialized_tool_calls:
            assistant_message["tool_calls"] = serialized_tool_calls

        return ProviderTurn(
            content=content,
            tool_calls=tuple(tool_calls),
            assistant_message=assistant_message,
        )


__all__ = ["GroqProvider"]
