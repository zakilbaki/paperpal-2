from transformers import pipeline, AutoTokenizer
import os, time, torch, re, gc, psutil

# -------------------------------------------------------
# ⚙️ CONFIGURATION — optimized for Render (2 GB)
# -------------------------------------------------------
DEFAULT_MODEL = os.getenv("SUMMARY_MODEL_NAME", "philschmid/bart-large-cnn-samsum")
DETAILED_MODEL = os.getenv("SUMMARY_MODEL_DETAILED", "google/pegasus-xsum")

MAX_TOKENS_PER_CHUNK = int(os.getenv("SUMMARY_MAX_TOKENS_PER_CHUNK", "300"))
OVERLAP = int(os.getenv("SUMMARY_OVERLAP", "15"))
PER_CHUNK_MAX_NEW_TOKENS = int(os.getenv("SUMMARY_PER_CHUNK_MAX_NEW_TOKENS", "60"))
REDUCE_MAX_NEW_TOKENS = int(os.getenv("SUMMARY_REDUCE_MAX_NEW_TOKENS", "100"))
MAX_WORKERS = int(os.getenv("SUMMARY_MAX_WORKERS", "1"))
LOG_PREFIX = "[SUMMARY]"

_tokenizer_cache, _summarizer_cache = {}, {}

os.environ["TOKENIZERS_PARALLELISM"] = "false"


# -------------------------------------------------------
# 🧠 Memory utility
# -------------------------------------------------------
def _mem(label=""):
    try:
        rss = psutil.Process(os.getpid()).memory_info().rss / 1024**2
        print(f"[MEMORY] {label}: {rss:.1f} MB")
    except Exception:
        pass


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
# 🔤 Model + Tokenizer caching
# -------------------------------------------------------
def _get_tokenizer(name):
    if name not in _tokenizer_cache:
        _tokenizer_cache[name] = AutoTokenizer.from_pretrained(name, use_fast=True)
    return _tokenizer_cache[name]


def _get_summarizer(name):
    if name not in _summarizer_cache:
        torch.set_num_threads(1)  # single-threaded for safety
        device = -1  # CPU only
        summarizer = pipeline(
            "summarization",
            model=name,
            tokenizer=_get_tokenizer(name),
            device=device,
            framework="pt",
        )
        _summarizer_cache[name] = summarizer
        print(f"{LOG_PREFIX} 🚀 Loaded summarizer: {name} (device={device})")
        _mem("after model load")
    return _summarizer_cache[name]


# -------------------------------------------------------
# 🧩 Token-safe chunking
# -------------------------------------------------------
def _chunk_text_token_safe(text, max_tokens=MAX_TOKENS_PER_CHUNK):
    tok = _get_tokenizer(DEFAULT_MODEL)
    ids = tok.encode(text, add_special_tokens=False)
    stride = max_tokens - OVERLAP
    return [
        tok.decode(ids[i:i + max_tokens], skip_special_tokens=True)
        for i in range(0, len(ids), stride)
    ]


# -------------------------------------------------------
# ⚡ Main Summarization
# -------------------------------------------------------
async def summarize_text(text: str, max_tokens: int = 512, summary_type: str = "medium") -> dict:
    if not text.strip():
        raise ValueError("Empty text cannot be summarized.")

    start = time.time()
    cleaned = clean_text(text)

    # Safety: cap input size
    if len(cleaned) > 180_000:
        cleaned = cleaned[:180_000]

    if len(cleaned.split()) < 120:
        return {
            "summary": cleaned[:800] + "...",
            "chunks": 1,
            "successful_chunks": 1,
            "duration_ms": 0,
            "model_name": "none",
            "cached": True,
        }

    if summary_type.lower() == "detailed":
        model_name = DETAILED_MODEL
        max_new_tokens = REDUCE_MAX_NEW_TOKENS
    else:
        model_name = DEFAULT_MODEL
        max_new_tokens = PER_CHUNK_MAX_NEW_TOKENS

    summarizer = _get_summarizer(model_name)
    tokenizer = _get_tokenizer(model_name)
    chunks = _chunk_text_token_safe(cleaned, MAX_TOKENS_PER_CHUNK)

    if len(chunks) > 8:
        print(f"{LOG_PREFIX} ⚠️ Too many chunks ({len(chunks)}). Truncating to 8.")
        chunks = chunks[:8]

    print(f"{LOG_PREFIX} 🕒 Start summarization ({summary_type}) with {len(chunks)} chunks")
    _mem("before summarize")

    summaries = []
    for i, chunk in enumerate(chunks, 1):
        try:
            token_len = len(tokenizer.encode(chunk, add_special_tokens=False))
            print(f"{LOG_PREFIX} Summarizing chunk {i}/{len(chunks)} ({token_len} tokens)")
            out = summarizer(
                chunk,
                max_new_tokens=max_new_tokens,
                min_length=int(max_new_tokens * 0.4),
                do_sample=False,
            )[0]["summary_text"].strip()
            summaries.append(out)

            if i % 2 == 0:
                gc.collect()
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
        except Exception as e:
            print(f"{LOG_PREFIX} ❌ Chunk {i} failed: {e}")

    combined = " ".join(summaries).strip()

    # Optional refinement if long
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

    duration_ms = int((time.time() - start) * 1000)
    _mem("after summarize")
    gc.collect()
    torch.cuda.empty_cache() if torch.cuda.is_available() else None

    return {
        "summary": combined,
        "chunks": len(chunks),
        "successful_chunks": len(summaries),
        "duration_ms": duration_ms,
        "model_name": model_name,
        "max_new_tokens": max_new_tokens,
        "cached": False,
    }
