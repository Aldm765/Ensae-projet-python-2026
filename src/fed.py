"""Tâche B : les décisions de la Fed et leur effet sur les marchés.

1. Collecte des dates de réunion du FOMC (scraping du site de la Fed, 2000-2025)
2. Taux directeur de la Fed (API FRED) pour connaître le sens de chaque décision
3. Analyse : étude d'événement sur le S&P 500, le CAC 40 et le Nikkei
"""
import re
import time
from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
from dotenv import find_dotenv, load_dotenv
import matplotlib.pyplot as plt
from src.commun import charger_prix, etude_evenement, volatilite_anormale

# Chemins et adresses
RACINE = Path(__file__).resolve().parents[1]
FICHIER = RACINE / "data" / "annonces_fed.csv"
URL_RECENTE = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
URL_ARCHIVE = "https://www.federalreserve.gov/monetarypolicy/fomchistorical{annee}.htm"
ENTETES = {"User-Agent": "Mozilla/5.0 (projet etudiant ENSAE)"}

# Numéro de chaque mois à partir de ses 3 premières lettres (en anglais)
MOIS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}

# La Fed annonce vers 20h (heure de Paris) : le S&P 500 réagit le jour même,
# le CAC 40 et le Nikkei, déjà fermés, réagissent le lendemain.
REACTION = {"SP500": False, "CAC40": True, "NIKKEI": True}

UN_JOUR = pd.Timedelta(days=1)


# ---------- 1. Collecte des dates ----------

def heure_paris(date, heure_ny):
    """Convertit une heure de New York en heure de Paris."""
    moment = pd.Timestamp(str(date.date()) + " " + heure_ny)
    moment = moment.tz_localize("America/New_York")
    moment = moment.tz_convert("Europe/Paris")
    return moment.strftime("%H:%M")


def date_decision(annee, mois_txt, jours_txt):
    """Renvoie le dernier jour de la réunion, qui est le jour de l'annonce."""
    # "Apr/May" -> on garde le dernier mois, "May"
    dernier_mois = mois_txt.split("/")[-1]
    numero_mois = MOIS[dernier_mois.strip()[:3].lower()]

    # "17-18*" -> on garde le dernier nombre, 18
    nombres = re.findall(r"\d+", jours_txt)
    dernier_jour = int(nombres[-1])

    return pd.Timestamp(annee, numero_mois, dernier_jour)


def dates_fomc_recentes(debut=2021, fin=2025):
    """Récupère les dates de décision sur la page actuelle du FOMC (2021-2025)."""
    page = requests.get(URL_RECENTE, headers=ENTETES, timeout=30)
    page.raise_for_status()
    soup = BeautifulSoup(page.text, "lxml")

    lignes = []
    for titre in soup.find_all("h4"):
        trouve = re.search(r"(\d{4}) FOMC Meetings", titre.get_text())
        if trouve is None:
            continue
        annee = int(trouve.group(1))
        if annee < debut or annee > fin:
            continue

        panneau = titre.find_parent(class_="panel")
        for mois in panneau.find_all(class_="fomc-meeting__month"):
            case_jours = mois.find_next_sibling(class_="fomc-meeting__date")
            texte_jours = case_jours.get_text(" ", strip=True)

            # Le "notation vote" n'est pas une décision de taux : on l'ignore
            if "notation vote" in texte_jours.lower():
                continue

            date = date_decision(annee, mois.get_text(strip=True), texte_jours)
            lignes.append({"date": date,
                           "banque": "Fed",
                           "heure_paris": heure_paris(date, "14:00"),
                           "type": "prevue"})
    return pd.DataFrame(lignes)


def lire_titre(titre):
    """Lit un titre d'archive, par exemple "March 15 (unscheduled) Meeting - 2020".

    Renvoie (date, type), ou None si la réunion doit être exclue.
    """
    texte = titre.lower()

    # Réunions annulées et votes par écrit : pas de décision de taux
    if "cancelled" in texte or "notation vote" in texte:
        return None
    if "meeting" not in texte and "conference call" not in texte:
        return None

    # L'année est à la fin du titre
    annee = int(re.search(r"(\d{4})\s*$", titre).group(1))

    # On garde la partie avant " - 2020" et on enlève ce qui est entre parenthèses
    partie = titre.split(" - ")[0]
    partie = re.sub(r"\(.*?\)", "", partie)

    # On cherche les mots qui sont des mois et on garde le dernier
    mois_trouves = []
    for mot in re.findall(r"[A-Za-z]+", partie):
        if mot[:3].lower() in MOIS:
            mois_trouves.append(mot)
    numero_mois = MOIS[mois_trouves[-1][:3].lower()]

    # Le jour de l'annonce est le dernier nombre
    jour = int(re.findall(r"\d+", partie)[-1])
    date = pd.Timestamp(annee, numero_mois, jour)

    if "unscheduled" in texte or "conference call" in texte:
        genre = "urgence"
    else:
        genre = "prevue"
    return date, genre


def dates_fomc_archives(debut=2000, fin=2020):
    """Récupère les dates de décision sur les pages d'archives (une page par année)."""
    lignes = []
    for annee in range(debut, fin + 1):
        page = requests.get(URL_ARCHIVE.format(annee=annee), headers=ENTETES, timeout=30)
        page.raise_for_status()
        soup = BeautifulSoup(page.text, "lxml")

        for balise in soup.find_all(["h3", "h4", "h5", "h6"]):
            titre = balise.get_text(" ", strip=True)

            # Les titres de réunion se terminent par "- 2020", "- 2019", etc.
            if not re.search(r"- \d{4}$", titre):
                continue

            resultat = lire_titre(titre)
            if resultat is None:
                continue
            date, genre = resultat

            # Avant 2013 la Fed publiait vers 14h15 (New York), ensuite à 14h.
            # Pour les urgences, l'heure varie : on la laisse vide.
            if genre == "prevue":
                if annee < 2013:
                    heure_ny = "14:15"
                else:
                    heure_ny = "14:00"
                heure = heure_paris(date, heure_ny)
            else:
                heure = None

            lignes.append({"date": date, "banque": "Fed",
                           "heure_paris": heure, "type": genre})

        # Une seconde de pause entre deux pages, pour ne pas surcharger le site
        time.sleep(1)

    archives = pd.DataFrame(lignes)
    archives = archives.drop_duplicates("date")
    return archives


def retirer_doublons(annonces, ecart_max=2):
    """Si deux réunions prévues sont à 2 jours ou moins d'écart, on garde la dernière.

    Exemple : septembre 2003 apparaît le 15 et le 16, on garde le 16.
    """
    prevues = annonces[annonces["type"] == "prevue"].sort_values("date")
    dates = list(prevues["date"])
    index = list(prevues.index)

    a_retirer = []
    for i in range(len(dates) - 1):
        ecart = dates[i + 1] - dates[i]
        if ecart.days <= ecart_max:
            a_retirer.append(index[i])

    return annonces.drop(a_retirer)


# ---------- 2. Taux directeur (API FRED) ----------

def serie_fred(code, debut="1999-01-01", fin="2025-12-31"):
    """Télécharge une série quotidienne de FRED. La clé est lue dans le fichier .env."""
    load_dotenv(find_dotenv(usecwd=True))
    cle = os.getenv("FRED_API_KEY")

    parametres = {"series_id": code,
                  "api_key": cle,
                  "file_type": "json",
                  "observation_start": debut,
                  "observation_end": fin}
    reponse = requests.get("https://api.stlouisfed.org/fred/series/observations",
                           params=parametres, timeout=30)
    reponse.raise_for_status()

    observations = pd.DataFrame(reponse.json()["observations"])
    # FRED écrit "." quand il n'y a pas de valeur : on transforme en case vide
    valeurs = pd.to_numeric(observations["value"], errors="coerce")
    valeurs.index = pd.to_datetime(observations["date"])
    return valeurs.dropna()


def taux_directeur():
    """Taux cible unique jusqu'au 15/12/2008, puis borne haute de la fourchette."""
    ancien = serie_fred("DFEDTAR", fin="2008-12-15")
    nouveau = serie_fred("DFEDTARU", debut="2008-12-16")
    return pd.concat([ancien, nouveau])


def variation(date, taux):
    """Variation du taux entre la veille et le lendemain de l'annonce."""
    taux_avant = taux.asof(date - UN_JOUR)
    taux_apres = taux.asof(date + UN_JOUR)
    return round(taux_apres - taux_avant, 2)


def date_changement(date, taux, fenetre=2):
    """Pour une urgence : premier jour (dans les 2 jours) où le taux change.

    Renvoie (jour, variation), ou None si le taux n'a pas bougé.
    """
    taux_avant = taux.asof(date - UN_JOUR)
    for k in range(fenetre + 1):
        jour = date + k * UN_JOUR
        taux_du_jour = taux.asof(jour)
        if taux_du_jour != taux_avant:
            return jour, round(taux_du_jour - taux_avant, 2)
    return None


def construire_annonces():
    """Refait toute la collecte et réécrit data/annonces_fed.csv (environ 1 minute)."""
    archives = dates_fomc_archives()
    recentes = dates_fomc_recentes()
    toutes = pd.concat([archives, recentes], ignore_index=True)
    toutes = retirer_doublons(toutes)
    taux = taux_directeur()

    # Réunions prévues : on calcule la variation du taux
    prevues = toutes[toutes["type"] == "prevue"].copy()
    variations = []
    for date in prevues["date"]:
        variations.append(variation(date, taux))
    prevues["variation_taux"] = variations

    # Urgences : on ne garde que celles où le taux a vraiment changé,
    # et on les date au jour du changement
    lignes_urgences = []
    urgences = toutes[toutes["type"] == "urgence"]
    for _, urgence in urgences.iterrows():
        resultat = date_changement(urgence["date"], taux)
        if resultat is None:
            continue
        jour, var = resultat
        ligne = urgence.to_dict()
        ligne["date"] = jour
        ligne["variation_taux"] = var
        lignes_urgences.append(ligne)
    urgences_gardees = pd.DataFrame(lignes_urgences)

    annonces = pd.concat([prevues, urgences_gardees], ignore_index=True)
    annonces = annonces.sort_values("date")
    annonces = annonces.reset_index(drop=True)
    annonces["date"] = annonces["date"].dt.date
    annonces.to_csv(FICHIER, index=False)
    return annonces


# ---------- 3. Analyse ----------

def charger_annonces():
    """Lit data/annonces_fed.csv (versionné dans le dépôt, donc toujours disponible)."""
    annonces = pd.read_csv(FICHIER, parse_dates=["date"])
    return annonces


def analyse():
    """Étude d'événement autour des réunions prévues de la Fed, sur les trois marchés.

    Renvoie un tableau avec les colonnes : banque, marche, jour, ratio, p_value, n.
    """
    annonces = charger_annonces()
    dates_prevues = annonces[annonces["type"] == "prevue"]["date"]

    resultats = []
    for marche in REACTION:
        lendemain = REACTION[marche]
        prix = charger_prix(marche)
        vol = volatilite_anormale(prix)
        res = etude_evenement(vol, dates_prevues, lendemain=lendemain)
        res["banque"] = "Fed"
        res["marche"] = marche
        resultats.append(res)

    tableau = pd.concat(resultats, ignore_index=True)
    tableau = tableau[["banque", "marche", "jour", "ratio", "p_value", "n"]]
    return tableau


def figure(resultats=None):
    """Graphique de la volatilité de J-5 à J+5 autour des décisions de la Fed."""
    if resultats is None:
        resultats = analyse()

    fig, ax = plt.subplots(figsize=(8, 4))
    for marche in REACTION:
        donnees = resultats[resultats["marche"] == marche]
        ax.plot(donnees["jour"], donnees["ratio"], marker="o", label=marche)

    ax.axhline(1, color="grey", linestyle="--")   # niveau d'un jour normal
    ax.axvline(0, color="grey", linestyle=":")    # jour de réaction
    ax.set_xlabel("Jours par rapport au jour de réaction")
    ax.set_ylabel("Volatilité / jours témoins")
    ax.set_title("Volatilité autour des décisions de la Fed (2000-2025)")
    ax.legend()
    return fig


def analyse_urgences():
    """Même étude d'événement, mais sur les décisions d'urgence (7 dates).

    Les urgences sont souvent annoncées le matin à New York : le S&P 500 et le
    CAC 40 réagissent le jour même, le Nikkei (déjà fermé) le lendemain.
    """
    annonces = charger_annonces()
    dates_urgences = annonces[annonces["type"] == "urgence"]["date"]
    reaction_urgence = {"SP500": False, "CAC40": False, "NIKKEI": True}

    resultats = []
    for marche in reaction_urgence:
        lendemain = reaction_urgence[marche]
        prix = charger_prix(marche)
        vol = volatilite_anormale(prix)
        res = etude_evenement(vol, dates_urgences, lendemain=lendemain)
        res["banque"] = "Fed"
        res["marche"] = marche
        resultats.append(res)

    tableau = pd.concat(resultats, ignore_index=True)
    tableau = tableau[["banque", "marche", "jour", "ratio", "p_value", "n"]]
    return tableau