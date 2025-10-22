from __future__ import annotations  # must be first

from typing import Optional
import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings


# --- Global MongoDB clients ---
_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_client() -> AsyncIOMotorClient:
    """
    Return a singleton AsyncIOMotorClient using settings.MONGODB_URI.
    """
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            uuidRepresentation="standard",
            tlsCAFile=certifi.where(),  # ensure SSL trust works on macOS
        )
    return _client


def get_db() -> AsyncIOMotorDatabase:
    """
    Return the main application database instance.
    """
    global _db
    if _db is None:
        client = get_client()
        _db = client[settings.MONGODB_DB]
    return _db


async def get_database() -> AsyncIOMotorDatabase:
    """
    FastAPI dependency-compatible accessor for the DB.
    Example: Depends(get_database)
    """
    return get_db()


async def ping() -> bool:
    """
    Check MongoDB connection health.
    Returns True if 'ping' succeeds, False otherwise.
    """
    client = get_client()
    try:
        res = await client.admin.command("ping")
        return bool(res.get("ok", 0) == 1)
    except Exception:
        return False
