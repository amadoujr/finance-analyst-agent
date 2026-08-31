"""Route questions to RAG, Calc, or both."""

from __future__ import annotations

import re
from typing import Literal

from finance_analyst.calc.fundamentals import list_tickers
from finance_analyst.llm import get_llm, msg_text

CALC_HINTS = (
    "roe",
    "ratio",
    "ratios",
    "margin",
    "marge",
    "debt",
    "dette",
    "revenue",
    "revenu",
    "equity",
    "capitaux",
    "profit",
    "ebitda",
    "financial ratio",
    "net income",
    "résultat net",
)

RAG_HINTS = (
    "risk",
    "risque",
    "factor",
    "business",
    "strategy",
    "stratégie",
    "competition",
    "regulatory",
    "forward-looking",
    "item 1a",
    "10-k",
    "describe",
    "décris",
    "explain",
    "cyber",
    "tariff",
    "douane",
)

COMPANY_TO_TICKER = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "alphabet": "GOOGL",
    "google": "GOOGL",
}


def extract_ticker(question: str, explicit: str | None = None) -> str | None:
    if explicit and explicit.strip():
        return explicit.strip().upper()
    known = set(list_tickers())
    upper_q = question.upper()
    for sym in known:
        if re.search(rf"\b{sym}\b", upper_q):
            return sym
    lower_q = question.lower()
    for name, sym in COMPANY_TO_TICKER.items():
        if name in lower_q:
            return sym
    return None


def classify_route_heuristic(question: str) -> Literal["rag", "calc", "both"]:
    q = question.lower()
    has_calc = any(h in q for h in CALC_HINTS)
    has_rag = any(h in q for h in RAG_HINTS)
    if has_calc and has_rag:
        return "both"
    if has_calc:
        return "calc"
    if has_rag:
        return "rag"
    return "rag"


def classify_route_llm(question: str) -> Literal["rag", "calc", "both"]:
    prompt = (
        "Classify this finance analyst question into exactly one route:\n"
        "- rag = qualitative 10-K text (risks, business, strategy)\n"
        "- calc = quantitative ratios (ROE, margin, debt/equity) from structured data\n"
        "- both = needs document context AND numeric ratios\n"
        "Reply with one word only: rag, calc, or both.\n\n"
        f"Question: {question}\n\nRoute:"
    )
    raw = msg_text(get_llm().invoke(prompt)).strip().lower()
    if raw.startswith("both") or "both" in raw.split()[0]:
        return "both"
    if raw.startswith("calc"):
        return "calc"
    return "rag"


def classify_route(
    question: str,
    *,
    use_llm: bool = False,
) -> Literal["rag", "calc", "both"]:
    heuristic = classify_route_heuristic(question)
    if heuristic != "rag":
        return heuristic
    if use_llm and not any(h in question.lower() for h in RAG_HINTS):
        return classify_route_llm(question)
    return "rag"
