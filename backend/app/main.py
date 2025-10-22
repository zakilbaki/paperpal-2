from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# -------------------------------------------------------
# 🧩 Load environment variables
# -------------------------------------------------------
# Ensures backend/.env is loaded on startup (works locally + on Render)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# -------------------------------------------------------
# 🚀 Create FastAPI app
# -------------------------------------------------------
app = FastAPI(
    title="PaperPal API",
    version="0.1.0",
    description="Backend API for PDF uploads, parsing, and MongoDB storage.",
)

# -------------------------------------------------------
# 🌐 CORS setup for Streamlit frontend
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
# 🧱 Routers import
# -------------------------------------------------------
# ✅ Correct imports for both local + Render
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.papers import router as papers_router

# Register routers
app.include_router(health_router, prefix="/api/v1/health", tags=["Health"])
app.include_router(papers_router, prefix="/api/v1/papers", tags=["Papers"])

# -------------------------------------------------------
# 🏁 Root endpoint
# -------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "Welcome to PaperPal API 👋"}
