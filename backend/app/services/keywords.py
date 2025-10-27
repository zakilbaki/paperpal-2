from __future__ import annotations
from typing import Dict, Any, Optional
import time
from yake import KeywordExtractor
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId


class KeywordService:
    """YAKE keyword extraction with Mongo caching."""

    def __init__(self, db: AsyncIOMotorClient):
        self.db = db

    async def extract(self, paper_id: str, top_k: int = 15) -> Dict[str, Any]:
        start = time.time()
        coll = self.db.get_default_database()["papers"]

        # 1️⃣ Check cache
        doc = await coll.find_one({"_id": ObjectId(paper_id)}, {"keywords": 1})
        if doc and "keywords" in doc and doc["keywords"]:
            return {
                "paper_id": paper_id,
                "keywords": doc["keywords"],
                "cached": True,
                "duration_ms": int((time.time() - start) * 1000),
            }

        # 2️⃣ Load text
        doc = await coll.find_one({"_id": ObjectId(paper_id)})
        if not doc:
            raise ValueError("Paper not found")

        source_text: Optional[str] = None
        for key in ("full_text", "text", "content_text"):
            if isinstance(doc.get(key), str) and doc[key].strip():
                source_text = doc[key]
                break

        if not source_text:
            summary = (doc.get("summary") or {}).get("text")
            if isinstance(summary, str) and summary.strip():
                source_text = summary

        if not source_text:
            raise ValueError("No text available for keyword extraction")

        # 3️⃣ Extract
        extractor = KeywordExtractor(lan="en", n=3, dedupLim=0.9, top=top_k)
        keywords = [{"text": k, "score": float(s)} for k, s in extractor.extract_keywords(source_text)]

        # 4️⃣ Save
        await coll.update_one({"_id": ObjectId(paper_id)}, {"$set": {"keywords": keywords}}, upsert=False)

        return {
            "paper_id": paper_id,
            "keywords": keywords,
            "cached": False,
            "duration_ms": int((time.time() - start) * 1000),
        }
