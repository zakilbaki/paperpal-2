from transformers import pipeline, AutoTokenizer
from concurrent.futures import ThreadPoolExecutor
import os, time, asyncio, torch, re, math

# -------------------------------------------------------
# ⚙️ CONFIGURATION (Optimized for Render CPU)
# -------------------------------------------------------
DEFAULT_MODEL = os.getenv("SUMMARY_MODEL_NAME", "facebook/bart-base")
DETAILED_MODEL = os.getenv("SUMMARY_MODEL_DETAILED", "facebook/bart-large-cnn")

MAX_TOKENS_PER_CHUNK = int(os.getenv("SUMMARY_MAX_TOKENS_PER_CHUNK", "500"))
OVERLAP = int(os.getenv("SUMMARY_OVERLAP", "10"))
PER_CHUNK_MAX_NEW_TOKENS = int(os.getenv("SUMMARY_PER_CHUNK_MAX_NEW_TOKENS", "100"))
REDUCE_MAX_NEW_TOKENS = int(os.getenv("SUMMARY_REDUCE_MAX_NEW_TOKENS", "180"))
MAX_WORKERS = int(os.getenv("SUMMARY_MAX_WORKERS", "2"))  # Limit to 2 threads on Render
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
    chunks = [tok.decode(ids[i:i + max_tokens], skip_special_tokens=True)
              for i in range(0, len(ids), stride)]
    return chunks

# -------------------------------------------------------
# ⚡ Adaptive Summarization (fast + safe)
# -------------------------------------------------------
async def summarize_text(
    text: str,
    max_tokens: int = 512,
    summary_type: str = "medium",
) -> dict:
    if not text.strip():
        raise ValueError("Empty text cannot be summarized.")

    start_time = time.time()
    cleaned = clean_text(text)
    if len(cleaned) < 50:
        raise ValueError("Paper text too short after cleaning.")

    # Choose model adaptively
    if summary_type.lower() == "detailed":
        model_name = DETAILED_MODEL
        max_new_tokens = REDUCE_MAX_NEW_TOKENS
    elif summary_type.lower() == "short":
        model_name = DEFAULT_MODEL
        max_new_tokens = min(PER_CHUNK_MAX_NEW_TOKENS, 80)
    else:
        model_name = DEFAULT_MODEL
        max_new_tokens = PER_CHUNK_MAX_NEW_TOKENS

    summarizer = _get_summarizer(model_name)
    tokenizer = _get_tokenizer(model_name)

    # Token-aware chunking
    chunks = _chunk_text_token_safe(cleaned, MAX_TOKENS_PER_CHUNK)
    print(f"{LOG_PREFIX} Total chunks: {len(chunks)} | Model: {model_name}")

    if not chunks:
        return {"summary": "", "chunks": 0, "duration_ms": 0}

    # If many chunks, process sequentially for stability
    sequential_mode = len(chunks) > 6
    summaries = []

    async def summarize_chunk(idx: int, chunk: str):
        try:
            token_len = len(tokenizer.encode(chunk, add_special_tokens=False))
            print(f"{LOG_PREFIX} Summarizing chunk {idx}/{len(chunks)} ({token_len} tokens)")
            out = summarizer(
                chunk,
                max_new_tokens=max_new_tokens,
                min_length=int(max_new_tokens * 0.4),
                do_sample=False,
            )[0]["summary_text"].strip()
            return out
        except Exception as e:
            print(f"{LOG_PREFIX} ❌ Chunk {idx} failed: {e}")
            return ""

    # Sequential or parallel depending on chunk count
    if sequential_mode:
        for i, ch in enumerate(chunks):
            summaries.append(await summarize_chunk(i + 1, ch))
    else:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(chunks))) as executor:
            tasks = [loop.run_in_executor(executor, summarizer, ch, max_new_tokens, int(max_new_tokens * 0.4), False)
                     for ch in chunks]
            summaries = await asyncio.gather(*tasks)

    summaries = [s for s in summaries if s]
    combined = " ".join(summaries).strip()

    # Optional second-pass compression
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
    print(f"{LOG_PREFIX} ✅ Completed {len(summaries)} chunks in {duration_ms} ms")

    return {
        "summary": combined,
        "chunks": len(chunks),
        "successful_chunks": len(summaries),
        "duration_ms": duration_ms,
        "model_name": model_name,
        "max_new_tokens": max_new_tokens,
        "cached": False,
    }
