import os
import requests
from typing import Dict, Any

# Load environment variables
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
API_PREFIX = os.getenv("API_PREFIX", "/api/v1")
UPLOAD_ROUTE = os.getenv("API_UPLOAD_ROUTE", "/papers/upload")
BEARER_TOKEN = os.getenv("API_BEARER_TOKEN", "")


class BackendClient:
    def __init__(self,
                 base_url: str = BACKEND_BASE_URL,
                 api_prefix: str = API_PREFIX,
                 token: str = BEARER_TOKEN):
        self.base_url = base_url.rstrip("/")
        self.api_prefix = api_prefix.strip("/")
        self.token = token.strip()

    @property
    def session(self) -> requests.Session:
        s = requests.Session()
        if self.token:
            s.headers.update({"Authorization": f"Bearer {self.token}"})
        return s

    def upload_pdf(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Send a PDF file to the FastAPI backend and return the JSON response."""
        url = f"{self.base_url}/{self.api_prefix}{UPLOAD_ROUTE}"
        files = {"file": (filename, file_bytes, "application/pdf")}
        with self.session as s:
            resp = s.post(url, files=files, timeout=120)
        # Debug printing if error
        if not resp.ok:
            print("❌ Backend error:", resp.status_code, resp.text)
        resp.raise_for_status()
        return resp.json()

