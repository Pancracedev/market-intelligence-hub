# Market Intelligence Hub

[![CI](https://github.com/Pancracedev/market-intelligence-hub/actions/workflows/ci.yml/badge.svg)](https://github.com/Pancracedev/market-intelligence-hub/actions/workflows/ci.yml)

Plateforme SaaS multi-utilisateurs de **veille concurrentielle automatisée**. Chaque utilisateur configure lui-même les concurrents/indicateurs qu'il veut suivre — aucun nom de concurrent n'est codé en dur.

## Le problème métier

95% des entreprises jugent la veille concurrentielle stratégique, mais seulement 20% l'automatisent. Le reste : du scraping manuel, des données dispersées, des rapports obsolètes dès leur publication. Cette plateforme automatise entièrement la collecte, la transformation et la visualisation d'indicateurs de marché, pour n'importe quel utilisateur et n'importe quelle cible qu'il configure.

## Comment ça marche

Un utilisateur crée un compte, puis ajoute un **watcher** : ce qu'il veut suivre.

| Type de watcher | Ce qu'il suit | Comment |
|---|---|---|
| `price` | Le prix d'un produit sur un site concurrent | URL + sélecteur CSS, scraping respectueux (robots.txt, rate-limit par domaine) |
| `eurostat` | Un indicateur économique public (ex: inflation par pays) | Code dataset Eurostat + filtres |
| `trend` | Un mot-clé de recherche | Google Trends *(prévu, non encore câblé)* |

Chaque watcher a sa propre fréquence (`schedule`) et ses données sont isolées par compte.

## Stack technique

| Composant | Technologie |
|---|---|
| Frontend | Next.js (App Router) + TypeScript + Tailwind + Recharts |
| API | FastAPI, JWT (auth maison), isolation multi-tenant |
| Orchestration | Apache Airflow (LocalExecutor, dynamic task mapping) |
| Ingestion | Python (scraping générique, client Eurostat, retries + backoff) |
| Data Lake | MinIO (S3-compatible), zones `bronze/` `silver/` `gold/`, partitionnées par `watcher_id` |
| Format analytique | Parquet |
| Métadonnées | PostgreSQL (`users`, `watchers`, `watcher_state`, `runs`) |
| Conteneurisation | Docker Compose |
| CI/CD | GitHub Actions (lint, tests, build Docker + frontend) |

## Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                     GitHub Actions (CI/CD)                        │
│      lint → tests (ingestion + api) → build (airflow/api/front)   │
└───────────────────────────────┬───────────────────────────────────┘
                                 ▼
┌───────────────────────────────────────────────────────────────────┐
│                         Docker Compose                            │
│ ┌────────┐ ┌────────┐ ┌──────────┐ ┌───────┐ ┌──────────────────┐ │
│ │Airflow │ │FastAPI │ │PostgreSQL│ │ MinIO │ │  Frontend        │ │
│ │(dyn.   │ │ (API,  │ │(app+     │ │(Data  │ │  Next.js         │ │
│ │mapping)│ │  JWT)  │ │ airflow) │ │ Lake) │ │                  │ │
│ └───┬────┘ └───┬────┘ └──────────┘ └───┬───┘ └────────┬─────────┘ │
│     │          │                       │              │          │
│     └── un run par watcher dû ──────────┘              │          │
│                    (bronze → silver → gold)            │          │
│     API sert /watchers, /runs, /timeseries  ◄───────────┘         │
└───────────────────────────────────────────────────────────────────┘
```

Détails complets, choix techniques justifiés et flux de données : [docs/DAT.md](docs/DAT.md).

## Pipeline de données (par watcher)

1. **Ingestion** : selon le type de watcher — scraping du prix (requests + BeautifulSoup4, robots.txt + rate-limit) ou appel à l'API Eurostat — avec retries/backoff sur les erreurs transitoires.
2. **Bronze** : payload brut, horodaté, stocké tel quel dans MinIO sous `{watcher_type}/{watcher_id}/...`.
3. **Silver** : nettoyage, typage → table Parquet structurée.
4. **Gold** : agrégats analytiques (série temporelle + résumé "dernière variation") + enregistrement du run en PostgreSQL, scopé au watcher (et donc à son propriétaire).
5. **Frontend** : chaque utilisateur ne voit que ses propres watchers et leurs données, via l'API (jamais d'accès direct à MinIO depuis le navigateur).

## Démarrage rapide

Prérequis : Docker et Docker Compose.

```bash
git clone https://github.com/Pancracedev/market-intelligence-hub.git
cd market-intelligence-hub
cp .env.example .env
make up
```

Un compte de démonstration est créé automatiquement au démarrage de l'API :

| Email | Mot de passe |
|---|---|
| `demo@example.com` | `demo12345` |

(désactivable via `SEED_DEMO_USER=false` dans `.env` — utile uniquement en local/démo, jamais en production).

### Développement local (sans Docker)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # si uv n'est pas déjà installé
make sync   # crée les .venv et installe les dépendances (via uv.lock) pour ingestion/ et api/
make test   # lance les tests (mockés, sans dépendance réseau/DB)
make lint    # ruff sur les packages Python
```

Pour le frontend :

```bash
cd frontend && npm install && npm run dev
```

Accès aux services une fois démarrés :

| Service | URL | Identifiants |
|---|---|---|
| Frontend | http://localhost:3000 | créez un compte |
| Airflow | http://localhost:8080 | admin / admin |
| API (docs) | http://localhost:8000/docs | — |
| Console MinIO | http://localhost:9001 | minioadmin / minioadmin123 |

Le DAG `watcher_pipeline` tourne toutes les heures et traite tous les watchers actifs "dus" selon leur propre fréquence. Pour forcer une exécution immédiate :

```bash
make dag-trigger
# ou depuis l'UI Airflow : DAGs → watcher_pipeline → Trigger
```

## Tests

```bash
make test    # tests unitaires ingestion + API (mockés, sans dépendance réseau/DB)
make lint    # ruff sur les packages Python
```

## Roadmap

- [ ] Watcher `trend` (Google Trends via pytrends)
- [ ] Scoring / alertes Slack-Email sur variation significative
- [ ] Row-Level Security Postgres, refresh tokens, cookies httpOnly
- [ ] Infrastructure as Code (Terraform) pour déploiement cloud
- [ ] Monitoring Prometheus + Grafana
- [ ] Tests de qualité de données (Great Expectations)

## Licence

MIT — voir [LICENSE](LICENSE).
