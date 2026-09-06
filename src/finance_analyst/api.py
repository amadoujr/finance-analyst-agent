"""FastAPI — health + supervisor SSE + HITL resume."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Iterator
from typing import Any, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from finance_analyst import __version__
from finance_analyst.config import DISCLAIMER, GEMINI_MODEL, LANGCHAIN_PROJECT, LLM_PROVIDER
from finance_analyst.graph.runner import stream_analyze, stream_resume
from finance_analyst.observability.langsmith import langsmith_enabled

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


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    ticker: str | None = Field(default=None, max_length=12)
    thread_id: str | None = Field(default=None, max_length=80)


class ResumeRequest(BaseModel):
    thread_id: str = Field(min_length=1, max_length=80)
    action: Literal["approve", "edit", "reject"]
    edit: str = Field(default="", max_length=8000)
    ticker: str | None = Field(default=None, max_length=12)


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def _sse_from_sync(iterator: Iterator[dict[str, Any]]):
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def worker() -> None:
        try:
            for event in iterator:
                loop.call_soon_threadsafe(queue.put_nowait, event)
        except Exception as exc:  # noqa: BLE001
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "error", "message": str(exc)},
            )
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    producer = asyncio.create_task(asyncio.to_thread(worker))
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield _sse(item)
            await asyncio.sleep(0)
    finally:
        await producer


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "version": __version__,
        "provider": LLM_PROVIDER,
        "model": GEMINI_MODEL if LLM_PROVIDER == "gemini" else "hf",
        "disclaimer": DISCLAIMER,
        "langsmith": langsmith_enabled(),
        "langsmith_project": LANGCHAIN_PROJECT,
        "hitl": True,
    }


@app.post("/ask")
async def ask(body: AskRequest) -> StreamingResponse:
    iterator = stream_analyze(
        body.question,
        ticker=body.ticker,
        thread_id=body.thread_id,
    )
    return StreamingResponse(
        _sse_from_sync(iterator),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/resume")
async def resume(body: ResumeRequest) -> StreamingResponse:
    iterator = stream_resume(
        body.thread_id,
        action=body.action,
        edit=body.edit,
        ticker=body.ticker,
    )
    return StreamingResponse(
        _sse_from_sync(iterator),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
