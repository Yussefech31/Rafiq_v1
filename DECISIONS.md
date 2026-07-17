# DECISIONS.md — Journal des décisions techniques RAFIQ

Chaque simplification MVP est tracée ici pour le rapport final.

| # | Décision | Justification | Évolution prévue |
|---|----------|---------------|------------------|
| 1 | **Modèle d'embedding**: `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions) | Supporte arabe + français, bon compromis vitesse/qualité, gratuit (pas d'API payante), bien testé sur des tâches multilingues. | Évaluer `multilingual-e5-large` ou l'API Voyage si budget disponible. |
| 2 | **Vector store**: FAISS par défaut, Qdrant via `docker-compose` si Docker disponible | FAISS = zéro infrastructure, persistence locale. Qdrant = production-grade si Docker est disponible. Détection automatique. | Migration vers Qdrant Cloud ou Weaviate en production. |
| 3 | **Score de confiance**: formule pondérée simple (`top_similarity * 0.6 + top3_agreement * 0.4`) | Pas de classificateur entraîné — trop coûteux en temps pour le MVP. La formule simple est interprétable et ajustable. | Entraîner un classificateur binaire sur les retours experts (Phase 4+). |
| 4 | **Pas de BM25 / recherche hybride en v1** | Dense-only retrieval simplifie l'architecture. Les embeddings multilingues couvrent raisonnablement le besoin. | v2 TODO: ajouter BM25 sparse search + fusion RRF. |
| 5 | **Pas de cross-encoder / reranker en v1** | Ajoute une latence et une dépendance modèle supplémentaire. Marginal pour le corpus actuel (< 10k chunks). | v2 TODO: `cross-encoder/ms-marco-MiniLM-L-12-v2` ou équivalent multilingue. |
| 6 | **SQLite pour métadonnées** | Zéro configuration, fichier unique, suffisant pour un corpus < 100k entrées. | Migrer vers PostgreSQL pour la production multi-utilisateurs. |
| 7 | **Un seul template Word** | Le besoin identifié est un format unique de réponse administrative. | Bibliothèque de templates si d'autres formats sont demandés. |
| 8 | **Pas d'authentification** | Démo PFA, pas de données sensibles dans le prototype. Clé API hardcodée suffisante. | OAuth2 / SSO ministériel en production. |
| 9 | **LLM: Claude claude-sonnet-4-6 via Anthropic API** | Excellent en français, suit bien les instructions de citation, API fiable. | Évaluer des modèles locaux (Mistral, Llama) pour réduire les coûts. |
| 10 | **Frontend: HTML/JS vanilla** | Aucun framework = zéro setup, modification rapide, pas de build step. | React/Vue si le frontend grandit significativement. |
| 11 | **Chunking: règles regex uniquement en Phase 1** | Split sur `||`, bullets, paragraphes. Suffisant pour le corpus structuré Excel. | Phase 2+: LLM-based splitting pour les cas ambigus. |
| 12 | **Pas de fine-tuning** | La boucle de capitalisation (writeback qa_store) améliore le système sans fine-tuning. C'est le design central du projet. | Fine-tuning d'embedding sur le corpus si les résultats retrieval sont insuffisants. |
| 13 | **Normalisation arabe légère** | Suppression tashkeel, normalisation alef, suppression tatweel. Pas de stemming/lemmatisation. | Ajouter CAMeL Tools ou Farasa pour une normalisation plus poussée. |
