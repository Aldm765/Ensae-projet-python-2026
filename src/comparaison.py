"""Comparaison de la Fed et de la BCE : réunions proches et asymétrie."""
import numpy as np
import pandas as pd

from src import bce, fed
from src.commun import charger_prix, etude_evenement, volatilite_anormale

# Jour de réaction de chaque marché, pour chaque banque
REACTIONS = {"Fed": fed.REACTION, "BCE": bce.MARCHES_BCE}


def dates_banques():
    """Renvoie les dates des réunions prévues de la Fed et des décisions de la BCE."""
    annonces_fed = fed.charger_annonces()
    dates_fed = annonces_fed.loc[annonces_fed["type"] == "prevue", "date"]
    dates_bce = bce.charger_annonces()["date"]
    return {"Fed": dates_fed, "BCE": dates_bce}


def hors_proches(dates, autres, ecart=1):
    """Garde les dates à plus de `ecart` jours de toute date de `autres`."""
    gardees = []
    for date in dates:
        distance_minimale = (autres - date).abs().min()
        if distance_minimale > pd.Timedelta(days=ecart):
            gardees.append(date)
    return pd.Series(gardees)


def preparer(banque, marche, dates):
    """Renvoie la volatilité sans les autres annonces et les séances étudiées."""
    autre_banque = "BCE" if banque == "Fed" else "Fed"
    lendemain = REACTIONS[banque][marche]
    lendemain_autre = REACTIONS[autre_banque][marche]
    vol = volatilite_anormale(charger_prix(marche))

    # Les séances étudiées : les annonces éloignées de l'autre banque
    gardees = hors_proches(dates[banque], dates[autre_banque])
    seances = bce.seances_reaction(vol, gardees, lendemain)

    # Toutes les autres annonces sont retirées des jours témoins
    seances_banque = bce.seances_reaction(vol, dates[banque], lendemain)
    seances_autre = bce.seances_reaction(vol, dates[autre_banque], lendemain_autre)
    a_retirer = seances_banque.union(seances_autre).difference(seances)

    vol_propre = bce.retirer_autres(vol, seances, a_retirer)
    return vol_propre, seances


def controle_reunions_proches():
    """Refait le jour 0 sans les réunions à un jour d'une décision de l'autre banque."""
    dates = dates_banques()

    lignes = []
    for banque, reaction in REACTIONS.items():
        for marche in reaction:
            vol, seances = preparer(banque, marche, dates)
            jour_0 = bce.effet_jour_0(vol, seances)
            lignes.append({"banque": banque, "marche": marche, "ratio": jour_0["ratio"],
                           "p_value": jour_0["p_value"], "n": int(jour_0["n"])})
    return pd.DataFrame(lignes)


def ecarts_jour_0(vol, seances):
    """Renvoie l'écart de chaque annonce aux témoins du même jour de la semaine."""
    exclus = set()
    for date in seances:
        position = vol.index.get_loc(date)
        for voisin in [position - 1, position, position + 1]:
            if 0 <= voisin < len(vol):
                exclus.add(vol.index[voisin])

    temoins = vol.drop(list(exclus))
    moyenne_jour = temoins.groupby(temoins.index.dayofweek).mean()

    obs = vol.loc[seances]
    return obs - obs.index.dayofweek.map(moyenne_jour).to_numpy()


def analyse_asymetrie():
    """Compare l'effet de la Fed sur le CAC 40 et celui de la BCE sur le S&P 500.

    rapport > 1 : la Fed pèse plus sur Paris que la BCE sur New York.
    L'intervalle de confiance à 95 % utilise l'approximation normale.
    """
    dates = dates_banques()

    vol_cac, seances_fed = preparer("Fed", "CAC40", dates)
    fed_vers_cac = ecarts_jour_0(vol_cac, seances_fed)

    vol_sp, seances_bce = preparer("BCE", "SP500", dates)
    bce_vers_sp = ecarts_jour_0(vol_sp, seances_bce)

    # Écart entre les deux effets moyens, et son erreur standard
    ecart = fed_vers_cac.mean() - bce_vers_sp.mean()
    variance_fed = fed_vers_cac.var() / len(fed_vers_cac)
    variance_bce = bce_vers_sp.var() / len(bce_vers_sp)
    erreur = np.sqrt(variance_fed + variance_bce)

    return pd.DataFrame([{"fed_vers_cac40": np.exp(fed_vers_cac.mean()),
                          "bce_vers_sp500": np.exp(bce_vers_sp.mean()),
                          "rapport": np.exp(ecart),
                          "ic95_bas": np.exp(ecart - 1.96 * erreur),
                          "ic95_haut": np.exp(ecart + 1.96 * erreur),
                          "n_fed": len(fed_vers_cac),
                          "n_bce": len(bce_vers_sp)}])
