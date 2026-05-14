"""Optional: merge Presenton userConfig.json into os.environ (Docker-style)."""

from __future__ import annotations

import json
import os
from pathlib import Path

_AUTH_KEYS = frozenset(
    {"AUTH_USERNAME", "AUTH_PASSWORD_HASH", "AUTH_SECRET_KEY"}
)


def resolve_user_config_path(repo_root: Path) -> Path:
    p = (os.environ.get("USER_CONFIG_PATH") or "").strip()
    if p:
        return Path(p)
    app_data = (os.environ.get("APP_DATA_DIRECTORY") or "").strip()
    if app_data:
        return Path(app_data) / "userConfig.json"
    return repo_root / "app_data" / "userConfig.json"


def sync_user_config_into_env(repo_root: Path) -> None:
    path = resolve_user_config_path(repo_root)
    if not path.is_file():
        return
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return
    if not isinstance(data, dict):
        return
    for key, value in data.items():
        if key in _AUTH_KEYS:
            continue
        if value is None:
            continue
        existing = os.environ.get(key)
        if existing is not None and str(existing).strip() != "":
            continue
        if isinstance(value, bool):
            os.environ[key] = "true" if value else "false"
        else:
            s = str(value).strip()
            if s:
                os.environ[key] = s


def infer_llm_provider() -> str:
    """Return provider string when LLM is unset (same spirit as Docker defaults)."""
    if (os.environ.get("ANTHROPIC_API_KEY") or "").strip():
        return "anthropic"
    if (os.environ.get("OPENAI_API_KEY") or "").strip():
        return "openai"
    if (os.environ.get("OPENROUTER_API_KEY") or "").strip():
        return "openrouter"
    if (os.environ.get("LITELLM_BASE_URL") or "").strip():
        return "litellm"
    if (os.environ.get("CEREBRAS_API_KEY") or "").strip():
        return "cerebras"
    if (os.environ.get("GOOGLE_API_KEY") or "").strip():
        return "google"
    if (os.environ.get("VERTEX_PROJECT") or "").strip() or (
        os.environ.get("VERTEX_API_KEY") or ""
    ).strip():
        return "vertex"
    if (os.environ.get("AZURE_OPENAI_API_KEY") or "").strip():
        return "azure"
    if (os.environ.get("OLLAMA_URL") or "").strip():
        return "ollama"
    if (os.environ.get("CUSTOM_LLM_URL") or "").strip():
        return "custom"
    return ""
