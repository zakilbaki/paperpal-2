from transformers import pipeline, AutoTokenizer
from concurrent.futures import ThreadPoolExecutor
import os, time, asyncio, torch, re

# -------------------------------------------------------
# ⚙️ CONFIGURATION (Render-optimized)
# -------------------------------------------------------
DEFAULT_MODEL = os.getenv("SUMMARY_MODEL_NAME", "sshleifer/distilbart-cnn-12-6")
DETAILED_MODEL = os.getenv("SUMMARY_MODEL_DETAILED", "google/pegasus-xsum")

MAX_TOKENS_PER_CHUNK = 400
OVERLAP = 20
PER_CHUNK_MAX_NEW_TOKENS = 80
REDUCE_MAX_NEW_TOKENS = 160
MAX_WORKERS = 2
LOG_PREFIX = "[SUMMARY]"

_tokenizer_cache = {}
_summarizer_cache = {}

# -------------------------------------------------------
# 🧹 Text Cleaning
# -------------------------------------------------------
def clean_text(text: str) -> str:
    text = re.sub(r"(TextColor|Filename|escription|▬|■|□|▲|▶|►|▪|●|–|—|‐|-)", " ", text)
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"[^a-zA-Z0-9.,;:!?%'\-\s]", "", text)
    text = re.sub(r"\n+", " ", text)
    return text.strip()

# -------------------------------------------------------
# 🔤 Lazy Model Loading
# -------------------------------------------------------
def _get_tokenizer(model_name: str):
    if model_name not in _tokenizer_cache:
        _tokenizer_cache[model_name] = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    return _tokenizer_cache[model_name]

def _get_summarizer(model_name: str):
    if model_name not in _summarizer_cache:
        device = 0 if torch.cuda.is_available() else -1
        _summarizer_cache[model_name] = pipeline(
            "summarization",
            model=model_name,
            tokenizer=_get_tokenizer(model_name),
            device=device,
        )
        print(f"{LOG_PREFIX} 🚀 Loaded summarizer: {model_name} (device={device})")
    return _summarizer_cache[model_name]

# -------------------------------------------------------
# 🧩 Token-safe Chunking
# -------------------------------------------------------
def _chunk_text_token_safe(text: str, max_tokens: int = MAX_TOKENS_PER_CHUNK):
    tok = _get_tokenizer(DEFAULT_MODEL)
    ids = tok.encode(text, add_special_tokens=False)
    stride = max_tokens - OVERLAP
    return [tok.decode(ids[i:i + max_tokens], skip_special_tokens=True) for i in range(0, len(ids), stride)]

# -------------------------------------------------------
# ⚡ Main Summarization
# -------------------------------------------------------
async def summarize_text(text: str, max_tokens: int = 512, summary_type: str = "medium") -> dict:
    if not text.strip():
        raise ValueError("Empty text cannot be summarized.")

    start_time = time.time()
    cleaned = clean_text(text)
    if len(cleaned.split()) < 120:
        return {
            "summary": cleaned[:800] + "...",
            "chunks": 1,
            "successful_chunks": 1,
            "duration_ms": 0,
            "model_name": "none",
            "cached": True
        }

    # Choose model
    if summary_type.lower() == "detailed":
        model_name = DETAILED_MODEL
        max_new_tokens = REDUCE_MAX_NEW_TOKENS
    else:
        model_name = DEFAULT_MODEL
        max_new_tokens = PER_CHUNK_MAX_NEW_TOKENS

    summarizer = _get_summarizer(model_name)
    tokenizer = _get_tokenizer(model_name)
    chunks = _chunk_text_token_safe(cleaned, MAX_TOKENS_PER_CHUNK)
    print(f"{LOG_PREFIX} 🕒 Start summarization ({summary_type}) with {len(chunks)} chunks")

    if not chunks:
        return {"summary": "", "chunks": 0, "duration_ms": 0}

    def summarize_chunk_sync(chunk: str) -> str:
        try:
            return summarizer(
                chunk,
                max_new_tokens=max_new_tokens,
                min_length=int(max_new_tokens * 0.4),
                do_sample=False,
            )[0]["summary_text"].strip()
        except Exception as e:
            print(f"{LOG_PREFIX} ❌ Chunk failed: {e}")
            return ""

    # Run with limited concurrency
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(chunks))) as executor:
        tasks = [loop.run_in_executor(executor, summarize_chunk_sync, ch) for ch in chunks]
        summaries = await asyncio.gather(*tasks)

    summaries = [s for s in summaries if s]
    combined = " ".join(summaries).strip()

    # Second-pass compression for long outputs
    if len(summaries) > 1 and len(combined.split()) > 400:
        try:
            print(f"{LOG_PREFIX} 🔁 Refining final summary...")
            combined = summarizer(
                combined,
                max_new_tokens=max_new_tokens,
                min_length=int(max_new_tokens * 0.5),
                do_sample=False,
            )[0]["summary_text"].strip()
        except Exception as e:
            print(f"{LOG_PREFIX} ⚠️ Refinement failed: {e}")

    duration_ms = int((time.time() - start_time) * 1000)
    print(f"{LOG_PREFIX} ✅ Done in {duration_ms/1000:.2f}s, used model={model_name}")

    return {
        "summary": combined,
        "chunks": len(chunks),
        "successful_chunks": len(summaries),
        "duration_ms": duration_ms,
        "model_name": model_name,
        "max_new_tokens": max_new_tokens,
        "cached": False,
    }
