"""LangSmith config (no network)."""

from __future__ import annotations

from finance_analyst.observability import langsmith as ls


def test_langsmith_disabled_without_env(monkeypatch) -> None:
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    assert ls.langsmith_enabled() is False
    assert ls.run_config(ticker="AAPL") == {}


def test_langsmith_enabled_builds_config(monkeypatch) -> None:
    monkeypatch.setenv("LANGCHAIN_API_KEY", "lsv2_test")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_PROJECT", "finance-analyst-agent")

    cfg = ls.run_config(ticker="MSFT", session_id="sess-1")
    assert cfg["run_name"] == "finance-analyze"
    assert cfg["tags"] == ["finance-analyst"]
    assert cfg["metadata"]["ticker"] == "MSFT"
    assert cfg["metadata"]["session_id"] == "sess-1"
    assert cfg["metadata"]["project"] == "finance-analyst-agent"
