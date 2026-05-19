import asyncio
import json
import uuid
from typing import Optional

import dirtyjson
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from llmai import get_client
from llmai.shared import SystemMessage, UserMessage
from models.presentation_outline_model import SlideOutlineModel
from models.sql.presentation import PresentationModel
from models.sql.slide import SlideModel
from services.database import get_async_session
from services.image_generation_service import ImageGenerationService
from utils.asset_directory_utils import get_images_directory
from utils.get_layout_by_name import get_layout_by_name
from utils.llm_config import get_llm_config
from utils.llm_provider import get_model
from utils.llm_utils import extract_text, get_generate_kwargs
from utils.personas import get_persona
from utils.process_slides import process_old_and_new_slides_and_fetch_assets
from utils.llm_calls.generate_slide_content import get_slide_content_from_type_and_outline

SLIDE_ACTIONS_ROUTER = APIRouter(prefix="/slide", tags=["Slide Actions"])

_PROOFREAD_SYSTEM = """You are a proofreader. Fix ONLY spelling and grammar errors in the text values of the provided JSON object.

Rules:
- Preserve every field name exactly as-is.
- Preserve values that start with "__" (e.g. __image_url__, __icon_url__) unchanged.
- Preserve URLs, numbers, booleans, and null values unchanged.
- Do not rephrase, shorten, or expand any text — only correct errors.
- Return valid JSON with the same structure as the input."""


def _walk_and_fix(original: dict, corrected: dict) -> dict:
    """Recursively merge corrected text back, skipping protected fields."""
    result = {}
    for key, orig_val in original.items():
        if key not in corrected:
            result[key] = orig_val
            continue
        corr_val = corrected[key]
        if key.startswith("__"):
            result[key] = orig_val
        elif isinstance(orig_val, dict) and isinstance(corr_val, dict):
            result[key] = _walk_and_fix(orig_val, corr_val)
        elif isinstance(orig_val, list) and isinstance(corr_val, list):
            merged = []
            for i, item in enumerate(orig_val):
                if i < len(corr_val):
                    if isinstance(item, dict) and isinstance(corr_val[i], dict):
                        merged.append(_walk_and_fix(item, corr_val[i]))
                    elif isinstance(item, str) and isinstance(corr_val[i], str):
                        merged.append(corr_val[i])
                    else:
                        merged.append(item)
                else:
                    merged.append(item)
            result[key] = merged
        elif isinstance(orig_val, str) and isinstance(corr_val, str):
            result[key] = corr_val
        else:
            result[key] = orig_val
    return result


@SLIDE_ACTIONS_ROUTER.post("/regenerate/{slide_id}", response_model=SlideModel)
async def regenerate_slide(
    slide_id: uuid.UUID,
    request: Request,
    sql_session: AsyncSession = Depends(get_async_session),
):
    slide = await sql_session.get(SlideModel, slide_id)
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    presentation = await sql_session.get(PresentationModel, slide.presentation)
    if not presentation:
        raise HTTPException(status_code=404, detail="Presentation not found")

    outlines = presentation.get_outlines()
    if slide.index >= len(outlines.slides):
        raise HTTPException(status_code=400, detail="Slide index out of range")
    outline: SlideOutlineModel = outlines.slides[slide.index]

    layout_group = await get_layout_by_name(slide.layout_group)
    try:
        slide_layout = next(s for s in layout_group.slides if s.id == slide.layout)
    except StopIteration:
        slide_layout = layout_group.slides[0]

    persona_key = request.headers.get("x-persona")
    persona_config = get_persona(persona_key)
    persona_image_suffix = (
        persona_config.get("image_generation", {}).get("default_prompt_suffix") or None
    )

    new_content = await get_slide_content_from_type_and_outline(
        slide_layout,
        outline,
        presentation.language,
        presentation.tone,
        presentation.verbosity,
        presentation.instructions,
        persona_config=persona_config,
    )

    image_generation_service = ImageGenerationService(get_images_directory())
    new_assets = await process_old_and_new_slides_and_fetch_assets(
        image_generation_service,
        slide.content,
        new_content,
        persona_image_suffix=persona_image_suffix,
    )

    slide.id = uuid.uuid4()
    slide.content = new_content
    slide.speaker_note = new_content.get("__speaker_note__", "")
    sql_session.add(slide)
    sql_session.add_all(new_assets)
    await sql_session.commit()

    return slide


@SLIDE_ACTIONS_ROUTER.post("/proofread/{slide_id}", response_model=SlideModel)
async def proofread_slide(
    slide_id: uuid.UUID,
    sql_session: AsyncSession = Depends(get_async_session),
):
    slide = await sql_session.get(SlideModel, slide_id)
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")

    client = get_client(config=get_llm_config())
    model = get_model()

    content_json = json.dumps(slide.content, ensure_ascii=False)
    messages = [
        SystemMessage(content=_PROOFREAD_SYSTEM),
        UserMessage(content=f"Proofread this slide content JSON:\n\n{content_json}"),
    ]

    kwargs = get_generate_kwargs(model=model, messages=messages, temperature=0.0)
    try:
        response = await asyncio.to_thread(client.generate, **kwargs)
        text = extract_text(response.content) or ""
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object in response")
        corrected = dict(dirtyjson.loads(text[start:end]))
        fixed_content = _walk_and_fix(slide.content, corrected)
    except Exception:
        raise HTTPException(status_code=500, detail="Proofread LLM call failed")

    slide.id = uuid.uuid4()
    slide.content = fixed_content
    sql_session.add(slide)
    await sql_session.commit()

    return slide
