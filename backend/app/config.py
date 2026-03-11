from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    openai_api_key: str = ""
    database_url: str = "sqlite:///./caarya_job_fit.db"
    redis_url: str = "redis://localhost:6379/0"

    # Scoring weights
    semantic_weight: float = 0.40
    skill_weight: float = 0.35
    signals_weight: float = 0.25

    # Paths
    jobs_data_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "jobs")
    faiss_index_path: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "faiss_index")
    uploads_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads")

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
