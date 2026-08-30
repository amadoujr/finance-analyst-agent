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

Récupérer 2–3 **10-K** SEC (EDGAR) + un CSV de fondamentaux **seedés à la main** pour le worker Calcul. Pourquoi seedé ? Pour que les ratios soient **vérifiables** et que le LLM ne « invente » pas le chiffre source.
