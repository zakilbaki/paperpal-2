from __future__ import annotations
from fastapi import APIRouter
from typing import Any

# -------------------------------------------------------
# 🧩 Dual import logic (works both locally and on Render)
# -------------------------------------------------------
try:
    # Local run (from project root): backend.app.*
    from backend.app.db.mongo import ping
    from backend.app.core.config import settings
except ModuleNotFoundError:
    # Render container (WORKDIR=/app): app.*
    from app.db.mongo import ping
    from app.core.config import settings

# -------------------------------------------------------
# 🚑 Router
# -------------------------------------------------------
router = APIRouter()

@router.get("/", summary="Health check")
async def health_check() -> dict[str, Any]:
    """
    Health endpoint returning service status and MongoDB connection.
    """
    mongo_ok = await ping()
    return {
        "service": settings.APP_NAME,
        "env": settings.APP_ENV,
        "mongo_ok": mongo_ok,
    }
