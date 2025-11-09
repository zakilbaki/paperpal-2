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
