from __future__ import annotations
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv

# -------------------------------------------------------
# 🔍 Locate and load .env
# -------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
ENV_PATH = os.path.join(BASE_DIR, ".env")

print(f"[DEBUG] Loading .env from: {ENV_PATH}")
if not os.path.exists(ENV_PATH):
    print("[ERROR] .env file not found!")
else:
    load_dotenv(dotenv_path=ENV_PATH)
    print("[DEBUG] .env file loaded successfully.")

# -------------------------------------------------------
# ⚙️ Settings model
# -------------------------------------------------------
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",  # ✅ allow unused .env variables
    )

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
