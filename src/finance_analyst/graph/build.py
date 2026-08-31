"""LangGraph supervisor graph."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from finance_analyst.config import DISCLAIMER
from finance_analyst.graph.routing import classify_route, extract_ticker
from finance_analyst.graph.state import AnalystState
from finance_analyst.calc.worker import ask_calc
from finance_analyst.rag.worker import ask_rag


def classify_node(state: AnalystState) -> dict[str, Any]:
    question = state["question"]
    route = classify_route(question, use_llm=False)
    ticker = extract_ticker(question, state.get("ticker"))
    print(f"  [supervisor] route={route} ticker={ticker}")
    return {"route": route, "ticker": ticker}


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
        answer = f"Aucun résultat produit.\n{DISCLAIMER}"
        grade: Literal["ok", "refuse"] = "refuse"
    else:
        answer = "\n\n".join(parts)
        grade = "ok"
        if state.get("rag_grade") == "refuse" and route == "rag":
            grade = "refuse"
        if state.get("calc_grade") == "refuse" and route == "calc":
            grade = "refuse"

    print(f"  [synthesize] route={route} grade={grade}")
    return {"answer": answer, "citations": citations}


def route_after_classify(state: AnalystState) -> str:
    return state.get("route", "rag")


def route_after_rag(state: AnalystState) -> str:
    if state.get("route") == "both":
        return "calc"
    return "synthesize"


def build_graph() -> Any:
    graph = StateGraph(AnalystState)
    graph.add_node("classify", classify_node)
    graph.add_node("rag", rag_node)
    graph.add_node("calc", calc_node)
    graph.add_node("synthesize", synthesize_node)

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
    graph.add_edge("synthesize", END)

    return graph.compile()


def get_app() -> Any:
    return build_graph()
