from __future__ import annotations
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import certifi
import datetime as dt

# -------------------------------------------------------
# ⚙️ Mongo connection (from environment)
# -------------------------------------------------------
MONGO_URI = os.getenv("MONGODB_URI")
MONGO_DB = os.getenv("MONGODB_DB", "paperpal_db")
MONGO_COLL = os.getenv("MONGODB_COLLECTION_PAPERS", "papers")

_client = AsyncIOMotorClient(MONGO_URI, tls=True, tlsCAFile=certifi.where())
_db = _client[MONGO_DB]
_coll = _db[MONGO_COLL]

# -------------------------------------------------------
# 🧩 CRUD Helpers (nested summaries)
# -------------------------------------------------------

async def get_summary(paper_id: str, summary_type: str = "medium") -> Optional[Dict[str, Any]]:
    """
    Retrieve a summary of the given type ('short', 'medium', 'detailed').
    Falls back to legacy single-field 'summary' if the new structure is missing.
    """
    projection = {f"summaries.{summary_type}": 1, "summary": 1}
    doc = await _coll.find_one({"_id": ObjectId(paper_id)}, projection)
    if not doc:
        return None

    # New structure: summaries.short / summaries.medium / summaries.detailed
    summaries = doc.get("summaries", {})
    if summary_type in summaries:
        return summaries[summary_type]

    # Backward compatibility (legacy single summary)
    if "summary" in doc:
        return doc["summary"]

    return None


async def save_summary(
    paper_id: str,
    summary_data: Dict[str, Any],
    summary_type: str = "medium",
) -> None:
    """
    Save or overwrite a summary of a specific type into:
        summaries.<type> = summary_data
    """
    await _coll.update_one(
        {"_id": ObjectId(paper_id)},
        {
            "$set": {
                f"summaries.{summary_type}": summary_data,
                "summaries.updated_at": dt.datetime.utcnow(),
            }
        },
        upsert=True,
    )


async def clear_summary(paper_id: str, summary_type: Optional[str] = None) -> None:
    """
    Remove one summary type or all nested summaries.
    """
    if summary_type:
        await _coll.update_one(
            {"_id": ObjectId(paper_id)},
            {"$unset": {f"summaries.{summary_type}": ""}},
        )
    else:
        await _coll.update_one(
            {"_id": ObjectId(paper_id)},
            {"$unset": {"summaries": ""}},
        )
