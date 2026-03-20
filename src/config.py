"""Application configuration utilities."""

from __future__ import annotations

import os
import tempfile


def _get_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./genrecon.db")
AUTO_CREATE_DB = _get_bool(os.getenv("AUTO_CREATE_DB"), default=True)
API_KEY = os.getenv("API_KEY")
RECON_ENCRYPTION_KEY = os.getenv("RECON_ENCRYPTION_KEY")

RECON_TEMP_DIR = os.getenv("RECON_TEMP_DIR", tempfile.gettempdir())
RECON_PARTITION_COUNT = min(_get_int(os.getenv("RECON_PARTITION_COUNT"), default=64), 4096)
