from fastapi import APIRouter
from backend.app.db.mongo import ping
from backend.app.core.config import settings

router = APIRouter()

@router.get("/", summary="Health check")
async def health():
    ok = await ping()
    return {
        "service": settings.APP_NAME,
        "env": settings.APP_ENV,
        "mongo_ok": ok,
    }
