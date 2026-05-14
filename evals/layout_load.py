"""Resolve layout_json test vars: inline JSON or file://schemas/... under evals/."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_EVALS_DIR = Path(__file__).resolve().parent


def resolve_layout_json(value: Any) -> str:
    """Return raw JSON text for PresentationLayoutModel.model_validate_json."""
    if value is None:
        return ""
    s = str(value).strip()
    if not s.startswith("file://"):
        return s
    rel = s.removeprefix("file://").lstrip("/")
    path = _EVALS_DIR / rel
    if not path.is_file():
        raise FileNotFoundError(f"layout_json file not found: {path} (from {value!r})")
    return path.read_text(encoding="utf-8")
