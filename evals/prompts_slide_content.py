"""Slide content prompts — aligned with production; templates under evals/prompts/."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from llmai.shared import SystemMessage, UserMessage

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_SLIDE_SYSTEM_TEMPLATE = (_PROMPTS_DIR / "slide_system.txt").read_text(encoding="utf-8")
_SLIDE_USER_TEMPLATE = (_PROMPTS_DIR / "slide_user.txt").read_text(encoding="utf-8")


def _resolve_prompt_language(language: Optional[str]) -> str:
    if language is None:
        return "auto-detect"
    s = str(language).strip()
    if not s:
        return "auto-detect"
    if s.lower() in {"auto", "auto-detect"}:
        return "auto-detect"
    return s


def _get_schema_markdown(response_schema: Optional[dict]) -> str:
    if not response_schema:
        return "- Follow the provided response schema strictly."
    try:
        schema_text = json.dumps(response_schema, ensure_ascii=False)
    except Exception:
        return "- Follow the provided response schema strictly."
    return f"- Follow this response schema exactly: {schema_text}"


def get_system_prompt(
    tone: Optional[str] = None,
    verbosity: Optional[str] = None,
    instructions: Optional[str] = None,
    response_schema: Optional[dict] = None,
):
    markdown_emphasis_rules = (
        "- Strictly use markdown to emphasize important points, by bolding or "
        "italicizing the part of text."
    )

    user_instructions = f"# User Instructions:\n{instructions}" if instructions else ""
    tone_instructions = (
        f"# Tone Instructions:\nMake slide as {tone} as possible." if tone else ""
    )

    verbosity_instructions = ""
    if verbosity:
        verbosity_instructions = "# Verbosity Instructions:\n"
        if verbosity == "concise":
            verbosity_instructions += "Make slide as concise as possible."
        elif verbosity == "standard":
            verbosity_instructions += "Make slide as standard as possible."
        elif verbosity == "text-heavy":
            verbosity_instructions += "Make slide as text-heavy as possible."

    output_fields_instructions = "# Output Fields:\n" + _get_schema_markdown(
        response_schema
    )

    return _SLIDE_SYSTEM_TEMPLATE.format(
        markdown_emphasis_rules=markdown_emphasis_rules,
        user_instructions=user_instructions,
        tone_instructions=tone_instructions,
        verbosity_instructions=verbosity_instructions,
        output_fields_instructions=output_fields_instructions,
    )


def get_user_prompt(outline: str, language: Optional[str]):
    return _SLIDE_USER_TEMPLATE.format(
        current_date_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        language=_resolve_prompt_language(language),
        content=outline,
    )


def get_messages(
    outline: str,
    language: Optional[str],
    tone: Optional[str] = None,
    verbosity: Optional[str] = None,
    instructions: Optional[str] = None,
    response_schema: Optional[dict] = None,
) -> list[object]:
    return [
        SystemMessage(
            content=get_system_prompt(
                tone,
                verbosity,
                instructions,
                response_schema,
            ),
        ),
        UserMessage(
            content=get_user_prompt(outline, language),
        ),
    ]
