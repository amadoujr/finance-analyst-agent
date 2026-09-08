import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  askQuestion,
  fetchHealth,
  resumeHitl,
  type Citation,
  type InterruptPayload,
  type StepEvent,
} from "./api";
import "./App.css";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  route?: string;
  citations?: Citation[];
  humanDecision?: string;
};

type LiveStep = { id: number; node: string; label: string; detail: string };

const SUGGESTIONS = [
  { q: "What are Apple's main risk factors?", ticker: "AAPL" },
  { q: "What is Apple's ROE and net margin?", ticker: "AAPL" },
  { q: "ROE and risk factors for Microsoft", ticker: "MSFT" },
  { q: "Should I buy Apple stock?", ticker: "AAPL" },
];

export default function App() {
  const [input, setInput] = useState("");
  const [ticker, setTicker] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [running, setRunning] = useState(false);
  const [liveSteps, setLiveSteps] = useState<LiveStep[]>([]);
  const [phase, setPhase] = useState("");
  const [error, setError] = useState("");
  const [online, setOnline] = useState(true);
  const [disclaimer, setDisclaimer] = useState("");
  const [pendingHitl, setPendingHitl] = useState<{
    threadId: string;
    payload: InterruptPayload;
  } | null>(null);
  const [editText, setEditText] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const stepId = useRef(0);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setOnline(true);
        setDisclaimer(h.disclaimer || "");
      })
      .catch(() => setOnline(false));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, liveSteps, running, pendingHitl]);

  function stopAll() {
    abortRef.current?.abort();
    setRunning(false);
    setLiveSteps([]);
    setPhase("");
  }

  function handleStep(ev: StepEvent) {
    if (ev.type === "step" && ev.node) {
      setPhase(ev.label || ev.node);
      setLiveSteps((prev) => [
        ...prev,
        {
          id: ++stepId.current,
          node: ev.node!,
          label: ev.label || ev.node!,
          detail: String(ev.detail ?? ""),
        },
      ]);
    }
  }

  async function consumeStream(
    gen: AsyncGenerator<StepEvent>,
  ): Promise<{
    answer: string;
    route: string;
    citations: Citation[];
    humanDecision?: string;
    interrupt?: { threadId: string; payload: InterruptPayload };
  }> {
    let answer = "";
    let route = "";
    let citations: Citation[] = [];
    let humanDecision: string | undefined;
    let interrupt: { threadId: string; payload: InterruptPayload } | undefined;

    for await (const ev of gen) {
      handleStep(ev);
      if (ev.type === "error") {
        setError(ev.message || "Erreur");
      }
      if (ev.type === "interrupt" && ev.thread_id) {
        interrupt = {
          threadId: ev.thread_id,
          payload: ev.payload || {},
        };
      }
      if (ev.type === "final") {
        answer = ev.answer || "";
        route = ev.route || route;
        citations = ev.citations || citations;
        humanDecision = ev.human_decision;
      }
    }
    return { answer, route, citations, humanDecision, interrupt };
  }

  async function sendQuestion(raw: string, tickerHint?: string) {
    const q = raw.trim();
    if (!q || running || pendingHitl) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setRunning(true);
    setPhase("Traitement…");
    setError("");
    setLiveSteps([]);
    stepId.current = 0;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: q }]);

    try {
      const result = await consumeStream(
        askQuestion(q, {
          ticker: (tickerHint ?? ticker).trim() || undefined,
          signal: controller.signal,
        }),
      );
      if (controller.signal.aborted) return;

      if (result.interrupt) {
        setPendingHitl(result.interrupt);
        setEditText(result.interrupt.payload.draft || "");
        setPhase("Validation humaine requise");
        setRunning(false);
        setLiveSteps([]);
        return;
      }

      if (result.answer) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: result.answer,
            route: result.route,
            citations: result.citations,
            humanDecision: result.humanDecision,
          },
        ]);
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setError((err as Error).message || "Erreur");
      }
    } finally {
      setRunning(false);
      setLiveSteps([]);
      setPhase((p) => (p === "Validation humaine requise" ? p : ""));
    }
  }

  async function onHitl(action: "approve" | "edit" | "reject") {
    if (!pendingHitl || running) return;
    const { threadId } = pendingHitl;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setRunning(true);
    setPhase(`HITL · ${action}`);
    setError("");
    setLiveSteps([]);

    try {
      const result = await consumeStream(
        resumeHitl(threadId, action, {
          edit: action === "edit" ? editText : "",
          ticker: ticker.trim() || undefined,
          signal: controller.signal,
        }),
      );
      if (controller.signal.aborted) return;
      setPendingHitl(null);
      setEditText("");
      if (result.answer) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: result.answer,
            route: result.route || "hitl",
            citations: result.citations,
            humanDecision: result.humanDecision || action,
          },
        ]);
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setError((err as Error).message || "Erreur resume");
      }
    } finally {
      setRunning(false);
      setLiveSteps([]);
      setPhase("");
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void sendQuestion(input);
  }

  function onClear() {
    stopAll();
    setMessages([]);
    setPendingHitl(null);
    setEditText("");
    setError("");
    setInput("");
  }

  const busy = running;

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <p className="brand">Finance Analyst</p>
          <p className="lede">
            <span className={`dot${online ? "" : " off"}`} />
            Multi-agents · RAG + Calcul + HITL
            {!online && " · API hors ligne"}
          </p>
        </div>
        <button type="button" className="ghost" onClick={onClear}>
          Nouvelle session
        </button>
      </header>

      <p className="disclaimer">
        {disclaimer ||
          "Ceci n’est pas un conseil d’investissement. Corpus 10-K + ratios seedés."}
      </p>

      <section className="layout">
        <div className="shell">
          <div className="messages">
            {messages.length === 0 && !pendingHitl && (
              <>
                <p className="empty">
                  Pose une question sur AAPL / MSFT / GOOGL. Le supervisor route
                  vers le RAG, le calcul de ratios, ou les deux. Les questions
                  d’achat/vente passent par une validation humaine.
                </p>
                <div className="suggestions">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s.q}
                      type="button"
                      disabled={busy || !online}
                      onClick={() => {
                        setTicker(s.ticker);
                        void sendQuestion(s.q, s.ticker);
                      }}
                    >
                      {s.q}
                    </button>
                  ))}
                </div>
              </>
            )}

            {messages.map((msg, i) => (
              <article key={i} className={`bubble bubble-${msg.role}`}>
                <p className="bubble-role">
                  {msg.role === "user" ? "Toi" : "Analyst"}
                  {msg.route && (
                    <span className={`pill pill-${msg.route}`}>{msg.route}</span>
                  )}
                  {msg.humanDecision && (
                    <span className="pill pill-hitl">{msg.humanDecision}</span>
                  )}
                </p>
                <div className="bubble-body">{msg.content}</div>
                {msg.citations && msg.citations.length > 0 && (
                  <ul className="citations">
                    {msg.citations.map((c, j) => (
                      <li key={`${c.chunk_id || c.doc_id}-${j}`}>
                        <code>[{c.chunk_id || c.doc_id}]</code>{" "}
                        {c.ticker && <span>{c.ticker} · </span>}
                        {c.source}
                        {c.excerpt && (
                          <span className="excerpt"> — {c.excerpt}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </article>
            ))}

            {pendingHitl && (
              <div className="hitl-panel">
                <h2>Validation humaine requise</h2>
                <p className="hitl-reason">
                  {pendingHitl.payload.reason || "sensitive_investment_question"}
                </p>
                <pre className="hitl-draft">
                  {(pendingHitl.payload.draft || "").slice(0, 1200)}
                  {(pendingHitl.payload.draft || "").length > 1200 ? "…" : ""}
                </pre>
                <label className="hitl-edit-label">
                  Édition (si tu choisis Edit)
                  <textarea
                    rows={4}
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    disabled={busy}
                  />
                </label>
                <div className="hitl-actions">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void onHitl("approve")}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    disabled={busy || editText.trim().length < 3}
                    onClick={() => void onHitl("edit")}
                  >
                    Edit & publish
                  </button>
                  <button
                    type="button"
                    className="ghost danger"
                    disabled={busy}
                    onClick={() => void onHitl("reject")}
                  >
                    Reject
                  </button>
                </div>
              </div>
            )}

            {busy && (
              <div className="status-card">
                <p className="status-title">{phase || "En cours…"}</p>
                <ol className="steps">
                  {liveSteps.map((s) => (
                    <li key={s.id}>
                      <span className="badge">{s.label}</span>
                      <span className="detail">{s.detail}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {error && <p className="error">{error}</p>}

          <form className="composer" onSubmit={onSubmit}>
            <div className="ticker-row">
              <label>
                Ticker
                <select
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  disabled={busy || !!pendingHitl}
                >
                  <option value="">Auto</option>
                  <option value="AAPL">AAPL</option>
                  <option value="MSFT">MSFT</option>
                  <option value="GOOGL">GOOGL</option>
                </select>
              </label>
            </div>
            <textarea
              rows={2}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={busy || !!pendingHitl}
              placeholder={
                pendingHitl
                  ? "Valide d’abord le brouillon HITL…"
                  : "Question d’analyse (10-K, ratios, ou reco)…"
              }
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSubmit(e as unknown as FormEvent);
                }
              }}
            />
            <div className="actions">
              <button
                type="submit"
                disabled={busy || !!pendingHitl || input.trim().length < 3}
              >
                {running ? "…" : "Analyser"}
              </button>
              {busy && (
                <button type="button" className="ghost danger" onClick={stopAll}>
                  Stop
                </button>
              )}
            </div>
          </form>
        </div>

        <aside className="sidebar">
          <div className="side-card">
            <h2>Comment ça marche</h2>
            <ol className="howto">
              <li>
                <strong>Supervisor</strong> route rag / calc / both
              </li>
              <li>
                <strong>RAG</strong> lit les 10-K (citations)
              </li>
              <li>
                <strong>Calcul</strong> ratios Python sur CSV seedé
              </li>
              <li>
                <strong>HITL</strong> pause si question d’achat/vente
              </li>
            </ol>
          </div>
          <div className="side-card">
            <h2>Corpus</h2>
            <p className="side-lede">AAPL · MSFT · GOOGL (SEC EDGAR)</p>
            <p className="side-lede">
              Les montants de ratios viennent de{" "}
              <code>fundamentals.csv</code>, pas du LLM.
            </p>
          </div>
        </aside>
      </section>
    </div>
  );
}
