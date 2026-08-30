#!/usr/bin/env python3
"""Download a few public 10-K filings from SEC EDGAR (sample corpus).

Usage:
  uv run python scripts/fetch_edgar.py

Notes:
  - SEC requires a descriptive User-Agent with contact email.
  - Set SEC_USER_AGENT in .env, e.g. "FinanceAnalystAgent contact@example.com"
  - PDFs/HTMLs land in data/raw/ (gitignored).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finance_analyst.config import RAW_DIR  # noqa: E402

# Well-known public companies — CIK zero-padded 10 digits.
# We resolve the latest 10-K accession via the SEC submissions API.
TICKERS: list[dict[str, str]] = [
    {"ticker": "AAPL", "cik": "0000320193", "name": "Apple Inc."},
    {"ticker": "MSFT", "cik": "0000789019", "name": "Microsoft Corp."},
    {"ticker": "GOOGL", "cik": "0001652044", "name": "Alphabet Inc."},
]

SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{primary}"


def user_agent() -> str:
    ua = os.getenv("SEC_USER_AGENT", "").strip()
    if not ua:
        ua = "FinanceAnalystAgent learning-portfolio (replace-with-your-email@example.com)"
    return ua


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent(), "Accept-Encoding": "identity"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent(), "Accept-Encoding": "identity"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def latest_10k(cik: str) -> tuple[str, str, str]:
    """Return (accession, primary_document, filing_date) for the newest 10-K."""
    data = fetch_json(SEC_SUBMISSIONS.format(cik=cik))
    recent = data["filings"]["recent"]
    forms = recent["form"]
    for i, form in enumerate(forms):
        if form == "10-K":
            return (
                recent["accessionNumber"][i],
                recent["primaryDocument"][i],
                recent["filingDate"][i],
            )
    raise RuntimeError(f"No 10-K found for CIK {cik}")


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, str]] = []

    for row in TICKERS:
        ticker, cik, name = row["ticker"], row["cik"], row["name"]
        print(f"→ {ticker} ({name}) …")
        try:
            accession, primary, filing_date = latest_10k(cik)
        except (urllib.error.URLError, RuntimeError, KeyError) as exc:
            print(f"  ! skip: {exc}")
            continue

        cik_int = str(int(cik))
        acc_nodash = accession.replace("-", "")
        url = SEC_ARCHIVES.format(
            cik_int=cik_int, acc_nodash=acc_nodash, primary=primary
        )
        dest = RAW_DIR / f"{ticker}_{filing_date}_{primary}"
        if dest.exists() and dest.stat().st_size > 0:
            print(f"  = already have {dest.name}")
        else:
            time.sleep(0.25)  # be polite to SEC
            try:
                blob = fetch_bytes(url)
            except urllib.error.URLError as exc:
                print(f"  ! download failed: {exc}")
                continue
            dest.write_bytes(blob)
            print(f"  ✓ saved {dest.name} ({len(blob):,} bytes)")

        manifest.append(
            {
                "ticker": ticker,
                "name": name,
                "cik": cik,
                "filing_date": filing_date,
                "accession": accession,
                "file": dest.name,
                "source_url": url,
            }
        )

    out = RAW_DIR / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest → {out}")
    print("Next: fill data/structured/fundamentals.csv from these filings.")


if __name__ == "__main__":
    main()
