export type Citation = {
  chunk_id?: string;
  ticker?: string;
  source?: string;
  excerpt?: string;
  doc_id?: string;
};

export type InterruptPayload = {
  reason?: string;
  question?: string;
  draft?: string;
  disclaimer?: string;
  actions?: string[];
};

export type StepEvent = {
  type: "start" | "step" | "final" | "error" | "interrupt";
  question?: string;
  thread_id?: string;
  provider?: string;
  model?: string;
  node?: string;
  label?: string;
  detail?: string;
  route?: string;
  answer?: string;
  citations?: Citation[];
  message?: string;
  payload?: InterruptPayload;
  human_decision?: string;
  langsmith?: boolean;
  disclaimer?: string;
};

const API_BASE = (
  import.meta.env.VITE_API_BASE !== undefined
    ? import.meta.env.VITE_API_BASE
    : ""
).replace(/\/$/, "");

async function* readSse(
  response: Response,
  signal?: AbortSignal,
): AsyncGenerator<StepEvent> {
  if (!response.body) throw new Error("No response body");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const onAbort = () => {
    void reader.cancel();
  };
  signal?.addEventListener("abort", onAbort);

  try {
    while (true) {
      if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() ?? "";
      for (const chunk of chunks) {
        const dataLine = chunk.split("\n").find((l) => l.startsWith("data:"));
        if (!dataLine) continue;
        try {
          yield JSON.parse(dataLine.replace(/^data:\s?/, "")) as StepEvent;
        } catch {
          /* ignore */
        }
      }
    }
  } finally {
    signal?.removeEventListener("abort", onAbort);
  }
}

export async function fetchHealth(): Promise<{
  ok: boolean;
  model?: string;
  disclaimer?: string;
  langsmith?: boolean;
}> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("API offline");
  return res.json();
}

export async function* askQuestion(
  question: string,
  options?: { ticker?: string; threadId?: string; signal?: AbortSignal },
): AsyncGenerator<StepEvent> {
  const response = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      question,
      ticker: options?.ticker || null,
      thread_id: options?.threadId || null,
    }),
    signal: options?.signal,
  });
  if (!response.ok) throw new Error(`API error ${response.status}`);
  yield* readSse(response, options?.signal);
}

export async function* resumeHitl(
  threadId: string,
  action: "approve" | "edit" | "reject",
  options?: { edit?: string; ticker?: string; signal?: AbortSignal },
): AsyncGenerator<StepEvent> {
  const response = await fetch(`${API_BASE}/resume`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      thread_id: threadId,
      action,
      edit: options?.edit || "",
      ticker: options?.ticker || null,
    }),
    signal: options?.signal,
  });
  if (!response.ok) throw new Error(`Resume error ${response.status}`);
  yield* readSse(response, options?.signal);
}
