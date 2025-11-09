from __future__ import annotations
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class Section(BaseModel):
    title: str
    content: str


class PaperUploadResponse(BaseModel):
    doc_id: str
    filename: str
    content_type: str
    size_bytes: int
    num_sections: int
    char_count: int
    sections: List[Section]  # ✅ Use proper model, not Dict
    paper_title: Optional[str] = None

    class Config:
        # ⚙️ Let Pydantic handle forward refs automatically
        populate_by_name = True


class PaperMetaDB(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
