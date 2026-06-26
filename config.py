# config.py — Murder Mystery global parameters

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

DEBUG = os.getenv("MM_DEBUG", "").lower() in ("1", "true", "yes")

# ── LLM Provider ───────────────────────────────────────────────────────
# Leave LLM_BASE_URL empty unless you want to override the provider default.
# When provider="openai" and LLM_BASE_URL is empty, the client falls back
# to a local Ollama (http://localhost:11434/v1).
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_API_KEY  = os.getenv("LLM_API_KEY",  "")

# ── Backend (custom proxy) credentials ─────────────────────────────────
# Only used when LLM_PROVIDER="backend".
BACKEND_URL = os.getenv("BACKEND_URL", "")
BACKEND_KEY = os.getenv("BACKEND_KEY", "")

# ── Models ─────────────────────────────────────────────────────────────
# DEFAULT_MODEL is the common fallback — set it in .env.
# WRITER_MODEL / DETECTIVE_MODEL / SUSPECT_MODEL allow per-role overrides.
_default = os.getenv("DEFAULT_MODEL", "llama3.2")

WRITER_MODEL    = os.getenv("WRITER_MODEL",    _default)
DETECTIVE_MODEL = os.getenv("DETECTIVE_MODEL", _default)
SUSPECT_MODEL   = os.getenv("SUSPECT_MODEL",   _default)

WRITER_TEMPERATURE    = 0.9
DETECTIVE_TEMPERATURE = 0.2
SUSPECT_TEMPERATURE   = 0.7

# ── General parameters ─────────────────────────────────────────────────
# Thinking models spend a large share of the output budget on the <think>
# block; 4096 truncated the actual answer (finish_reason=length). Raised so
# reasoning + final answer both fit. (We do NOT force /no_think.)
MAX_TOKENS         = 16384
MAX_TOKENS_FORZATO = 16384
TIMEOUT            = 300
WRITER_TIMEOUT     = 400

MAX_DETECTIVE_STEPS     = 15
MAX_MESSAGGI_DETECTIVE  = 30
MAX_CHARS_DETECTIVE     = 150000
MAX_MESSAGGI_SOSPETTATO = 20
MESSAGGI_RECENTI        = 6

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
CASES_DIR = BASE_DIR / "cases"
CASES_DIR.mkdir(exist_ok=True)
