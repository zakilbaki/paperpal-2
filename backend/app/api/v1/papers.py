from __future__ import annotations
from typing import List, Dict
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends

# ✅ FIXED imports for Render and local
from backend.app.db.mongo import get_database
from backend.app.models.paper import PaperMetaDB, PaperUploadResponse
from backend.app.services.pdf_parser import extract_pdf_text, segment_sections

router = APIRouter()

@router.post("/upload", response_model=PaperUploadResponse)
async def upload_paper(
    file: UploadFile = File(..., description="PDF file to analyze"),
    db=Depends(get_database),
):
    # ---------------------------------------------------------
    # 🧩 1. Validate file type
    # ---------------------------------------------------------
    if file.content_type not in {
        "application/pdf",
        "application/x-pdf",
        "binary/octet-stream",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a PDF file.",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file.",
        )

    # ---------------------------------------------------------
    # 🧠 2. Extract text
    # ---------------------------------------------------------
    try:
        text = extract_pdf_text(raw)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"PDF parse error: {e}",
        )

    # ---------------------------------------------------------
    # 📚 3. Segment into sections
    # ---------------------------------------------------------
    sections_raw = segment_sections(text)
    sections: List[Dict[str, str]] = []

    for s in sections_raw:
        raw_title = (s.get("title") or s.get("name") or "").strip()
        content = s.get("content") or s.get("text") or ""

        # 🧹 Clean and normalize section title
        if not raw_title or raw_title.isdigit() or len(raw_title) < 3:
            lower_text = content.lower()
            if "abstract" in lower_text[:600]:
                raw_title = "Abstract"
            elif "introduction" in lower_text[:800]:
                raw_title = "Introduction"
            elif "conclusion" in lower_text[-1500:]:
                raw_title = "Conclusion"
            elif "reference" in lower_text[-2000:]:
                raw_title = "References"
            else:
                raw_title = "Untitled Section"

        title = raw_title.capitalize()
        sections.append({"title": title, "content": content})

    # ---------------------------------------------------------
    # 🏷️ 3.5 Infer paper title from first lines
    # ---------------------------------------------------------
    paper_title = "Unknown Title"
    if sections:
        first_title = sections[0]["title"]
        if first_title.lower().startswith("untitled") or first_title.isdigit() or len(first_title) < 3:
            first_line = next((line.strip() for line in text.splitlines() if len(line.strip()) > 5), None)
            if first_line:
                paper_title = first_line
                sections[0]["title"] = paper_title
        else:
            paper_title = first_title

    # ---------------------------------------------------------
    # 💾 4. Store metadata in MongoDB
    # ---------------------------------------------------------
    meta = PaperMetaDB(
        filename=file.filename or "uploaded.pdf",
        content_type=file.content_type,
        size_bytes=len(raw),
    ).model_dump()

    meta["paper_title"] = paper_title

    result = await db.papers.insert_one(meta)
    paper_id = str(result.inserted_id)

    # ---------------------------------------------------------
    # 📤 5. Return structured response
    # ---------------------------------------------------------
    return PaperUploadResponse(
        doc_id=paper_id,
        filename=meta["filename"],
        content_type=meta["content_type"],
        size_bytes=meta["size_bytes"],
        num_sections=len(sections),
        sections=sections,
        char_count=len(text),
        paper_title=paper_title,
    )

# ✅ Ensures model rebuild for Pydantic v2
PaperUploadResponse.model_rebuild()
