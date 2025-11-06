from __future__ import annotations
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# -------------------------------------------------------
# 🧩 Ensure backend is in sys.path for local dev
# -------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# -------------------------------------------------------
# 🧩 Load environment variables
# -------------------------------------------------------
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(dotenv_path=ENV_PATH)
print(f"[DEBUG] Loaded .env from: {ENV_PATH}")

# -------------------------------------------------------
# 🚀 Create FastAPI app
# -------------------------------------------------------
app = FastAPI(
    title="PaperPal API",
    version="2.0.0",
    description="Backend API for summarization, keyword extraction, paper comparison, PDF upload, and MongoDB storage.",
)

# -------------------------------------------------------
# 🌐 CORS setup
# -------------------------------------------------------
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:8501")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------
# 🧱 Router imports
# -------------------------------------------------------
try:
    from app.api.v1 import health, papers, summarize, compare, upload
    print("[DEBUG] Imported routers via app.api.v1")
except Exception as e:
    print("[ERROR] Router import failed:", e)
    raise

# -------------------------------------------------------
# 🔗 Register routers
# -------------------------------------------------------
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(papers.router, prefix="/api/v1/papers", tags=["Papers"])
app.include_router(summarize.router, prefix="/api/v1/papers", tags=["Summarization"])
app.include_router(compare.router, prefix="/api/v1/papers", tags=["Comparison"])
app.include_router(upload.router, prefix="/api/v1/papers", tags=["Upload"])

# -------------------------------------------------------
# 🏁 Root endpoint
# -------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "Welcome to PaperPal API 👋"}

# -------------------------------------------------------
# 🧪 Debug: list routes on startup
# -------------------------------------------------------
@app.on_event("startup")
async def show_registered_routes():
    print("\n[DEBUG] Registered routes:")
    for route in app.routes:
        print(f"  {route.path:40} → {', '.join(route.methods)}")
    print("-------------------------------------------------------")
