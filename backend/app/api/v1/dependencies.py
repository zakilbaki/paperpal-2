from ...core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient

_client = None

def get_db():
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGODB_URI)
    return _client[settings.MONGODB_DB]
