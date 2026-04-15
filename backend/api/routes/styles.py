from fastapi import APIRouter
from models.styles import STYLES
from models.schemas import StyleOption

router = APIRouter(prefix="/styles", tags=["styles"])


@router.get("", response_model=list[StyleOption])
async def list_styles():
    return [StyleOption(**s) for s in STYLES.values()]
