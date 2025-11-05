from transformers import pipeline
import os
import time
import torch
import re

# -------------------------------------------------------
# ⚙️ CONFIGURATION
# -------------------------------------------------------
DEFAULT_MODEL = os.getenv("SUMMARY_MODEL_NAME", "sshleifer/distilbart-cnn-12-6")
MAX_TOKENS = int(os.getenv("SUMMARY_MAX_TOKENS", "400"))

_summarizer = None


# -------------------------------------------------------
# 🧹 Text Cleaning Utility
# -------------------------------------------------------
def clean_text(text: str) -> str:
    """Remove artifacts and garbage tokens."""
    text = re.sub(r"(TextColor|Filename|escription|▬|■|□|▲|▶|►|▪|●|–|—|‐|-)", " ", text)
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"[^a-zA-Z0-9.,;:!?%'\-\s]", "", text)
    text = re.sub(r"\n+", " ", text)
    return text.strip()


# -------------------------------------------------------
# 🧠 Lazy-load summarizer (RAM-friendly)
# -------------------------------------------------------
def _get_summarizer():
    global _summarizer
    if _summarizer is None:
        device = 0 if torch.cuda.is_available() else -1
        print(f"[SUMMARY] Loading summarizer model: {DEFAULT_MODEL} (device={device})")
        _summarizer = pipeline(
            "summarization",
            model=DEFAULT_MODEL,
            device=device,
        )
        print("[SUMMARY] Model ready ✅")
    return _summarizer


# -------------------------------------------------------
# 🧩 Summarize Text
# -------------------------------------------------------
def summarize_text(text: str, summary_type: str = "medium") -> dict:
    start = time.time()
    if not text.strip():
        raise ValueError("Input text is empty.")

    text = clean_text(text)
    summarizer = _get_summarizer()

    try:
        result = summarizer(
            text[:3000],  # limit input length to stay safe on Render
            max_length=200,
            min_length=50,
            do_sample=False,
        )
        summary = result[0]["summary_text"]
    except Exception as e:
        summary = f"[ERROR] Summarization failed: {e}"

    duration = int((time.time() - start) * 1000)
    print(f"[SUMMARY] ✅ Completed in {duration} ms")

    return {
        "summary": summary,
        "duration_ms": duration,
        "model_name": DEFAULT_MODEL,
        "cached": False,
    }
