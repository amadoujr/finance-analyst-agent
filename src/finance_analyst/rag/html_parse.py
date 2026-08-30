"""Parse SEC EDGAR HTML / inline XBRL into plain text."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup


def html_to_text(raw: str | bytes) -> str:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")

    soup = BeautifulSoup(raw, "lxml")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # Hidden iXBRL header noise
    for tag in soup.find_all(True):
        name = (tag.name or "").lower()
        if name.startswith("ix:"):
            # Keep nonNumeric / nonFraction text that might appear in body;
            # drop header-only containers.
            parent_names = {p.name for p in tag.parents if getattr(p, "name", None)}
            if "ix:header" in parent_names or name == "ix:header":
                tag.decompose()

    text = soup.get_text("\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
