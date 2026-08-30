"""FastAPI entrypoint — health check first; graph/SSE arrive in later phases."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from finance_analyst import __version__
from finance_analyst.config import DISCLAIMER, GEMINI_MODEL, LLM_PROVIDER
import os

app = FastAPI(
    title="finance-analyst-agent",
    version=__version__,
    description="Multi-agent financial document analysis (portfolio / learning).",
)

_cors = os.getenv("CORS_ORIGINS", "*").strip()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors.split(",") if o.strip()] or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "version": __version__,
        "provider": LLM_PROVIDER,
        "model": GEMINI_MODEL if LLM_PROVIDER == "gemini" else "hf",
        "disclaimer": DISCLAIMER,
    }
