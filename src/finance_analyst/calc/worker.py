"""Calc worker — deterministic ratios + optional LLM narrative."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from finance_analyst.calc.fundamentals import get_fundamentals, list_tickers
from finance_analyst.calc.ratios import compute_all_ratios, format_ratio_pct, format_ratio_x
from finance_analyst.config import DISCLAIMER, GEMINI_MODEL, LLM_PROVIDER
from finance_analyst.llm import get_llm, msg_text


class CalcResult(TypedDict):
    mode: Literal["calc"]
    ticker: str
    grade: Literal["ok", "refuse"]
    answer: str
    ratios: dict[str, Any]
    citations: list[dict[str, str]]


def compute_ratios(ticker: str) -> dict[str, Any]:
    row = get_fundamentals(ticker)
    if not row:
        available = ", ".join(list_tickers())
        raise ValueError(
            f"Ticker {ticker.upper()} absent du CSV. Disponibles : {available}"
        )
    return compute_all_ratios(row)


def _format_deterministic_answer(data: dict[str, Any]) -> str:
    ratios = data["ratios"]
    unit = data["unit"]
    fy = data["fiscal_year"]
    lines = [
        f"{data['company']} ({data['ticker']}) — FY{fy} ({data['currency']}, {unit})",
        "",
        "Fondamentaux seedés :",
        f"  · Revenu : {data['inputs']['revenue']:,.0f}",
        f"  · Résultat net : {data['inputs']['net_income']:,.0f}",
        f"  · Capitaux propres : {data['inputs']['total_equity']:,.0f}",
        f"  · Dette totale : {data['inputs']['total_debt']:,.0f}",
        "",
        "Ratios (calcul Python, pas le LLM) :",
        f"  · Marge nette : {format_ratio_pct(ratios['net_margin'])} "
        f"({data['formulas']['net_margin']})",
        f"  · ROE : {format_ratio_pct(ratios['return_on_equity'])} "
        f"({data['formulas']['return_on_equity']})",
        f"  · Dette / capitaux propres : {format_ratio_x(ratios['debt_to_equity'])} "
        f"({data['formulas']['debt_to_equity']})",
        "",
        f"Source : {data['source']}",
        DISCLAIMER,
    ]
    return "\n".join(lines)


def _citations_from_data(data: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "chunk_id": f"{data['ticker']}-FY{data['fiscal_year']}",
            "ticker": data["ticker"],
            "source": data["source"],
            "excerpt": (
                f"revenue={data['inputs']['revenue']}, "
                f"net_income={data['inputs']['net_income']}, "
                f"equity={data['inputs']['total_equity']}, "
                f"debt={data['inputs']['total_debt']}"
            ),
        }
    ]


def ask_calc(
    question: str,
    *,
    ticker: str | None = None,
    use_llm_narrative: bool = False,
) -> CalcResult:
    """Compute ratios for one ticker. Ticker required or parsed from --ticker."""
    sym = (ticker or "").strip().upper()
    if not sym:
        raise ValueError("Ticker requis pour le worker Calcul (ex. --ticker AAPL).")

    try:
        data = compute_ratios(sym)
    except ValueError as exc:
        return {
            "mode": "calc",
            "ticker": sym,
            "grade": "refuse",
            "answer": f"{exc}\n{DISCLAIMER}",
            "ratios": {},
            "citations": [],
        }

    citations = _citations_from_data(data)

    if use_llm_narrative:
        prompt = (
            "Tu expliques des ratios financiers calculés par code (ne recalcule pas).\n"
            f"{DISCLAIMER}\n\n"
            f"Question: {question.strip()}\n\n"
            f"Données:\n{_format_deterministic_answer(data)}\n\n"
            "Réponse courte en français, cite le ticker et les ratios."
        )
        print(f"  [calc+llm] {LLM_PROVIDER}/{GEMINI_MODEL} …")
        answer = msg_text(get_llm().invoke(prompt)).strip()
    else:
        answer = _format_deterministic_answer(data)

    return {
        "mode": "calc",
        "ticker": sym,
        "grade": "ok",
        "answer": answer,
        "ratios": data,
        "citations": citations,
    }
