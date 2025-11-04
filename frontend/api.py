import os
import requests
from typing import Dict, Any, Callable, Optional

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1/papers"


class BackendClient:
    def __init__(self, base_url: str = BACKEND_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    # ---------- Upload ----------
    def upload_pdf(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Upload a PDF file to the backend."""
        url = f"{self.base_url}{API_PREFIX}/upload"
        files = {"file": (filename, file_bytes, "application/pdf")}
        resp = self.session.post(url, files=files, timeout=120)
        resp.raise_for_status()
        return resp.json()

    # ---------- Summarization ----------
    def summarize(
        self,
        paper_id: str,
        summary_type: str = "medium",
        use_cache: bool = True,
        max_tokens: Optional[int] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Request a summary of a given type.

        Args:
            paper_id: MongoDB paper ID.
            summary_type: 'short' | 'medium' | 'detailed'.
            use_cache: if True, reuse previous summary (faster).
            max_tokens: optional override.
            progress_callback: optional function to report progress text (for Streamlit spinners).
        """
        payload = {
            "paper_id": paper_id,
            "summary_type": summary_type,
            "use_cache": use_cache,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        url = f"{self.base_url}{API_PREFIX}/summarize"

        if progress_callback:
            progress_callback(f"⏳ Sending {summary_type} summarization request...")

        res = self.session.post(url, json=payload, timeout=600)
        res.raise_for_status()

        if progress_callback:
            progress_callback("✅ Summary retrieved successfully!")

        return res.json()

        # ---------- Keywords ----------
    def keywords(self, paper_id: str, top_k: int = 15, use_cache: bool = False) -> Dict[str, Any]:
        """Extract keywords from a paper (fresh unless use_cache=True)."""
        url = f"{self.base_url}{API_PREFIX}/keywords"
        payload = {"paper_id": paper_id, "top_k": top_k, "use_cache": use_cache}
        resp = self.session.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


    # ---------- Compare ----------
    def compare(
        self,
        paper_a: str,
        paper_b: str,
        section_aware: bool = True
    ) -> Dict[str, Any]:
        """Compare two papers for similarity."""
        url = f"{self.base_url}{API_PREFIX}/compare"
        payload = {
            "paper_id_a": paper_a,
            "paper_id_b": paper_b,
            "section_aware": section_aware,
        }
        resp = self.session.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()
