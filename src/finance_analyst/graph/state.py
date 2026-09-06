"""LangGraph analyst state."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class AnalystState(TypedDict, total=False):
    question: str
    ticker: str | None
    route: Literal["rag", "calc", "both"]
    rag_answer: str
    rag_grade: Literal["ok", "refuse"]
    calc_answer: str
    calc_grade: Literal["ok", "refuse"]
    draft: str
    needs_human: bool
    human_decision: Literal["approve", "edit", "reject"] | None
    human_edit: str
    answer: str
    citations: list[dict[str, str]]
    ratios: dict[str, Any]
