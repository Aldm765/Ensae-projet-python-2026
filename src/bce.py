"""Effet des décisions de la BCE sur le CAC 40, le S&P 500 et le Nikkei."""
import time
from io import StringIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
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


# ---------- 1. Collecte des décisions ----------

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
    variations = variations[variations != 0]

    variation_par_decision = {}
    for date_effet, variation in variations.items():
        decisions_avant = decisions[decisions["date"] <= date_effet]
        if decisions_avant.empty:
            continue
        derniere_decision = decisions_avant["date"].max()
        if derniere_decision not in variation_par_decision:
            variation_par_decision[derniere_decision] = variation

    resultat = decisions.copy()
    resultat["variation_taux"] = resultat["date"].map(variation_par_decision)
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


# ---------- 2. Analyse et figure ----------

def analyse():
    """Renvoie l'effet des décisions : banque, marche, jour, ratio, p_value, n."""
    dates = charger_annonces()["date"]

    resultats = []
    for marche, lendemain in MARCHES_BCE.items():
        vol = volatilite_anormale(charger_prix(marche))
        effet = etude_evenement(vol, dates, lendemain=lendemain)
        effet["banque"] = "BCE"
        effet["marche"] = marche
        resultats.append(effet)

    tableau = pd.concat(resultats, ignore_index=True)
    return tableau[["banque", "marche", "jour", "ratio", "p_value", "n"]]


def figure(resultats=None):
    """Trace le ratio de volatilité de J-5 à J+5, un panneau par marché."""
    if resultats is None:
        resultats = analyse()

    fig, axes = plt.subplots(1, len(MARCHES_BCE), figsize=(11, 4), sharey=True)
    for ax, marche in zip(axes, MARCHES_BCE):
        effet = resultats[resultats["marche"] == marche]
        significatif = effet[effet["p_value"] < SEUIL]
        non_significatif = effet[effet["p_value"] >= SEUIL]

        ax.axhline(1, color=GRIS, linewidth=1)
        ax.axvline(0, color=GRIS, linewidth=1, linestyle=":")
        ax.plot(effet["jour"], effet["ratio"], color=BLEU, linewidth=2)
        ax.scatter(significatif["jour"], significatif["ratio"], s=48, color=BLEU,
                   label="p < 5 %", zorder=3)
        ax.scatter(non_significatif["jour"], non_significatif["ratio"], s=42,
                   facecolor="white", edgecolor=BLEU, label="non significatif", zorder=3)

        ax.set_title(NOMS[marche], loc="left", fontsize=11, color=TEXTE)
        ax.set_xlabel("Séances autour de la décision", color=TEXTE)
        ax.set_xticks(range(-5, 6))
        ax.spines[["top", "right"]].set_visible(False)

    axes[0].set_ylabel("Volatilité / jours témoins", color=TEXTE)
    axes[0].legend(frameon=False, loc="upper right")
    fig.suptitle("Volatilité autour des décisions de la BCE, 2000-2025 (1 = aucun effet)",
                 x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    return fig


# ---------- 3. Contrôles ----------

def seances_reaction(vol, dates, lendemain):
    """Renvoie la séance où le marché réagit à chaque date, sans doublon."""
    cote = "right" if lendemain else "left"
    positions = set()
    for date in pd.DatetimeIndex(dates):
        positions.add(vol.index.searchsorted(date, side=cote))
    return vol.index[sorted(positions)]


def retirer_autres(vol, seances, autres):
    """Retire de vol les autres décisions et leurs voisines, pour des témoins propres."""
    a_retirer = set()
    for date in autres:
        position = vol.index.get_loc(date)
        for voisin in [position - 1, position, position + 1]:
            if 0 <= voisin < len(vol):
                a_retirer.add(vol.index[voisin])

    # On garde les séances étudiées, même si elles sont voisines d'une autre décision
    a_retirer = a_retirer - set(seances)
    return vol.drop(list(a_retirer))


def effet_jour_0(vol, dates, lendemain=False):
    """Renvoie la ligne du jour 0 de l'étude d'événement."""
    effet = etude_evenement(vol, dates, lendemain=lendemain)
    return effet[effet["jour"] == 0].iloc[0]


def controle_changement():
    """Compare le jour 0 des décisions avec et sans changement de taux.

    p_ecart teste directement la différence entre les deux groupes : un effet
    significatif dans un groupe et pas dans l'autre ne suffit pas à la prouver.
    """
    annonces = charger_annonces()
    taux_depot_change = annonces["variation_taux"] != 0
    taux_principal_change = annonces["date"].isin(pd.to_datetime(TAUX_PRINCIPAL_SEUL))
    a_change = taux_depot_change | taux_principal_change

    lignes = []
    for marche, lendemain in MARCHES_BCE.items():
        vol = volatilite_anormale(charger_prix(marche))
        avec = seances_reaction(vol, annonces.loc[a_change, "date"], lendemain)
        sans = seances_reaction(vol, annonces.loc[~a_change, "date"], lendemain)
        sans = sans.difference(avec)
        p_ecart = mannwhitneyu(vol.loc[avec], vol.loc[sans]).pvalue

        groupes = [("avec changement", avec, sans), ("sans changement", sans, avec)]
        for groupe, seances, autres in groupes:
            jour_0 = effet_jour_0(retirer_autres(vol, seances, autres), seances)
            lignes.append({"banque": "BCE", "marche": marche, "groupe": groupe,
                           "ratio": jour_0["ratio"], "p_value": jour_0["p_value"],
                           "n": int(jour_0["n"]), "p_ecart": p_ecart})
    return pd.DataFrame(lignes)


def controle_2002():
    """Refait le jour 0 sans les réunions bimensuelles de 2000 et 2001.

    Ces réunions restent exclues des jours témoins.
    """
    annonces = charger_annonces()
    gardees = annonces.loc[annonces["date"].dt.year >= 2002, "date"]

    lignes = []
    for marche, lendemain in MARCHES_BCE.items():
        vol = volatilite_anormale(charger_prix(marche))
        seances = seances_reaction(vol, gardees, lendemain)
        autres = seances_reaction(vol, annonces["date"], lendemain).difference(seances)
        jour_0 = effet_jour_0(retirer_autres(vol, seances, autres), seances)
        lignes.append({"banque": "BCE", "marche": marche, "ratio": jour_0["ratio"],
                       "p_value": jour_0["p_value"], "n": int(jour_0["n"])})
    return pd.DataFrame(lignes)


def volatilite_garman_klass(prix, fenetre=20):
    """Même calcul que volatilite_anormale, avec la variance de Garman-Klass.

    Cette mesure utilise aussi l'ouverture et la clôture, en plus de l'amplitude.
    """
    amplitude = np.log(prix["high"] / prix["low"])
    rendement = np.log(prix["close"] / prix["open"])
    variance = 0.5 * amplitude ** 2 - (2 * np.log(2) - 1) * rendement ** 2
    variance = variance.where(variance > 0)

    log_vol = np.log(np.sqrt(variance))
    moyenne_passee = log_vol.shift(1).rolling(fenetre, min_periods=15).mean()
    return (log_vol - moyenne_passee).dropna()


def controle_garman_klass():
    """Refait le jour 0 avec Garman-Klass à la place de Parkinson."""
    dates = charger_annonces()["date"]

    lignes = []
    for marche, lendemain in MARCHES_BCE.items():
        vol = volatilite_garman_klass(charger_prix(marche))
        jour_0 = effet_jour_0(vol, dates, lendemain=lendemain)
        lignes.append({"banque": "BCE", "marche": marche, "ratio": jour_0["ratio"],
                       "p_value": jour_0["p_value"], "n": int(jour_0["n"])})
    return pd.DataFrame(lignes)


if __name__ == "__main__":
    print(controle_changement().round(4).to_string(index=False))
    print()
    print(controle_2002().round(4).to_string(index=False))
    print()
    print(controle_garman_klass().round(4).to_string(index=False))
