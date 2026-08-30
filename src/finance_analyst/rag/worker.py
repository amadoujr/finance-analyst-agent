"""Worker RAG: retrieve → grade → generate | refuse."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from langchain_core.documents import Document

from finance_analyst.config import DISCLAIMER, GEMINI_MODEL, LLM_PROVIDER
from finance_analyst.llm import get_llm, msg_text
from finance_analyst.rag.retrieve import retrieve


class RagResult(TypedDict):
    question: str
    grade: Literal["ok", "refuse"]
    answer: str
    citations: list[dict[str, str]]
    docs_count: int


def parse_grade(text: str) -> Literal["ok", "refuse"]:
    cleaned = text.strip().lower()
    first = cleaned.split()[0] if cleaned else ""
    first = first.strip(".:;,'\"")
    if first.startswith("ok"):
        return "ok"
    if "refuse" in cleaned[:40] or first.startswith("refuse"):
        return "refuse"
    if "ok" in cleaned[:20] and "refuse" not in cleaned[:20]:
        return "ok"
    return "refuse"


def _context_blocks(docs: list[Document]) -> tuple[str, list[dict[str, str]]]:
    blocks: list[str] = []
    citations: list[dict[str, str]] = []
    for d in docs:
        chunk_id = str(d.metadata.get("chunk_id", "?"))
        ticker = str(d.metadata.get("ticker", "?"))
        source = str(d.metadata.get("source", ""))
        blocks.append(f"[{chunk_id}] ({ticker} · {source})\n{d.page_content}")
        citations.append(
            {
                "chunk_id": chunk_id,
                "ticker": ticker,
                "source": source,
                "excerpt": d.page_content[:220].replace("\n", " "),
            }
        )
    return "\n\n".join(blocks), citations


def grade_docs(question: str, docs: list[Document]) -> Literal["ok", "refuse"]:
    if not docs:
        return "refuse"
    context, _ = _context_blocks(docs)
    prompt = (
        "Tu évalues si les EXTRAITS de rapports 10-K permettent de répondre "
        "à la question (même partiellement).\n"
        "Réponds par UN seul mot : ok ou refuse.\n"
        "- ok = au moins un extrait traite du sujet\n"
        "- refuse = hors périmètre ou extraits non pertinents\n"
        "Les questions de conseil d'investissement ('dois-je acheter ?') "
        "peuvent être ok si le corpus décrit l'activité, mais la réponse "
        "finale devra rappeler que ce n'est pas un conseil.\n\n"
        f"Question: {question}\n\nExtraits:\n{context}\n\nDécision:"
    )
    raw = msg_text(get_llm().invoke(prompt)).strip()
    decision = parse_grade(raw)
    print(f"  [grade] {decision} (raw={raw!r})")
    return decision


def generate_answer(question: str, docs: list[Document]) -> tuple[str, list[dict[str, str]]]:
    context, citations = _context_blocks(docs)
    prompt = (
        "Tu es un assistant d'analyse documentaire financière (portfolio / pédagogique).\n"
        f"Disclaimer obligatoire à respecter : {DISCLAIMER}\n\n"
        "Règles strictes :\n"
        "1. Réponds UNIQUEMENT à partir des extraits fournis.\n"
        "2. Cite les chunks via leur id, ex. [AAPL-C0012].\n"
        "3. N'invente AUCUN chiffre absent des extraits. Si un montant manque, dis-le.\n"
        "4. Ne donne pas de recommandation d'achat/vente ; reste factuel.\n"
        "5. Réponse claire en français (≤ 12 phrases).\n\n"
        f"Question: {question}\n\n"
        f"Extraits:\n{context}"
    )
    print(f"  [generate] {LLM_PROVIDER}/{GEMINI_MODEL} …")
    answer = msg_text(get_llm().invoke(prompt)).strip()
    return answer, citations


def refuse_answer(docs: list[Document]) -> tuple[str, list[dict[str, str]]]:
    tickers = sorted({str(d.metadata.get("ticker", "?")) for d in docs})
    answer = (
        "Je ne peux pas répondre de façon fiable à partir du corpus 10-K disponible.\n"
        "Aucune information inventée n’est fournie.\n"
        f"Tickers indexés touchés : {', '.join(tickers) if tickers else '(aucun)'}.\n"
        f"{DISCLAIMER}"
    )
    citations = [
        {
            "chunk_id": str(d.metadata.get("chunk_id", "")),
            "ticker": str(d.metadata.get("ticker", "")),
            "source": str(d.metadata.get("source", "")),
            "excerpt": d.page_content[:120].replace("\n", " "),
        }
        for d in docs
    ]
    return answer, citations


def ask_rag(
    question: str,
    *,
    ticker: str | None = None,
) -> RagResult:
    q = question.strip()
    print(f"  [retrieve] q={q!r} ticker={ticker}")
    docs = retrieve(q, ticker=ticker)
    print(f"  [retrieve] {len(docs)} chunks")
    for d in docs:
        print(
            f"      · {d.metadata.get('chunk_id')} "
            f"({d.metadata.get('ticker')}) {d.metadata.get('source')}"
        )

    grade = grade_docs(q, docs)
    if grade == "ok":
        answer, citations = generate_answer(q, docs)
    else:
        answer, citations = refuse_answer(docs)

    return {
        "question": q,
        "grade": grade,
        "answer": answer,
        "citations": citations,
        "docs_count": len(docs),
    }


def ask_rag_dict(question: str, *, ticker: str | None = None) -> dict[str, Any]:
    return dict(ask_rag(question, ticker=ticker))
