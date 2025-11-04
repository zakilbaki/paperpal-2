from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId
from bson.errors import InvalidId

from ...services.summarize_llm import summarize_text
from ...services.db_summary import get_summary, save_summary
from ...db.mongo import get_database

router = APIRouter(tags=["Summarization"])

# -------------------------------------------------------
# 🧩 Request / Response Models
# -------------------------------------------------------
class SummarizeIn(BaseModel):
    paper_id: str = Field(..., description="MongoDB ObjectId of the paper")
    summary_type: str = Field("medium", description="Summary type: short | medium | detailed")
    max_tokens: Optional[int] = Field(None, description="Override max tokens (optional)")
    strategy: str = "map_reduce"
    use_cache: bool = Field(False, description="If True, reuse cached summary instead of regenerating")


class SummarizeOut(BaseModel):
    paper_id: str
    summary_type: str
    summary: str
    chunks: int
    duration_ms: int
    cached: bool


# -------------------------------------------------------
# ⚙️ Token Mapping Helper
# -------------------------------------------------------
def _max_tokens_for_type(summary_type: str) -> int:
    mapping = {"short": 120, "medium": 256, "detailed": 512}
    return mapping.get(summary_type.lower(), 256)


# -------------------------------------------------------
# 🚀 Summarization Endpoint
# -------------------------------------------------------
@router.post("/summarize", response_model=SummarizeOut)
async def summarize_paper(payload: SummarizeIn, db=Depends(get_database)):
    """
    Summarize a paper’s text. Regenerates on click unless use_cache=True.
    Stores results per summary_type under summaries.<type>.
    """
    summary_type = payload.summary_type.lower().strip()
    print(f"[SUMMARY] Received summarization request for {payload.paper_id} ({summary_type})")

    # ✅ Validate ID
    try:
        paper_oid = ObjectId(payload.paper_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid paper ID format")

    # 1️⃣ Check cache
    if payload.use_cache:
        cached_summary = await get_summary(payload.paper_id, summary_type)
        if cached_summary:
            print(f"[SUMMARY] Returning cached {summary_type} summary.")
            return SummarizeOut(
                paper_id=payload.paper_id,
                summary_type=summary_type,
                summary=cached_summary.get("text"),
                chunks=cached_summary.get("chunks", 0),
                duration_ms=cached_summary.get("duration_ms", 0),
                cached=True,
            )

    # 2️⃣ Retrieve paper text
    paper = await db.papers.find_one({"_id": paper_oid})
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found in MongoDB")

    full_text = paper.get("text") or paper.get("content") or ""
    if not full_text.strip():
        raise HTTPException(status_code=400, detail="Paper text is empty")

    # 3️⃣ Determine max token count
    max_tokens = payload.max_tokens or _max_tokens_for_type(summary_type)
    print(f"[SUMMARY] Regenerating {summary_type} summary (max_tokens={max_tokens})")

    # 4️⃣ Run summarizer
    res = await summarize_text(text=full_text, max_tokens=max_tokens, summary_type=summary_type)
    if not res or "summary" not in res:
        raise RuntimeError("Summarization returned no result")

    print(f"[SUMMARY] Summarization successful — {len(res['summary'])} chars")

    summary_data = {
        "text": res["summary"],
        "chunks": res["chunks"],
        "duration_ms": res["duration_ms"],
        "model": {
            "id": res.get("model_name", "facebook/bart-large-cnn"),
            "strategy": payload.strategy,
            "max_tokens": max_tokens,
        },
    }

    # 5️⃣ Save result
    await save_summary(payload.paper_id, summary_data, summary_type)
    print(f"[SUMMARY] ✅ {summary_type.capitalize()} summary saved to MongoDB.")

    return SummarizeOut(
        paper_id=payload.paper_id,
        summary_type=summary_type,
        summary=summary_data["text"],
        chunks=summary_data["chunks"],
        duration_ms=summary_data["duration_ms"],
        cached=False,
    )


# Optional health check
@router.get("/summarize")
async def summarize_ping():
    return {"message": "Summarization endpoint active"}
