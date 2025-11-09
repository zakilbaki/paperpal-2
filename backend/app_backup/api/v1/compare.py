from __future__ import annotations
import time
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from bson import ObjectId
from bson.errors import InvalidId
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ...db.mongo import get_database

router = APIRouter(tags=["Comparison"])


# -------------------------------------------------------
# 📄 Request schema
# -------------------------------------------------------
class CompareRequest(BaseModel):
    paper_id_a: str = Field(..., description="ObjectId of the first paper")
    paper_id_b: str = Field(..., description="ObjectId of the second paper")
    section_aware: bool = Field(True, description="Whether to compare section by section")
    use_cache: bool = Field(True, description="Use cached results if available")


# -------------------------------------------------------
# 🧩 Utility: safe text extraction
# -------------------------------------------------------
def _extract_text_field(paper: Dict[str, Any], key: str) -> str:
    """Safely extract text or nested dict values from Mongo document."""
    val = paper.get(key, "")
    if isinstance(val, dict):
        return val.get("text", "")
    return str(val or "")


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences of reasonable length."""
    import re
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 20]


# -------------------------------------------------------
# 🧠 Core comparison logic
# -------------------------------------------------------
async def compare_papers(
    db,
    paper_id_a: ObjectId,
    paper_id_b: ObjectId,
    section_aware: bool = True
) -> Dict[str, Any]:
    start_time = time.time()

    # --- Fetch both papers ---
    paper_a = await db.papers.find_one({"_id": paper_id_a})
    paper_b = await db.papers.find_one({"_id": paper_id_b})
    if not paper_a or not paper_b:
        raise HTTPException(status_code=404, detail="One or both papers not found in MongoDB.")

    # --- Extract main text for overall similarity ---
    text_a = _extract_text_field(paper_a, "summary") or _extract_text_field(paper_a, "text")
    text_b = _extract_text_field(paper_b, "summary") or _extract_text_field(paper_b, "text")

    if not text_a.strip() or not text_b.strip():
        return {
            "overall_similarity": 0.0,
            "section_scores": {},
            "section_matrix": {},
            "keyword_overlap": {},
            "similar_sentences": [],
        }

    # --- Compute overall similarity using TF-IDF ---
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform([text_a, text_b])
    overall_similarity = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])

    # --- Section-aware comparison ---
    section_scores: Dict[str, float] = {}
    sections = ["title", "abstract", "summary", "keywords"]
    for sec in sections:
        a = _extract_text_field(paper_a, sec)
        b = _extract_text_field(paper_b, sec)

        # Handle keywords stored as list of dicts or strings
        if sec == "keywords":
            if isinstance(paper_a.get("keywords"), list):
                a = " ".join(
                    kw["text"] if isinstance(kw, dict) else str(kw)
                    for kw in paper_a["keywords"]
                )
            if isinstance(paper_b.get("keywords"), list):
                b = " ".join(
                    kw["text"] if isinstance(kw, dict) else str(kw)
                    for kw in paper_b["keywords"]
                )

        if a.strip() and b.strip():
            try:
                tfidf_s = vectorizer.fit_transform([a, b])
                section_scores[sec] = float(cosine_similarity(tfidf_s[0:1], tfidf_s[1:2])[0][0])
            except Exception:
                section_scores[sec] = 0.0

    # --- Section cross-matrix ---
    section_matrix = {"rows": sections, "cols": sections, "values": []}
    all_a = [_extract_text_field(paper_a, s) for s in sections]
    all_b = [_extract_text_field(paper_b, s) for s in sections]
    for sa in all_a:
        row = []
        for sb in all_b:
            if sa.strip() and sb.strip():
                tfidf_ab = vectorizer.fit_transform([sa, sb])
                val = float(cosine_similarity(tfidf_ab[0:1], tfidf_ab[1:2])[0][0])
            else:
                val = 0.0
            row.append(val)
        section_matrix["values"].append(row)

    # --- Keyword overlap ---
    kws_a = [
        kw["text"].lower() if isinstance(kw, dict) else str(kw).lower()
        for kw in (paper_a.get("keywords") or [])
    ]
    kws_b = [
        kw["text"].lower() if isinstance(kw, dict) else str(kw).lower()
        for kw in (paper_b.get("keywords") or [])
    ]
    if kws_a and kws_b:
        overlap = set(kws_a) & set(kws_b)
        unique_a = list(set(kws_a) - overlap)
        unique_b = list(set(kws_b) - overlap)
        jaccard = len(overlap) / len(set(kws_a) | set(kws_b))
    else:
        overlap, unique_a, unique_b, jaccard = set(), [], [], 0.0

    keyword_overlap = {
        "jaccard": round(jaccard, 3),
        "overlap_count": len(overlap),
        "top_overlap": sorted(list(overlap))[:15],
        "unique_a": unique_a[:15],
        "unique_b": unique_b[:15],
    }

    # --- Similar sentences (summary only) ---
    sentences_a = _split_sentences(_extract_text_field(paper_a, "summary"))
    sentences_b = _split_sentences(_extract_text_field(paper_b, "summary"))
    similar_pairs = []
    if sentences_a and sentences_b:
        vect = TfidfVectorizer(stop_words="english")
        tfidf_all = vect.fit_transform(sentences_a + sentences_b)
        sim_matrix = cosine_similarity(tfidf_all[: len(sentences_a)], tfidf_all[len(sentences_a):])
        for i, row in enumerate(sim_matrix):
            j = int(row.argmax())
            score = float(row[j])
            if score > 0.7:
                similar_pairs.append({
                    "a": sentences_a[i],
                    "b": sentences_b[j],
                    "score": round(score, 3)
                })
        similar_pairs = sorted(similar_pairs, key=lambda x: x["score"], reverse=True)[:15]

    duration = int((time.time() - start_time) * 1000)

    return {
        "overall_similarity": round(overall_similarity, 3),
        "section_scores": section_scores,
        "section_matrix": section_matrix,
        "keyword_overlap": keyword_overlap,
        "similar_sentences": similar_pairs,
        "meta": {
            "paper_a": {"_id": str(paper_id_a), "name": paper_a.get("filename", "Paper A")},
            "paper_b": {"_id": str(paper_id_b), "name": paper_b.get("filename", "Paper B")},
            "duration_ms": duration,
            "cached": False,
        },
    }


# -------------------------------------------------------
# ⚖️ Endpoint
# -------------------------------------------------------
@router.post("/compare")
async def compare_papers_endpoint(payload: CompareRequest, db=Depends(get_database)):
    """Compare two stored papers and return similarity metrics."""
    try:
        print(f"[COMPARE] Payload: {payload.dict()}")

        # --- Validate IDs ---
        try:
            paper_id_a = ObjectId(payload.paper_id_a)
            paper_id_b = ObjectId(payload.paper_id_b)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid ObjectId format")

        # --- Run comparison ---
        res = await compare_papers(db, paper_id_a, paper_id_b, section_aware=payload.section_aware)
        res["meta"]["cached"] = False  # caching to be added later

        return {"status": "success", "data": res}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print("[ERROR] Comparison failed:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}")
