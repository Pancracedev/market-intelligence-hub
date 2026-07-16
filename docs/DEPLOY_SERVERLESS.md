# Déploiement gratuit sans serveur (Neon + Cloudflare R2 + GitLab CI + Vercel + Render)

Alternative à [docs/DEPLOY.md](DEPLOY.md) (VM Oracle Cloud) pour qui préfère ne
gérer aucun serveur : chaque brique de la stack est remplacée par un service
managé gratuit à vie, sans carte bancaire à vérifier ni risque
d'endormissement d'un composant critique. Tout est piloté depuis votre dépôt
**GitLab** existant.

| Composant docker-compose | Remplacement | Gratuit ? |
|---|---|---|
| MinIO | [Cloudflare R2](https://developers.cloudflare.com/r2/) | 10 Go de stockage, à vie |
| Postgres (`app-db`) | [Neon](https://neon.tech) | 1 projet Postgres serverless, à vie |
| Airflow (scheduler) | Pipelines programmés GitLab CI/CD | Déjà inclus dans votre dépôt GitLab |
| Frontend Next.js | [Vercel](https://vercel.com) | À vie, pensé pour Next.js |
| API FastAPI | [Render](https://render.com) (web service *free*) | À vie (s'endort après inactivité, acceptable ici car appelée par un navigateur, pas par le scheduler) |

Airflow, Airflow-Postgres et MinIO du `docker-compose.yml` local ne sont donc
**pas déployés du tout** dans ce scénario — ils restent utiles uniquement pour
le développement local (`make up`).

## 1. Cloudflare R2 (remplace MinIO)

1. Créez un compte sur [dash.cloudflare.com](https://dash.cloudflare.com) (gratuit).
2. **R2 → Create bucket**, créez-en un seul (ex: `market-intelligence-hub`) — les trois
   zones bronze/silver/gold sont déjà des préfixes de clé dans le code, pas des buckets
   séparés, donc un seul bucket suffit. Notez son nom.
3. **R2 → Manage API tokens → Create API token** avec permission *Object Read & Write*
   sur ce bucket. Notez l'**Access Key ID** et la **Secret Access Key** (affichée une
   seule fois).
4. Notez votre **Account ID** Cloudflare (visible dans l'URL du dashboard ou la page R2).

Variables à renseigner (dans Render et dans les variables CI/CD GitLab — jamais commitées) :

```
MINIO_ENDPOINT=<account_id>.r2.cloudflarestorage.com
MINIO_SECURE=true
MINIO_ROOT_USER=<Access Key ID>
MINIO_ROOT_PASSWORD=<Secret Access Key>
MINIO_BUCKET_BRONZE=market-intelligence-hub
MINIO_BUCKET_SILVER=market-intelligence-hub
MINIO_BUCKET_GOLD=market-intelligence-hub
STORAGE_REGION=auto
```

## 2. Neon (remplace le Postgres applicatif)

1. Créez un compte sur [neon.tech](https://neon.tech) (gratuit, sans carte).
2. **Create a project** — Neon crée une base par défaut et vous donne une chaîne de
   connexion du type `postgresql://user:password@ep-xxx.eu-central-1.aws.neon.tech/dbname`.
3. Exécutez le schéma une fois, depuis votre machine, contre cette base :

```bash
psql "postgresql://user:password@ep-xxx.eu-central-1.aws.neon.tech/dbname?sslmode=require" \
  -f infra/postgres/init.sql
```

4. Reportez les morceaux de cette chaîne dans les variables :

```
APP_DB_USER=<user>
APP_DB_PASSWORD=<password>
APP_DB_HOST=ep-xxx.eu-central-1.aws.neon.tech
APP_DB_PORT=5432
APP_DB_NAME=<dbname>
APP_DB_SSLMODE=require
```

## 3. GitLab CI/CD — pipelines programmés (remplace Airflow)

Le fichier [.gitlab-ci.yml](../.gitlab-ci.yml) contient déjà deux jobs `run-watchers`
et `run-digest`, qui n'agissent que lorsqu'ils sont déclenchés par un **pipeline
programmé** (`Build → Pipeline schedules` dans GitLab). Un seul schedule horaire
suffit pour les deux — pas besoin de variable spécifique au schedule (l'interface/API
GitLab pour ça s'est révélée peu fiable en pratique) : `run-watchers` traite de toute
façon uniquement les watchers dont c'est l'heure (via leur propre champ `schedule`),
et `run-digest` vérifie lui-même s'il est lundi 6h UTC avant de faire quoi que ce soit.

1. **Settings → CI/CD → Variables** : ajoutez toutes les variables listées aux
   sections 1 et 2 ci-dessus, plus `GROQ_API_KEY` (et `ANTHROPIC_API_KEY` si vous
   l'utilisez), `SMTP_*` si vous voulez les emails. Cochez *Protect variable* si vos
   pipelines tournent uniquement sur `main`.
2. **Build → Pipeline schedules → New schedule** — un seul suffit :
   Description `hourly`, cron `0 * * * *` (toutes les heures), branche `main`.
3. Testez immédiatement avec le bouton *Run pipeline schedule* (icône ▶) pour
   vérifier que `run-watchers` s'exécute sans attendre le cron.

## 4. Vercel (frontend)

1. Sur [vercel.com](https://vercel.com), **Add New → Project**, importez le dépôt
   GitLab (Vercel supporte GitLab nativement, comme GitHub).
2. **Root Directory** : `frontend` (le projet Next.js n'est pas à la racine du dépôt).
3. **Environment Variables** : ajoutez `NEXT_PUBLIC_API_BASE_URL` = l'URL de votre API
   Render une fois créée (étape suivante), ex. `https://market-intelligence-hub-api.onrender.com`.
   Next.js l'inline au build — Vercel rebuild automatiquement à chaque push sur `main`,
   donc modifier cette variable puis relancer un déploiement suffit.
4. Deploy. Vercel vous donne une URL `https://votre-projet.vercel.app` (domaine
   personnalisé possible ensuite, gratuit aussi).

## 5. Render (API)

1. Sur [render.com](https://render.com), **New → Blueprint**, connectez le dépôt
   GitLab — Render détecte automatiquement [render.yaml](../render.yaml) à la racine.
2. Render crée le service web à partir de `api/Dockerfile`. Avant le premier déploiement,
   remplissez dans l'onglet **Environment** toutes les variables marquées `sync: false`
   dans `render.yaml` (celles des sections 1 et 2, plus `JWT_SECRET_KEY` — générez une
   valeur aléatoire avec `openssl rand -hex 32` — et `CORS_ORIGINS` = l'URL Vercel du
   frontend, ex. `https://votre-projet.vercel.app`).
3. Deploy. Render vous donne une URL `https://market-intelligence-hub-api.onrender.com`.
4. Repassez sur Vercel pour renseigner `NEXT_PUBLIC_API_BASE_URL` avec cette URL exacte
   si ce n'était pas encore fait, puis redéployez le frontend.

Le plan *free* de Render met le service en veille après 15 minutes sans requête ;
la requête suivante le réveille en quelques secondes (cold start), ce qui est
acceptable pour une API consultée depuis un navigateur — contrairement à un
scheduler, qui doit tourner à l'heure prévue sans dépendre d'un visiteur pour se
réveiller (c'est pour ça que `run-watchers`/`run-digest` passent par GitLab CI et
non par ce service).

## 6. Vérification bout-en-bout

1. Ouvrez l'URL Vercel, créez un compte, ajoutez un watcher `price`.
2. Déclenchez manuellement le schedule `watchers` (bouton ▶ dans GitLab) et vérifiez
   dans les logs du job qu'il traite bien ce watcher (`watcher <id>: ok`).
3. Rechargez la page du produit dans le frontend : le point de données doit apparaître.
4. Déclenchez manuellement le schedule `digest` et vérifiez la réception de l'email
   (ou l'apparition d'un résumé sur `/digests`).

## Récapitulatif

Aucune carte bancaire à vérifier (Neon, R2, Vercel, Render et GitLab
n'en demandent pas pour ces paliers gratuits), aucun serveur à surveiller,
aucune limite de temps sur ces paliers gratuits — seulement des limites de
volume (10 Go R2, plafond de calcul Neon, minutes CI GitLab) largement
suffisantes pour un usage personnel ou une petite équipe.
