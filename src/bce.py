"""Effet des décisions de la BCE sur le CAC 40, le S&P 500 et le Nikkei."""
import time
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL_BCE = "https://www.ecb.europa.eu/press/govcdec/mopo/{annee}/html/index_include.en.html"
URL_TAUX = "https://data-api.ecb.europa.eu/service/data/FM/B.U2.EUR.4F.KR.DFR.LEV"
ENTETES = {"User-Agent": "Mozilla/5.0"}

ANNEES = range(2000, 2026)
FICHIER_ANNONCES = Path(__file__).resolve().parents[1] / "data" / "annonces_bce.csv"

# La BCE publie à 13h45, puis à 14h15 depuis la réunion du 21 juillet 2022.
NOUVEL_HORAIRE = "2022-07-21"

# Réunions hors calendrier, avec leur heure quand elle est documentée.
URGENCES = {"2001-09-17": "15:30", "2008-10-08": None}


def scraper_annee(annee):
    """Renvoie les communiqués de politique monétaire d'une année : date, titre."""
    reponse = requests.get(URL_BCE.format(annee=annee), headers=ENTETES, timeout=30)
    reponse.raise_for_status()
    soupe = BeautifulSoup(reponse.text, "lxml")

    lignes = []
    for balise_date in soupe.find_all("dt"):
        bloc = balise_date.find_next_sibling("dd")
        titre = bloc.find("div", class_="title").get_text(strip=True)
        lignes.append({"date": balise_date["isodate"], "titre": titre})

    resultat = pd.DataFrame(lignes)
    resultat["date"] = pd.to_datetime(resultat["date"])
    return resultat.sort_values("date").reset_index(drop=True)


def scraper_decisions(annees=ANNEES):
    """Renvoie les dates des décisions de politique monétaire, une ligne par date.

    Une page mêle décisions, déclarations et comptes rendus, et peut contenir
    des lignes de l'année suivante : on filtre donc sur le titre et sur l'année.
    """
    pages = []
    for annee in annees:
        page = scraper_annee(annee)
        pages.append(page[page["date"].dt.year == annee])
        time.sleep(0.3)

    communiques = pd.concat(pages, ignore_index=True)
    est_decision = communiques["titre"].str.contains("monetary policy decisions", case=False)
    dates = communiques.loc[est_decision, ["date"]].drop_duplicates()
    return dates.sort_values("date").reset_index(drop=True)


def charger_taux_depot():
    """Renvoie le taux de dépôt de la BCE, indexé par date d'entrée en vigueur."""
    parametres = {"format": "csvdata", "startPeriod": "1999-01-01", "endPeriod": "2025-12-31"}
    reponse = requests.get(URL_TAUX, params=parametres, headers=ENTETES, timeout=30)
    reponse.raise_for_status()

    taux = pd.read_csv(StringIO(reponse.text), usecols=["TIME_PERIOD", "OBS_VALUE"])
    taux.columns = ["date", "taux"]
    taux["date"] = pd.to_datetime(taux["date"])
    return taux.set_index("date").sort_index()["taux"]


def ajouter_variation(decisions, taux):
    """Ajoute variation_taux, en points de pourcentage, à chaque décision.

    L'API date un changement à son entrée en vigueur, souvent quelques jours
    après la décision : on l'attribue à la dernière décision qui le précède.
    Si une décision en porte deux, on garde le premier. Le 8 octobre 2008, le
    taux baisse de 0,50 puis remonte le 9 par resserrement du corridor : la
    somme ferait disparaître la baisse d'urgence.
    """
    variations = taux.diff().dropna()
    variations = variations[(variations != 0) & (variations.index >= decisions["date"].min())]

    position = decisions["date"].searchsorted(variations.index, side="right") - 1
    changements = pd.DataFrame({"date": decisions["date"].to_numpy()[position],
                                "variation_taux": variations.to_numpy()})
    changements = changements.drop_duplicates("date", keep="first")

    resultat = decisions.merge(changements, on="date", how="left")
    resultat["variation_taux"] = resultat["variation_taux"].fillna(0).round(2)
    return resultat


def construire_annonces():
    """Construit le calendrier des décisions et le sauvegarde dans data/."""
    annonces = ajouter_variation(scraper_decisions(), charger_taux_depot())
    annonces["banque"] = "BCE"
    annonces["type"] = "prevue"
    annonces["heure_paris"] = "13:45"
    annonces.loc[annonces["date"] >= NOUVEL_HORAIRE, "heure_paris"] = "14:15"

    for date, heure in URGENCES.items():
        annonces.loc[annonces["date"] == date, ["type", "heure_paris"]] = ["urgence", heure]

    annonces = annonces[["date", "banque", "heure_paris", "type", "variation_taux"]]
    FICHIER_ANNONCES.parent.mkdir(parents=True, exist_ok=True)
    annonces.to_csv(FICHIER_ANNONCES, index=False, date_format="%Y-%m-%d")
    return annonces


if __name__ == "__main__":
    print(construire_annonces())
