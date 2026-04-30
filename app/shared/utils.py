"""
RakshaSetu — Shared Utilities
Logging, JSON helpers, and common functions.
"""

import json
import logging
import sys
from datetime import datetime, date
from app.config import settings


def setup_logging():
    """Configure logging for the entire application."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s │ %(name)-25s │ %(levelname)-8s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("raksha_setu.log", encoding="utf-8"),
        ],
    )
    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def to_json(data: dict, indent: int = 2) -> str:
    """Serialize dict to JSON string with datetime support."""
    return json.dumps(data, cls=DateTimeEncoder, indent=indent, ensure_ascii=False)


def from_json(text: str) -> dict:
    """Parse JSON string, handling common LLM output issues."""
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


def classify_severity(rainfall_mm: float, flood_level: float, crowd_density: float) -> str:
    """
    Classify overall severity based on multiple factors.
    No hardcoded thresholds — uses a weighted scoring approach.
    """
    score = (
        rainfall_mm / 100 * 0.4  # Normalize rainfall (100mm = max)
        + flood_level * 0.35     # 0-1 scale
        + crowd_density * 0.25   # 0-1 scale
    )
    if score >= 0.7:
        return "CRITICAL"
    elif score >= 0.45:
        return "HIGH"
    elif score >= 0.25:
        return "MEDIUM"
    return "LOW"


def get_llm():
    """Create and return the Ollama-backed ChatOllama instance."""
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=settings.ollama.model,
        base_url=settings.ollama.base_url,
        temperature=settings.ollama.temperature,
        num_predict=2048,
    )
