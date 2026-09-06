"""Shared paths and env config."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
# Reuse lab keys if present (local convenience)
load_dotenv(ROOT.parent / "langchain-lab" / ".env", override=False)

# Legacy LANGCHAIN_TRACING=true breaks modern LangChain (forces TracerV1).
# Prefer LANGCHAIN_TRACING_V2; drop the old flag if present.
_legacy = os.getenv("LANGCHAIN_TRACING", "").strip().lower()
if _legacy in ("1", "true", "yes"):
    if not os.getenv("LANGCHAIN_TRACING_V2"):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ.pop("LANGCHAIN_TRACING", None)

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
STRUCTURED_DIR = DATA_DIR / "structured"
INDEX_DIR = DATA_DIR / "index"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)

LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "finance-analyst-agent").strip()

DISCLAIMER = (
    "Ceci n’est pas un conseil d’investissement. "
    "Assistant pédagogique basé sur un corpus et des faits seedés."
)
