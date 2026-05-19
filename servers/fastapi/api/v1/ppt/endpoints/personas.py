from fastapi import APIRouter

from utils.personas import list_personas

PERSONAS_ROUTER = APIRouter(prefix="/personas", tags=["Personas"])


@PERSONAS_ROUTER.get("")
async def get_personas() -> dict[str, str]:
    """Return all available persona keys with their descriptions."""
    return list_personas()
