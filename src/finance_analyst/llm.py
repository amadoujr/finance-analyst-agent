"""LLM factory (Gemini default, HF optional later)."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from finance_analyst.config import GEMINI_MODEL, LLM_PROVIDER


def msg_text(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            else:
                text = getattr(block, "text", None)
                if text:
                    parts.append(str(text))
        return "".join(parts)
    return str(content)


@lru_cache(maxsize=1)
def get_llm():
    if LLM_PROVIDER in ("hf", "huggingface"):
        raise RuntimeError(
            "Provider HF non branché dans cette phase — utilise LLM_PROVIDER=gemini."
        )
    from langchain_google_genai import ChatGoogleGenerativeAI

    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY manquant (.env)")
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        max_tokens=1024,
        timeout=60,
        max_retries=1,
    )
