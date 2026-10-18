#!/usr/bin/env python3
"""Run eval cases (smoke by default; --live for Gemini/RAG).

  uv run python scripts/run_evals.py
  uv run python scripts/run_evals.py --live
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from langgraph.types import Command

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finance_analyst.calc.worker import compute_ratios  # noqa: E402
from finance_analyst.graph.build import build_graph  # noqa: E402
from finance_analyst.graph.routing import classify_route_heuristic  # noqa: E402
from finance_analyst.graph.sensitivity import is_sensitive_question  # noqa: E402
from finance_analyst.rag.index import index_exists  # noqa: E402


def load_cases() -> list[dict[str, Any]]:
    path = ROOT / "evals" / "cases.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return list(data.get("cases") or [])


def check_route(case: dict[str, Any]) -> tuple[bool, str]:
    got = classify_route_heuristic(case["question"])
    exp = case["expect_route"]
    ok = got == exp
    return ok, f"route={got} expected={exp}"


def check_sensitive(case: dict[str, Any]) -> tuple[bool, str]:
    got = is_sensitive_question(case["question"])
    exp = bool(case["expect_sensitive"])
    return got == exp, f"sensitive={got} expected={exp}"


def check_calc(case: dict[str, Any]) -> tuple[bool, str]:
    data = compute_ratios(case["ticker"])
    ratios = data["ratios"]
    tol = float(case.get("tolerance", 0.001))
    msgs: list[str] = []
    ok = True
    if "expect_roe_approx" in case:
        got = ratios["return_on_equity"]
        exp = float(case["expect_roe_approx"])
        match = got is not None and abs(got - exp) <= tol
        ok = ok and match
        msgs.append(f"roe={got} expected≈{exp}")
    if "expect_net_margin_approx" in case:
        got = ratios["net_margin"]
        exp = float(case["expect_net_margin_approx"])
        match = got is not None and abs(got - exp) <= tol
        ok = ok and match
        msgs.append(f"margin={got} expected≈{exp}")
    return ok, "; ".join(msgs)


def check_hitl_graph(case: dict[str, Any]) -> tuple[bool, str]:
    import finance_analyst.graph.build as build_mod

    def fake_ask_rag(q: str, ticker: str | None = None) -> dict[str, Any]:
        return {
            "answer": "Mock draft from 10-K.",
            "grade": "ok",
            "citations": [
                {
                    "chunk_id": "MOCK-C1",
                    "ticker": ticker or "AAPL",
                    "source": "mock.htm",
                    "excerpt": "risk",
                }
            ],
            "question": q,
            "docs_count": 1,
        }

    build_mod.ask_rag = fake_ask_rag  # type: ignore[assignment]
    app = build_graph()
    config = {"configurable": {"thread_id": f"eval-{case['id']}"}}
    list(
        app.stream(
            {
                "question": case["question"],
                "ticker": case.get("ticker"),
            },
            config=config,
            stream_mode="updates",
        )
    )
    snap = app.get_state(config)
    if not (snap.interrupts or (snap.next and "hitl" in (snap.next or ()))):
        return False, "expected interrupt before HITL"
    action = case.get("auto_resume", "reject")
    list(app.stream(Command(resume=action), config=config, stream_mode="updates"))
    final = app.get_state(config).values
    decision = final.get("human_decision")
    ok = decision == action
    return ok, f"human_decision={decision}"


def check_live_rag(case: dict[str, Any]) -> tuple[bool, str]:
    from finance_analyst.rag.worker import ask_rag

    result = ask_rag(case["question"], ticker=case.get("ticker"))
    grade = result["grade"]
    require = case.get("require_grade", "ok")
    ok = grade == require and bool(result.get("answer"))
    return ok, f"grade={grade} citations={len(result.get('citations') or [])}"


def check_live_hitl(case: dict[str, Any]) -> tuple[bool, str]:
    from finance_analyst.graph.runner import analyze

    result = analyze(
        case["question"],
        ticker=case.get("ticker"),
        auto_resume=case.get("auto_resume", "reject"),
    )
    ok = (
        not result.get("interrupted")
        and result.get("human_decision") == case.get("auto_resume", "reject")
        and bool(result.get("answer"))
    )
    return ok, f"decision={result.get('human_decision')} route={result.get('route')}"


def run_case(case: dict[str, Any], *, live: bool) -> dict[str, Any]:
    kind = case["kind"]
    if kind in ("live_rag", "live_hitl") and not live:
        return {
            "id": case["id"],
            "kind": kind,
            "status": "skip",
            "detail": "pass --live to run",
        }
    if kind in ("live_rag", "live_hitl"):
        if not os.getenv("GOOGLE_API_KEY"):
            return {
                "id": case["id"],
                "kind": kind,
                "status": "skip",
                "detail": "GOOGLE_API_KEY missing",
            }
        if not index_exists():
            return {
                "id": case["id"],
                "kind": kind,
                "status": "skip",
                "detail": "FAISS index missing (scripts/build_index.py)",
            }

    try:
        if kind == "route":
            ok, detail = check_route(case)
        elif kind == "sensitive":
            ok, detail = check_sensitive(case)
        elif kind == "calc":
            ok, detail = check_calc(case)
        elif kind == "hitl_graph":
            ok, detail = check_hitl_graph(case)
        elif kind == "live_rag":
            ok, detail = check_live_rag(case)
        elif kind == "live_hitl":
            ok, detail = check_live_hitl(case)
        else:
            return {
                "id": case["id"],
                "kind": kind,
                "status": "fail",
                "detail": f"unknown kind {kind}",
            }
        return {
            "id": case["id"],
            "kind": kind,
            "status": "pass" if ok else "fail",
            "detail": detail,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "id": case["id"],
            "kind": kind,
            "status": "fail",
            "detail": str(exc),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run live RAG/HITL cases (needs Gemini + FAISS index)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON summary",
    )
    args = parser.parse_args()

    results = [run_case(c, live=args.live) for c in load_cases()]
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skip")

    if args.json:
        print(json.dumps({"passed": passed, "failed": failed, "skipped": skipped, "results": results}, indent=2))
    else:
        for r in results:
            mark = {"pass": "✓", "fail": "✗", "skip": "·"}[r["status"]]
            print(f"  {mark} [{r['status']}] {r['id']} ({r['kind']}) — {r['detail']}")
        print(f"\nSummary: {passed} passed, {failed} failed, {skipped} skipped")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
