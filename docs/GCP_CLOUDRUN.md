# Déployer sur GCP Cloud Run (débutant)

Ce guide suppose que tu n’as **jamais** utilisé GCP. On va pas à pas jusqu’à une URL publique.

## Configuration réellement utilisée — 18 octobre 2026

Le premier déploiement est **privé**, dans `finance-analyst-agent-511018`, région `europe-west1`. Les commandes ci-dessous documentent les opérations déjà réalisées : ne pas recréer les ressources pour simplement les consulter. Les sections génériques plus bas proposent aussi une variante publique ; ce n'est pas la configuration actuellement déployée.

### Identité → permission → application

Ton utilisateur Google déploie. Un compte de service représente l'application pendant son exécution. IAM associe une identité, un rôle et une ressource ; ce n'est pas un « profil » à connecter dans le code.

Création de l'identité :

```bash
gcloud iam service-accounts create finance-analyst-runtime \
  --display-name="Finance Analyst Cloud Run runtime" \
  --project=finance-analyst-agent-511018
```

Console : **IAM et administration → Comptes de service → Créer un compte de service**. Les rôles généraux sur le projet et les accès facultatifs sont laissés vides pour cette configuration. Aucune clé JSON n'a été créée.

Permission sur le seul secret Gemini :

```bash
gcloud secrets add-iam-policy-binding google-api-key \
  --member=serviceAccount:finance-analyst-runtime@finance-analyst-agent-511018.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor \
  --project=finance-analyst-agent-511018
```

Console : **Secret Manager → google-api-key → Autorisations → Accorder l'accès**. Ajouter l'adresse du compte de service avec le rôle **Accesseur de secrets Secret Manager**. Ce rôle est limité à ce secret, pas à tout le projet.

Déploiement de l'image CPU par digest :

```bash
gcloud run deploy finance-analyst \
  --image=europe-west1-docker.pkg.dev/finance-analyst-agent-511018/finance-analyst/api@sha256:4d50dafc5017d680f48c21f0502a75997be706bd859b2acfd86ecda9c8f3320c \
  --project=finance-analyst-agent-511018 \
  --region=europe-west1 \
  --service-account=finance-analyst-runtime@finance-analyst-agent-511018.iam.gserviceaccount.com \
  --no-allow-unauthenticated \
  --memory=1Gi --cpu=1 \
  --min-instances=0 --max-instances=1 --concurrency=1 --timeout=300 \
  --set-env-vars=LLM_PROVIDER=gemini,GEMINI_MODEL=gemini-3.1-flash-lite,LANGCHAIN_TRACING_V2=false \
  --set-secrets=GOOGLE_API_KEY=google-api-key:1
```

Console : **Cloud Run → service finance-analyst** pour consulter la configuration existante. Pour reproduire : déployer un conteneur, sélectionner l'image, la région et l'authentification requise ; renseigner les ressources et limites ; choisir le compte de service dans Sécurité ; ajouter dans Variables et secrets la référence `GOOGLE_API_KEY` → `google-api-key`, version `1`. Les intitulés peuvent varier selon l'écran.

`GOOGLE_API_KEY` est le nom lu par Python ; `google-api-key` est le nom du secret ; `1` est la version de sa valeur. Cloud Run lit le secret au démarrage grâce à son identité. L'accès des visiteurs au site est une permission distincte de l'accès de l'application au secret.

### Ouvrir le service privé et dépanner le proxy

```bash
gcloud run services proxy finance-analyst \
  --project=finance-analyst-agent-511018 \
  --region=europe-west1 --port=8080
```

Puis ouvrir http://localhost:8080 et laisser le terminal actif. Le programme tourne chez Google ; le proxy local ajoute ton authentification. `Ctrl+C` ferme uniquement le proxy.

Avec l'installation Homebrew, le composant additionnel peut être installé dans `/opt/homebrew/share/google-cloud-sdk/bin` sans être trouvé dans le `PATH`. Symptôme observé : installation du composant réussie puis `cloud-run-proxy binary not installed`.

Correction dans le terminal courant, sans réinstallation :

```bash
export PATH="/opt/homebrew/share/google-cloud-sdk/bin:$PATH"
command -v cloud-run-proxy
```

Relancer ensuite la commande proxy. L'export ne vaut que pour le terminal courant ; pour le conserver, ajouter cette ligne une seule fois à `~/.zshrc`. Si le port est occupé, choisir `--port=8081` et ouvrir http://localhost:8081. Ne pas modifier IAM ni rendre l'application publique pour résoudre ce problème local de chemin.

## Ce qu'il faut comprendre pour ce projet

GCP fournit des services que tu actives dans un **projet** : c'est le périmètre qui regroupe les ressources, les permissions et leur suivi de consommation. Le projet est relié à un compte de facturation. Une **région** désigne l'emplacement des ressources ; on choisira une région commune pour l'image et l'application.

Notre parcours : code + Dockerfile → Cloud Build → image dans Artifact Registry → application sur Cloud Run.

- **Cloud Build** construit l'image chez Google : build React, installation Python et construction de l'index FAISS. Docker local est donc optionnel pour ce parcours.
- **Artifact Registry** conserve les images versionnées ; il n'exécute pas l'application.
- **Cloud Run** exécute l'image et fournit une URL HTTPS. Un seul service héberge ici React et FastAPI.
- **Secret Manager** conserve la clé Gemini et permet de la fournir à l'application au démarrage.
- **IAM** gère les permissions. Ton compte déploie ; un compte de service représente l'application et reçoit le droit de lire son secret.
- **Cloud Logging** reçoit les logs du service ; ils servent à diagnostiquer les erreurs de démarrage et les requêtes.

Gemini reste appelé via l'intégration API existante. Déployer l'application sur GCP n'impose pas de migrer vers Vertex AI. LangSmith reste complémentaire pour les traces du graphe et des appels LLM.

Le corpus, le CSV et l'index sont inclus dans l'image pour cette première démo. Aucune base cloud à configurer pour le premier déploiement. Les validations HITL stockées en RAM restent perdues au redémarrage ; limiter le nombre d'instances ne fournit pas de persistance.

Avant le premier build, créer un budget avec des alertes dans Billing. Un budget **ne bloque pas automatiquement les dépenses**. Suivre séparément construction d'images, stockage, exécution et consommation Gemini.

Références : [Cloud Run](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run), [Cloud Build et Artifact Registry](https://docs.cloud.google.com/build/docs/build-push-docker-image), [Secrets](https://docs.cloud.google.com/run/docs/configuring/services/secrets), [identité du service](https://docs.cloud.google.com/run/docs/configuring/services/service-identity), [logs](https://docs.cloud.google.com/run/docs/logging), [budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets).

## Ce qu’on déploie

### Image CPU

Le déploiement prévu n'utilise pas de GPU. `pyproject.toml` sélectionne donc l'index officiel PyTorch CPU sur Linux ; macOS conserve sa distribution native depuis PyPI. Le `uv.lock` doit être régénéré avec `uv lock` après modification des sources.

Le Dockerfile vérifie `torch.version.cuda is None` pendant le build. `UV_NO_CACHE=1` évite d'embarquer les archives de dépendances, tandis que le modèle MiniLM téléchargé et l'index FAISS restent disponibles dans l'image. La construction de l'index sert également de vérification des embeddings sur Linux.

Un build Cloud Build avec `gcloud builds submit --tag` ne garantit pas la réutilisation des couches d'un build précédent : ne pas supposer que les builds suivants seront automatiquement rapides. Un cache distant explicite pourra être ajouté séparément.

Commande de la version optimisée pour le projet d'apprentissage :

```bash
gcloud builds submit \
  --tag=europe-west1-docker.pkg.dev/finance-analyst-agent-511018/finance-analyst/api:v2-cpu \
  --project=finance-analyst-agent-511018 .
```

Une **image Docker** qui contient :

- l’API FastAPI (`/ask`, `/resume`, `/health`)
- l’UI React buildée (`web/dist`)
- l’index FAISS + embeddings MiniLM
- le CSV de fondamentaux

**Mémoire Cloud Run : 1 Gi minimum** (MiniLM + torch — leçon de la hotline à 512 Mo).

## Prérequis locaux

1. Compte Google + projet GCP (crée-en un sur [console.cloud.google.com](https://console.cloud.google.com))
2. Facturation activée (Cloud Run a un free tier, mais Google demande une carte)
3. Outils installés :
   - [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install)
   - Docker Desktop seulement pour construire/tester l'image localement ; optionnel si on utilise Cloud Build.

4. Dans le repo, les 10-K doivent être présents **avant** le build Docker :

```bash
cd finance-analyst-agent
uv run python scripts/fetch_edgar.py   # remplit data/raw/
# data/structured/fundamentals.csv déjà versionné
```

## 1. Login & projet

```bash
gcloud auth login
gcloud auth configure-docker

export PROJECT_ID=ton-projet-gcp          # ex. finance-analyst-amadou
export REGION=europe-west1                # ou us-central1
gcloud config set project "$PROJECT_ID"
```

Active les APIs :

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com
```

## 2. Artifact Registry (stockage d’images)

```bash
gcloud artifacts repositories create finance-analyst \
  --repository-format=docker \
  --location="$REGION" \
  --description="Finance analyst agent images"
```

Image cible :

```bash
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/finance-analyst/api:latest"
```

## 3. Secret Manager (clé Gemini)

Ne mets **jamais** `GOOGLE_API_KEY` en clair dans le Dockerfile.

```bash
# Une seule fois — colle ta clé quand demandé
printf '%s' 'TA_CLE_GEMINI' | gcloud secrets create google-api-key --data-file=-

# Ou si le secret existe déjà :
# printf '%s' 'TA_CLE_GEMINI' | gcloud secrets versions add google-api-key --data-file=-
```

Donne le droit de lecture au compte de service Cloud Run (par défaut Compute SA) :

```bash
export PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
export RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding google-api-key \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

Optionnel LangSmith :

```bash
printf '%s' 'lsv2_...' | gcloud secrets create langchain-api-key --data-file=-
gcloud secrets add-iam-policy-binding langchain-api-key \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

## 4. Build & push de l’image

Depuis la racine du repo (avec `data/raw/` rempli) :

```bash
docker build -t "$IMAGE" .
docker push "$IMAGE"
```

Le build peut prendre **plusieurs minutes** (npm + torch + `build_index.py`).

### Alternative : Cloud Build

Sans Docker local, Google construit et publie l'image à partir du Dockerfile. Le fichier `.gcloudignore` du dépôt exclut les secrets et les dépendances locales, mais conserve les filings nécessaires au build. Avant l'envoi, vérifier la liste :

```bash
gcloud meta list-files-for-upload
# Vérifier : les .htm de data/raw sont présents, aucun .env n'est présent.
```

```bash
gcloud builds submit --tag "$IMAGE" .
```

## 5. Deploy Cloud Run

```bash
gcloud run deploy finance-analyst \
  --image="$IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300 \
  --set-env-vars="LLM_PROVIDER=gemini,GEMINI_MODEL=gemini-2.5-flash-lite" \
  --set-secrets="GOOGLE_API_KEY=google-api-key:latest"
```

Avec LangSmith (optionnel) :

```bash
gcloud run deploy finance-analyst \
  --image="$IMAGE" \
  --region="$REGION" \
  --allow-unauthenticated \
  --memory=1Gi \
  --set-env-vars="LLM_PROVIDER=gemini,GEMINI_MODEL=gemini-2.5-flash-lite,LANGCHAIN_TRACING_V2=true,LANGCHAIN_PROJECT=finance-analyst-agent" \
  --set-secrets="GOOGLE_API_KEY=google-api-key:latest,LANGCHAIN_API_KEY=langchain-api-key:latest"
```

À la fin, `gcloud` affiche une URL du type :

`https://finance-analyst-xxxxx-ew.a.run.app`

## 6. Vérifier

```bash
curl -s https://TON-URL/health | jq
# Ouvre l’URL dans le navigateur → UI React
```

Test SSE rapide :

```bash
curl -N -X POST https://TON-URL/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is Apple ROE?","ticker":"AAPL"}'
```

## Coûts & free tier (ordre de grandeur)

- Cloud Run : facturé à l’usage ; free tier mensuel souvent suffisant pour une démo portfolio
- **Cold start** : si personne n’a hit le service, le premier chargement peut prendre 30s–2min (image + MiniLM)
- Gemini : quotas free / pay-as-you-go selon ton compte Google AI

## Pièges fréquents

| Symptôme | Cause probable |
|---|---|
| OOM / container killed | Mémoire &lt; 1Gi |
| Build Docker échoue sur `build_index` | `data/raw/` vide → lance `fetch_edgar.py` avant |
| 403 Gemini | Secret mal monté ou mauvaise clé |
| UI blanche mais `/health` OK | Build front raté / `VITE_API_BASE` mal set (doit être vide en prod same-origin) |
| HITL resume perdu après cold start | MemorySaver en RAM — normal en V1 ; Postgres checkpointer en roadmap |

## Architecture deploy

```
Browser → Cloud Run (1 service)
            ├─ GET /           → React (web/dist)
            ├─ POST /ask       → LangGraph SSE
            ├─ POST /resume    → HITL
            └─ Secret Manager  → GOOGLE_API_KEY
```

## Après le premier deploy

1. Mets l’URL dans le README + portfolio
2. Fais 2–3 screenshots (chat, HITL, LangSmith)
3. Note le cold start dans le post LinkedIn / README (honnêteté démo free)
