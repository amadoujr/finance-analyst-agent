"""Detect questions that need human approval before a final answer."""

from __future__ import annotations

import re

SENSITIVE_PATTERNS = (
    r"\b(buy|sell|purchase|investir|investissement)\b",
    r"\b(should i|dois[- ]je|faut[- ]il)\b.*\b(buy|acheter|vendre|investir)\b",
    r"\b(recommend|recommand|conseil(le)?)\b.*\b(buy|acheter|stock|action|investir)\b",
    r"\b(investissement|investment)\s+(advice|conseil)\b",
    r"\b(acheter|vendre)\b.*\b(action|actions|stock|titre)\b",
    r"\bis it (a )?(good|bad) (time|idea) to (buy|sell|invest)\b",
)


def is_sensitive_question(question: str) -> bool:
    q = (question or "").strip().lower()
    if not q:
        return False
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, q, flags=re.IGNORECASE):
            return True
    # Short FR/EN keywords that almost always imply advice
    short_hits = (
        "dois-je acheter",
        "should i buy",
        "should i sell",
        "faut-il acheter",
        "recommandation d'achat",
        "buy recommendation",
        "price target",
        "objectif de cours",
    )
    return any(h in q for h in short_hits)


def default_safe_refusal(question: str, draft: str) -> str:
    return (
        "## Décision humaine : rejetée\n\n"
        "Aucune recommandation d’investissement n’est publiée.\n"
        "Ce système est pédagogique et ne fournit pas de conseil financier.\n\n"
        f"Question concernée : {question.strip()}\n\n"
        "---\n"
        "Brouillon non publié (extrait) :\n"
        f"{(draft or '')[:400]}…"
    )
