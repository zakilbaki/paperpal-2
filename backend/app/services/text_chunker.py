from __future__ import annotations
from typing import List
import re

# Simple, fast sentence splitter using punctuation.
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

def split_sentences(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    text = re.sub(r"\s+", " ", text)
    return re.split(_SENT_SPLIT, text)

def chunk_by_tokens(
    text: str,
    tokenizer,
    max_tokens: int = 900,
    overlap: int = 50,
) -> List[str]:
    """Greedy sentence-based chunking bounded by tokenizer token count."""
    sents = split_sentences(text)
    chunks: List[str] = []
    current: List[str] = []
    current_tokens = 0

    for sent in sents:
        toks = len(tokenizer.encode(sent, add_special_tokens=False))
        if toks > max_tokens:
            enc = tokenizer.encode(sent, add_special_tokens=False)
            for i in range(0, len(enc), max_tokens):
                dec = tokenizer.decode(enc[i:i + max_tokens], skip_special_tokens=True)
                if dec.strip():
                    if current:
                        chunks.append(" ".join(current).strip())
                        current, current_tokens = [], 0
                    chunks.append(dec)
            continue

        if current_tokens + toks <= max_tokens:
            current.append(sent)
            current_tokens += toks
        else:
            if current:
                chunks.append(" ".join(current).strip())
                tail = []
                if overlap > 0:
                    t = 0
                    for s in reversed(current):
                        t += len(tokenizer.encode(s, add_special_tokens=False))
                        tail.append(s)
                        if t >= overlap:
                            break
                    tail = list(reversed(tail))
                current = tail + [sent]
                current_tokens = sum(len(tokenizer.encode(s, add_special_tokens=False)) for s in current)
            else:
                current = [sent]
                current_tokens = toks

    if current:
        chunks.append(" ".join(current).strip())

    return [c for c in chunks if c.strip()]
