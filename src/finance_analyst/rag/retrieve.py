"""Hybrid retrieve: semantic FAISS + lexical keyword overlap."""

from __future__ import annotations

import re
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from finance_analyst.rag.index import load_faiss_index

TOP_K = 4


def _tokens(text: str) -> set[str]:
    return {
        t
        for t in re.findall(r"[a-z0-9][a-z0-9'-]{2,}", text.lower())
        if len(t) >= 3
    }


def _all_docs(store: FAISS) -> list[Document]:
    # FAISS docstore: id → Document
    docs: list[Document] = []
    docstore = store.docstore
    ids = getattr(store, "index_to_docstore_id", {}) or {}
    for _i, doc_id in ids.items():
        doc = docstore.search(doc_id)
        if isinstance(doc, Document):
            docs.append(doc)
    return docs


def lexical_hits(
    question: str,
    store: FAISS,
    *,
    limit: int = TOP_K,
    ticker: str | None = None,
) -> list[Document]:
    q_tokens = _tokens(question)
    if not q_tokens:
        return []
    scored: list[tuple[int, Document]] = []
    for doc in _all_docs(store):
        if ticker and doc.metadata.get("ticker") != ticker.upper():
            continue
        overlap = len(q_tokens & _tokens(doc.page_content))
        if overlap > 0:
            scored.append((overlap, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:limit]]


def merge_docs(*groups: list[Document], limit: int = TOP_K) -> list[Document]:
    seen: set[str] = set()
    out: list[Document] = []
    for group in groups:
        for d in group:
            key = d.metadata.get("chunk_id") or (
                f"{d.metadata.get('source')}|{d.page_content[:80]}"
            )
            if key in seen:
                continue
            seen.add(str(key))
            out.append(d)
            if len(out) >= limit:
                return out
    return out


def retrieve(
    question: str,
    *,
    store: FAISS | None = None,
    top_k: int = TOP_K,
    ticker: str | None = None,
) -> list[Document]:
    store = store or load_faiss_index()
    filter_dict: dict[str, Any] | None = None
    if ticker:
        filter_dict = {"ticker": ticker.upper()}

    try:
        if filter_dict:
            semantic = store.similarity_search(
                question, k=top_k, filter=filter_dict
            )
        else:
            semantic = store.similarity_search(question, k=top_k)
    except Exception:
        # Some FAISS builds ignore metadata filter — fall back + post-filter
        semantic = store.similarity_search(question, k=top_k * 3)
        if ticker:
            semantic = [
                d
                for d in semantic
                if d.metadata.get("ticker") == ticker.upper()
            ][:top_k]

    lexical = lexical_hits(question, store, limit=top_k, ticker=ticker)
    return merge_docs(lexical, semantic, limit=top_k)
