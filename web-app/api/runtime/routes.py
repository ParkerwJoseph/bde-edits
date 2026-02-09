from fastapi import APIRouter
from config.settings import API_BASE_URL

router = APIRouter()


@router.get("")
async def get_runtime_config():
    """Return runtime configuration for frontend"""
    return {"apiBaseUrl": API_BASE_URL}
