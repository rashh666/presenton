"""Outline prompts — aligned with production; templates under evals/prompts/."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from llmai.shared import SystemMessage, UserMessage

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_OUTLINE_SYSTEM_TEMPLATE = (_PROMPTS_DIR / "outline_system.txt").read_text(encoding="utf-8")
_OUTLINE_USER_TEMPLATE = (_PROMPTS_DIR / "outline_user.txt").read_text(encoding="utf-8")


def get_system_prompt(
    verbosity: Optional[str] = None,
    include_title_slide: bool = True,
    include_table_of_contents: bool = False,
):
    verbosity_instruction = (
        "Slide content should be around 20 words but detailed enough to generate a good slide."
        if verbosity == "concise"
        else (
            "Slide content should be around 60 words but detailed enough to generate a good slide."
            if verbosity == "text-heavy"
            else "Slide content should be around 40 words but detailed enough to generate a good slide."
        )
    )
    title_slide_instruction = (
        "Include presenter name in first slide."
        if include_title_slide
        else "Do not include presenter name in any slides."
    )
    toc_instruction = (
        "Include a table of contents slide in the outline sequence."
        if include_table_of_contents
        else ""
    )
    toc_block = f"{toc_instruction}\n" if toc_instruction else ""
    slide_outline_structure = (
        "Each slide content:\n"
        "   - Must have a ## title.\n"
        "   - Must be in Markdown format.\n"
        "   - Don't use **bold** and __italic__ text."
        "   - First slide title must be the same as the presentation title."
    )
    return _OUTLINE_SYSTEM_TEMPLATE.format(
        verbosity_instruction=verbosity_instruction,
        title_slide_instruction=title_slide_instruction,
        toc_block=toc_block,
        slide_outline_structure=slide_outline_structure,
    )


def _resolve_prompt_language(language: Optional[str]) -> str:
    if language is None:
        return "auto-detect"
    s = str(language).strip()
    if not s:
        return "auto-detect"
    if s.lower() in {"auto", "auto-detect"}:
        return "auto-detect"
    return s


def _resolve_prompt_n_slides(n_slides: Optional[int]) -> str:
    if n_slides is None:
        return "auto-detect"
    return str(n_slides)


def get_user_prompt(
    content: str,
    n_slides: Optional[int],
    language: Optional[str],
    additional_context: Optional[str] = None,
    tone: Optional[str] = None,
    instructions: Optional[str] = None,
    include_title_slide: bool = True,
    include_table_of_contents: bool = False,
):
    display_language = _resolve_prompt_language(language)
    display_slides = _resolve_prompt_n_slides(n_slides)
    toc_text = f"Include Table Of Contents: {str(include_table_of_contents).lower()}\n"
    return _OUTLINE_USER_TEMPLATE.format(
        content=content or "",
        display_slides=display_slides,
        display_language=display_language,
        tone=tone or "",
        today=datetime.now().strftime("%Y-%m-%d"),
        include_title_slide=include_title_slide,
        toc_text=toc_text if include_table_of_contents else "",
        instructions=instructions or "",
        additional_context=additional_context or "None",
    )


def get_messages(
    content: str,
    n_slides: Optional[int],
    language: Optional[str],
    additional_context: Optional[str] = None,
    tone: Optional[str] = None,
    verbosity: Optional[str] = None,
    instructions: Optional[str] = None,
    include_title_slide: bool = True,
    include_table_of_contents: bool = False,
) -> list[object]:
    return [
        SystemMessage(
            content=get_system_prompt(
                verbosity,
                include_title_slide,
                include_table_of_contents,
            ),
        ),
        UserMessage(
            content=get_user_prompt(
                content,
                n_slides,
                language,
                additional_context,
                tone,
                instructions,
                include_title_slide,
                include_table_of_contents,
            ),
        ),
    ]
