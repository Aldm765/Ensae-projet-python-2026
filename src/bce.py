"""Effet des décisions de la BCE sur le CAC 40, le S&P 500 et le Nikkei."""
import pandas as pd
import requests
from bs4 import BeautifulSoup

URL_BCE = "https://www.ecb.europa.eu/press/govcdec/mopo/{annee}/html/index_include.en.html"
ENTETES = {"User-Agent": "Mozilla/5.0"}


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