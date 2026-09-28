from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KNOWHOW_", env_file=".env", extra="ignore")

    app_name: str = "MentorMind Know-How API"
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
    profile_db: str = "data/work/profiles.sqlite"
    work_dir: str = "data/work"
    samples_dir: str = "data/samples"


@lru_cache
def get_settings() -> Settings:
    return Settings()
