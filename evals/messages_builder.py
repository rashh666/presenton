"""Assemble messages for each pipeline stage (prompts live in prompts_*.py — edit there)."""

from __future__ import annotations

import json
from typing import Any

import layout_load
import prompts_outline
import prompts_slide_content
import prompts_structure
from contracts import (
    PresentationLayoutModel,
    PresentationOutlineModel,
    get_presentation_outline_model_with_n_slides,
)


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in {"true", "1", "yes", "y"}:
        return True
    if s in {"false", "0", "no", "n", ""}:
        return False
    return default


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in {"", "none", "null", "auto", "auto-detect"}:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def build_outline_messages(vars_: dict) -> list[Any]:
    return prompts_outline.get_messages(
        content=str(vars_.get("content", "")),
        n_slides=_as_optional_int(vars_.get("n_slides")),
        language=vars_.get("language"),
        additional_context=vars_.get("additional_context"),
        tone=vars_.get("tone"),
        verbosity=vars_.get("verbosity"),
        instructions=vars_.get("instructions"),
        include_title_slide=_as_bool(vars_.get("include_title_slide"), True),
        include_table_of_contents=_as_bool(vars_.get("include_table_of_contents"), False),
    )


def build_structure_messages(vars_: dict) -> list[Any]:
    layout = PresentationLayoutModel.model_validate_json(
        layout_load.resolve_layout_json(vars_["layout_json"])
    )
    data = str(vars_.get("outline_as_markdown", "")).strip()
    outline_obj: PresentationOutlineModel | None = None
    if vars_.get("outline_slides_json"):
        outline_obj = PresentationOutlineModel.model_validate_json(
            str(vars_["outline_slides_json"])
        )
        if not data:
            data = outline_obj.to_string()
    n_raw = vars_.get("n_slides")
    if n_raw is not None and str(n_raw).strip() != "":
        n_slides = int(n_raw)
    elif outline_obj is not None:
        n_slides = len(outline_obj.slides)
    else:
        raise ValueError("structure stage requires n_slides or outline_slides_json")
    return prompts_structure.get_messages(
        layout,
        n_slides,
        data,
        instructions=vars_.get("instructions") or None,
    )


def build_slide_messages(vars_: dict) -> list[Any]:
    schema = json.loads(str(vars_["response_schema_json"]))
    return prompts_slide_content.get_messages(
        outline=str(vars_.get("slide_markdown", "")),
        language=vars_.get("language"),
        tone=vars_.get("tone") or None,
        verbosity=vars_.get("verbosity") or None,
        instructions=vars_.get("instructions") or None,
        response_schema=schema,
    )


def outline_response_model_class(vars_: dict):
    n = _as_optional_int(vars_.get("n_slides"))
    if n is not None:
        return get_presentation_outline_model_with_n_slides(n)
    return PresentationOutlineModel
