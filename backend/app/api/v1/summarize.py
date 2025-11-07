from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Literal
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime
import asyncio

from ...services.summarize_llm import summarize_text
from ...services.db_summary import get_summary, save_summary
from ...db.mongo import get_database, get_db

router = APIRouter(tags=["Summarization"])

# -------------------------------------------------------
# 🧩 Request / Response Models
# -------------------------------------------------------
class SummarizeIn(BaseModel):
    paper_id: str = Field(..., description="MongoDB ObjectId of the paper")
    summary_type: Literal["short", "medium", "detailed"] = "medium"
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


# Async jobs
class SummarizeAsyncRequest(BaseModel):
    paper_id: str
    summary_type: Literal["short", "medium", "detailed"] = "medium"
    use_cache: bool = True


class SummarizeAsyncResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "error"] = "queued"


class JobResult(BaseModel):
    status: Literal["queued", "running", "done", "error"]
    summary: Optional[str] = None
    chunks: Optional[int] = None
    successful_chunks: Optional[int] = None
    duration_ms: Optional[int] =
