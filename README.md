# Finance Analyst Agent

Assistant IA d’**analyse financière multi-agents** : lire des rapports (10-K), croiser des faits chiffrés, calculer des ratios, et produire une synthèse — avec **validation humaine** avant toute conclusion sensible.

> **Disclaimer.** Outil pédagogique / portfolio. Ce n’est **pas** un conseil d’investissement. Les réponses s’appuient sur un corpus documentaire contrôlé et des faits structurés seedés.

## Contexte

En due diligence ou veille marché, un analyste passe beaucoup de temps à :

- lire des 10-K / rapports annuels (dizaines voire centaines de pages)
- retrouver un chiffre ou une formulation précise
- calculer des ratios (marge, ROE, levier…)
- rédiger une synthèse — parfois avec une **recommandation**

Les LLM « chat seuls » hallucinent facilement sur les montants et mélangent les exercices. Les offres **AI Engineer 2026** demandent justement : intégration LLM, pipelines RAG, agents en prod, évaluation, gouvernance.

## Problème

Un seul prompt fourre-tout ne suffit pas :

1. **Docs qualitatifs** (texte PDF) ≠ **faits quantitatifs** (états financiers tabulés)
2. Une **recommandation d’investissement** ne doit pas partir sans regard humain (risque + conformité)
3. Sans **traces** ni **éval**, on ne sait pas si le système se dégrade

## Solution (V1)

Un graphe **LangGraph** avec un **supervisor** qui route vers :

| Worker | Rôle |
|---|---|
| **RAG** | Retrieval sur 10-K (embeddings MiniLM + secours lexical) + citations |
| **Calcul** | Outils Python (ratios) sur un CSV de fondamentaux seedés |
| **HITL** | `interrupt()` avant d’afficher une conclusion sensible |
| **LangSmith** | Traces des runs (observabilité native LangChain) |

Déploiement cible : **Docker → GCP Cloud Run** (≥ 1 Gi RAM). LLM : **Gemini** (HF en fallback). Pas Claude.

```
Utilisateur → Supervisor
                 ├─→ Worker RAG
                 ├─→ Worker Calcul
                 └─→ HITL si conclusion sensible
              ← Synthèse + citations
```

## Ce que ça démontre

- Multi-agents LangGraph (conditional edges), pas un seul retrieve→generate
- RAG finance avec citations + refus hors corpus
- Calcul déterministe (tools) pour les ratios — pas « inventer » un ROE
- Human-in-the-loop (gouvernance)
- Observabilité LangSmith
- Déploiement cloud GCP (apprentissage guidé dans `docs/`)

## Stack

| Brique | Choix V1 |
|---|---|
| Orchestration | LangGraph |
| LLM | Gemini (`GEMINI_MODEL`) |
| Embeddings | `all-MiniLM-L6-v2` (LangChain HuggingFaceEmbeddings) |
| Vector store | FAISS (fichier) |
| Quanti | `data/structured/fundamentals.csv` |
| API | FastAPI SSE (`/ask`, `/resume`) |
| UI | React + Vite (à venir) |
| Observabilité | LangSmith (`LANGCHAIN_TRACING_V2`) |
| Deploy | Cloud Run (GCP) |
| CI | GitHub Actions + éval smoke |

## État du repo (progression)

| Phase | Statut |
|---|---|
| Scaffold + docs | fait |
| Corpus EDGAR + fondamentaux | fait (filings locaux + CSV seed) |
| Worker RAG | fait (FAISS + MiniLM + CLI ask) |
| Worker Calcul | fait (ratios CSV + tests + CLI --calc) |
| Supervisor + SSE | fait (LangGraph route rag/calc/both) |
| LangSmith | fait (tracing natif LangChain) |
| HITL + API resume | fait (`interrupt` + `/resume`) |
| UI React | à faire |
| Éval + CI | à faire |
| Cloud Run | à faire |

## Lancer (local)

Prérequis : Python ≥ 3.11, [`uv`](https://github.com/astral-sh/uv), clé Gemini.

```bash
cd finance-analyst-agent
cp .env.example .env   # GOOGLE_API_KEY + optionnel LANGCHAIN_* (voir docs/OBSERVABILITY.md)
uv sync

# Télécharger les 10-K (une fois) → data/raw/
uv run python scripts/fetch_edgar.py

# Construire l’index FAISS (une fois, ou après nouveau corpus)
uv run python scripts/build_index.py

# Supervisor (défaut) — route automatique
uv run python -m finance_analyst --ticker AAPL "ROE and main risk factors?"

# Workers seuls
uv run python -m finance_analyst --rag --ticker AAPL "risk factors?"
uv run python -m finance_analyst --calc --ticker AAPL "What is the ROE?"

uv run uvicorn finance_analyst.api:app --reload --port 8080
# POST /ask  (SSE) — peut renvoyer type=interrupt
# POST /resume { thread_id, action: approve|edit|reject }
```

Question sensible (HITL) :

```bash
uv run python -m finance_analyst --ticker AAPL "Should I buy Apple stock?" --auto-resume reject
```

## Documentation pédagogique

Le README = vue **produit / recruteur**. Les détails « pourquoi c’est compliqué » sont dans `docs/` :

| Doc | Contenu |
|---|---|
| [`docs/LEARNING.md`](docs/LEARNING.md) | Fil conducteur phase par phase |
| `docs/RAG_FINANCE.md` | PDF, chunking, hallucinations chiffres |
| `docs/LANGGRAPH_GRAPH.md` | State, nodes, edges, SSE |
| `docs/HITL_GOVERNANCE.md` | Pourquoi bloquer les reco + interrupt/resume |
| `docs/OBSERVABILITY.md` | LangSmith — activer les traces |
| `docs/GCP_CLOUDRUN.md` | Pas-à-pas GCP pour débutants |

## Roadmap (hors V1)

- Worker SQL (text-to-SQL + Postgres)
- Qdrant managé
- Gate CI Ragas qui bloque le deploy
- Auth multi-tenant

## Licence / données

Filings SEC publics (EDGAR). Respecter les conditions d’usage SEC. Ne pas redistribuer de données non publiques.
