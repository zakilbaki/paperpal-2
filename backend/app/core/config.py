from __future__ import annotations
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv

# -------------------------------------------------------
# 🔍 Locate and load .env (Render + Local compatible)
# -------------------------------------------------------

# Local .env (when developing)
LOCAL_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../", ".env"))

# Render Secret File location
RENDER_ENV_PATH = "/etc/secrets/app.env"

# Priority: Render > Local
if os.path.exists(RENDER_ENV_PATH):
    print(f"[DEBUG] Loading .env from: {RENDER_ENV_PATH}")
    load_dotenv(dotenv_path=RENDER_ENV_PATH)
    print("[DEBUG] .env file loaded successfully from Render secret file.")
elif os.path.exists(LOCAL_ENV_PATH):
    print(f"[DEBUG] Loading .env from: {LOCAL_ENV_PATH}")
    load_dotenv(dotenv_path=LOCAL_ENV_PATH)
    print("[DEBUG] .env file loaded successfully from local file.")
else:
    print("[ERROR] .env file not found! Checked both Render and local paths.")

# -------------------------------------------------------
# ⚙️ Settings model
# -------------------------------------------------------
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    APP_NAME: str = "paperpal"
    APP_ENV: str = "dev"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    MONGODB_URI: str = Field(..., description="MongoDB connection string")
    MONGODB_DB: str = "paperpal_db"

    FRONTEND_ORIGIN: str = "http://localhost:8501"

# -------------------------------------------------------
# 🧠 Singleton instance
# -------------------------------------------------------
settings = Settings()

if __name__ == "__main__":
    print("✅ Loaded MONGODB_URI:", settings.MONGODB_URI)

