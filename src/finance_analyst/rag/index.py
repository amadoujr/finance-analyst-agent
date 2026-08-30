"""Build and load FAISS index over EDGAR filings."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from finance_analyst.config import EMBEDDING_MODEL, INDEX_DIR, RAW_DIR
from finance_analyst.rag.html_parse import html_to_text

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
# Keep index builds tractable on a laptop (full 10-K HTML can be huge).
MAX_CHARS_PER_FILING = 180_000


def load_manifest() -> list[dict[str, Any]]:
    path = RAW_DIR / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run: uv run python scripts/fetch_edgar.py"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def load_filing_documents() -> list[Document]:
    docs: list[Document] = []
    for row in load_manifest():
        path = RAW_DIR / row["file"]
        if not path.exists():
            print(f"  ! missing filing: {path.name}")
            continue
        text = html_to_text(path.read_bytes())
        if len(text) < 200:
            print(f"  ! too little text after parse: {path.name}")
            continue
        if len(text) > MAX_CHARS_PER_FILING:
            print(
                f"  · truncating {row['ticker']}: "
                f"{len(text):,} → {MAX_CHARS_PER_FILING:,} chars"
            )
            text = text[:MAX_CHARS_PER_FILING]
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "ticker": row["ticker"],
                    "company": row.get("name", ""),
                    "filing_date": row.get("filing_date", ""),
                    "source": path.name,
                    "source_url": row.get("source_url", ""),
                    "doc_id": f"{row['ticker']}-{row.get('filing_date', 'na')}",
                },
            )
        )
        print(f"  · parsed {row['ticker']}: {len(text):,} chars from {path.name}")
    return docs


def chunk_documents(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    # Stable chunk ids for citations
    for i, chunk in enumerate(chunks):
        ticker = chunk.metadata.get("ticker", "DOC")
        chunk.metadata["chunk_id"] = f"{ticker}-C{i:04d}"
    return chunks


def build_faiss_index(*, persist: bool = True) -> FAISS:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading filings …")
    docs = load_filing_documents()
    if not docs:
        raise RuntimeError("No filings to index. Run scripts/fetch_edgar.py first.")
    print(f"Chunking ({CHUNK_SIZE}/{CHUNK_OVERLAP}) …")
    chunks = chunk_documents(docs)
    print(f"Embedding {len(chunks)} chunks with {EMBEDDING_MODEL} …")
    store = FAISS.from_documents(chunks, get_embeddings())
    if persist:
        store.save_local(str(INDEX_DIR))
        print(f"Saved FAISS → {INDEX_DIR}")
    return store


def index_exists() -> bool:
    return (INDEX_DIR / "index.faiss").exists()


@lru_cache(maxsize=1)
def load_faiss_index() -> FAISS:
    if not index_exists():
        raise FileNotFoundError(
            f"No index in {INDEX_DIR}. Run: uv run python scripts/build_index.py"
        )
    return FAISS.load_local(
        str(INDEX_DIR),
        get_embeddings(),
        allow_dangerous_deserialization=True,
    )


def clear_index_cache() -> None:
    load_faiss_index.cache_clear()
