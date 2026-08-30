"""CLI — RAG worker (index must exist).

  uv run python -m finance_analyst
  uv run python -m finance_analyst "What are Apple's main risk factors?"
  uv run python -m finance_analyst --ticker AAPL "Describe the business"
"""

from __future__ import annotations

import argparse
import sys

from finance_analyst import __version__
from finance_analyst.config import DISCLAIMER, GEMINI_MODEL, LLM_PROVIDER


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Finance analyst — RAG CLI")
    parser.add_argument("question", nargs="?", help="Question to ask")
    parser.add_argument(
        "--ticker",
        help="Optional ticker filter (AAPL, MSFT, GOOGL)",
    )
    args = parser.parse_args(argv)

    print(f"finance-analyst-agent v{__version__}")
    print(f"LLM: {LLM_PROVIDER} / {GEMINI_MODEL}")
    print(DISCLAIMER)
    print()

    question = (args.question or "").strip()
    if not question:
        try:
            question = input("Question: ").strip()
        except EOFError:
            question = ""
    if not question:
        print(
            "Usage:\n"
            '  uv run python -m finance_analyst "What does Microsoft say about AI risks?"\n'
            "  uv run python scripts/build_index.py   # once after fetch_edgar"
        )
        return

    from finance_analyst.rag.worker import ask_rag

    result = ask_rag(question, ticker=args.ticker)
    print("\n--- Answer ---")
    print(result["answer"])
    print("\n--- Citations ---")
    for c in result["citations"]:
        print(f"  [{c['chunk_id']}] {c['ticker']} · {c['source']}")
        print(f"      {c['excerpt'][:160]}…")


if __name__ == "__main__":
    main(sys.argv[1:])
