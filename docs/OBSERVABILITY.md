# Observabilité — LangSmith

## Pourquoi LangSmith ici ?

Ce projet est construit avec **LangChain** et **LangGraph**. LangSmith est l’outil de tracing **natif** de cet écosystème : peu de code, traces automatiques des runs LLM et des nœuds du graphe.

## Activer

1. Compte sur [https://smith.langchain.com](https://smith.langchain.com)
2. Créer une clé API (Settings → API Keys)
3. Dans `.env` :

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_PROJECT=finance-analyst-agent
```

4. Lancer une analyse :

```bash
uv run python -m finance_analyst --ticker AAPL "ROE and risk factors?"
```

5. Ouvrir LangSmith → projet `finance-analyst-agent` → tu vois le run `finance-analyze` avec les spans (grade, generate, etc.).

Sans clé ou avec `LANGCHAIN_TRACING_V2=false` : **aucun tracing** (`langsmith: false` dans `/health`).

## Comment c’est branché

| Fichier | Rôle |
|---|---|
| `observability/langsmith.py` | Détecte si tracing actif + `run_config()` (run_name, tags, metadata) |
| `graph/runner.py` | Passe `config` à `app.stream()` ; `wait_for_all_tracers()` en fin de run CLI |

Pas de `CallbackHandler` manuel : avec `LANGCHAIN_TRACING_V2=true`, LangChain **instrumente** automatiquement les appels `invoke()` dans les workers RAG.

## Metadata

- `run_name`: `finance-analyze`
- `tags`: `finance-analyst`
- `metadata.ticker` si `--ticker` est fourni

## Langfuse ?

Retiré de ce repo (V1 utilisait Langfuse pour montrer une alternative OSS). Pour un projet 100 % LangChain/LangGraph, **LangSmith est le choix cohérent**.

## Limites V1

- Pas encore de scores Ragas exportés vers LangSmith
- Pas de `session_id` côté UI (à ajouter avec le front React)
