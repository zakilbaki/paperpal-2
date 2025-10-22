from fastapi import APIRouter
from app.db.mongo import ping

from app.db.mongo import settings

router = APIRouter()

@router.get("/health")
async def health():
    ok = await ping()
    return {
        "service": settings.APP_NAME,
        "env": settings.APP_ENV,
        "mongo_ok": ok,
    }
