import os
import numpy as np
from bson import ObjectId
from sentence_transformers import SentenceTransformer
from typing import Any, Dict, List

# -------------------------------------------------------
# 🧠 Global model configuration
# -------------------------------------------------------
DEFAULT_MODEL = os.getenv("STS_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
_model: SentenceTransformer | None = None


# -------------------------------------------------------
# 🔹 Core utilities
# -------------------------------------------------------
def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def get_model() -> SentenceTransformer:
    """Load or reuse the SentenceTransformer model."""
    global _model
    if _model is None:
        print(f"[COMPARE] 🚀 Loading semantic model: {DEFAULT_MODEL}")
        _model = SentenceTransformer(DEFAULT_MODEL)
    return _model


def similarity(text_a: str, text_b: str) -> float:
    """
    Compute semantic similarity (0–1) between two text strings using embeddings.
    Uses cosine similarity normalized to [0, 1].
    """
    if not text_a.strip() or not text_b.strip():
        return 0.0
    model = get_model()
    emb = model.encode([text_a, text_b], convert_to_numpy=True)
    cos = _cosine(emb[0], emb[1])
    return round((cos + 1.0) / 2.0, 3)


# -------------------------------------------------------
# 🔹 Helper: extract usable text
# -------------------------------------------------------
def _extract_text_field(paper: Dict[str, Any], key: str) -> str:
    """Safely extract a text field from paper, handling dicts like summary = {'text': '...'}."""
    val = paper.get(key, "")
    if isinstance(val, dict):
        return val.get("text", "")
    return str(val or "")


# -------------------------------------------------------
# 🔹 MongoDB paper comparison
# -------------------------------------------------------
async def compare_papers(
    db,
    paper_id_a: ObjectId,
    paper_id_b: ObjectId,
    section_aware: bool = True
) -> Dict[str, Any]:
    """
    Compare two papers stored in MongoDB by their text fields.
    If section_aware=True, compute similarity per section (title, abstract, summary, keywords).
    """
    paper_a = await db["papers"].find_one({"_id": paper_id_a})
    paper_b = await db["papers"].find_one({"_id": paper_id_b})

    if not paper_a or not paper_b:
        raise ValueError("One or both papers not found in the database.")

    # ------------------------------------
    # 1️⃣ Extract comparable sections
    # ------------------------------------
    fields_to_compare = ["title", "abstract", "summary", "keywords"]
    results: Dict[str, float] = {}
    total_score = 0.0
    compared_sections = 0

    for field in fields_to_compare:
        text_a = _extract_text_field(paper_a, field)
        text_b = _extract_text_field(paper_b, field)

        # handle keywords stored as list of dicts or strings
        if field == "keywords":
            if isinstance(paper_a.get("keywords"), list):
                text_a = " ".join(
                    kw["text"] if isinstance(kw, dict) else str(kw)
                    for kw in paper_a["keywords"]
                )
            if isinstance(paper_b.get("keywords"), list):
                text_b = " ".join(
                    kw["text"] if isinstance(kw, dict) else str(kw)
                    for kw in paper_b["keywords"]
                )

        if not text_a.strip() or not text_b.strip():
            continue

        try:
            score = similarity(text_a, text_b)
        except Exception as err:
            print(f"[WARN] Section '{field}' similarity failed: {err}")
            score = 0.0

        results[field] = score
        total_score += score
        compared_sections += 1

    # ------------------------------------
    # 2️⃣ Compute overall similarity
    # ------------------------------------
    overall = round(total_score / compared_sections, 3) if compared_sections > 0 else 0.0

    # ------------------------------------
    # 3️⃣ Build response
    # ------------------------------------
    return {
        "paper_a": str(paper_id_a),
        "paper_b": str(paper_id_b),
        "section_aware": section_aware,
        "section_scores": results,
        "overall_similarity": overall,
    }
