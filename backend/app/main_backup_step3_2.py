from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# -------------------------------------------------------
# 🧩 Load environment variables
# -------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH)
print(f"[DEBUG] Loaded .env from: {ENV_PATH}")

# -------------------------------------------------------
# 🚀 Create FastAPI app
# -------------------------------------------------------
app = FastAPI(
    title="PaperPal API",
    version="0.1.0",
    description="Backend API for PDF uploads, summarization, keyword extraction, and MongoDB storage.",
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
# 🧱 Router imports (local & Render compatible)
# -------------------------------------------------------
try:
    # Local dev (project root context)
    from backend.app.api.v1 import health, summarize, papers, compare
from backend.app.api.v1 import compareexcept ModuleNotFoundError:
    # Render container (WORKDIR=/app)
    from app.api.v1 import health, summarize, papers, compare

# -------------------------------------------------------
# 🔗 Register routers
# -------------------------------------------------------
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(summarize.router, prefix="/api/v1/papers", tags=["Summarization"])
app.include_router(papers.router, prefix="/api/v1/papers", tags=["Papers"])
app.include_router(compare.router, prefix="/api/v1/papers", tags=["Comparison"])
app.include_router(compare.router, prefix="/api/v1/papers", tags=["Comparison"])
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
        methods = ", ".join(route.methods)
        print(f"  {route.path:40} → {methods}")
    print("-------------------------------------------------------")
