# --- Keyword Extraction Schemas ---
from pydantic import BaseModel
from typing import List

class KeywordsRequest(BaseModel):
    paper_id: str
    top_k: int = 15
    use_cache: bool = False   # 🚀 new field


class KeywordItem(BaseModel):
    text: str
    score: float

class KeywordsResponse(BaseModel):
    paper_id: str
    keywords: List[KeywordItem]
    cached: bool
    duration_ms: int
# --- Async summarization models ---
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

JobStatus = Literal["queued", "running", "done", "error"]

class SummarizeAsyncRequest(BaseModel):
    paper_id: str
    summary_type: Literal["short", "medium", "detailed"] = "medium"
    use_cache: bool = True

class SummarizeAsyncResponse(BaseModel):
    job_id: str
    status: JobStatus = "queued"

class JobResult(BaseModel):
    status: JobStatus
    summary: Optional[str] = None
    chunks: Optional[int] = None
    successful_chunks: Optional[int] = None
    duration_ms: Optional[int] = None
    model_name: Optional[str] = None
    cached: Optional[bool] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
