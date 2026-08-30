# RAG finance — PDF/HTML, chunks, chiffres

## Idée centrale

Sur un 10-K, le danger n’est pas seulement « ne pas trouver le paragraphe » — c’est **citer un mauvais montant** ou mélanger deux exercices fiscaux.

Stratégie V1 :

1. **RAG** pour le **qualitatif** (risques, description du business, citations de texte)
2. **CSV** `data/structured/fundamentals.csv` + **tools Python** pour le **quantitatif** (ratios)
3. Le prompt interdit d’inventer un chiffre absent du contexte / des tools

## Corpus actuel

Script : `scripts/fetch_edgar.py`  
Source : SEC EDGAR (submissions API + Archives).

Entreprises seed : **AAPL**, **MSFT**, **GOOGL** (dernier 10-K disponible).  
Fichiers locaux dans `data/raw/` (gitignored). Manifest versionné : `data/raw/manifest.json`.

Les filings SEC récents sont souvent du **HTML** (pas du PDF). Le worker RAG devra parser HTML → texte (BeautifulSoup / stripping) puis chunker.

## Chunking (prévu worker RAG)

- Taille ~800–1200 caractères, overlap ~150
- Métadonnées : `ticker`, `filing_date`, `source_file`, éventuellement titre de section si détectable
- Index FAISS + embeddings `all-MiniLM-L6-v2`

## Pourquoi pas « tout faire par RAG » pour les ratios ?

Le retrieve peut ramener un tableau mal découpé ; le LLM arrondit ou confond « millions ».  
Les ratios V1 sont donc calculés par du **code** sur des fondamentaux seedés (vérifiables), pendant que le RAG justifie le *narratif*.

## Suite

Implémenter l’index + `ask` CLI avec citations `(ticker, extrait)`.
