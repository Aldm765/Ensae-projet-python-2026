# Annonces des banques centrales et volatilité des marchés

Projet réalisé dans le cadre du cours *Python pour la data science* (ENSAE, 2026-2027).

## Problématique

Quand la Réserve fédérale américaine (Fed) ou la Banque centrale européenne (BCE) annoncent une décision de taux, la volatilité boursière monte-t-elle, et ce choc se transmet-il aux autres places financières ? Nous traitons trois questions :

1. **Effet local** : la volatilité d'un marché monte-t-elle autour des décisions de sa banque centrale, par rapport à des jours témoins ?
2. **Transmission** : le choc passe-t-il à l'Europe, à l'Asie ou aux États-Unis, et avec quel décalage ?
3. **Asymétrie** : la Fed pèse-t-elle plus sur l'Europe que la BCE sur les États-Unis ?

Marchés étudiés : S&P 500, CAC 40, Nikkei 225 et VIX, de 2000 à 2025.

## Données

| Source | Contenu | Accès |
|---|---|---|
| Yahoo Finance (`yfinance`) | Prix quotidiens (ouverture, plus haut, plus bas, clôture) des 4 indices | API non officielle |
| Site de la Fed | Dates des réunions du FOMC | Scraping |
| Site de la BCE | Dates des décisions de politique monétaire | Scraping |
| FRED (Fed de Saint-Louis) | Taux directeur de la Fed | API (clé gratuite) |
| ECB Data Portal | Taux de dépôt de la BCE | API |

Les prix (`data/raw/`) et les calendriers d'annonces (`data/annonces_fed.csv`, `data/annonces_bce.csv`) sont versionnés dans le dépôt : le rapport s'exécute sans accès à Internet et ne dépend pas de la disponibilité des sites.

**Limites connues :** le scraping dépend de la structure des sites, qui peut changer ; `yfinance` n'est pas une API officielle.

## Structure du dépôt

```
├── README.md
├── requirements.txt       # versions figées des packages
├── rapport.ipynb          # le rapport final
├── data/
│   ├── annonces_fed.csv   # 214 décisions de la Fed (207 prévues, 7 urgences)
│   ├── annonces_bce.csv   # 293 décisions de la BCE
│   └── raw/               # prix quotidiens : SP500, CAC40, NIKKEI, VIX
├── src/
│   ├── commun.py          # chargement des prix, volatilité anormale, étude d'événement
│   ├── marches.py         # statistiques descriptives et graphiques des marchés
│   ├── transmission.py    # corrélations décalées, correction de Forbes et Rigobon
│   ├── fed.py             # dates de la Fed et effet sur les marchés
│   ├── bce.py             # dates de la BCE, effet sur les marchés et contrôles
│   └── comparaison.py     # asymétrie Fed/BCE et contrôle des réunions proches
├── textes/                # textes du rapport, une partie par fichier
└── brouillons/            # notebooks d'exploration, un par partie
```

## Reproduire le projet

Il faut **Python 3.12 ou plus**, exigé par la version de `numpy` figée dans `requirements.txt`.

Sur le SSP Cloud (service VSCode-python) :

```bash
git clone https://github.com/Aldm765/Ensae-projet-python-2026.git
cd Ensae-projet-python-2026
pip install -r requirements.txt
```

Puis ouvrir `rapport.ipynb` et lancer **Restart**, puis **Run All**. Aucune clé d'API n'est nécessaire, car le rapport lit les données versionnées.

Pour refaire la collecte complète (optionnel) :

- dates de la BCE : `bce.construire_annonces()` ;
- dates de la Fed : `fed.construire_annonces()`, qui demande une clé FRED dans un fichier `.env` à la racine (`FRED_API_KEY=votre_clé`, gratuite sur fred.stlouisfed.org). Ce fichier n'est jamais publié ;
- prix : `charger_prix(marche, telecharger=True)` dans `src/commun.py`.

## Utilisation de l'IA

Un assistant IA a été utilisé pour expliquer les concepts (Git, API, scraping), relire le code et aider à l'écrire. Chaque fonction a été relue, testée et comprise par l'équipe.

## Auteurs

- Alexandre Lim de Montgolfier
- Romain Mirat
- Albéric Pungier
