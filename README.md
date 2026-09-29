# Evaluation DevOps — ESIEA

![CI](https://github.com/thesnake94/evaluation-devops/actions/workflows/ci.yml/badge.svg)

Projet réalisé dans le cadre de l'évaluation DevOps ESIEA.

L'objectif est de mettre en œuvre un pipeline complet :

- application HTTP Python / Flask ;
- tests automatisés ;
- intégration continue avec GitHub Actions ;
- conteneurisation Docker ;
- Docker Compose ;
- publication d'images sur GitHub Container Registry ;
- déploiement continu ;
- healthcheck et rollback ;
- instrumentation Prometheus ;
- règles d'alerting.

---

## Architecture

L'application repose sur les services suivants :

- `web` : application Flask ;
- `redis` : stockage du compteur de visites ;
- `prometheus` : collecte des métriques applicatives.

Flux simplifié :

```text
Utilisateur
    |
    v
Flask :5000
    |
    +------> Redis :6379
    |
    +------> /metrics
                 |
                 v
          Prometheus :9090
```

---

## Endpoints

### Accueil

```text
GET /
```

Retourne les informations principales du service.

### Healthcheck

```text
GET /health
```

Réponse attendue :

```json
{
  "status": "ok"
}
```

Cet endpoint est utilisé par Docker et par le pipeline de déploiement.

### Status

```text
GET /status
```

Affiche l'état du service ainsi que la version ou le SHA déployé.

### Visits

```text
GET /visits
```

Incrémente un compteur stocké dans Redis.

Cet endpoint permet notamment de vérifier que l'application communique réellement avec Redis.

### Metrics

```text
GET /metrics
```

Expose les métriques au format Prometheus.

### Simulation d'erreur

```text
GET /simulate-error
```

Retourne volontairement un code HTTP 500 afin de tester l'alerte de taux d'erreurs.

### Simulation de latence

```text
GET /simulate-latency
```

Introduit volontairement une latence afin de tester l'alerte p95.

---

## Lancement local avec Docker Compose

### Prérequis

- Docker
- Docker Compose

### Démarrer le projet

```bash
docker compose up -d --build
```

### Vérifier les services

```bash
docker compose ps
```

Les services `web` et `redis` doivent apparaître healthy.

### Tester l'application

```bash
curl http://localhost:5000/
curl http://localhost:5000/health
curl http://localhost:5000/status
curl http://localhost:5000/visits
```

### Arrêter les services

```bash
docker compose down
```

---

## Développement local Python

Créer un environnement virtuel :

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Installer les dépendances :

```bash
pip install -r requirements-dev.txt
```

Démarrer Redis :

```bash
docker compose up -d redis
```

Exécuter les tests :

```bash
python3 -m pytest -v
```

Exécuter les tests avec couverture :

```bash
python3 -m pytest --cov=app --cov-report=term
```

Exécuter le lint Python :

```bash
python3 -m flake8 app.py test_app.py --max-line-length=100
```

---

## Docker

Le Dockerfile utilise :

- `python:3.12-slim` ;
- un build multi-stage ;
- un utilisateur non-root `appuser` ;
- un `HEALTHCHECK` basé sur `/health` ;
- un `.dockerignore`.

Construction manuelle :

```bash
docker build -t evaluation-devops:1.0 .
```

Vérification de l'utilisateur :

```bash
docker run --rm evaluation-devops:1.0 id
```

Le résultat ne doit pas contenir :

```text
uid=0(root)
```

---

## CI — GitHub Actions

Le workflow :

```text
.github/workflows/ci.yml
```

est déclenché sur :

- push vers `main` ;
- pull request vers `main`.

La CI comprend :

- lint Python ;
- lint YAML ;
- tests Python 3.11 ;
- tests Python 3.12 ;
- Redis comme service GitHub Actions ;
- cache des dépendances pip ;
- rapport JUnit ;
- couverture de code ;
- publication des rapports comme artifacts ;
- construction de l'image Docker ;
- job final `CI OK`.

Les tests utilisent réellement Redis via le endpoint `/visits`.

Le check `CI OK` est utilisé comme contrôle final du pipeline.

---

## Action GitHub locale réutilisable

Le projet contient une action locale :

```text
.github/actions/setup-python/action.yml
```

Elle réalise notamment :

- l'installation de la version Python demandée ;
- la gestion du cache pip ;
- l'installation des dépendances du projet.

Elle est appelée par les workflows afin d'éviter de dupliquer cette logique.

---

## CD — GitHub Actions

Le workflow :

```text
.github/workflows/cd.yml
```

est exécuté après une CI réussie sur `main`.

Il peut également être lancé manuellement grâce à :

```text
workflow_dispatch
```

avec l'environnement :

```text
production
```

Le pipeline utilise :

```text
GITHUB_TOKEN
```

avec des permissions explicites :

```text
contents: read
packages: write
```

---

## GitHub Container Registry

Les images sont publiées sur :

```text
ghcr.io/thesnake94/evaluation-devops
```

Trois tags sont produits :

```text
latest
<SHA court>
v1.0.0
```

Le SHA permet d'identifier précisément l'image correspondant à un commit.

---

## Déploiement

Le déploiement utilise un runner GitHub-hosted :

```text
runs-on: ubuntu-latest
```

Dans le cadre de cet atelier, le runner GitHub Actions joue le rôle d'environnement cible simplifié.

Le runner étant éphémère, l'environnement déployé existe pendant la durée du job GitHub Actions.

Le job de déploiement :

1. récupère l'image depuis GHCR ;
2. démarre Redis ;
3. démarre l'application ;
4. effectue jusqu'à trois vérifications sur `/health` ;
5. effectue un smoke test utilisant Redis ;
6. considère le déploiement comme réussi si les vérifications passent.

---

## Rollback

En cas d'échec du healthcheck, le script :

```text
deploy/deploy.sh
```

récupère le SHA du commit précédent.

Il tente ensuite de récupérer l'image correspondante depuis GHCR et de redémarrer cette version.

Même lorsqu'un rollback réussit, le job initial reste en échec afin de signaler que le nouveau déploiement n'a pas fonctionné.

---

## Métriques Prometheus

L'application expose :

```text
/metrics
```

### Nombre de requêtes

```text
http_requests_total
```

Labels :

```text
endpoint
code
```

Exemple :

```text
http_requests_total{endpoint="/health",code="200"}
```

### Latence

```text
http_request_duration_seconds
```

Cette métrique est un histogramme et permet notamment de calculer le p95 et le p99.

### Version déployée

```text
app_deployed_version
```

Exemple :

```text
app_deployed_version{version="abcdef1"} 1
```

---

## Prometheus

Interface :

```text
http://localhost:9090
```

Vérifier les cibles :

```bash
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool
```

Le job :

```text
flask-app
```

doit être :

```text
up
```

---

## Requêtes PromQL

Nombre de requêtes par seconde et par endpoint :

```promql
sum by (endpoint) (
  rate(http_requests_total[1m])
)
```

Taux de réponses HTTP 5xx :

```promql
sum(rate(http_requests_total{code=~"5.."}[1m]))
/
sum(rate(http_requests_total[1m]))
```

Latence p95 :

```promql
histogram_quantile(
  0.95,
  sum by (le, endpoint) (
    rate(http_request_duration_seconds_bucket[1m])
  )
)
```

---

## Alerting

Les règles se trouvent dans :

```text
observability/alert_rules.yml
```

### TauxErreurEleve

Condition :

```text
plus de 5 % de réponses HTTP 5xx pendant 30 secondes
```

Cette durée permet d'éviter de déclencher une alerte sur un pic très bref.

### LatenceP95Elevee

Condition :

```text
p95 supérieur à 500 ms pendant 30 secondes
```

---

## Tester l'alerte 5xx

Générer du trafic :

```bash
for i in $(seq 1 45); do
    curl -s http://localhost:5000/health > /dev/null
    curl -s http://localhost:5000/simulate-error > /dev/null
    sleep 1
done
```

Vérifier les alertes :

```bash
curl -s http://localhost:9090/api/v1/alerts | python3 -m json.tool
```

L'alerte doit passer par :

```text
pending
```

puis :

```text
firing
```

---

## Tester l'alerte de latence

```bash
for i in $(seq 1 40); do
    curl -s http://localhost:5000/simulate-latency > /dev/null
done
```

Puis :

```bash
curl -s http://localhost:9090/api/v1/alerts | python3 -m json.tool
```

L'alerte :

```text
LatenceP95Elevee
```

doit également atteindre l'état :

```text
firing
```

---

## Structure du dépôt

```text
evaluation-devops/
├── .github/
│   ├── actions/
│   │   └── setup-python/
│   │       └── action.yml
│   └── workflows/
│       ├── ci.yml
│       └── cd.yml
│
├── deploy/
│   └── deploy.sh
│
├── observability/
│   ├── prometheus.yml
│   └── alert_rules.yml
│
├── app.py
├── test_app.py
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── .yamllint.yml
└── README.md
```

---

## Sécurité

Le projet applique notamment les principes suivants :

- aucun secret stocké dans le dépôt ;
- `.env` exclu par `.gitignore` ;
- `.git` et `.env` exclus de l'image Docker ;
- application Docker exécutée par un utilisateur non-root ;
- utilisation de `GITHUB_TOKEN` ;
- permissions GitHub Actions explicites ;
- aucune valeur sensible affichée volontairement dans les logs.

---

## Technologies

- Python
- Flask
- Redis
- pytest
- flake8
- Docker
- Docker Compose
- GitHub Actions
- GitHub Container Registry
- Prometheus
