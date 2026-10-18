# Learning journal — Finance Analyst Agent

Ce fichier se remplit **au fur et à mesure**. Objectif : expliquer les choix et les pièges, en complément du README.

## Phase 0 — Scaffold (fait)

### Pourquoi un repo séparé de `langchain-lab` ?

Les labs 01–05 sont une **progression d’apprentissage**. Ce projet est un **produit portfolio cloud** (GCP, multi-agents, HITL, LangSmith). Un repo dédié clarifie le message recruteur : « voici une app déployable », pas « encore une étape du tuto ».

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

Prochaine étape : **HITL** (`interrupt` avant conclusion d’investissement).

---

## Phase 5 — LangSmith (fait)

### Tracing natif LangChain

Avec `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY`, les `invoke()` Gemini dans les workers sont tracés **automatiquement** — pas de `CallbackHandler` Langfuse à maintenir.

### run_config()

On passe quand même `run_name`, `tags` et `metadata` (ticker) à `app.stream()` pour retrouver les runs dans le bon projet LangSmith.

### flush

`wait_for_all_tracers()` en fin de run CLI pour ne pas perdre les traces sur un process court.

Prochaine étape : **HITL** (`interrupt` avant conclusion d’investissement).

---

## Phase 6 — HITL (fait)

### interrupt() ≠ disclaimer

Un disclaimer en bas de réponse ne suffit pas. On **pause** le graphe (`interrupt`) avant de publier une reco d’achat/vente.

### MemorySaver + thread_id

Sans checkpointer, impossible de reprendre. V1 = mémoire process ; Cloud Run multi-instances demandera un store partagé plus tard.

### API /resume

Le front (prochaine phase) affichera Approve / Edit / Reject et rappellera `POST /resume` avec le `thread_id`.

Prochaine étape : **UI React** (steps SSE + panneau HITL).

---

## Phase 7 — UI React (fait)

### Même pattern que la hotline

Chat + events SSE (`step` / `final` / `interrupt`). Le panneau HITL apparaît quand l’API envoie `type: interrupt` ; Approve / Edit / Reject appelle `POST /resume`.

### Dev local

API `:8080`, Vite `:5176` avec proxy. En prod (Cloud Run), on servira `web/dist` depuis FastAPI.

Prochaine étape : **éval + CI**, puis **GCP Cloud Run**.

---

## Phase 8 — Éval + CI (fait)

### Smoke sans LLM

`evals/cases.yaml` + `scripts/run_evals.py` : routing, sensibilité HITL, ratios CSV, graphe HITL mocké. Les cas `live_*` sont skippés sans `--live`.

### GitHub Actions

Chaque push/PR : `uv sync` → `pytest` → `run_evals.py`. Pas de gate Ragas bloquant (roadmap).

---

## Phase 9 — Docker / Cloud Run (doc + image)

### Pourquoi 1 Gi

MiniLM + torch dans le même container que l’API. À 512 Mo → OOM (déjà vu sur la hotline).

### Secret Manager

La clé Gemini n’est **pas** dans l’image. Cloud Run la monte via `--set-secrets`.

### Guide

Suivre [`docs/GCP_CLOUDRUN.md`](GCP_CLOUDRUN.md) de zéro : projet → Artifact Registry → secrets → build → deploy.

### 18 octobre 2026 — première image publiée, puis optimisation CPU

Projet GCP : `finance-analyst-agent-511018`, dépôt Artifact Registry `finance-analyst` en `europe-west1`.

Le premier build abouti (`api:v1`) durait environ 10 min 25 s et stockait 3 171 553 767 octets d'image dans Artifact Registry. PyTorch depuis PyPI sur Linux installait des dépendances NVIDIA/CUDA inutiles pour notre cible CPU.

La version `api:v2-cpu` sélectionne l'index CPU officiel PyTorch sur Linux et ne conserve pas le cache d'archives uv dans l'image. Build `487259d6-6061-4837-aaf4-d3af8afccd54` réussi en environ 5 min 28 s (construction 3 min 37 s, publication 1 min 45 s). Taille enregistrée : 631 703 238 octets, soit environ 80 % de moins. Cette mesure concerne la taille rapportée par Artifact Registry, pas la RAM à allouer au service.

Le build vérifie `torch.version.cuda is None` et génère les 784 vecteurs/chunks FAISS avec PyTorch `2.14.1+cpu`. Vérifications locales : 19 tests et 8 évaluations smoke réussis, 2 cas live ignorés. L'image macOS conserve sa distribution PyTorch native ; le verrouillage sélectionne la distribution CPU sur Linux.

Image publiée : `europe-west1-docker.pkg.dev/finance-analyst-agent-511018/finance-analyst/api:v2-cpu`.
Digest : `sha256:4d50dafc5017d680f48c21f0502a75997be706bd859b2acfd86ecda9c8f3320c`.

À ce stade, aucune application Cloud Run n'a été déployée par ce travail. Prochaine étape : configurer le secret Gemini et l'identité du service, puis déployer et tester.

### 18 octobre 2026 — premier déploiement Cloud Run vérifié

Service `finance-analyst` en `europe-west1`, révision `finance-analyst-00001-t5p`. Image CPU sélectionnée par digest (voir ci-dessus), modèle `gemini-3.1-flash-lite` identique au test local.

- Compte de service dédié : `finance-analyst-runtime@finance-analyst-agent-511018.iam.gserviceaccount.com`.
- Rôle `roles/secretmanager.secretAccessor` accordé sur le seul secret `google-api-key` ; version 1 injectée dans `GOOGLE_API_KEY`.
- CPU 1, mémoire 1 Gi, minimum 0 instance, maximum 1, concurrence 1 et timeout 300 s. Ces limites ne garantissent ni un plafond financier ni la conservation du state HITL.
- Service privé : accès non authentifié refusé (HTTP 403). LangSmith non activé pour ce déploiement.
- Tests distants authentifiés : `/health` et `/` HTTP 200, calcul AAPL final avec une citation, RAG Gemini final avec quatre citations, interruption HITL puis reprise avec rejet confirmées.

URL privée : https://finance-analyst-377978973867.europe-west1.run.app

Pour ouvrir l'interface depuis son Mac avec ses identifiants gcloud :

```bash
gcloud run services proxy finance-analyst \
  --project=finance-analyst-agent-511018 \
  --region=europe-west1 --port=8080
```

Puis ouvrir http://localhost:8080 et laisser le terminal actif. Le proxy est local, mais l'application s'exécute chez Google. Arrêter une éventuelle API locale utilisant déjà ce port, ou choisir un autre port.

La publication sans authentification est une décision distincte. La validation ci-dessus porte sur une démo fonctionnelle ; les données seedées, les heuristiques HITL et le checkpointer en RAM restent les limites connues.
