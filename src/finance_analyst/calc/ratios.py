"""Financial ratio formulas on seed fundamentals (no LLM)."""

from __future__ import annotations

from typing import Any

from finance_analyst.calc.fundamentals import FundamentalsRow


def _safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def net_margin(row: FundamentalsRow) -> float | None:
    """Net income / revenue."""
    return _safe_div(row.net_income, row.revenue)


def return_on_equity(row: FundamentalsRow) -> float | None:
    """Net income / total equity (ROE)."""
    return _safe_div(row.net_income, row.total_equity)


def debt_to_equity(row: FundamentalsRow) -> float | None:
    """Total debt / total equity."""
    return _safe_div(row.total_debt, row.total_equity)


def compute_all_ratios(row: FundamentalsRow) -> dict[str, Any]:
    margin = net_margin(row)
    roe = return_on_equity(row)
    dte = debt_to_equity(row)

    return {
        "ticker": row.ticker,
        "company": row.company,
        "fiscal_year": row.fiscal_year,
        "currency": row.currency,
        "unit": row.unit,
        "inputs": {
            "revenue": row.revenue,
            "net_income": row.net_income,
            "total_equity": row.total_equity,
            "total_debt": row.total_debt,
        },
        "ratios": {
            "net_margin": margin,
            "return_on_equity": roe,
            "debt_to_equity": dte,
        },
        "formulas": {
            "net_margin": "net_income / revenue",
            "return_on_equity": "net_income / total_equity",
            "debt_to_equity": "total_debt / total_equity",
        },
        "source": "data/structured/fundamentals.csv",
        "source_note": row.source_note,
    }


def format_ratio_pct(value: float | None, *, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.{digits}f}%"


def format_ratio_x(value: float | None, *, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}x"
