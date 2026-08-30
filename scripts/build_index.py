#!/usr/bin/env python3
"""Build FAISS index from data/raw filings.

  uv run python scripts/build_index.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finance_analyst.rag.index import build_faiss_index, clear_index_cache  # noqa: E402


def main() -> None:
    clear_index_cache()
    store = build_faiss_index(persist=True)
    # Touch doc count
    n = len(getattr(store, "index_to_docstore_id", {}) or {})
    print(f"Done. Vectors/chunks: {n}")


if __name__ == "__main__":
    main()
