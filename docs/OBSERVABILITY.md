# Observabilité — Langfuse

## Pourquoi Langfuse (et pas seulement des logs) ?

En multi-agents, une question peut traverser **classify → RAG → calc → synthesize**, avec plusieurs appels Gemini. Les `print()` ne suffisent pas pour :

- voir la **latence** par nœud
- compter les **tokens** / coûts
- déboguer une régression après un changement de prompt

**Langfuse** enregistre des **traces** (runs LangChain/LangGraph) dans un dashboard web — utile en entretien (« voici comment je observe une app agents en prod »).

## Langfuse vs LangSmith

| | Langfuse | LangSmith |
|---|---|---|
| Vendor | OSS + cloud free tier | LangChain |
| Setup | `LANGFUSE_*` + `CallbackHandler` | `LANGCHAIN_TRACING_V2=true` |
| Dashboard | cloud.langfuse.com | smith.langchain.com |
| Ce repo | **branché** | documenté seulement |

LangSmith serait 2 variables d’env — on a choisi Langfuse pour l’indépendance et le free tier clair.

## Activer (cloud free)

1. Compte sur [https://cloud.langfuse.com](https://cloud.langfuse.com)
2. Créer un projet → récupérer **Public** + **Secret** key
3. Dans `.env` :

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com   # EU ; US: https://us.cloud.langfuse.com
```

4. Relancer une analyse :

```bash
uv run python -m finance_analyst --ticker AAPL "ROE and risk factors?"
```

5. Ouvrir Langfuse → **Traces** : tu dois voir un run `finance-analyze` avec spans LLM (grade, generate) imbriqués.

Sans clés : **aucun effet** — l’app tourne normalement (`langfuse: false` dans `/health`).

## Comment c’est branché

| Fichier | Rôle |
|---|---|
| `observability/langfuse.py` | Init client + `CallbackHandler` + `run_config()` |
| `graph/runner.py` | Passe `config={"callbacks": [...]}` à `app.stream()` + `flush()` en fin |

Les appels `get_llm().invoke()` dans les workers RAG héritent du callback LangGraph parent.

## Tags / metadata

Chaque run porte le tag `finance-analyst`. Optionnel : `ticker` dans metadata si `--ticker` est fourni.

## Limites V1

- Pas encore de score Ragas envoyé à Langfuse
- Pas de trace séparée par utilisateur (auth) — session_id à ajouter avec l’UI
