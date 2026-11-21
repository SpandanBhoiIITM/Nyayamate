"""Configuration: API key lookup, model defaults and paths.

The API key is read server-side only (env var / .env / Streamlit secrets /
session input). It is never rendered back into the page.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional at runtime
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CASES_DIR = DATA_DIR / "cases"
OUTPUTS_DIR = BASE_DIR / "outputs"
TEST_CASES_DIR = BASE_DIR / "tests" / "test_cases"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Free models on OpenRouter rotate often. These ids were on
# https://openrouter.ai/collections/free-models in November 2026.
RECOMMENDED_FREE_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
_env_model = os.getenv("OPENROUTER_MODEL", "").strip()
# "openrouter/free" (the old default) routes randomly and often returns empty replies,
# so it is only used when chosen explicitly in Settings.
DEFAULT_MODEL = _env_model if _env_model and _env_model != "openrouter/free" \
    else RECOMMENDED_FREE_MODEL

# If the chosen free model is busy or down, OpenRouter tries these next (same request).
FALLBACK_FREE_MODELS = [
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
]

# Suggested models shown in Settings. Any OpenRouter model id can be typed in.
SUGGESTED_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
    "baidu/ernie-5.5-flash-preview:free",
    "nvidia/nemotron-3.5-super-vl:free",
    "openrouter/free",
]

LANGUAGES = ["Auto-detect", "English", "Hindi", "Marathi", "Tamil", "Telugu",
             "Bengali", "Gujarati", "Kannada", "Malayalam", "Punjabi"]

REQUEST_TIMEOUT_SECONDS = 60
MAX_RETRIES_INVALID_JSON = 1


def get_env_api_key() -> str | None:
    """Return the key from env/.env, then Streamlit secrets. None if absent."""
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    try:
        import streamlit as st

        key = str(st.secrets.get("OPENROUTER_API_KEY", "")).strip()
        return key or None
    except Exception:  # no secrets file, or not running under Streamlit
        return None


for _d in (CASES_DIR, OUTPUTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
