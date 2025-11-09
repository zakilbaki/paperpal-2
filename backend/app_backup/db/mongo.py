from __future__ import annotations  # must be first

import asyncio
from typing import Optional
import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ServerSelectionTimeoutError

# -------------------------------------------------------
# 🧩 Config import (Render + Local compatible)
# -------------------------------------------------------
try:
    # Local run (uvicorn backend.app.main:app)
    from backend.app.core.config import settings
except ModuleNotFoundError:
    # Render container (starts at /app)
    from app.core.config import settings

# --- Global MongoDB clients ---
_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_client() -> AsyncIOMotorClient:
    """
    Return a singleton AsyncIOMotorClient using settings.MONGODB_URI.
    Includes full TLS and CA file for MongoDB Atlas.
    """
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            uuidRepresentation="standard",
            tls=True,                        # explicitly enable TLS
            tlsAllowInvalidCertificates=False,
            tlsCAFile=certifi.where(),        # ensures trusted CA
            serverSelectionTimeoutMS=5000,    # 5s timeout for connection
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
    Example:
        @router.get("/items")
        async def get_items(db=Depends(get_database)):
            ...
    """
    return get_db()


# -------------------------------------------------------
# 🧠 Health check with retry (Render-safe)
# -------------------------------------------------------
async def ping(max_retries: int = 5, delay_s: float = 2.0) -> bool:
    """
    Check MongoDB connection health with retry logic.
    Returns True if 'ping' succeeds, False otherwise.
    """
    client = get_client()
    for attempt in range(1, max_retries + 1):
        try:
            res = await client.admin.command("ping")
            if res.get("ok", 0) == 1:
                print(f"[✅] MongoDB ping successful (attempt {attempt})")
                return True
        except ServerSelectionTimeoutError as e:
            print(f"[⚠️] MongoDB ping timeout (attempt {attempt}/{max_retries}): {e}")
        except Exception as e:
            print(f"[❌] MongoDB ping failed (attempt {attempt}/{max_retries}): {e}")
        await asyncio.sleep(delay_s)
    print("[🚫] MongoDB ping failed after retries.")
    return False
