"""CLI placeholder — will call the LangGraph app once workers exist."""

from __future__ import annotations

from finance_analyst import __version__
from finance_analyst.config import DISCLAIMER, GEMINI_MODEL, LLM_PROVIDER


def main() -> None:
    print(f"finance-analyst-agent v{__version__}")
    print(f"LLM: {LLM_PROVIDER} / {GEMINI_MODEL}")
    print(DISCLAIMER)
    print()
    print("Phases suivantes : corpus EDGAR → worker RAG → calcul → supervisor.")
    print("Lancer l’API : uv run uvicorn finance_analyst.api:app --reload --port 8080")


if __name__ == "__main__":
    main()
