"""Langfuse config (no network)."""

from __future__ import annotations

from finance_analyst.observability import langfuse as lf


def test_langfuse_disabled_without_keys(monkeypatch) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    lf.get_langfuse_handler.cache_clear()
    lf._ensure_client.cache_clear()
    assert lf.langfuse_enabled() is False
    assert lf.get_langfuse_handler() is None
    assert lf.run_config(ticker="AAPL") == {}


def test_run_config_with_handler(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    lf.get_langfuse_handler.cache_clear()
    lf._ensure_client.cache_clear()

    class FakeHandler:
        pass

    monkeypatch.setattr(lf, "_ensure_client", lambda: True)
    monkeypatch.setattr(lf, "get_langfuse_handler", lambda: FakeHandler())

    cfg = lf.run_config(ticker="MSFT", session_id="sess-1")
    assert len(cfg["callbacks"]) == 1
    assert cfg["metadata"]["ticker"] == "MSFT"
    assert cfg["metadata"]["langfuse_session_id"] == "sess-1"
    assert cfg["run_name"] == "finance-analyze"
