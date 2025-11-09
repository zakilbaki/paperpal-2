from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Any, List
import time

from ..dependencies import get_db  # if you have such helper
from ...services.compare import compare_papers

router = APIRouter()

class CompareRequest(BaseModel):
    paper_id_a: str = Field(..., description="ObjectId of first paper")
    paper_id_b: str = Field(..., description="ObjectId of second paper")
    section_aware: bool = Field(True, description="Whether to compare by sections")

@router.post("/compare", tags=["Comparison"])
async def compare_papers_endpoint(payload: CompareRequest, db=Depends(get_db)):
    try:
        paper_id_a = ObjectId(payload.paper_id_a)
        paper_id_b = ObjectId(payload.paper_id_b)
        result = await compare_papers(
            db=db,
            paper_id_a=paper_id_a,
            paper_id_b=paper_id_b,
            section_aware=payload.section_aware,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
