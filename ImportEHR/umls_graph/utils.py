"""
utils.py — Shared utilities: logging setup, disk cache, helpers.
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

import config


# ──────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """Return a consistently-formatted logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
        logger.addHandler(handler)
    logger.setLevel(config.LOG_LEVEL)
    return logger


# ──────────────────────────────────────────────
# DISK CACHE
# ──────────────────────────────────────────────

class DiskCache:
    """
    Simple JSON-based file cache keyed by a hash of the request URL + params.
    Each entry is stored as an individual JSON file to avoid one giant blob.
    """

    def __init__(self, cache_dir: Path = config.CACHE_DIR, enabled: bool = config.CACHE_ENABLED):
        self._dir = cache_dir
        self._enabled = enabled
        self._logger = get_logger(self.__class__.__name__)
        if self._enabled:
            self._dir.mkdir(parents=True, exist_ok=True)

    def _key(self, url: str, params: dict) -> str:
        raw = json.dumps({"url": url, "params": params}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, url: str, params: dict) -> Optional[Any]:
        if not self._enabled:
            return None
        path = self._dir / f"{self._key(url, params)}.json"
        if path.exists():
            self._logger.debug("Cache HIT  → %s", url)
            return json.loads(path.read_text(encoding="utf-8"))
        self._logger.debug("Cache MISS → %s", url)
        return None

    def set(self, url: str, params: dict, data: Any) -> None:
        if not self._enabled:
            return
        path = self._dir / f"{self._key(url, params)}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def clear(self) -> None:
        if self._dir.exists():
            for f in self._dir.glob("*.json"):
                f.unlink()
            self._logger.info("Cache cleared.")


# ──────────────────────────────────────────────
# RETRY / BACK-OFF HELPER
# ──────────────────────────────────────────────

def retry_sleep(attempt: int, base: float = config.RETRY_BACKOFF_FACTOR) -> None:
    """Exponential back-off sleep between retry attempts."""
    delay = base ** attempt
    logging.getLogger("retry").warning("Rate-limited or error — sleeping %.1fs (attempt %d)", delay, attempt)
    time.sleep(delay)


# ──────────────────────────────────────────────
# MISC HELPERS
# ──────────────────────────────────────────────

def safe_get(d: dict, *keys, default=None):
    """Safely traverse nested dict keys."""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
    return d


def normalise_cui(cui: str) -> str:
    """Ensure CUI is upper-case and stripped."""
    return cui.strip().upper()


def ensure_output_dir(path: Path = config.OUTPUT_DIR) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path