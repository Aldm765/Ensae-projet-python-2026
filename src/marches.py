
"""Chargement, contrôle qualité et analyse descriptive des marchés."""

import numpy as np
import pandas as pd
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from src.commun import MARCHES, charger_prix

DEBUT_ETUDE = "2000-01-01"
FIN_ETUDE = "2025-12-31"


def charger_tous_marches(telecharger=False):
    """Charge les données OHLC des quatre marchés sur la période d'étude.

    Conserve la fenêtre fin 1999 (depuis DEBUT de commun.py) dans les données
    brutes pour calculer les moyennes glissantes dès janvier 2000, puis renvoie
    un dictionnaire {nom_marche: DataFrame}.
    """
    return {marche: charger_prix(marche, telecharger=telecharger) for marche in MARCHES}


def controler_donnees(donnees):
    """Contrôle les dates, les trous de cotation et les séances plates (high == low).

    Paramètres
    ----------
    donnees : dict[str, pd.DataFrame]
        Dictionnaire des prix renvoyé par charger_tous_marches().

    Renvoie
    -------
    pd.DataFrame
        Tableau récapitulatif des contrôles par marché sur 2000-2025.
    """
    lignes = []
    jours_ouvres_theoriques = pd.bdate_range(start=DEBUT_ETUDE, end=FIN_ETUDE)

    for marche, df in donnees.items():
        sous_df = df.loc[DEBUT_ETUDE:FIN_ETUDE]
        trous = jours_ouvres_theoriques.difference(sous_df.index)
        seances_plates = int((sous_df["high"] == sous_df["low"]).sum())
        seances_invalides = int((sous_df["high"] < sous_df["low"]).sum())

        lignes.append({
            "marche": marche,
            "debut": sous_df.index.min().strftime("%Y-%m-%d"),
            "fin": sous_df.index.max().strftime("%Y-%m-%d"),
            "nb_seances": len(sous_df),
            "trous_jours_ouvres": len(trous),
            "seances_high_egal_low": seances_plates,
            "seances_high_inf_low": seances_invalides,
        })

    return pd.DataFrame(lignes).set_index("marche")


def calculer_volatilites(prix):
    """Calcule les volatilités journalières de Parkinson et de Garman-Klass.

    Paramètres
    ----------
    prix : pd.DataFrame
        DataFrame contenant open, high, low, close.

    Renvoie
    -------
    pd.DataFrame
        Colonnes 'parkinson' et 'garman_klass' (écarts-types journaliers,
        avec NaN sur les séances plates où high == low).
    """
    valide = prix["high"] > prix["low"]
    ln_hl = np.log(prix["high"] / prix["low"]).where(valide)
    ln_co = np.log(prix["close"] / prix["open"]).where(valide)

    var_parkinson = (ln_hl ** 2) / (4 * np.log(2))
    var_gk = 0.5 * (ln_hl ** 2) - (2 * np.log(2) - 1) * (ln_co ** 2)
    var_gk = var_gk.where(var_gk >= 0)

    return pd.DataFrame({
        "parkinson": np.sqrt(var_parkinson),
        "garman_klass": np.sqrt(var_gk),
    })


def statistiques_descriptives(donnees):
    """Calcule les statistiques des rendements, les queues et la comparaison P / GK.

    Paramètres
    ----------
    donnees : dict[str, pd.DataFrame]
        Dictionnaire des prix renvoyé par charger_tous_marches().

    Renvoie
    -------
    tuple[pd.DataFrame, dict[str, pd.DataFrame]]
        - Tableau récapitulatif par indice (moyenne, écart-type, queues,
          plus forte baisse/hausse, volatilités moyennes Parkinson et Garman-Klass,
          corrélation P / GK).
        - Dictionnaire {marche: top 5 des plus grosses variations absolues}.
    """
    lignes = []
    extremes = {}

    for marche, df in donnees.items():
        sous_df = df.loc[DEBUT_ETUDE:FIN_ETUDE]
        rendements = np.log(sous_df["close"] / sous_df["close"].shift(1)).dropna()
        vols = calculer_volatilites(sous_df)

        idx_min = rendements.idxmin()
        idx_max = rendements.idxmax()

        lignes.append({
            "marche": marche,
            "rendement_moyen_pct": round(rendements.mean() * 100, 4),
            "ecart_type_pct": round(rendements.std() * 100, 3),
            "skewness": round(rendements.skew(), 2),
            "kurtosis": round(rendements.kurt(), 2),
            "q01_pct": round(rendements.quantile(0.01) * 100, 2),
            "q99_pct": round(rendements.quantile(0.99) * 100, 2),
            "pire_journee": f"{rendements.loc[idx_min] * 100:.2f}% ({idx_min.strftime('%Y-%m-%d')})",
            "meilleure_journee": f"{rendements.loc[idx_max] * 100:+.2f}% ({idx_max.strftime('%Y-%m-%d')})",
            "vol_parkinson_moy_pct": round(vols["parkinson"].mean() * 100, 3),
            "vol_gk_moy_pct": round(vols["garman_klass"].mean() * 100, 3),
            "corr_parkinson_gk": round(vols["parkinson"].corr(vols["garman_klass"]), 4),
        })

        top5 = rendements.reindex(rendements.abs().nlargest(5).index)
        extremes[marche] = pd.DataFrame({
            "rendement_pct": (top5 * 100).round(2),
            "vol_parkinson_pct": (vols.loc[top5.index, "parkinson"] * 100).round(2),
        })

    return pd.DataFrame(lignes).set_index("marche"), extremes


CRIS_PERIODES = [
    ("2008-09-01", "2009-03-31", "Crise financière\n(2008-2009)"),
    ("2020-02-01", "2020-04-30", "Covid-19\n(2020)"),
    ("2022-01-01", "2022-12-31", "Resserrement\nmonétaire (2022)"),
]

SOUS_PERIODES_CORR = [
    ("2000-01-01", "2007-12-31", "2000–2007\n(Pré-crise)"),
    ("2008-09-01", "2009-03-31", "Sept. 2008–Mars 2009\n(Crise financière)"),
    ("2020-02-01", "2020-04-30", "Fév.–Avr. 2020\n(Covid-19)"),
    ("2022-01-01", "2022-12-31", "Année 2022\n(Hausse des taux)"),
]


def tracer_volatilites_crises(donnees, fenetre_lissage=20):
    """Trace la volatilité de Parkinson lissée (20j) des indices avec crises marquées."""
    indices_actions = ["SP500", "CAC40", "NIKKEI"]
    couleurs = {"SP500": "#1f77b4", "CAC40": "#ff7f0e", "NIKKEI": "#2ca02c"}

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]}
    )

    for marche in indices_actions:
        sous_df = donnees[marche].loc[DEBUT_ETUDE:FIN_ETUDE]
        vol_lissee = calculer_volatilites(sous_df)["parkinson"].rolling(fenetre_lissage).mean() * 100
        ax1.plot(vol_lissee.index, vol_lissee, label=marche, color=couleurs[marche], linewidth=1.1)

    vix_close = donnees["VIX"].loc[DEBUT_ETUDE:FIN_ETUDE, "close"]
    ax2.plot(vix_close.index, vix_close, color="#d62728", linewidth=1.0, label="VIX (clôture)")

    for debut, fin, etiquette in CRIS_PERIODES:
        d0, d1 = pd.to_datetime(debut), pd.to_datetime(fin)
        ax1.axvspan(d0, d1, color="grey", alpha=0.2)
        ax2.axvspan(d0, d1, color="grey", alpha=0.2)
        milieu = d0 + (d1 - d0) / 2
        ax1.text(
            milieu, ax1.get_ylim()[1] * 0.88, etiquette,
            ha="center", va="top", fontsize=8.5, fontweight="bold", color="#333333"
        )

    ax1.set_ylabel("Volatilité Parkinson 20j (%)")
    ax1.set_title("Volatilité réalisée (Parkinson, moyenne glissante 20j) et indice VIX (2000–2025)")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    ax2.set_ylabel("Niveau du VIX")
    ax2.set_xlabel("Date")
    ax2.legend(loc="upper left")
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_locator(mdates.YearLocator(2))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fig.tight_layout()
    return fig


def tracer_cartes_correlation(donnees):
    """Trace les matrices de corrélation des rendements log par sous-période."""
    indices = ["SP500", "CAC40", "NIKKEI", "VIX"]
    rendements = pd.DataFrame({
        m: np.log(donnees[m]["close"] / donnees[m]["close"].shift(1))
        for m in indices
    }).loc[DEBUT_ETUDE:FIN_ETUDE]

    fig, axes = plt.subplots(1, 4, figsize=(15, 4))

    for ax, (debut, fin, titre) in zip(axes, SOUS_PERIODES_CORR):
        corr = rendements.loc[debut:fin].corr()
        im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
        ax.set_xticks(range(len(indices)))
        ax.set_yticks(range(len(indices)))
        ax.set_xticklabels(indices, rotation=45, ha="right", fontsize=9)
        ax.set_yticklabels(indices, fontsize=9)
        ax.set_title(titre, fontsize=10)

        for i in range(len(indices)):
            for j in range(len(indices)):
                val = corr.values[i, j]
                couleur_texte = "white" if abs(val) > 0.55 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=couleur_texte, fontsize=8.5)

    fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.8, label="Corrélation (rendements log)")
    fig.suptitle("Corrélations contemporaines des rendements quotidiens par régime de marché", y=1.03)
    return fig


def analyse():
    """Point d'entrée standard : renvoie le tableau des statistiques descriptives."""
    donnees = charger_tous_marches(telecharger=False)
    stats, _ = statistiques_descriptives(donnees)
    return stats


def figure():
    """Point d'entrée standard : génère les deux figures de l'analyse descriptive."""
    donnees = charger_tous_marches(telecharger=False)
    fig_vol = tracer_volatilites_crises(donnees)
    fig_corr = tracer_cartes_correlation(donnees)
    return fig_vol, fig_corr