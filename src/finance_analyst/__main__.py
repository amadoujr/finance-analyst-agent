"""CLI — supervisor (default), workers, HITL prompt."""

from __future__ import annotations

import argparse
import sys

from finance_analyst import __version__
from finance_analyst.config import DISCLAIMER, GEMINI_MODEL, LLM_PROVIDER


def _print_result(
    answer: str,
    citations: list[dict[str, str]],
    route: str = "",
) -> None:
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


def _prompt_hitl(payload: dict) -> tuple[str, str]:
    draft = (payload.get("draft") or "")[:800]
    print("\n=== HITL — validation humaine requise ===")
    print(payload.get("disclaimer", DISCLAIMER))
    print("\nBrouillon :\n")
    print(draft)
    if len(payload.get("draft") or "") > 800:
        print("…")
    print("\nActions : approve | edit | reject")
    while True:
        try:
            action = input("Décision> ").strip().lower()
        except EOFError:
            return "reject", ""
        if action in ("approve", "edit", "reject"):
            break
        print("Tape approve, edit ou reject.")
    edit = ""
    if action == "edit":
        print("Colle le texte édité (fin = ligne vide) :")
        lines: list[str] = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line == "":
                break
            lines.append(line)
        edit = "\n".join(lines).strip()
    return action, edit


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Finance analyst CLI")
    parser.add_argument("question", nargs="?", help="Question to ask")
    parser.add_argument("--ticker", help="Ticker hint (AAPL, MSFT, GOOGL)")
    parser.add_argument("--rag", action="store_true", help="Force RAG only")
    parser.add_argument("--calc", action="store_true", help="Force Calc only")
    parser.add_argument(
        "--calc-llm",
        action="store_true",
        help="Calc worker + LLM narrative",
    )
    parser.add_argument(
        "--auto-resume",
        choices=["approve", "edit", "reject"],
        help="For HITL tests: auto-resume without interactive prompt",
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
            '  uv run python -m finance_analyst "Should I buy AAPL?"\n'
            '  uv run python -m finance_analyst --ticker AAPL "What is the ROE?"'
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

    from finance_analyst.graph.runner import analyze, stream_resume

    print("  [mode] supervisor LangGraph (+ HITL si sensible)")
    result = analyze(
        question,
        ticker=args.ticker,
        auto_resume=args.auto_resume,
    )

    if result.get("interrupted") and not args.auto_resume:
        payload = result.get("interrupt") or {}
        action, edit = _prompt_hitl(payload)
        tid = result.get("thread_id") or ""
        final: dict = {}
        for event in stream_resume(
            tid,
            action=action,
            edit=edit,
            ticker=args.ticker,
        ):
            if event.get("type") == "final":
                final = event
            if event.get("type") == "error":
                print(f"Erreur resume: {event.get('message')}")
                return
        _print_result(
            final.get("answer", ""),
            final.get("citations", []),
            route="hitl",
        )
        return

    _print_result(
        result.get("answer", ""),
        result.get("citations", []),
        route=str(result.get("route", "")),
    )


if __name__ == "__main__":
    main(sys.argv[1:])
