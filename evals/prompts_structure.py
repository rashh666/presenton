"""Structure prompts — aligned with production; templates under evals/prompts/."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from llmai.shared import SystemMessage, UserMessage

from contracts import PresentationLayoutModel


_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_STRUCTURE_SYSTEM_TEMPLATE = (_PROMPTS_DIR / "structure_system.txt").read_text(encoding="utf-8")


def get_messages(
    presentation_layout: PresentationLayoutModel,
    n_slides: int,
    data: str,
    instructions: Optional[str] = None,
) -> list[object]:
    num_layouts = len(presentation_layout.slides)
    system_prompt = _STRUCTURE_SYSTEM_TEMPLATE.format(
        user_instruction_header=f"# User Instruction: {instructions or ''}" if instructions else "",
        n_slides=n_slides,
        num_layouts=num_layouts,
        max_layout_index=max(0, num_layouts - 1),
    )

    # Include JSON schema per layout so the model can match fields (table_md, body_markdown, …)
    # to outline content—mirrors the rich catalog signal from `STRUCTURE_FROM_SLIDES_MARKDOWN` path
    # in servers/fastapi/utils/llm_calls/generate_presentation_structure.py.
    return [
        SystemMessage(content=system_prompt),
        UserMessage(
            content=(
                f"{presentation_layout.to_string(with_schema=True)}\n\n"
                "--------------------------------------\n\n"
                f"{data}"
            )
        ),
    ]
