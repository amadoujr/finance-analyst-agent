# Learning journal — Finance Analyst Agent

Ce fichier se remplit **au fur et à mesure**. Objectif : expliquer les choix et les pièges, en complément du README.

## Phase 0 — Scaffold (fait)

### Pourquoi un repo séparé de `langchain-lab` ?

Les labs 01–05 sont une **progression d’apprentissage**. Ce projet est un **produit portfolio cloud** (GCP, multi-agents, HITL, Langfuse). Un repo dédié clarifie le message recruteur : « voici une app déployable », pas « encore une étape du tuto ».

### Pourquoi `uv` + package `src/` ?

- `uv` : install rapide, lockfile reproductible (utile CI + Cloud Run)
- layout `src/finance_analyst` : imports clairs (`finance_analyst.api`), moins de collisions avec un dossier `scripts/`

### Disclaimer dès le jour 1

En finance, le risque n’est pas seulement technique : une phrase du type « achetez cette action » peut être prise pour un conseil. On affiche le disclaimer dans le README, l’API `/health`, et plus tard l’UI.

### Prochaine phase

Récupérer 2–3 **10-K** SEC (EDGAR) + un CSV de fondamentaux **seedés** pour le worker Calcul. Pourquoi seedé ? Pour que les ratios soient **vérifiables** et que le LLM ne « invente » pas le chiffre source.

---

## Phase 2 — Worker RAG (fait)

### HTML iXBRL, pas PDF

Les 10-K EDGAR récents sont souvent du **XHTML inline XBRL** (une seule ligne géante). On parse avec BeautifulSoup/`lxml`, on enlève `script` / `ix:header`, puis `get_text`.

### MiniLM + FAISS

Embeddings : `sentence-transformers/all-MiniLM-L6-v2` via LangChain `HuggingFaceEmbeddings`.  
Index : **FAISS** persisté dans `data/index/` (gitignore). Rebuild : `uv run python scripts/build_index.py`.

### Retrieve hybride

Comme DocuSafe : similarité vectorielle **+** overlap lexical de tokens, puis fusion dédupliquée. Le lexical sauve les mots-clés exacts (ticker, « Item 1A », etc.).

### Grade → generate | refuse

Si les chunks ne portent pas sur la question → **refuse** (pas d’invention).  
Generate : citations `[AAPL-C0012]`, interdiction d’inventer des chiffres, pas de reco d’achat/vente.

### Truncation

On coupe chaque filing à ~180k caractères pour garder l’index raisonnable sur un laptop. Suffisant pour une démo ; en prod on indexerait par section Item.

---

## Phase 3 — Worker Calcul (fait)

### Pourquoi un CSV seedé ?

Les montants dans un 10-K HTML sont difficiles à extraire sans pipeline XBRL complet. Pour V1, on met les **inputs** dans `fundamentals.csv` (vérifiables) et on laisse le **code** calculer les ratios. Le LLM ne fait pas l’arithmétique — il peut seulement *expliquer* (`--calc-llm`).

### Ratios V1

- Marge nette = `net_income / revenue`
- ROE = `net_income / total_equity`
- Dette / capitaux propres = `total_debt / total_equity`

### CLI

```bash
uv run python -m finance_analyst --calc --ticker AAPL "What is the ROE?"
uv run uv sync --extra dev && uv run pytest
```

Prochaine étape : **supervisor LangGraph** qui route RAG vs Calcul selon la question.

---

## Phase 4 — Supervisor LangGraph (fait)

### Un graphe, pas trois CLIs

Le supervisor **classifie** la question (`rag` / `calc` / `both`) puis exécute les workers existants. Les workers ne sont pas réécrits — le graphe les **orchestre**.

### Heuristique avant LLM

Le routing V1 est **testable** (mots-clés ROE, risk, margin…). Pas besoin d’appeler Gemini pour savoir si la question est quantitative.

### SSE

`POST /ask` sur FastAPI = même pattern que les labs `langchain-lab` (events `step` + `final`). Prêt pour une UI React.

Prochaine étape : **Langfuse** (traces par nœud) puis **HITL**.
