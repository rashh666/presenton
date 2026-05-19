import json
import logging
import os
from typing import Any, Dict, Optional

LOGGER = logging.getLogger(__name__)

_DEFAULT_PERSONA_KEY = "rashid_strict"
_personas_cache: Optional[Dict[str, Any]] = None


def _get_personas_path() -> str:
    """
    Resolve personas.json location.

    Priority:
      1. PERSONAS_PATH env var (explicit override)
      2. {APP_DATA_DIRECTORY}/personas.json
      3. presenton root personas.json (sibling of docker-compose.yml)
    """
    explicit = (os.getenv("PERSONAS_PATH") or "").strip()
    if explicit:
        return explicit

    app_data = (os.getenv("APP_DATA_DIRECTORY") or "").strip()
    if app_data:
        candidate = os.path.join(app_data, "personas.json")
        if os.path.isfile(candidate):
            return candidate

    # Resolve relative to this file: servers/fastapi/utils/ -> presenton root
    here = os.path.dirname(__file__)
    root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    return os.path.join(root, "personas.json")


def load_personas(force_reload: bool = False) -> Dict[str, Any]:
    """Load and cache personas from personas.json. Returns {} if file is absent/invalid."""
    global _personas_cache
    if _personas_cache is not None and not force_reload:
        return _personas_cache

    path = _get_personas_path()
    if not os.path.isfile(path):
        LOGGER.warning("personas.json not found at %s; persona features are disabled", path)
        _personas_cache = {}
        return _personas_cache

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("personas.json must be a JSON object at the root level")
        _personas_cache = data
        LOGGER.info("Loaded %d persona(s) from %s", len(data), path)
    except Exception as exc:
        LOGGER.error("Failed to load personas from %s: %s", path, exc)
        _personas_cache = {}

    return _personas_cache


def get_persona(key: Optional[str]) -> Dict[str, Any]:
    """
    Return the persona config for *key*.

    Falls back to rashid_strict (or the first available persona) when the
    requested key is absent or personas.json was not found.  Returns {} when
    no personas are configured at all — callers must tolerate empty config.
    """
    personas = load_personas()
    if not personas:
        return {}

    if key and key in personas:
        return personas[key]

    if key:
        LOGGER.warning("Persona %r not found", key)

    if _DEFAULT_PERSONA_KEY in personas:
        if key:
            LOGGER.warning("Falling back to default persona '%s'", _DEFAULT_PERSONA_KEY)
        return personas[_DEFAULT_PERSONA_KEY]

    first_key = next(iter(personas))
    if key:
        LOGGER.warning("Falling back to first available persona '%s'", first_key)
    return personas[first_key]


def list_personas() -> Dict[str, str]:
    """Return {key: description} for all loaded personas."""
    personas = load_personas()
    return {k: v.get("description", "") for k, v in personas.items()}
