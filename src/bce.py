"""Effet des décisions de la BCE sur le CAC 40, le S&P 500 et le Nikkei."""
import time
from io import StringIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from matplotlib.lines import Line2D
from scipy.stats import mannwhitneyu

from src.commun import charger_prix, etude_evenement, volatilite_anormale

URL_BCE = "https://www.ecb.europa.eu/press/govcdec/mopo/{annee}/html/index_include.en.html"
URL_TAUX = "https://data-api.ecb.europa.eu/service/data/FM/B.U2.EUR.4F.KR.DFR.LEV"
ENTETES = {"User-Agent": "Mozilla/5.0"}

ANNEES = range(2000, 2026)
FICHIER_ANNONCES = Path(__file__).resolve().parents[1] / "data" / "annonces_bce.csv"

# La BCE publie à 13h45, puis à 14h15 depuis la réunion du 21 juillet 2022.
NOUVEL_HORAIRE = "2022-07-21"

# Réunions hors calendrier, avec leur heure quand elle est documentée.
URGENCES = {"2001-09-17": "15:30", "2008-10-08": None}

# Décisions qui baissent le taux principal sans toucher au taux de dépôt.
TAUX_PRINCIPAL_SEUL = ["2009-05-07", "2013-05-02", "2013-11-07"]

# lendemain=True si le marché est déjà fermé à l'heure de la décision.
# Paris est ouvert, New York ouvre à 15h30 (Paris), Tokyo a fermé le matin.
MARCHES_BCE = {"CAC40": False, "SP500": False, "NIKKEI": True}
NOMS = {"CAC40": "CAC 40", "SP500": "S&P 500", "NIKKEI": "Nikkei (séance suivante)"}

SEUIL = 0.05
BLEU, GRIS, TEXTE = "#2a78d6", "#b5b4ad", "#52514e"


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


def charger_annonces(telecharger=False):
    """Lit le calendrier sauvegardé. Avec telecharger=True, refait le scraping.

    Le rapport ne dépend ainsi pas de la disponibilité du site de la BCE.
    """
    if FICHIER_ANNONCES.exists() and not telecharger:
        return pd.read_csv(FICHIER_ANNONCES, parse_dates=["date"])
    return construire_annonces()


def analyse():
    """Renvoie l'effet des décisions : banque, marche, jour, ratio, p_value, n."""
    dates = charger_annonces()["date"]

    resultats = []
    for marche, lendemain in MARCHES_BCE.items():
        vol = volatilite_anormale(charger_prix(marche))
        effet = etude_evenement(vol, dates, lendemain=lendemain)
        resultats.append(effet.assign(banque="BCE", marche=marche))

    colonnes = ["banque", "marche", "jour", "ratio", "p_value", "n"]
    return pd.concat(resultats, ignore_index=True)[colonnes]


def figure(resultats=None):
    """Trace le ratio de volatilité de J-5 à J+5, un panneau par marché."""
    if resultats is None:
        resultats = analyse()

    fig, axes = plt.subplots(1, len(MARCHES_BCE), figsize=(11, 4), sharey=True)
    for ax, marche in zip(axes, MARCHES_BCE):
        effet = resultats[resultats["marche"] == marche]
        significatif = effet["p_value"] < SEUIL

        ax.axhline(1, color=GRIS, linewidth=1)
        ax.axvline(0, color=GRIS, linewidth=1, linestyle=":")
        ax.plot(effet["jour"], effet["ratio"], color=BLEU, linewidth=2, zorder=2)
        ax.scatter(effet.loc[significatif, "jour"], effet.loc[significatif, "ratio"],
                   s=48, color=BLEU, edgecolor="white", linewidth=1.5, zorder=3)
        ax.scatter(effet.loc[~significatif, "jour"], effet.loc[~significatif, "ratio"],
                   s=42, facecolor="white", edgecolor=BLEU, linewidth=1.5, zorder=3)

        ax.set_title(NOMS[marche], loc="left", fontsize=11, color=TEXTE)
        ax.set_xlabel("Séances autour de la décision", color=TEXTE)
        ax.set_xticks(range(-5, 6))
        ax.yaxis.set_major_formatter(lambda valeur, _: f"{valeur:.2f}".replace(".", ","))
        ax.tick_params(colors=TEXTE, length=0)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color(GRIS)

    axes[0].set_ylabel("Volatilité / jours témoins", color=TEXTE)
    fig.suptitle("Volatilité autour des décisions de la BCE, 2000-2025 (1,00 = aucun effet)",
                 x=0.01, ha="left", fontsize=13)
    legende = [Line2D([], [], marker="o", linestyle="", color=BLEU, label="p < 5 %"),
               Line2D([], [], marker="o", linestyle="", markerfacecolor="white",
                      markeredgecolor=BLEU, label="non significatif")]
    fig.legend(handles=legende, loc="upper right", ncol=2, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return fig


def seances_reaction(vol, dates, lendemain):
    """Renvoie la séance où le marché réagit à chaque date, sans doublon."""
    cote = "right" if lendemain else "left"
    position = vol.index.searchsorted(pd.DatetimeIndex(dates), side=cote)
    return vol.index[np.unique(position)]


def retirer_autres(vol, seances, autres):
    """Retire de vol les autres décisions et leurs voisines, pour des témoins propres."""
    position = vol.index.get_indexer(autres)
    voisins = np.unique(np.concatenate([position - 1, position, position + 1]))
    voisins = voisins[(voisins >= 0) & (voisins < len(vol))]
    return vol.drop(vol.index[voisins].difference(seances))


def controle_changement():
    """Compare le jour 0 des décisions avec et sans changement de taux.

    p_ecart teste directement la différence entre les deux groupes : un effet
    significatif dans un groupe et pas dans l'autre ne suffit pas à la prouver.
    """
    annonces = charger_annonces()
    a_change = (annonces["variation_taux"].ne(0)
                | annonces["date"].isin(pd.to_datetime(TAUX_PRINCIPAL_SEUL)))

    lignes = []
    for marche, lendemain in MARCHES_BCE.items():
        vol = volatilite_anormale(charger_prix(marche))
        avec = seances_reaction(vol, annonces.loc[a_change, "date"], lendemain)
        sans = seances_reaction(vol, annonces.loc[~a_change, "date"], lendemain).difference(avec)
        p_ecart = mannwhitneyu(vol.loc[avec], vol.loc[sans]).pvalue

        for groupe, seances, autres in [("avec changement", avec, sans),
                                        ("sans changement", sans, avec)]:
            effet = etude_evenement(retirer_autres(vol, seances, autres), seances)
            jour_0 = effet[effet["jour"] == 0].iloc[0]
            lignes.append({"banque": "BCE", "marche": marche, "groupe": groupe,
                           "ratio": jour_0["ratio"], "p_value": jour_0["p_value"],
                           "n": int(jour_0["n"]), "p_ecart": p_ecart})
    return pd.DataFrame(lignes)


if __name__ == "__main__":
    print(controle_changement().round(4).to_string(index=False))
