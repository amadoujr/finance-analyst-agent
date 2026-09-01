"""Stream supervisor graph as SSE-friendly events."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from finance_analyst.config import DISCLAIMER, GEMINI_MODEL, LLM_PROVIDER
from finance_analyst.graph.build import get_app
from finance_analyst.observability.langsmith import flush_tracing, langsmith_enabled, run_config

NODE_LABELS = {
    "classify": "Supervisor",
    "rag": "Worker RAG",
    "calc": "Worker Calcul",
    "synthesize": "Synthèse",
}


def stream_analyze(
    question: str,
    *,
    ticker: str | None = None,
) -> Iterator[dict[str, Any]]:
    q = question.strip()
    if not q:
        yield {"type": "error", "message": "Question vide."}
        return

    yield {
        "type": "start",
        "question": q,
        "provider": LLM_PROVIDER,
        "model": GEMINI_MODEL,
        "disclaimer": DISCLAIMER,
        "langsmith": langsmith_enabled(),
    }

    app = get_app()
    inputs: dict[str, Any] = {"question": q, "ticker": ticker}
    route = ""
    graph_config = run_config(ticker=ticker)

    try:
        for chunk in app.stream(
            inputs,
            config=graph_config,
            stream_mode="updates",
        ):
            for node, update in chunk.items():
                if node == "classify":
                    route = str(update.get("route", route))
                label = NODE_LABELS.get(node, node)
                detail = ""
                if node == "classify" and update.get("route"):
                    detail = f"route → {update['route']}"
                    if update.get("ticker"):
                        detail += f" · {update['ticker']}"
                elif node == "rag":
                    detail = f"grade={update.get('rag_grade', '?')}"
                elif node == "calc":
                    detail = f"grade={update.get('calc_grade', '?')}"
                elif node == "synthesize":
                    detail = "réponse finale"

                yield {
                    "type": "step",
                    "node": node,
                    "label": label,
                    "detail": detail,
                }

                if node == "synthesize":
                    yield {
                        "type": "final",
                        "route": route,
                        "answer": update.get("answer", ""),
                        "citations": update.get("citations", []),
                    }
    except Exception as exc:  # noqa: BLE001
        yield {"type": "error", "message": str(exc)}
    finally:
        flush_tracing()


def analyze(question: str, *, ticker: str | None = None) -> dict[str, Any]:
    final: dict[str, Any] = {}
    for event in stream_analyze(question, ticker=ticker):
        if event.get("type") == "final":
            final = event
        if event.get("type") == "error":
            return {
                "answer": event.get("message", "Erreur"),
                "citations": [],
                "route": "error",
            }
    return {
        "answer": final.get("answer", ""),
        "citations": final.get("citations", []),
        "route": final.get("route", ""),
    }
