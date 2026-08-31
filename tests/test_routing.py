"""Routing heuristics (no LLM)."""

from __future__ import annotations

from finance_analyst.graph.routing import (
    classify_route_heuristic,
    extract_ticker,
)


def test_route_roe_is_calc() -> None:
    assert classify_route_heuristic("What is Apple's ROE?") == "calc"


def test_route_risk_is_rag() -> None:
    assert classify_route_heuristic("What are the main risk factors?") == "rag"


def test_route_both() -> None:
    q = "What is Apple's ROE and what are the main risk factors?"
    assert classify_route_heuristic(q) == "both"


def test_extract_ticker_explicit() -> None:
    assert extract_ticker("hello", "msft") == "MSFT"


def test_extract_ticker_from_question() -> None:
    assert extract_ticker("Compare AAPL margins") == "AAPL"
    assert extract_ticker("Apple risk factors") == "AAPL"
