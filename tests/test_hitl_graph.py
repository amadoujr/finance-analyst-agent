"""HITL graph interrupt + resume (mocked workers, no network)."""

from __future__ import annotations

from langgraph.types import Command

from finance_analyst.graph.build import build_graph


def test_hitl_interrupt_then_reject(monkeypatch) -> None:
    import finance_analyst.graph.build as build_mod

    def fake_rag(state):
        return {
            "rag_answer": "Draft about Apple risks.",
            "rag_grade": "ok",
            "citations": [{"chunk_id": "AAPL-C1", "ticker": "AAPL", "source": "x", "excerpt": "e"}],
        }

    monkeypatch.setattr(build_mod, "ask_rag", lambda q, ticker=None: {
        "answer": "Draft about Apple risks.",
        "grade": "ok",
        "citations": [{"chunk_id": "AAPL-C1", "ticker": "AAPL", "source": "x", "excerpt": "e"}],
        "question": q,
        "docs_count": 1,
    })
    # rag_node calls ask_rag — already patched via build_mod if imported there
    monkeypatch.setattr(
        "finance_analyst.graph.build.ask_rag",
        lambda q, ticker=None: {
            "answer": "Draft about Apple risks.",
            "grade": "ok",
            "citations": [
                {
                    "chunk_id": "AAPL-C1",
                    "ticker": "AAPL",
                    "source": "x",
                    "excerpt": "e",
                }
            ],
            "question": q,
            "docs_count": 1,
        },
    )

    app = build_graph()
    config = {"configurable": {"thread_id": "test-hitl-1"}}
    list(
        app.stream(
            {"question": "Should I buy AAPL stock?", "ticker": "AAPL"},
            config=config,
            stream_mode="updates",
        )
    )
    snap = app.get_state(config)
    assert snap.interrupts or (snap.next and "hitl" in snap.next)

    list(app.stream(Command(resume="reject"), config=config, stream_mode="updates"))
    final = app.get_state(config).values
    assert final.get("human_decision") == "reject"
    assert "Décision humaine" in final.get("answer", "") or "rejet" in final.get(
        "answer", ""
    ).lower() or "recommandation" in final.get("answer", "").lower()
