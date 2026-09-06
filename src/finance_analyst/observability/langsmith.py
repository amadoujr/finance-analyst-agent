"""LangSmith tracing (native LangChain / LangGraph)."""

from __future__ import annotations

import os
from typing import Any


def langsmith_enabled() -> bool:
    key = os.getenv("LANGCHAIN_API_KEY", "").strip()
    tracing = os.getenv("LANGCHAIN_TRACING_V2", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    return bool(key and tracing)


def run_config(
    *,
    session_id: str | None = None,
    ticker: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """LangGraph config: run name + metadata (tracing via LANGCHAIN_* env)."""
    if not langsmith_enabled():
        return {}

    project = os.getenv("LANGCHAIN_PROJECT", "finance-analyst-agent").strip()
    metadata: dict[str, Any] = {"project": project}
    if session_id:
        metadata["session_id"] = session_id
    if ticker:
        metadata["ticker"] = ticker

    return {
        "run_name": "finance-analyze",
        "tags": tags or ["finance-analyst"],
        "metadata": metadata,
    }


def flush_tracing() -> None:
    """Wait for pending LangSmith trace batches (CLI / short-lived processes)."""
    if not langsmith_enabled():
        return
    try:
        from langchain_core.tracers.langchain import wait_for_all_tracers

        wait_for_all_tracers()
    except Exception:  # noqa: BLE001
        pass
