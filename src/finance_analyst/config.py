"""Shared paths and env config."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
# Reuse lab keys if present (local convenience)
load_dotenv(ROOT.parent / "langchain-lab" / ".env", override=False)

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

LANGFUSE_HOST = (
    os.getenv("LANGFUSE_HOST")
    or os.getenv("LANGFUSE_BASE_URL")
    or "https://cloud.langfuse.com"
).strip()

DISCLAIMER = (
    "Ceci n’est pas un conseil d’investissement. "
    "Assistant pédagogique basé sur un corpus et des faits seedés."
)
