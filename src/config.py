"""Application configuration utilities."""

from __future__ import annotations

import os


def _get_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./genrecon.db")
AUTO_CREATE_DB = _get_bool(os.getenv("AUTO_CREATE_DB"), default=True)
API_KEY = os.getenv("API_KEY")
RECON_ENCRYPTION_KEY = os.getenv("RECON_ENCRYPTION_KEY")
