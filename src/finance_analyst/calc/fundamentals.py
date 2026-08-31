"""Load seed fundamentals from CSV (deterministic, auditable)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from finance_analyst.config import STRUCTURED_DIR

FUNDAMENTALS_PATH = STRUCTURED_DIR / "fundamentals.csv"


@dataclass(frozen=True)
class FundamentalsRow:
    ticker: str
    company: str
    fiscal_year: int
    currency: str
    unit: str
    revenue: float
    net_income: float
    total_equity: float
    total_debt: float
    source_note: str


def load_fundamentals(path: Path | None = None) -> list[FundamentalsRow]:
    csv_path = path or FUNDAMENTALS_PATH
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing fundamentals CSV: {csv_path}")

    rows: list[FundamentalsRow] = []
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            rows.append(
                FundamentalsRow(
                    ticker=raw["ticker"].strip().upper(),
                    company=raw["company"].strip(),
                    fiscal_year=int(raw["fiscal_year"]),
                    currency=raw["currency"].strip(),
                    unit=raw["unit"].strip(),
                    revenue=float(raw["revenue"]),
                    net_income=float(raw["net_income"]),
                    total_equity=float(raw["total_equity"]),
                    total_debt=float(raw["total_debt"]),
                    source_note=raw.get("source_note", "").strip(),
                )
            )
    return rows


def get_fundamentals(
    ticker: str,
    *,
    path: Path | None = None,
) -> FundamentalsRow | None:
    sym = ticker.strip().upper()
    for row in load_fundamentals(path):
        if row.ticker == sym:
            return row
    return None


def list_tickers(*, path: Path | None = None) -> list[str]:
    return [r.ticker for r in load_fundamentals(path)]
