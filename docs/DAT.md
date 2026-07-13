# Document d'Architecture Technique (DAT) — Market Intelligence Hub

## 1. Contexte et objectif

Plateforme SaaS multi-utilisateurs de veille concurrentielle : chaque utilisateur configure lui-même les concurrents/indicateurs qu'il veut suivre ("watchers"), sans rien coder en dur. Cette itération couvre la fondation multi-tenant (auth, isolation par compte) et un chemin bout-en-bout complet pour les watchers de type `price` (scraping générique) et `eurostat` (indicateur public), avec un vrai frontend web.

## 2. Vue d'ensemble de l'architecture

```
GitHub (source + CI/CD)
        │
        ▼
GitHub Actions : lint → tests (ingestion, API) → build (airflow/api/frontend)
        │
        ▼
Docker Compose
 ├── airflow-db (Postgres)       — métadonnées internes Airflow, isolées
 ├── airflow-webserver/scheduler — DAG dynamique watcher_pipeline
 ├── app-db (Postgres)           — users, watchers, watcher_state, runs, domain_rate_limits
 ├── minio + minio-init          — Data Lake S3-compatible (bronze/silver/gold)
 ├── api (FastAPI)               — auth JWT + CRUD watchers, scopé par utilisateur
 └── frontend (Next.js)          — signup/login, dashboard, ajout de watcher, graphiques
```

## 3. Modèle de données central : le "watcher"

Un `watcher` est ce qu'un utilisateur veut suivre — généralisation du dataset unique de la v1 :

```sql
watchers (id PK, user_id FK, watcher_type, name, config JSONB, is_active, schedule, ...)
watcher_state (watcher_id PK/FK, latest_gold_timeseries_key, latest_gold_summary_key, updated_at)
runs (id PK, watcher_id FK, run_ts, status, error_message, records_count, gold_key, created_at)
```

`config` est validé côté API par une union discriminée Pydantic (`api/app/schemas.py`) selon `watcher_type` :
- `price` : `{url, css_selector, currency}` — scraping générique
- `trend` : `{keyword, geo, timeframe}` — Google Trends *(schéma prêt, pipeline non câblé dans cette itération)*
- `eurostat` : `{dataset_code, filters}` — généralisation du cas d'usage v1 (plus de valeur hardcodée)

Voir [infra/postgres/init.sql](../infra/postgres/init.sql).

## 4. Flux de données (ELT), généralisé par watcher

Les clés MinIO sont partitionnées `{watcher_type}/{watcher_id}/{run_ts}...` (au lieu de `eurostat/{dataset_code}/...` en v1) — isolation naturelle par id numérique, jamais deviné/partagé entre utilisateurs.

1. **Bronze** (`ingestion/src/ingestion/bronze.py`) — dispatcher `ingest_watcher_to_bronze(watcher, run_ts)` : scrape (`sources/price_scraper.py`, avec vérification robots.txt et rate-limit par domaine) ou appelle l'API Eurostat, stocke le payload brut.
2. **Silver** (`silver.py`) — dispatcher `transform_bronze_to_silver` : nettoie/type selon le type de watcher.
3. **Gold** (`gold.py`) — dispatcher `transform_silver_to_gold` : pour `eurostat`, le silver contient déjà tout l'historique (comme en v1) ; pour `price`, **chaque run n'observe qu'un seul point** — la zone Gold accumule donc tous les fichiers silver historiques du watcher (`price_silver_to_gold`) pour reconstruire la série temporelle complète. Écrit les métadonnées de run en Postgres, scopées au watcher (donc au propriétaire).

## 5. Orchestration Airflow : un DAG dynamique plutôt qu'un DAG par watcher

`airflow/dags/watcher_pipeline.py` tourne `@hourly` et utilise le **dynamic task mapping** (Airflow 2.9, `.expand()`) :
1. `list_due_watchers` interroge Postgres (`ingestion/src/ingestion/scheduling.py::get_due_watchers`) et filtre, pour chaque watcher actif, si son propre `schedule` (cron string ou preset `@daily`/`@hourly`/...) est "dû" depuis son dernier run (via `croniter`).
2. `ingest`/`to_silver`/`to_gold` sont mappés dynamiquement sur la liste de watchers dus — un run Airflow, N task instances, chacune indépendamment observable/réessayable dans l'UI.
3. Chaque étape journalise un run `failed` avec message d'erreur avant de re-lever l'exception, pour qu'un watcher en échec (site changé, sélecteur invalide) n'impacte ni les autres watchers ni la visibilité de l'échec.

Alternative écartée : un DAG par watcher (créé/détruit dynamiquement) ou un déclenchement direct par l'API — aurait dupliqué la logique de retry/observabilité qu'Airflow fournit déjà, pour un gain marginal à l'échelle visée (LocalExecutor, un seul nœud).

## 6. Authentification et isolation multi-tenant

- JWT fait main (`bcrypt` + `python-jose`, `api/app/auth.py`) plutôt que `fastapi-users` : cohérent avec le style minimal/explicite déjà en place, contrôle total sur la forme de `users`.
- Isolation appliquée **au niveau API** : chaque requête sur `/watchers`, `/runs` filtre `WHERE user_id = current_user.id` (via jointure). Pas de Row-Level Security Postgres dans cette itération — limite documentée, à durcir si le nombre d'utilisateurs/la sensibilité des données l'exige.
- Le frontend ne lit jamais MinIO directement (contrairement au dashboard Streamlit de la v1) : tout passe par l'API (`/watchers/{id}/timeseries`, `/summary`), qui applique l'isolation avant de lire le Parquet.

## 7. Scraping générique : éthique et fiabilité

Le watcher `price` scrape une URL fournie par l'utilisateur — pas un site fixe — donc :
- `ingestion/src/ingestion/robots.py` vérifie le `robots.txt` du domaine avant chaque requête (levée d'exception explicite si interdit, jamais un skip silencieux).
- `ingestion/src/ingestion/ratelimit.py` impose un délai minimal par domaine, **persisté en Postgres** (`domain_rate_limits`) car Airflow LocalExecutor exécute chaque tâche dans un process séparé — un limiteur en mémoire ne serait pas partagé entre tâches concurrentes.
- User-Agent honnête (`MarketIntelligenceHub/1.0`, avec contact), pas de spoofing de navigateur.
- Le frontend affiche un avertissement + rappelle que la responsabilité de la légalité du scraping d'un site donné incombe à l'utilisateur qui configure l'URL.

## 8. Choix techniques justifiés (compléments v1)

| Choix | Justification |
|---|---|
| **`ingestion` en dépendance de chemin (`uv.sources`) pour l'API** | L'API a besoin de lire les Parquet Gold depuis MinIO (`storage.py`) ; réutiliser le package plutôt que dupliquer ~10 lignes de client boto3. Le venv de l'API reste indépendant de celui d'Airflow (pas de contrainte de version partagée). |
| **Contrainte Airflow 2.9.3 respectée pour toute nouvelle dépendance `ingestion`** | `beautifulsoup4`, `croniter` ajoutés en vérifiant qu'ils sont résolvables sous `constraints-2.9.3/constraints-3.11.txt` (notamment SQLAlchemy 1.4.x) — cf. incident déjà rencontré en v1 lors de la migration vers `uv`. |
| **Next.js (App Router) + Tailwind + Recharts** plutôt que Streamlit | Un vrai produit multi-page (login/dashboard/formulaire/détail) avec une UX soignée ; Streamlit ne permettait pas des formulaires de configuration ni une navigation par utilisateur satisfaisants. |
| **JWT stocké côté client (`localStorage`)** plutôt que cookie httpOnly | Simplicité pour cette itération ; limitation connue (exposition XSS) documentée comme item de durcissement futur plutôt que sur-ingénierie immédiate. |
| **`bcrypt` direct plutôt que `passlib`** | `passlib[bcrypt]` a un bug de compatibilité connu avec les versions récentes de `bcrypt` (détection de version cassée) ; appel direct à la lib `bcrypt`, plus simple et sans cette classe de bug. |

## 9. CI/CD

`.github/workflows/ci.yml` — déclenché sur push/PR vers `main` :
1. `lint` — Ruff sur `ingestion/` et `api/`.
2. `test-ingestion` / `test-api` — Pytest, entièrement mockés (aucune dépendance réseau, DB ou MinIO réelle en CI).
3. `frontend-build` — `npm ci && npm run build` (Next.js).
4. `build` — build Docker des images `airflow`, `api`, `frontend` en matrice.

## 10. Accès aux services (environnement local)

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Airflow UI | http://localhost:8080 (admin/admin) |
| API (Swagger) | http://localhost:8000/docs |
| Console MinIO | http://localhost:9001 (minioadmin/minioadmin123) |

## 11. Alertes (email / Slack)

Chaque watcher `price` porte trois règles optionnelles (`alert_price_drop_pct`, `alert_on_stock_out`, `alert_on_promo`). Après chaque run réussi, `ingestion/src/ingestion/alerts.py::evaluate_and_notify` compare l'observation courante à la précédente (déjà calculées par `build_summary_single_series` en zone Gold) et déclenche une notification **uniquement sur transition** :
- baisse de prix : delta négatif dont le pourcentage dépasse le seuil configuré ;
- rupture de stock : `in_stock` passe de `True` à `False` (pas de spam si le produit reste indisponible d'un run à l'autre) ;
- promotion : `is_promo` passe de `False`/absent à `True`.

Deux canaux, `ingestion/src/ingestion/notifications.py` :
- **Email** : toujours envoyé à l'adresse du compte si `SMTP_HOST` est configuré (sinon no-op documenté, pas d'erreur) — aucune configuration côté utilisateur.
- **Slack** : simple POST vers le webhook entrant que l'utilisateur configure lui-même dans `/settings` (`users.slack_webhook_url`) — fonctionne immédiatement, sans clé API à gérer côté plateforme.

Chaque notification effectivement envoyée est journalisée dans `notifications_log` (exposée via `GET /watchers/{id}/alerts`) pour que l'utilisateur voie ce qui a été envoyé, sans avoir à déduire un historique depuis les runs.

## 12. Résumé hebdomadaire par IA

`ingestion/src/ingestion/digest.py` est la couche d'interprétation au-dessus du pipeline : plutôt que de lister des deltas bruts, elle transforme l'activité de la semaine en une synthèse en langage naturel.

1. `get_users_with_active_watchers()` liste les utilisateurs éligibles (≥1 watcher actif) — audience du DAG `airflow/dags/weekly_digest.py` (`@weekly`, dynamic task mapping, un digest par utilisateur).
2. `collect_digest_data(user_id, since)` rassemble, pour chaque watcher : le dernier résumé Gold (prix, stock, promo), le nombre de vérifications sur la fenêtre, et les alertes envoyées (`notifications_log`) sur la même fenêtre.
3. `render_prompt(...)` construit un prompt structuré ; `_call_llm(...)` essaie **Groq** en premier (gratuit, sans facturation — modèle configurable via `GROQ_DIGEST_MODEL`, par défaut `llama-3.3-70b-versatile`), puis **Anthropic** si configuré (`ANTHROPIC_DIGEST_MODEL`, défaut `claude-haiku-4-5`), pour produire une synthèse de 3 à 5 phrases orientée décision plutôt que description.
4. Si aucune clé n'est configurée, `_fallback_digest(...)` produit un résumé factuel simple (sans IA) — le pipeline ne casse jamais par absence de clé, même comportement que l'e-mail sans SMTP.
5. Le résultat est envoyé par email et journalisé dans `digest_log`, exposé via `GET /digests` (historique) et `POST /digests/generate` (génération à la demande, utile pour tester sans attendre la semaine).

## 13. Détection automatique du prix (sans sélecteur CSS)

Demander un sélecteur CSS à un utilisateur non technique est le principal point de friction du produit. `ingestion/src/ingestion/sources/product_detector.py` lit plutôt les données structurées que la plupart des sites e-commerce publient déjà pour le référencement (Google Shopping, rich snippets) :
1. **JSON-LD** (`<script type="application/ld+json">`, `@type: Product`) — la source la plus fiable, gère aussi les documents `@graph`.
2. **Open Graph** (`product:price:amount`, `product:availability`) en repli.
3. **Microdata** (`itemprop="price"`) en dernier repli.

`PriceConfig.mode` vaut `"auto"` par défaut (juste une URL, pas de sélecteur) ou `"manual"` (comportement v1, sélecteur CSS explicite requis) pour les sites sans aucune donnée structurée. Le frontend propose un bouton "Détecter" (`POST /watchers/detect`) qui affiche un aperçu avant la création du watcher, avec un panneau "Options avancées" repliable en cas d'échec de la détection. La détection de promotion reste réservée au mode manuel (`promo_selector`) faute de standard schema.org fiable pour le prix barré — en mode auto, une baisse de prix est déjà couverte par l'alerte `alert_price_drop_pct` existante.

## 14. Limites connues et évolutions prévues

- Watcher `trend` (Google Trends) : schéma prêt, pipeline non câblé.
- Isolation par API seulement (pas de Row-Level Security Postgres).
- Pas de refresh token / révocation de token.
- Granularité minimale du scheduling : 1h (le DAG tourne `@hourly`) — suffisant pour prix/tendances, à revoir si un besoin infra-horaire apparaît.
- Comparaison multi-concurrents par produit + suggestion de prix optimal (identifié comme prochaine étape à plus fort impact).
- Terraform, Prometheus/Grafana, Great Expectations : toujours pertinents, non abordés dans cette itération.
