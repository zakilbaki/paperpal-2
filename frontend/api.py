import os
import requests
from typing import Dict, Any, Callable, Optional

# -------------------------------------------------------------------
# 🌍 Backend connection settings
# -------------------------------------------------------------------
# Default to your live backend on Render
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "https://paperpal-backend1.onrender.com").rstrip("/")
API_PREFIX = os.getenv("API_PREFIX", "/api/v1/papers")

# -------------------------------------------------------------------
# 🚀 Backend Client
# -------------------------------------------------------------------
class BackendClient:
    def __init__(self, base_url: str = BACKEND_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()

    # ---------- Upload ----------
    def upload_pdf(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Upload a PDF file to the backend."""
        url = f"{self.base_url}{API_PREFIX}/upload"
        files = {"file": (filename, file_bytes, "application/pdf")}
        try:
            resp = self.session.post(url, files=files, timeout=180)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise RuntimeError(f"Upload failed: {e}")

    # ---------- Summarization ----------
    def summarize(
        self,
        paper_id: str,
        summary_type: str = "medium",
        use_cache: bool = True,
        max_tokens: Optional[int] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Request a summary from the backend."""
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

        try:
            res = self.session.post(url, json=payload, timeout=600)
            res.raise_for_status()
            if progress_callback:
                progress_callback("✅ Summary retrieved successfully!")
            return res.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Summarization failed: {e}")

    # ---------- Keywords ----------
    def keywords(self, paper_id: str, top_k: int = 15, use_cache: bool = False) -> Dict[str, Any]:
        """Extract keywords from a paper."""
        url = f"{self.base_url}{API_PREFIX}/keywords"
        payload = {"paper_id": paper_id, "top_k": top_k, "use_cache": use_cache}
        try:
            resp = self.session.post(url, json=payload, timeout=180)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise RuntimeError(f"Keyword extraction failed: {e}")
