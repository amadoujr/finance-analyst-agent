# RAG finance — PDF, chunks, chiffres

*(Doc rempli pendant la phase corpus / worker RAG.)*

## Idée centrale

Sur un 10-K, le danger n’est pas « ne pas trouver le paragraphe » — c’est **citer un mauvais montant** ou mélanger FY2023 et FY2024.

Stratégie V1 :

1. RAG pour le **qualitatif** (risques, description business, citations de texte)
2. CSV `fundamentals.csv` + tools Python pour le **quantitatif** (ratios)
3. Le prompt interdit d’inventer un chiffre absent du contexte / des tools
