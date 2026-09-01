"""Langfuse tracing (optional — enabled when keys are set)."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from finance_analyst.config import LANGFUSE_HOST


def langfuse_enabled() -> bool:
    pk = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    sk = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    return bool(pk and sk)


@lru_cache(maxsize=1)
def _ensure_client() -> bool:
    if not langfuse_enabled():
        return False
    from langfuse import Langfuse

    Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY", "").strip(),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY", "").strip(),
        host=LANGFUSE_HOST,
    )
    return True


@lru_cache(maxsize=1)
def get_langfuse_handler():
    if not _ensure_client():
        return None
    from langfuse.langchain import CallbackHandler

    return CallbackHandler()


def run_config(
    *,
    session_id: str | None = None,
    ticker: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """LangGraph / LangChain config with optional Langfuse callbacks."""
    handler = get_langfuse_handler()
    if not handler:
        return {}

    metadata: dict[str, Any] = {"langfuse_tags": tags or ["finance-analyst"]}
    if session_id:
        metadata["langfuse_session_id"] = session_id
    if ticker:
        metadata["ticker"] = ticker

    return {
        "callbacks": [handler],
        "metadata": metadata,
        "run_name": "finance-analyze",
    }


def flush_langfuse() -> None:
    if not langfuse_enabled():
        return
    try:
        from langfuse import get_client

        get_client().flush()
    except Exception:  # noqa: BLE001
        pass
