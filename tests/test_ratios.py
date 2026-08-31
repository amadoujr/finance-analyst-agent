"""Unit tests for fundamentals + ratio tools."""

from __future__ import annotations

import pytest

from finance_analyst.calc.fundamentals import get_fundamentals, load_fundamentals
from finance_analyst.calc.ratios import (
    compute_all_ratios,
    debt_to_equity,
    net_margin,
    return_on_equity,
)
from finance_analyst.calc.worker import ask_calc, compute_ratios


def test_load_three_tickers() -> None:
    rows = load_fundamentals()
    tickers = {r.ticker for r in rows}
    assert tickers == {"AAPL", "MSFT", "GOOGL"}


def test_aapl_net_margin() -> None:
    row = get_fundamentals("AAPL")
    assert row is not None
    margin = net_margin(row)
    assert margin is not None
    # 93736 / 391035
    assert abs(margin - 0.2399) < 0.001


def test_aapl_roe() -> None:
    row = get_fundamentals("AAPL")
    assert row is not None
    roe = return_on_equity(row)
    assert roe is not None
    assert abs(roe - 0.1646) < 0.001


def test_aapl_debt_to_equity() -> None:
    row = get_fundamentals("AAPL")
    assert row is not None
    dte = debt_to_equity(row)
    assert dte is not None
    assert abs(dte - 0.1874) < 0.001


def test_compute_all_ratios_structure() -> None:
    data = compute_ratios("MSFT")
    assert data["ticker"] == "MSFT"
    assert "ratios" in data
    assert data["ratios"]["net_margin"] is not None
    assert data["source"] == "data/structured/fundamentals.csv"


def test_ask_calc_unknown_ticker() -> None:
    result = ask_calc("What is the ROE?", ticker="UNKNOWN")
    assert result["grade"] == "refuse"
    assert "absent" in result["answer"].lower() or "disponibles" in result["answer"].lower()


def test_ask_calc_ok() -> None:
    result = ask_calc("What is Apple's ROE?", ticker="AAPL")
    assert result["grade"] == "ok"
    assert "ROE" in result["answer"]
    assert result["citations"][0]["ticker"] == "AAPL"
