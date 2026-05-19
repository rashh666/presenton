import json
from datetime import datetime
from typing import Optional

from llmai import get_client
from llmai.shared import JSONSchemaResponse, Message, SystemMessage, UserMessage

from models.presentation_layout import SlideLayoutModel
from models.presentation_outline_model import SlideOutlineModel
from utils.llm_client_error_handler import handle_llm_client_exceptions
from utils.llm_config import get_llm_config
from utils.llm_provider import get_model
from utils.llm_utils import generate_structured_with_schema_retries
from utils.schema_utils import (
    add_field_in_schema,
    ensure_array_schemas_have_items,
    remove_fields_from_schema,
)

SLIDE_CONTENT_SYSTEM_PROMPT = """
You will be given slide content and response schema.
You need to generate structured content json based on the schema.

# Steps
1. Analyze the content.
2. Analyze the response schema.
3. Generate structured content json based on the schema.
4. Generate speaker note if required.
5. Provide structured content json as output.

# General Rules
- Follow language guidelines.
- Speaker notes must be plain text (no markdown).
- Never exceed max character limits; do not clip mid-sentence to fit—rephrase instead.
- Do not use emojis or $schema fields.
- Follow user instructions literally; do not reinterpret, generalize, or expand them.
- Apply slide-specific instructions only to the exact slide mentioned (first/second/last/named) and only once.
- Do not apply patterns across multiple slides unless explicitly requested.
- If instructions are ambiguous, use the most direct interpretation without extending scope.

{markdown_emphasis_rules}

{user_instructions}

{tone_instructions}

{verbosity_instructions}

{output_fields_instructions}
"""


SLIDE_CONTENT_USER_PROMPT = """
# Current Date and Time:
{current_date_time}

# Icon Query And Image Prompt Language:
English

# Slide Language:
{language}

# SLIDE CONTENT: START
{content}
# SLIDE CONTENT: END
"""


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


def _build_persona_style_block(persona_config: Optional[dict]) -> str:
    if not persona_config:
        return ""
    lines: list[str] = []

    text_gen = persona_config.get("text_generation", {})
    sentence_style = text_gen.get("sentence_style")
    slide_density = text_gen.get("slide_density")
    rhetorical = text_gen.get("rhetorical_devices")
    if any([sentence_style, slide_density, rhetorical]):
        lines.append("# Persona Style Constraints:")
        if sentence_style:
            lines.append(f"- Sentence Style: {sentence_style}")
        if slide_density:
            lines.append(f"- Slide Density: {slide_density}")
        if rhetorical:
            lines.append(f"- Preferred Rhetorical Devices: {', '.join(rhetorical)}")

    slide_types = persona_config.get("slide_types", {})
    if slide_types:
        lines.append("# Slide Type Rules (apply to matching slide beat/purpose):")
        for beat, rule in slide_types.items():
            lines.append(f"- {beat}: {rule}")

    pacing = persona_config.get("presentation_pacing", {})
    if pacing:
        spc = pacing.get("slides_per_chapter")
        transition = pacing.get("transition_hint")
        if spc or transition:
            lines.append("# Presentation Pacing:")
            if spc:
                lines.append(f"- Slides per chapter: {spc}")
            if transition:
                lines.append(f"- Chapter transition: {transition}")

    notes_cfg = persona_config.get("speaker_notes", {})
    if notes_cfg:
        style = notes_cfg.get("style")
        length = notes_cfg.get("length")
        cue = notes_cfg.get("include_transition_cue")
        if any([style, length, cue is not None]):
            lines.append("# Speaker Notes Style:")
            if style:
                lines.append(f"- Style: {style}")
            if length:
                lines.append(f"- Length: {length}")
            if cue:
                lines.append("- Include a transition cue at the end of each speaker note.")

    return ("\n".join(lines) + "\n") if lines else ""


def get_system_prompt(
    tone: Optional[str] = None,
    verbosity: Optional[str] = None,
    instructions: Optional[str] = None,
    response_schema: Optional[dict] = None,
    persona_config: Optional[dict] = None,
):
    markdown_emphasis_rules = (
        "- Strictly use markdown to emphasize important points, by bolding or "
        "italicizing the part of text."
    )

    user_instructions = f"# User Instructions:\n{instructions}" if instructions else ""

    persona_tone = (persona_config or {}).get("text_generation", {}).get("tone") if persona_config else None
    effective_tone = persona_tone or tone
    tone_instructions = (
        f"# Tone Instructions:\nMake slide as {effective_tone} as possible." if effective_tone else ""
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

    persona_style_block = _build_persona_style_block(persona_config)

    output_fields_instructions = "# Output Fields:\n" + _get_schema_markdown(
        response_schema
    )

    return SLIDE_CONTENT_SYSTEM_PROMPT.format(
        markdown_emphasis_rules=markdown_emphasis_rules,
        user_instructions=user_instructions,
        tone_instructions=tone_instructions + ("\n" + persona_style_block if persona_style_block else ""),
        verbosity_instructions=verbosity_instructions,
        output_fields_instructions=output_fields_instructions,
    )


def get_user_prompt(outline: str, language: Optional[str]):
    return SLIDE_CONTENT_USER_PROMPT.format(
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
    persona_config: Optional[dict] = None,
) -> list[Message]:

    return [
        SystemMessage(
            content=get_system_prompt(
                tone,
                verbosity,
                instructions,
                response_schema,
                persona_config,
            ),
        ),
        UserMessage(
            content=get_user_prompt(outline, language),
        ),
    ]


async def get_slide_content_from_type_and_outline(
    slide_layout: SlideLayoutModel,
    outline: SlideOutlineModel,
    language: Optional[str],
    tone: Optional[str] = None,
    verbosity: Optional[str] = None,
    instructions: Optional[str] = None,
    persona_config: Optional[dict] = None,
):
    client = get_client(config=get_llm_config())
    model = get_model()

    persona_text_gen = (persona_config or {}).get("text_generation", {})
    persona_hallucination = persona_text_gen.get("hallucination", {})
    persona_temperature = persona_hallucination.get("temperature")
    persona_top_p = persona_hallucination.get("top_p")
    reflection_enabled = persona_hallucination.get("reflection_enabled", True)
    reflection_max_iterations = int(persona_hallucination.get("reflection_max_iterations", 4))

    response_schema = remove_fields_from_schema(
        slide_layout.json_schema, ["__image_url__", "__icon_url__"]
    )
    response_schema = add_field_in_schema(
        response_schema,
        {
            "__speaker_note__": {
                "type": "string",
                "minLength": 100,
                "maxLength": 500,
                "description": "Speaker note for the slide",
            }
        },
        True,
    )
    response_schema = ensure_array_schemas_have_items(response_schema)

    try:
        response_format = JSONSchemaResponse(
            name="response",
            json_schema=response_schema,
            strict=False,
        )
        messages = get_messages(
            outline.content,
            language,
            tone,
            verbosity,
            instructions,
            response_schema,
            persona_config,
        )

        return await generate_structured_with_schema_retries(
            client,
            model,
            messages=messages,
            response_format=response_format,
            json_schema=response_schema,
            strict=False,
            validate_schema=reflection_enabled,
            validate_schema_max_loop_count=reflection_max_iterations,
            temperature=persona_temperature,
            top_p=persona_top_p,
        )

    except Exception as e:
        raise handle_llm_client_exceptions(e)
