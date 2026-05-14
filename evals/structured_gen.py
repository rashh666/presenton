"""Structured generation via llmai (subset of servers/fastapi/utils/llm_utils.py)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from typing import Any, Optional

import dirtyjson
from llmai.shared import LLMTool, Message, ResponseFormat

from llm_env import get_extra_body


def get_generate_kwargs(
    model: str,
    messages: Sequence[Message],
    max_tokens: int | None = None,
    tools: list[LLMTool] | None = None,
    response_format: ResponseFormat | None = None,
    stream: bool = False,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": list(messages),
        "stream": stream,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if tools:
        kwargs["tools"] = tools
    if response_format is not None:
        kwargs["response_format"] = response_format

    extra_body = get_extra_body()
    if extra_body:
        kwargs["extra_body"] = extra_body

    return kwargs


def extract_text(content: Any) -> str | None:
    if content is None:
        return None
    if isinstance(content, str):
        return content
    if isinstance(content, Sequence) and not isinstance(content, (bytes, bytearray)):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
                continue
            text = getattr(part, "text", None)
            if isinstance(text, str):
                parts.append(text)
        joined = "".join(parts)
        return joined or None
    text = getattr(content, "text", None)
    if isinstance(text, str):
        return text
    return None


def extract_structured_content(content: Any) -> dict | None:
    if content is None:
        return None
    if isinstance(content, dict):
        return content
    if hasattr(content, "model_dump"):
        dumped = content.model_dump(mode="json")
        if isinstance(dumped, dict):
            return dumped

    raw_text = extract_text(content)
    if not raw_text:
        return None

    try:
        parsed = dirtyjson.loads(raw_text)
    except Exception:
        return None

    if isinstance(parsed, dict):
        return dict(parsed)
    return None


async def generate_structured(
    client: Any,
    model: str,
    messages: list[Message],
    response_format: ResponseFormat,
    *,
    tools: list[LLMTool] | None = None,
    max_inner_attempts: int = 3,
) -> dict:
    for attempt in range(max_inner_attempts):
        response = await asyncio.to_thread(
            client.generate,
            **get_generate_kwargs(
                model=model,
                messages=messages,
                response_format=response_format,
                tools=tools,
            ),
        )
        content = extract_structured_content(response.content)
        if content is not None:
            return content
        if attempt < max_inner_attempts - 1:
            await asyncio.sleep(0.5 * (attempt + 1))
    raise RuntimeError("LLM did not return parseable structured JSON")
