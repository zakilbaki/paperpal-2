from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import asyncio

# services
from ...services.summarize_llm import summarize_map_reduce
from ...services.db_summary import get_summary, save_summary

router = APIRouter(tags=["papers"])

# -------------------------------------------------------
# 📥 Request / Response Schemas
# -------------------------------------------------------
class SummarizeIn(BaseModel):
    paper_id: str = Field(..., description="MongoDB ObjectId of the paper")
    max_tokens: int = 1024
    strategy: str = "map_reduce"

class SummarizeOut(BaseModel):
    paper_id: str
    summary: str
    chunks: int
    duration_ms: int
    cached: bool

# -------------------------------------------------------
# 🚀 Route
# -------------------------------------------------------
@router.post("/summarize", response_model=SummarizeOut)
async def summarize_paper(payload: SummarizeIn):
    # 1️⃣ check existing summary
    cached_summary = await get_summary(payload.paper_id)
    if cached_summary:
        return SummarizeOut(
            paper_id=payload.paper_id,
            summary=cached_summary.get("text"),
            chunks=cached_summary.get("chunks", 0),
            duration_ms=cached_summary.get("duration_ms", 0),
            cached=True,
        )

    # 2️⃣ run summarization
    res = await summarize_map_reduce(full_text=cached_summary or "", max_tokens=payload.max_tokens)

    if not res or "summary" not in res:
        raise HTTPException(status_code=500, detail="Summarization failed")

    summary_data = {
        "text": res["summary"],
        "chunks": res["chunks"],
        "duration_ms": int(res["timings"]["total_sec"] * 1000),
        "model": {"id": "facebook/bart-large-cnn", "strategy": payload.strategy},
    }

    # 3️⃣ save to Mongo
    await save_summary(payload.paper_id, summary_data)

    return SummarizeOut(
        paper_id=payload.paper_id,
        summary=summary_data["text"],
        chunks=summary_data["chunks"],
        duration_ms=summary_data["duration_ms"],
        cached=False,
    )
