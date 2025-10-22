
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "paperpal"
    APP_ENV: str = "dev"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Mongo
    MONGODB_URI: str  # <-- CHANGED HERE
    MONGODB_DB: str = "paperpal_db"
    MONGODB_COLLECTION_PAPERS: str = "papers"
    MONGODB_COLLECTION_CHUNKS: str = "chunks"
    MONGODB_COLLECTION_EMBEDDINGS: str = "embeddings"

    # CORS
    FRONTEND_ORIGIN: str = Field(default="http://localhost:8501")

settings = Settings()
