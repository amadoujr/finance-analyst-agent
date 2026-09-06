"""LangGraph supervisor graph with optional HITL interrupt."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from finance_analyst.calc.worker import ask_calc
from finance_analyst.config import DISCLAIMER
from finance_analyst.graph.routing import classify_route, extract_ticker
from finance_analyst.graph.sensitivity import default_safe_refusal, is_sensitive_question
from finance_analyst.graph.state import AnalystState
from finance_analyst.rag.worker import ask_rag


def classify_node(state: AnalystState) -> dict[str, Any]:
    question = state["question"]
    route = classify_route(question, use_llm=False)
    ticker = extract_ticker(question, state.get("ticker"))
    needs_human = is_sensitive_question(question)
    print(f"  [supervisor] route={route} ticker={ticker} hitl={needs_human}")
    return {"route": route, "ticker": ticker, "needs_human": needs_human}


def rag_node(state: AnalystState) -> dict[str, Any]:
    result = ask_rag(state["question"], ticker=state.get("ticker"))
    return {
        "rag_answer": result["answer"],
        "rag_grade": result["grade"],
        "citations": result["citations"],
    }


def calc_node(state: AnalystState) -> dict[str, Any]:
    ticker = state.get("ticker")
    if not ticker:
        msg = (
            "Ticker requis pour les ratios (ex. AAPL). "
            "Reformule avec le symbole ou utilise --ticker."
        )
        return {
            "calc_answer": msg,
            "calc_grade": "refuse",
            "ratios": {},
        }
    result = ask_calc(state["question"], ticker=ticker, use_llm_narrative=False)
    citations = list(state.get("citations") or [])
    citations.extend(result["citations"])
    return {
        "calc_answer": result["answer"],
        "calc_grade": result["grade"],
        "ratios": result.get("ratios") or {},
        "citations": citations,
    }


def synthesize_node(state: AnalystState) -> dict[str, Any]:
    route = state.get("route", "rag")
    parts: list[str] = []
    citations = list(state.get("citations") or [])

    if route in ("rag", "both") and state.get("rag_answer"):
        parts.append("## Analyse documentaire (10-K)\n\n" + state["rag_answer"])
    if route in ("calc", "both") and state.get("calc_answer"):
        parts.append("## Ratios (données seedées)\n\n" + state["calc_answer"])

    if not parts:
        draft = f"Aucun résultat produit.\n{DISCLAIMER}"
    else:
        draft = "\n\n".join(parts)
        if state.get("rag_grade") == "refuse" and route == "rag":
            pass
        if state.get("calc_grade") == "refuse" and route == "calc":
            pass

    # Soft guardrail even before HITL
    if state.get("needs_human"):
        draft = (
            f"{draft}\n\n"
            "---\n"
            f"**Rappel :** {DISCLAIMER}\n"
            "Une validation humaine est requise avant publication."
        )

    print(
        f"  [synthesize] route={route} "
        f"needs_human={state.get('needs_human', False)}"
    )
    return {"draft": draft, "answer": draft, "citations": citations}


def hitl_node(state: AnalystState) -> dict[str, Any]:
    """Pause for human approval when the question is investment-sensitive."""
    payload = {
        "reason": "sensitive_investment_question",
        "question": state.get("question", ""),
        "draft": state.get("draft") or state.get("answer") or "",
        "disclaimer": DISCLAIMER,
        "actions": ["approve", "edit", "reject"],
    }
    decision = interrupt(payload)

    # decision can be str ("approve") or dict {"action": "...", "edit": "..."}
    action = "reject"
    edit_text = ""
    if isinstance(decision, str):
        action = decision.strip().lower()
    elif isinstance(decision, dict):
        action = str(decision.get("action", "reject")).strip().lower()
        edit_text = str(decision.get("edit") or decision.get("text") or "").strip()

    if action not in ("approve", "edit", "reject"):
        action = "reject"

    draft = state.get("draft") or state.get("answer") or ""
    if action == "approve":
        answer = (
            f"{draft}\n\n"
            "---\n"
            "✅ Validé par un humain (HITL). "
            f"{DISCLAIMER}"
        )
    elif action == "edit":
        answer = edit_text or default_safe_refusal(state.get("question", ""), draft)
        if edit_text:
            answer = (
                f"{edit_text}\n\n"
                "---\n"
                "✏️ Texte édité et validé par un humain (HITL). "
                f"{DISCLAIMER}"
            )
    else:
        answer = default_safe_refusal(state.get("question", ""), draft)

    print(f"  [hitl] decision={action}")
    return {
        "human_decision": action,  # type: ignore[typeddict-item]
        "human_edit": edit_text,
        "answer": answer,
    }


def route_after_classify(state: AnalystState) -> str:
    return state.get("route", "rag")


def route_after_rag(state: AnalystState) -> str:
    if state.get("route") == "both":
        return "calc"
    return "synthesize"


def route_after_synthesize(state: AnalystState) -> str:
    if state.get("needs_human"):
        return "hitl"
    return "end"


def build_graph(*, checkpointer: Any | None = None) -> Any:
    graph = StateGraph(AnalystState)
    graph.add_node("classify", classify_node)
    graph.add_node("rag", rag_node)
    graph.add_node("calc", calc_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("hitl", hitl_node)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "rag": "rag",
            "calc": "calc",
            "both": "rag",
        },
    )
    graph.add_conditional_edges(
        "rag",
        route_after_rag,
        {
            "calc": "calc",
            "synthesize": "synthesize",
        },
    )
    graph.add_edge("calc", "synthesize")
    graph.add_conditional_edges(
        "synthesize",
        route_after_synthesize,
        {
            "hitl": "hitl",
            "end": END,
        },
    )
    graph.add_edge("hitl", END)

    saver = checkpointer if checkpointer is not None else MemorySaver()
    return graph.compile(checkpointer=saver)


@lru_cache(maxsize=1)
def get_app() -> Any:
    return build_graph()
