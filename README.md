# api8inf349 - Projet partie 2

## Exigences couvertes
- PostgreSQL via variables d'environnement `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `DB_NAME`
- Redis via `REDIS_URL`
- Support d'une commande multi-produits avec rétrocompatibilité pour `product`
- Cache Redis pour les commandes payées
- Paiement asynchrone avec RQ (`flask worker`)
- Dockerfile à la racine
- docker-compose.yml avec PostgreSQL 12 et Redis 5
- Interface HTML minimale avec Jinja2
## pour lactivation de la l'environnement virtuel il faut dans le cmd  :
.venv\Scripts\activate
## Installation locale des bibliotheques 
 pip install -r requirements.txt

## Démarrer les dépendances
```bash
docker compose up -d
```
### CMD
```cmd
set FLASK_APP=api8inf349
set FLASK_DEBUG=True
set REDIS_URL=redis://localhost:6379/0
set DB_HOST=localhost
set DB_USER=user
set DB_PASSWORD=pass
set DB_PORT=5432
set DB_NAME=api8inf349
```

## Initialiser la base
```bash
python -m flask init-db
```

## Lancer l'application
```bash
python -m flask run
```

## pour le  Lancement du  le worker  localement , on fait :
Dans un autre terminal(cmd):
  .venv\Scripts\activate
  ## Apres on lances les commandes suivantes :
  set FLASK_APP=api8inf349
set FLASK_DEBUG=True
set REDIS_URL=redis://localhost:6379/0
set DB_HOST=localhost
set DB_USER=user
set DB_PASSWORD=pass
set DB_PORT=5432
set DB_NAME=api8inf349

## apres on fini avec cette commande qui permet de lancer le worker localement aussi: 
python -m flask worker

## Exemple création d'une commande multi-produits
```json
{
  "products": [
    {"id": 1, "quantity": 2},
    {"id": 2, "quantity": 1}
  ]
}
```

## Exemple mise à jour des informations client
```json
{
  "order": {
    "email": "jgnault@uqac.ca",
    "shipping_information": {
      "country": "Canada",
      "address": "201, rue Président-Kennedy",
      "postal_code": "H2X 3Y7",
      "city": "Chicoutimi",
      "province": "QC"
    }
  }
}
```

## Exemple paiement
```json
{
  "credit_card": {
    "name": "John Doe",
    "number": "4242 4242 4242 4242",
    "expiration_year": 2030,
    "expiration_month": 9,
    "cvv": "123"
  }
}
```
