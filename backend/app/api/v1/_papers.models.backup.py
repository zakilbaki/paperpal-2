from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from ...services.keywords import KeywordService
from ...models.schemas import KeywordsRequest, KeywordsResponse

router = APIRouter(tags=["papers"])  # ✅ no prefix here; handled in main.py


# -------------------------------------------------------
# 🧩 Dependency: get database handle
# -------------------------------------------------------
async def get_db():
    """Return an AsyncIOMotorDatabase instance."""
    from app.core.config import settings
    client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        tls=True,
        tlsAllowInvalidCertificates=False
    )
    return client[settings.MONGODB_DB]


# -------------------------------------------------------
# 🧠 Keyword Extraction Endpoint
# -------------------------------------------------------
@router.post("/keywords", response_model=KeywordsResponse)
async def extract_keywords(
    payload: KeywordsRequest,
    db=Depends(get_db)
):
    """
    Extract top keywords from a paper summary or full text.
    Cached results are returned instantly if already stored in MongoDB.
    """
    try:
        service = KeywordService(db)
        result = await service.extract(
            paper_id=payload.paper_id,
            top_k=payload.top_k
        )
        return KeywordsResponse(**result)

    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Keyword extraction failed: {e}")
