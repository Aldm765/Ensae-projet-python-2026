# Annonces des banques centrales et volatilité des marchés

Projet réalisé dans le cadre du cours *Python pour la data science* (ENSAE, 2026-2027).

## Problématique

Les annonces de politique monétaire de la Réserve fédérale américaine (Fed) et de la
Banque centrale européenne (BCE) font-elles monter la volatilité boursière ? Et si oui,
ce choc se transmet-il aux autres marchés : actions étrangères, taux obligataires, change ?

Nous comparons la volatilité des marchés autour des jours d'annonce à celle des jours
ordinaires, puis nous regardons si un choc né sur un marché (ex. annonce de la Fed sur
les actions américaines) se propage aux autres (actions européennes et asiatiques,
taux, euro-dollar).

## Données

| Source | Contenu | Méthode d'accès |
|---|---|---|
| Site de la Fed (federalreserve.gov) | Dates des réunions et annonces du FOMC | Scraping |
| Site de la BCE (ecb.europa.eu) | Dates des décisions de politique monétaire | Scraping |
| ECB Data Portal | Taux directeurs de la BCE | API |
| FRED (Fed de Saint-Louis) | Taux directeur de la Fed, VIX, taux à 10 ans américains, EUR/USD | API (clé gratuite) |
| Yahoo Finance (package `yfinance`) | Cours quotidiens : S&P 500, Euro Stoxx 50, CAC 40, Nikkei 225, VIX | API non officielle |

Les données ne sont pas stockées dans ce dépôt : elles sont téléchargées par le code.
Une copie des données brutes est conservée sur l'espace de stockage S3 du SSP Cloud,
et le petit tableau des dates d'annonce (`data/annonces.csv`) est versionné ici,
afin que le projet reste reproductible même si une source change.

**Limites connues :** le scraping dépend de la structure des sites, qui peut changer ;
`yfinance` n'est pas une API officielle.

## Structure du dépôt

```
├── README.md            # ce fichier
├── requirements.txt     # packages Python nécessaires
├── rapport.ipynb        # rapport final
├── data/
│   └── annonces.csv     # dates des annonces Fed et BCE (copie de secours)
└── src/
    ├── collecte.py      # cours des marchés (yfinance, FRED)
    ├── nettoyage.py     # rendements et volatilité
    ├── fed.py           # annonces de la Fed et effet sur les marchés américains
    ├── bce.py           # annonces de la BCE et effet sur les marchés européens
    ├── transmission.py  # transmission du choc entre marchés
    └── visualisation.py # fonctions graphiques communes
```

## Reproduire le projet

Sur le SSP Cloud (service VSCode-python) :

```bash
git clone https://github.com/Aldm765/Ensae-projet-python-2026.git
cd Ensae-projet-python-2026
pip install -r requirements.txt
```

Créer un fichier `.env` à la racine contenant votre clé FRED (gratuite sur
fred.stlouisfed.org) :

```
FRED_API_KEY=Votre clé 
```

Puis exécuter `rapport.ipynb` de la première à la dernière cellule.

## Utilisation de l'IA

Un assistant IA a été utilisé pour expliquer les concepts (Git, API, scraping)
et aider à écrire le code. Chaque fonction a été relue, testée et comprise
par l'équipe.

## Auteurs

- Alexandre Lim de Montgolfier
- Romain Mirat
- Albéric Pungier 