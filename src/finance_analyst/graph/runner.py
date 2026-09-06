"""Stream supervisor graph as SSE-friendly events (with HITL interrupt)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

from langgraph.types import Command

from finance_analyst.config import DISCLAIMER, GEMINI_MODEL, LLM_PROVIDER
from finance_analyst.graph.build import get_app
from finance_analyst.observability.langsmith import (
    flush_tracing,
    langsmith_enabled,
    run_config,
)

NODE_LABELS = {
    "classify": "Supervisor",
    "rag": "Worker RAG",
    "calc": "Worker Calcul",
    "synthesize": "Synthèse",
    "hitl": "Validation humaine",
}


def _merge_config(
    thread_id: str,
    *,
    ticker: str | None = None,
) -> dict[str, Any]:
    cfg = run_config(ticker=ticker, session_id=thread_id)
    configurable = dict(cfg.get("configurable") or {})
    configurable["thread_id"] = thread_id
    cfg["configurable"] = configurable
    return cfg


def _payload_from_interrupts(interrupts: Any) -> dict[str, Any]:
    if not interrupts:
        return {}
    first = interrupts[0] if isinstance(interrupts, (list, tuple)) else interrupts
    value = getattr(first, "value", first)
    return value if isinstance(value, dict) else {"raw": value}


def stream_analyze(
    question: str,
    *,
    ticker: str | None = None,
    thread_id: str | None = None,
) -> Iterator[dict[str, Any]]:
    q = question.strip()
    if not q:
        yield {"type": "error", "message": "Question vide."}
        return

    tid = thread_id or str(uuid.uuid4())
    yield {
        "type": "start",
        "question": q,
        "thread_id": tid,
        "provider": LLM_PROVIDER,
        "model": GEMINI_MODEL,
        "disclaimer": DISCLAIMER,
        "langsmith": langsmith_enabled(),
    }

    app = get_app()
    inputs: dict[str, Any] = {"question": q, "ticker": ticker}
    route = ""
    citations: list[dict[str, str]] = []
    graph_config = _merge_config(tid, ticker=ticker)

    try:
        for chunk in app.stream(inputs, config=graph_config, stream_mode="updates"):
            if not isinstance(chunk, dict):
                continue
            for node, update in chunk.items():
                if not isinstance(update, dict):
                    continue
                if node == "classify":
                    route = str(update.get("route", route))
                if update.get("citations"):
                    citations = list(update["citations"])

                detail = ""
                if node == "classify":
                    detail = f"route → {update.get('route')}"
                    if update.get("ticker"):
                        detail += f" · {update['ticker']}"
                    if update.get("needs_human"):
                        detail += " · HITL"
                elif node == "rag":
                    detail = f"grade={update.get('rag_grade', '?')}"
                elif node == "calc":
                    detail = f"grade={update.get('calc_grade', '?')}"
                elif node == "synthesize":
                    detail = "brouillon prêt"
                elif node == "hitl":
                    detail = f"decision={update.get('human_decision', '?')}"

                yield {
                    "type": "step",
                    "node": node,
                    "label": NODE_LABELS.get(node, node),
                    "detail": detail,
                    "thread_id": tid,
                }

        snap = app.get_state(graph_config)
        interrupts = getattr(snap, "interrupts", None) or ()
        if interrupts or (snap.next and "hitl" in (snap.next or ())):
            # Prefer interrupt payloads; fall back to draft in values
            payload = _payload_from_interrupts(interrupts)
            values = snap.values or {}
            if not payload:
                payload = {
                    "reason": "sensitive_investment_question",
                    "question": values.get("question", q),
                    "draft": values.get("draft") or values.get("answer") or "",
                    "disclaimer": DISCLAIMER,
                    "actions": ["approve", "edit", "reject"],
                }
            yield {
                "type": "interrupt",
                "thread_id": tid,
                "route": values.get("route") or route,
                "payload": payload,
            }
            return

        values = snap.values or {}
        yield {
            "type": "final",
            "route": values.get("route") or route,
            "answer": values.get("answer", ""),
            "citations": values.get("citations") or citations,
            "thread_id": tid,
        }
    except Exception as exc:  # noqa: BLE001
        yield {"type": "error", "message": str(exc), "thread_id": tid}
    finally:
        flush_tracing()


def stream_resume(
    thread_id: str,
    *,
    action: str,
    edit: str = "",
    ticker: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Resume a paused HITL thread with approve | edit | reject."""
    tid = thread_id.strip()
    if not tid:
        yield {"type": "error", "message": "thread_id requis."}
        return

    action_norm = action.strip().lower()
    if action_norm not in ("approve", "edit", "reject"):
        yield {
            "type": "error",
            "message": "action doit être approve|edit|reject",
        }
        return

    if action_norm == "edit":
        resume_value: Any = {"action": "edit", "edit": edit}
    else:
        resume_value = action_norm

    yield {
        "type": "start",
        "thread_id": tid,
        "resume": action_norm,
        "provider": LLM_PROVIDER,
        "model": GEMINI_MODEL,
    }

    app = get_app()
    graph_config = _merge_config(tid, ticker=ticker)

    try:
        for chunk in app.stream(
            Command(resume=resume_value),
            config=graph_config,
            stream_mode="updates",
        ):
            if not isinstance(chunk, dict):
                continue
            for node, update in chunk.items():
                if node == "hitl" and isinstance(update, dict):
                    yield {
                        "type": "step",
                        "node": "hitl",
                        "label": NODE_LABELS["hitl"],
                        "detail": f"decision={update.get('human_decision')}",
                        "thread_id": tid,
                    }

        snap = app.get_state(graph_config)
        values = snap.values or {}
        yield {
            "type": "final",
            "route": "hitl",
            "answer": values.get("answer", ""),
            "citations": values.get("citations") or [],
            "thread_id": tid,
            "human_decision": values.get("human_decision"),
        }
    except Exception as exc:  # noqa: BLE001
        yield {"type": "error", "message": str(exc), "thread_id": tid}
    finally:
        flush_tracing()


def analyze(
    question: str,
    *,
    ticker: str | None = None,
    thread_id: str | None = None,
    auto_resume: str | None = None,
) -> dict[str, Any]:
    """Run until final or interrupt. Optional auto_resume for tests/CLI."""
    final: dict[str, Any] = {}
    interrupt_event: dict[str, Any] | None = None
    tid = thread_id

    for event in stream_analyze(question, ticker=ticker, thread_id=thread_id):
        if event.get("thread_id"):
            tid = event["thread_id"]
        if event.get("type") == "final":
            final = event
        if event.get("type") == "interrupt":
            interrupt_event = event
        if event.get("type") == "error":
            return {
                "answer": event.get("message", "Erreur"),
                "citations": [],
                "route": "error",
                "thread_id": tid,
                "interrupted": False,
            }

    if interrupt_event and auto_resume:
        for event in stream_resume(
            tid or "",
            action=auto_resume,
            ticker=ticker,
        ):
            if event.get("type") == "final":
                final = event
            if event.get("type") == "error":
                return {
                    "answer": event.get("message", "Erreur"),
                    "citations": [],
                    "route": "error",
                    "thread_id": tid,
                    "interrupted": False,
                }
        return {
            "answer": final.get("answer", ""),
            "citations": final.get("citations", []),
            "route": final.get("route", "hitl"),
            "thread_id": tid,
            "interrupted": False,
            "human_decision": final.get("human_decision"),
        }

    if interrupt_event:
        return {
            "answer": "",
            "citations": [],
            "route": interrupt_event.get("route", ""),
            "thread_id": tid,
            "interrupted": True,
            "interrupt": interrupt_event.get("payload"),
        }

    return {
        "answer": final.get("answer", ""),
        "citations": final.get("citations", []),
        "route": final.get("route", ""),
        "thread_id": tid,
        "interrupted": False,
    }
