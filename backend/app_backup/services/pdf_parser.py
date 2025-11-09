from __future__ import annotations

from io import BytesIO
from typing import Dict, List, Tuple
import re

from pdfminer.high_level import extract_text


SECTION_ORDER = [
    "title",
    "abstract",
    "introduction",
    "methods",
    "materials and methods",
    "results",
    "discussion",
    "conclusion",
    "references",
]

# Build a regex that matches common section headers (case-insensitive, line-start)
_SECTION_PATTERN = re.compile(
    r"^(abstract|introduction|materials?\s+and\s+methods|methods|results|discussion|conclusion|references)\s*:?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


def extract_pdf_text(file_bytes: bytes) -> str:
    """
    Extract raw text from PDF bytes using pdfminer.six.
    """
    with BytesIO(file_bytes) as bio:
        text = extract_text(bio) or ""
    # Normalize line endings and collapse trailing spaces
    return "\n".join(line.rstrip() for line in text.splitlines())


def segment_sections(text: str) -> List[Dict[str, str]]:
    """
    Heuristic segmentation:
    - If we find known headers, split by them.
    - Otherwise return a single 'body' section.
    - Title: use first non-empty line as 'title' if it looks reasonable.
    """
    if not text.strip():
        return []

    # Attempt to grab the first non-empty line as the title
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    sections: List[Tuple[str, str]] = []

    # Find section header positions
    matches = list(_SECTION_PATTERN.finditer(text))
    if not matches:
        # No obvious headers → single 'body' section, plus inferred title if present
        if first_line and len(first_line.split()) <= 25:
            sections.append(("title", first_line))
        sections.append(("body", text))
        return [{"name": name.lower(), "text": content.strip()} for name, content in sections if content.strip()]

    # If we have matches, slice text between them
    # Prepend the area before the first header as potential 'title'
    preamble = text[: matches[0].start()].strip()
    if preamble:
        if first_line and len(first_line.split()) <= 25:
            sections.append(("title", first_line))
        else:
            sections.append(("preamble", preamble))

    for i, m in enumerate(matches):
        name = m.group(1).lower()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if content:
            sections.append((name, content))

    # Merge “materials and methods” into “methods” label
    normalized = []
    for name, content in sections:
        if "materials" in name and "methods" in name:
            normalized.append(("methods", content))
        else:
            normalized.append((name, content))

    # Keep a stable order (title first if present, then others in SECTION_ORDER, then anything else)
    ordered: List[Dict[str, str]] = []
    by_name = {}
    for n, c in normalized:
        by_name.setdefault(n, [])
        by_name[n].append(c)

    # Title first
    if "title" in by_name:
        ordered.append({"name": "title", "text": "\n\n".join(by_name.pop("title"))})

    # Known order
    for n in SECTION_ORDER:
        if n in by_name:
            ordered.append({"name": n, "text": "\n\n".join(by_name.pop(n))})

    # Remainders
    for n, chunks in by_name.items():
        ordered.append({"name": n, "text": "\n\n".join(chunks)})

    return ordered

