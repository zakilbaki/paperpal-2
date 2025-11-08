from __future__ import annotations
import time
import fitz  # PyMuPDF
from fastapi import APIRouter, File, UploadFile, HTTPException
from bson import ObjectId
from app.db.mongo import get_db

router = APIRouter(tags=["papers"])

@router.post("/upload")
async def upload_paper(file: UploadFile = File(...)):
    """
    Upload a PDF, extract text, and store it in MongoDB.
    Returns the new paper_id.
    """
    try:
        t0 = time.perf_counter()
        contents = await file.read()

        # 🚫 Limit upload size to 1 MB
        MAX_SIZE_MB = 1
        if len(contents) > MAX_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max allowed size is {MAX_SIZE_MB} MB."
            )

        # Extract text from the PDF
        text = ""
        with fitz.open(stream=contents, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text("text") + "\n"

        if not text.strip():
            raise HTTPException(status_code=400, detail="Empty or unreadable PDF")

        # Insert into MongoDB
        db = get_db()
        res = await db.papers.insert_one({
            "filename": file.filename,
            "text": text,
            "created_at": time.time(),
            "size_bytes": len(contents),
        })

        t1 = time.perf_counter()
        paper_id = str(res.inserted_id)

        return {
            "status": "success",
            "paper_id": paper_id,
            "duration_ms": int((t1 - t0) * 1000)
        }

    except HTTPException:
        raise  # preserve intentional errors (like file too large)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
