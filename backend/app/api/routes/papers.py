
# --- Keyword Extraction Endpoint ---
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from app.services.keywords import KeywordService
from app.models.schemas import KeywordsRequest, KeywordsResponse

router = APIRouter(prefix="/api/v1/papers", tags=["papers"])

async def get_db() -> AsyncIOMotorClient:
    from app.core.config import settings
    return AsyncIOMotorClient(
        settings.MONGODB_URI,
        tls=True,
        tlsAllowInvalidCertificates=False
    )

@router.post("/keywords", response_model=KeywordsResponse)
async def extract_keywords(
    payload: KeywordsRequest,
    db: AsyncIOMotorClient = Depends(get_db)
):
    """Extract and cache top keywords for a paper."""
    try:
        service = KeywordService(db)
        result = await service.extract(paper_id=payload.paper_id, top_k=payload.top_k)
        return KeywordsResponse(**result)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Keyword extraction failed: {e}")
