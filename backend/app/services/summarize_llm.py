from transformers import pipeline, AutoTokenizer
from concurrent.futures import ThreadPoolExecutor
import os
import time
import asyncio
import torch
import re

# -------------------------------------------------------
# ⚙️ CONFIGURATION
# -------------------------------------------------------
DEFAULT_MODEL = os.getenv("SUMMARY_MODEL_NAME", "facebook/bart-base")
MAX_TOKENS_PER_CHUNK = int(os.getenv("SUMMARY_MAX_TOKENS_PER_CHUNK", "700"))
OVERLAP = int(os.getenv("SUMMARY_OVERLAP", "30"))
PER_CHUNK_MAX_NEW_TOKENS = int(os.getenv("SUMMARY_PER_CHUNK_MAX_NEW_TOKENS", "150"))
REDUCE_MAX_NEW_TOKENS = int(os.getenv("SUMMARY_REDUCE_MAX_NEW_TOKENS", "200"))
MAX_WORKERS = int(os.getenv("SUMMARY_MAX_WORKERS", "8"))  # concurrent threads

_tokenizer = None
_summarizer = None


# -------------------------------------------------------
# 🧹 Text Cleaning Utility
# -------------------------------------------------------
def clean_text(text: str) -> str:
    """Remove OCR artifacts, extra symbols, and garbage tokens."""
    text = re.sub(r"(TextColor|Filename|escription|▬|■|□|▲|▶|►|▪|●|–|—|‐|-)", " ", text)
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"[^a-zA-Z0-9.,;:!?%'\-\s]", "", text)
    text = re.sub(r"\n+", " ", text)
    return text.strip()


# -------------------------------------------------------
# 🔤 Tokenizer / Model loader
# -------------------------------------------------------
def _get_tokenizer(model_name: str = DEFAULT_MODEL):
    """Lazy-load tokenizer."""
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    return _tokenizer


def _get_summarizer(model_name: str = DEFAULT_MODEL):
    """Lazy-load summarization model (GPU auto-detect)."""
    global _summarizer
    if _summarizer is None:
        device = 0 if torch.cuda.is_available() else -1
        _summarizer = pipeline(
            "summarization",
            model=model_name,
            tokenizer=_get_tokenizer(model_name),
            device=device,
        )
        print(f"[SUMMARY] 🚀 Loaded summarizer model: {model_name} (device={device})")
    return _summarizer


# -------------------------------------------------------
# 🧩 Token-safe chunking
# -------------------------------------------------------
def _chunk_text_token_safe(text: str, max_tokens: int = MAX_TOKENS_PER_CHUNK):
    """Split long text into safe token chunks for summarization."""
    tok = _get_tokenizer()
    ids = tok.encode(text, add_special_tokens=False)
    stride = max_tokens - OVERLAP
    chunks = []
    for i in range(0, len(ids), stride):
        chunk_ids = ids[i:i + max_tokens]
        chunks.append(tok.decode(chunk_ids, skip_special_tokens=True))
        if i + max_tokens >= len(ids):
            break
    return chunks


# -------------------------------------------------------
# 🧠 Parallel summarization (multi-threaded)
# -------------------------------------------------------
async def summarize_text(text: str, max_tokens: int = 512, summary_type: str = "medium") -> dict:
    """
    Chunk-aware summarization with true parallel processing and model switching.
    - short / medium → bart-base
    - detailed → bart-large-cnn
    """
    start = time.time()
    if not text.strip():
        raise ValueError("Input text is empty.")

    # 🧹 Clean text before summarizing
    cleaned_text = clean_text(text)
    if len(cleaned_text) < 50:
        raise ValueError("Paper text too short after cleaning.")

    # Pick model based on summary type
    model_name = "facebook/bart-large-cnn" if summary_type.lower() == "detailed" else DEFAULT_MODEL
    summarizer = _get_summarizer(model_name)
    tokenizer = _get_tokenizer(model_name)

    chunks = _chunk_text_token_safe(cleaned_text, MAX_TOKENS_PER_CHUNK)
    print(f"[SUMMARY] Total chunks: {len(chunks)} | Model: {model_name}")

    # Define worker for one chunk
    def summarize_chunk(chunk: str, idx: int):
        token_len = len(tokenizer.encode(chunk, add_special_tokens=False))
        if token_len > MAX_TOKENS_PER_CHUNK:
            print(f"[SUMMARY] ⚠️ Skipping chunk {idx}: {token_len} tokens")
            return ""
        try:
            print(f"[SUMMARY] Summarizing chunk {idx}/{len(chunks)} ({token_len} tokens)")
            result = summarizer(
                chunk,
                max_length=min(max_tokens, PER_CHUNK_MAX_NEW_TOKENS),
                min_length=int(min(max_tokens, PER_CHUNK_MAX_NEW_TOKENS) * 0.4),
                do_sample=False,
            )
            return result[0]["summary_text"].strip()
        except Exception as e:
            print(f"[SUMMARY] ❌ Chunk {idx} failed: {e}")
            return ""

    # Run all chunks concurrently
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(chunks))) as executor:
        tasks = [loop.run_in_executor(executor, summarize_chunk, ch, i + 1)
                 for i, ch in enumerate(chunks)]
        summaries = await asyncio.gather(*tasks)

    summaries = [s for s in summaries if s]
    final_summary = " ".join(summaries).strip()
    duration = int((time.time() - start) * 1000)

    print(f"[SUMMARY] ✅ Completed {len(summaries)} summaries in {duration} ms")

    return {
        "summary": final_summary,
        "chunks": len(chunks),
        "successful_chunks": len(summaries),
        "duration_ms": duration,
        "max_tokens_used": max_tokens,
        "model_name": model_name,
        "cached": False,
    }
