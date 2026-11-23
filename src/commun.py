"""Socle commun : prix, volatilité et étude d'événement.

Ce fichier est figé. Pour le modifier, prévenir les deux autres membres.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import mannwhitneyu

DEBUT, FIN = "1999-10-01", "2026-01-01"
MARCHES = {"SP500": "^GSPC", "CAC40": "^FCHI", "NIKKEI": "^N225", "VIX": "^VIX"}
DOSSIER = Path(__file__).resolve().parents[1] / "data" / "raw"
URL_S3 = None  # à remplir, par exemple "https://.../{marche}.csv"


def charger_prix(marche, telecharger=False):
    """Renvoie open, high, low, close d'un marché, indexés par date.

    Lit d'abord la copie locale, puis S3. Avec telecharger=True, ou si aucune
    copie n'existe, télécharge depuis Yahoo et sauvegarde dans data/raw/.
    """
    fichier = DOSSIER / f"{marche}.csv"
    if fichier.exists() and not telecharger:
        return pd.read_csv(fichier, index_col="date", parse_dates=True)
    if URL_S3 and not telecharger:
        return pd.read_csv(URL_S3.format(marche=marche), index_col="date", parse_dates=True)
    brut = yf.download(MARCHES[marche], start=DEBUT, end=FIN, progress=False, auto_adjust=False)
    brut.columns = brut.columns.get_level_values(0).str.lower()
    prix = brut[["open", "high", "low", "close"]].dropna().rename_axis("date")
    DOSSIER.mkdir(parents=True, exist_ok=True)
    prix.to_csv(fichier)
    return prix


def volatilite_anormale(prix, fenetre=20):
    """Log de Parkinson du jour moins sa moyenne sur les séances précédentes."""
    ecart = np.log(prix["high"] / prix["low"]).where(prix["high"] > prix["low"])
    log_vol = np.log(np.sqrt(ecart**2 / (4 * np.log(2))))
    return (log_vol - log_vol.shift(1).rolling(fenetre, min_periods=15).mean()).dropna()


def etude_evenement(vol, dates, lendemain=False, avant=5, apres=5):
    """Compare la volatilité autour des annonces à des jours témoins.

    lendemain=True quand le marché est déjà fermé à l'heure de l'annonce : le
    jour 0 devient alors sa première séance après la date. Les témoins sont les
    mêmes jours de la semaine, hors annonce à une séance près.
    Renvoie une ligne par jour : jour, ratio, p_value, n.
    """
    cote = "right" if lendemain else "left"
    pos = vol.index.searchsorted(pd.DatetimeIndex(dates), side=cote)
    pos = np.unique(pos[(pos >= avant) & (pos < len(vol) - apres)])
    exclus = np.unique(np.concatenate([pos - 1, pos, pos + 1]))
    temoins = vol.drop(vol.index[exclus])

    moyenne_jour = temoins.groupby(temoins.index.dayofweek).mean()
    ecart_temoins = temoins - temoins.index.dayofweek.map(moyenne_jour).to_numpy()

    lignes = []
    for jour in range(-avant, apres + 1):
        obs = vol.iloc[pos + jour]
        ecart = obs - obs.index.dayofweek.map(moyenne_jour).to_numpy()
        lignes.append({"jour": jour, "ratio": np.exp(ecart.mean()),
                       "p_value": mannwhitneyu(ecart, ecart_temoins).pvalue, "n": len(obs)})
    return pd.DataFrame(lignes)
