# Market Intelligence Hub

[![CI](https://github.com/Pancracedev/market-intelligence-hub/actions/workflows/ci.yml/badge.svg)](https://github.com/Pancracedev/market-intelligence-hub/actions/workflows/ci.yml)

Plateforme automatisée et conteneurisée de **veille concurrentielle / market intelligence**, construite comme un projet Data DevOps de bout en bout : ingestion, pipeline ELT en zones Bronze/Silver/Gold, Data Lake, orchestration, API et dashboard temps réel.

## Le problème métier

95% des entreprises jugent la veille concurrentielle stratégique, mais seulement 20% l'automatisent. Le reste : du scraping manuel, des données dispersées, des rapports obsolètes dès leur publication. Cette plateforme automatise entièrement la collecte, la transformation et la visualisation d'indicateurs de marché.

## Stack technique

| Composant | Technologie |
|---|---|
| Orchestration | Apache Airflow (LocalExecutor) |
| Ingestion | Python (client Eurostat, retries + backoff) |
| Data Lake | MinIO (S3-compatible), zones `bronze/` `silver/` `gold/` |
| Format analytique | Parquet |
| Métadonnées | PostgreSQL |
| API | FastAPI |
| Dashboard | Streamlit |
| Conteneurisation | Docker Compose |
| CI/CD | GitHub Actions (lint, tests, build Docker) |

## Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                     GitHub Actions (CI/CD)                        │
│           lint  →  tests (ingestion + api)  →  docker build       │
└───────────────────────────────┬───────────────────────────────────┘
                                 ▼
┌───────────────────────────────────────────────────────────────────┐
│                         Docker Compose                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌───────┐ │
│  │ Airflow  │  │ FastAPI  │  │PostgreSQL│  │  MinIO  │  │Stream-│ │
│  │(webserver│  │  (API)   │  │(app+     │  │(Data    │  │ lit   │ │
│  │+scheduler│  │          │  │ airflow) │  │ Lake)   │  │       │ │
│  └────┬─────┘  └────┬─────┘  └──────────┘  └────┬────┘  └───┬───┘ │
│       │             │                            │           │    │
│       └── DAG: ingest → bronze → silver → gold ───┘           │    │
│                                                    └── lit gold ┘   │
└───────────────────────────────────────────────────────────────────┘
```

Détails complets, choix techniques justifiés et flux de données : [docs/DAT.md](docs/DAT.md).

## Pipeline de données

1. **Ingestion** : appel à l'API publique [Eurostat](https://ec.europa.eu/eurostat/) (indicateur configurable, par défaut `prc_hicp_manr` — inflation annuelle par pays), avec retries/backoff sur les erreurs transitoires.
2. **Bronze** : payload JSON-stat brut, horodaté, stocké tel quel dans MinIO.
3. **Silver** : nettoyage, typage, déduplication → table Parquet structurée.
4. **Gold** : agrégats analytiques (série temporelle complète + résumé "plus fortes variations" par pays) + enregistrement des métadonnées de run en PostgreSQL.
5. **Dashboard** : lecture directe des Parquet Gold depuis MinIO, visualisation des tendances et des variations.

## Démarrage rapide

Prérequis : Docker et Docker Compose.

```bash
git clone https://github.com/Pancracedev/market-intelligence-hub.git
cd market-intelligence-hub
cp .env.example .env
make up
```

### Développement local (sans Docker)

Chaque package Python (`ingestion/`, `api/`, `dashboard/`) est géré avec [`uv`](https://docs.astral.sh/uv/) et son propre `.venv` :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # si uv n'est pas déjà installé
make sync   # crée les .venv et installe les dépendances (via uv.lock) pour les 3 packages
make test   # lance les tests (ingestion + api) avec uv run
make lint   # ruff sur ingestion + api
```

Accès aux services une fois démarrés :

| Service | URL | Identifiants |
|---|---|---|
| Airflow | http://localhost:8080 | admin / admin |
| API (docs) | http://localhost:8000/docs | — |
| Dashboard | http://localhost:8501 | — |
| Console MinIO | http://localhost:9001 | minioadmin / minioadmin123 |

Déclencher manuellement la première exécution du pipeline :

```bash
make dag-trigger
# ou depuis l'UI Airflow : DAGs → market_intelligence_pipeline → Trigger
```

Après quelques secondes, les données apparaissent dans MinIO (`bronze/`, `silver/`, `gold/`) et dans le dashboard Streamlit.

## Tests

```bash
make test    # tests unitaires ingestion + API (mockés, sans dépendance réseau/DB)
make lint    # ruff sur les packages Python
```

## Roadmap (bonus)

- [ ] Scoring automatique des variations significatives + alertes Slack/Email
- [ ] Sources additionnelles (Google Trends, scraping concurrent)
- [ ] Infrastructure as Code (Terraform) pour déploiement cloud
- [ ] Monitoring Prometheus + Grafana
- [ ] Tests de qualité de données (Great Expectations)

## Licence

MIT — voir [LICENSE](LICENSE).
