"""
Central configuration for the Privacy-Preserving Federated Learning Platform.
All settings are read from environment variables with sensible defaults.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────
    APP_NAME: str = "Privacy-Preserving FL Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ── Database ─────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./platform.db"

    # ── Redis ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT / Auth ───────────────────────────────────────────────────
    JWT_SECRET: str = "super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours

    # ── Flower FL Server ─────────────────────────────────────────────
    FL_SERVER_ADDRESS: str = "0.0.0.0:8080"
    FL_DEFAULT_ROUNDS: int = 5
    FL_MIN_CLIENTS: int = 2
    FL_FRACTION_FIT: float = 1.0

    # ── Differential Privacy ─────────────────────────────────────────
    DP_NOISE_MULTIPLIER: float = 1.1
    DP_MAX_GRAD_NORM: float = 1.0
    DP_TARGET_DELTA: float = 1e-5

    # ── Model Storage ────────────────────────────────────────────────
    MODEL_STORAGE_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "model_storage"
    )

    # ── CORS ─────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
