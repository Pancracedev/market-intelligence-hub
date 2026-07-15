# Déploiement en production (gratuit) — Oracle Cloud Always Free

Ce guide déploie la stack complète (Airflow, Postgres, MinIO, API, frontend, Caddy)
sur une VM Oracle Cloud "Always Free" — gratuite en permanence, pas seulement un
essai limité dans le temps.

## 1. Créer le compte et la VM

1. Inscrivez-vous sur [oracle.com/cloud/free](https://www.oracle.com/cloud/free/).
   Une carte bancaire est demandée pour vérifier votre identité, mais **elle n'est
   jamais débitée** pour les ressources "Always Free" — restez dans les limites
   décrites ci-dessous et ça ne coûtera rien.
2. **Région "home"** : choisissez **France Central (Marseille) — `eu-marseille-1`**.
   Les régions populaires (Paris, Frankfurt, Londres) manquent régulièrement de
   capacité ARM Ampere gratuite ; Marseille en a nettement plus souvent de
   disponible. Ce choix est définitif (impossible à changer après coup), donc
   vérifiez-le avant de valider l'inscription.
3. Une fois le compte actif : **Compute → Instances → Create Instance**.
4. **Change shape** → onglet **Ampere** → `VM.Standard.A1.Flex` → réglez au
   maximum gratuit : **4 OCPU / 24 GB RAM**.
5. **Image** : Ubuntu 22.04 (compatible ARM).
6. **Clé SSH** : collez votre clé publique existante (celle déjà utilisée pour
   GitHub/GitLab, ex. `~/.ssh/git_signing_key.pub`), ou laissez Oracle en générer
   une et téléchargez la clé privée.
7. **Create**. Notez l'**adresse IP publique** de l'instance une fois créée.

## 2. Ouvrir les ports réseau (80, 443, 22 uniquement)

Par défaut, Oracle bloque tout sauf le port 22 (SSH). Dans **VCN → Security
Lists** (ou **Network Security Groups**) associée au sous-réseau de la VM,
ajoutez des règles d'entrée (*Ingress*) :

| Port | Source | Usage |
|---|---|---|
| 22 | votre IP (ou `0.0.0.0/0` si IP variable) | SSH |
| 80 | `0.0.0.0/0` | HTTP (redirection vers HTTPS par Caddy) |
| 443 | `0.0.0.0/0` | HTTPS |

Ne pas ouvrir 8000, 3000, 8080, 9000, 9001 : ces services restent internes,
accessibles uniquement via Caddy ou un tunnel SSH (voir section 7).

Ubuntu embarque aussi son propre firewall (`iptables`/`ufw`) — si actif,
autorisez les mêmes ports :

```bash
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
```

## 3. Se connecter et installer Docker

```bash
ssh -i ~/.ssh/votre_cle ubuntu@<IP_PUBLIQUE>

curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker   # ou déconnectez-vous / reconnectez-vous
docker compose version   # vérifie que le plugin Compose est bien inclus
```

## 4. Cloner le dépôt

```bash
git clone https://github.com/Pancracedev/market-intelligence-hub.git
# ou : git clone https://gitlab.com/devpancrace/market-intelligence-hub.git
cd market-intelligence-hub
```

## 5. Configurer `.env`

```bash
cp .env.example .env
nano .env
```

À adapter vous-même pour la production (aucun secret n'est pré-rempli, c'est
volontaire — remplissez-les directement sur la VM, jamais dans un fichier commité) :

- `JWT_SECRET_KEY`, `AIRFLOW__WEBSERVER__SECRET_KEY` : générez des valeurs
  aléatoires, ex. `openssl rand -hex 32`.
- `APP_DB_PASSWORD`, `AIRFLOW_DB_PASSWORD`, `MINIO_ROOT_PASSWORD` : changez les
  mots de passe par défaut.
- `SEED_DEMO_USER=false` : désactivez le compte de démo en production.
- `CORS_ORIGINS=https://app.VOTREDOMAINE.com`
- `NEXT_PUBLIC_API_BASE_URL=https://api.VOTREDOMAINE.com`
  (⚠️ cette valeur est figée dans le build du frontend — toute modification
  nécessite `docker compose build frontend` pour être prise en compte)
- `GROQ_API_KEY` (gratuit sur [console.groq.com](https://console.groq.com)) si
  vous voulez le résumé hebdomadaire par IA.
- `SMTP_*` si vous voulez les alertes email.

## 6. Domaine et DNS

Il vous faut un nom de domaine (même un sous-domaine gratuit fonctionne, ex. via
Freenom ou un domaine que vous possédez déjà). Créez deux enregistrements DNS de
type **A** pointant vers l'IP publique de la VM :

```
app.votredomaine.com  →  <IP_PUBLIQUE>
api.votredomaine.com  →  <IP_PUBLIQUE>
```

Puis éditez `deploy/Caddyfile` sur la VM pour remplacer `app.example.com` et
`api.example.com` par vos vrais sous-domaines.

## 7. Lancer la stack en production

```bash
make up-prod
```

Cela construit toutes les images (avec `NEXT_PUBLIC_API_BASE_URL` déjà pris en
compte via `.env`) et démarre tous les services, plus Caddy comme unique point
d'entrée public sur 80/443. Caddy obtient et renouvelle automatiquement un
certificat Let's Encrypt pour vos deux sous-domaines dès que le DNS est propagé.

Vérifiez :

```bash
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml ps
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml logs -f caddy
```

Puis ouvrez `https://app.votredomaine.com` dans un navigateur.

## 8. Accès admin (Airflow, MinIO) sans les exposer publiquement

Airflow et la console MinIO restent volontairement liés à `127.0.0.1` sur la VM
(non accessibles depuis Internet, y compris via Caddy). Pour y accéder
occasionnellement, ouvrez un tunnel SSH depuis votre machine :

```bash
ssh -L 8080:localhost:8080 -L 9001:localhost:9001 ubuntu@<IP_PUBLIQUE>
```

puis ouvrez `http://localhost:8080` (Airflow, `admin`/`admin` — **changez ce mot
de passe** via l'UI Airflow après le premier déploiement) ou
`http://localhost:9001` (MinIO) sur votre propre machine.

## 9. Mises à jour

```bash
git pull
make up-prod   # rebuild + redémarre les services modifiés
```

## Récapitulatif des coûts

Tout ce qui est utilisé ici entre dans les limites "Always Free" d'Oracle
Cloud : 4 OCPU / 24 GB ARM, 200 GB de stockage bloc, bande passante sortante
incluse. Aucune carte n'est débitée tant que vous ne dépassez pas ces
ressources ou n'activez pas manuellement des services payants ailleurs dans la
console Oracle.
