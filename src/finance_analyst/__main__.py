"""CLI — supervisor (default), or single workers."""

from __future__ import annotations

import argparse
import sys

from finance_analyst import __version__
from finance_analyst.config import DISCLAIMER, GEMINI_MODEL, LLM_PROVIDER


def _print_result(answer: str, citations: list[dict[str, str]], route: str = "") -> None:
    if route:
        print(f"\n--- Route: {route} ---")
    print("\n--- Answer ---")
    print(answer)
    if citations:
        print("\n--- Citations ---")
        for c in citations:
            cid = c.get("chunk_id", "?")
            print(f"  [{cid}] {c.get('ticker', '')} · {c.get('source', '')}")
            excerpt = c.get("excerpt", "")
            if excerpt:
                print(f"      {excerpt[:160]}…")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Finance analyst CLI")
    parser.add_argument("question", nargs="?", help="Question to ask")
    parser.add_argument("--ticker", help="Ticker hint (AAPL, MSFT, GOOGL)")
    parser.add_argument(
        "--rag",
        action="store_true",
        help="Force RAG worker only",
    )
    parser.add_argument(
        "--calc",
        action="store_true",
        help="Force Calc worker only",
    )
    parser.add_argument(
        "--calc-llm",
        action="store_true",
        help="Calc worker + LLM narrative",
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
            '  uv run python -m finance_analyst "ROE and risk factors for Apple"\n'
            '  uv run python -m finance_analyst --ticker AAPL "What is the ROE?"\n'
            "  uv run python -m finance_analyst --rag --ticker AAPL \"risk factors?\"\n"
            "  uv run python -m finance_analyst --calc --ticker AAPL \"ROE?\""
        )
        return

    if args.calc or args.calc_llm:
        from finance_analyst.calc.worker import ask_calc

        result = ask_calc(
            question,
            ticker=args.ticker,
            use_llm_narrative=args.calc_llm,
        )
        _print_result(result["answer"], result["citations"], route="calc")
        return

    if args.rag:
        from finance_analyst.rag.worker import ask_rag

        result = ask_rag(question, ticker=args.ticker)
        _print_result(result["answer"], result["citations"], route="rag")
        return

    from finance_analyst.graph.runner import analyze

    print("  [mode] supervisor LangGraph")
    result = analyze(question, ticker=args.ticker)
    _print_result(
        result.get("answer", ""),
        result.get("citations", []),
        route=str(result.get("route", "")),
    )


if __name__ == "__main__":
    main(sys.argv[1:])
