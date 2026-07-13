# Document d'Architecture Technique (DAT) — Market Intelligence Hub

## 1. Contexte et objectif

Automatiser la veille concurrentielle : ingestion, transformation et visualisation de données de marché, sans intervention manuelle récurrente. Cette première itération couvre le Niveau 1 (pipeline fonctionnel end-to-end sur une source réelle) avec une fondation extensible pour les niveaux suivants (scoring, alertes, IaC, monitoring).

## 2. Vue d'ensemble de l'architecture

```
GitHub (source + CI/CD)
        │
        ▼
GitHub Actions : lint → tests (ingestion, API) → build images Docker
        │
        ▼
Docker Compose
 ├── airflow-db (Postgres)       — métadonnées internes Airflow, isolées
 ├── airflow-webserver/scheduler — orchestration du DAG ELT
 ├── app-db (Postgres)           — métadonnées applicatives (datasets, runs)
 ├── minio + minio-init          — Data Lake S3-compatible (bronze/silver/gold)
 ├── api (FastAPI)               — expose /health, /datasets, /runs
 └── dashboard (Streamlit)       — lit les Parquet Gold + interroge l'API
```

## 3. Flux de données (ELT)

1. **Extract** — `ingestion/src/ingestion/sources/eurostat.py` interroge l'API Eurostat (format JSON-stat 2.0, aucune clé requise), avec retries exponentiels sur erreurs 429/5xx.
2. **Load (Bronze)** — `ingestion/src/ingestion/bronze.py` stocke le payload brut, horodaté (`eurostat/{dataset}/{run_ts}.json`), sans transformation. Traçabilité et rejouabilité garanties.
3. **Transform (Silver)** — `ingestion/src/ingestion/silver.py` parse le JSON-stat (dimensions → coordonnées via index mixed-radix), nettoie (valeurs manquantes, doublons, codes inconnus), type les colonnes, écrit un Parquet dans `silver/`.
4. **Transform (Gold)** — `ingestion/src/ingestion/gold.py` calcule, par pays, la dernière valeur et sa variation vs. la période précédente (base du futur scoring "changements stratégiques"), écrit deux Parquet (`_timeseries`, `_summary`) dans `gold/`, et journalise le run (`datasets`, `runs`) dans Postgres.

Chaque étape est une tâche Airflow indépendante (`@task`), avec passage de contexte via XCom et retries configurés au niveau du DAG (`airflow/dags/ingestion_pipeline.py`).

## 4. Choix techniques justifiés

| Choix | Justification |
|---|---|
| **Eurostat REST API** comme première source | Aucune authentification requise, dataset stable et documenté, illustre le cas d'usage "bases de données publiques" du cahier des charges. Le code est isolé dans `sources/` pour ajouter facilement une 2e source (Google Trends, scraping). |
| **MinIO** plutôt que S3 réel | Gratuit, exécutable en local, API S3-compatible → migration vers AWS S3/GCS sans changement de code applicatif (seul `storage.py` gère l'endpoint). |
| **Parquet** pour Silver/Gold | Format colonnaire compressé, interopérable (pandas, DuckDB, Spark), standard en ingénierie de données — contrairement au JSON brut conservé en Bronze. |
| **Deux bases Postgres distinctes** (`airflow-db`, `app-db`) | Isolation des métadonnées internes d'Airflow et des métadonnées applicatives — évite tout couplage accidentel et simplifie une migration/scaling indépendant de chaque composant. |
| **Airflow LocalExecutor** | Suffisant pour un DAG séquentiel unique à ce stade ; évite la complexité opérationnelle de CeleryExecutor/Redis tant qu'elle n'est pas justifiée par la charge. |
| **FastAPI** plutôt que Flask | Typage natif, documentation OpenAPI générée automatiquement (`/docs`), meilleure adéquation avec un stack Python moderne et testable (`TestClient`). |
| **Streamlit** plutôt que Superset | Mise en place en quelques dizaines de lignes, hébergement gratuit possible (Streamlit Cloud) pour une démo publique — pertinent pour la validation Niveau 1 avant d'envisager Superset si le besoin BI d'entreprise se confirme. |
| **DuckDB** (usage prévu, pas de service dédié) | Interrogation ad hoc des fichiers Gold sans infrastructure supplémentaire ; introduit uniquement côté consommation (API/dashboard) si des requêtes analytiques plus complexes sont nécessaires. |

## 5. Modèle de données (app-db)

```sql
datasets (dataset_code PK, latest_gold_timeseries_key, latest_gold_summary_key, updated_at)
runs (id PK, run_ts, dataset_code, status, records_count, gold_key, created_at)
```

Voir [infra/postgres/init.sql](../infra/postgres/init.sql).

## 6. CI/CD

`.github/workflows/ci.yml` — déclenché sur push/PR vers `main` :
1. `lint` — Ruff sur `ingestion/` et `api/`.
2. `test-ingestion` / `test-api` — Pytest, entièrement mockés (aucune dépendance réseau ou base de données réelle en CI).
3. `build` — build Docker des 3 images (`airflow`, `api`, `dashboard`) en matrice, garantissant que chaque Dockerfile reste buildable à chaque changement.

## 7. Accès aux services (environnement local)

| Service | URL |
|---|---|
| Airflow UI | http://localhost:8080 (admin/admin) |
| API (Swagger) | http://localhost:8000/docs |
| Dashboard Streamlit | http://localhost:8501 |
| Console MinIO | http://localhost:9001 (minioadmin/minioadmin123) |

## 8. Limites connues et évolutions prévues (bonus)

- **Niveau 2** : scoring de détection de changement significatif (déjà amorcé via le calcul `delta` en zone Gold) + alertes Slack/Email sur seuil dépassé.
- **Niveau 3** : Terraform pour déploiement cloud (S3/RDS managés), Prometheus/Grafana pour le monitoring des DAGs et services, Great Expectations pour la validation de qualité des données en zone Silver.
- Ajout de sources supplémentaires (Google Trends via `pytrends`, scraping de sites concurrents) en suivant le même pattern `sources/<nouvelle_source>.py`.
