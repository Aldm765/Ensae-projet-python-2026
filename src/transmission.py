
"""Analyse de la transmission des chocs et des corrélations internationales."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src.marches import DEBUT_ETUDE, FIN_ETUDE, charger_tous_marches

PERIODES_CONTAGION = [
    ("2008-09-01", "2009-03-31", "Crise financière (2008-2009)"),
    ("2020-02-01", "2020-04-30", "Covid-19 (Fév.-Avr. 2020)"),
    ("2022-01-01", "2022-12-31", "Resserrement monétaire (2022)"),
]
PERIODE_CALME = ("2003-01-01", "2007-06-30")


def preparer_rendements(donnees):
    """Construit les séries alignées de rendements journaliers et overnight."""
    indices = ["SP500", "CAC40", "NIKKEI", "VIX"]
    r_close = pd.DataFrame({
        m: np.log(donnees[m]["close"] / donnees[m]["close"].shift(1))
        for m in indices
    })
    r_overnight = pd.DataFrame({
        m: np.log(donnees[m]["open"] / donnees[m]["close"].shift(1))
        for m in ["CAC40", "NIKKEI"]
    })
    return r_close.loc[DEBUT_ETUDE:FIN_ETUDE], r_overnight.loc[DEBUT_ETUDE:FIN_ETUDE]


def analyser_decalage_horaire(donnees):
    """Compare la transmission contemporaine (t) et décalée (t -> t+1) depuis le S&P 500."""
    r_close, r_overnight = preparer_rendements(donnees)
    sp_t = r_close["SP500"]
    sp_t_moins_1 = r_close["SP500"].shift(1)

    lignes = []
    for cible in ["CAC40", "NIKKEI"]:
        paire_meme_jour = pd.concat([sp_t, r_close[cible]], axis=1).dropna()
        paire_lendemain = pd.concat([sp_t_moins_1, r_close[cible]], axis=1).dropna()
        paire_overnight = pd.concat([sp_t_moins_1, r_overnight[cible]], axis=1).dropna()

        reg_close = stats.linregress(paire_lendemain.iloc[:, 0], paire_lendemain.iloc[:, 1])
        reg_open = stats.linregress(paire_overnight.iloc[:, 0], paire_overnight.iloc[:, 1])

        lignes.append({
            "marche_cible": cible,
            "corr_meme_jour_t": round(paire_meme_jour.iloc[:, 0].corr(paire_meme_jour.iloc[:, 1]), 4),
            "corr_lendemain_t1": round(reg_close.rvalue, 4),
            "beta_close_t1": round(reg_close.slope, 4),
            "p_val_close_t1": float(f"{reg_close.pvalue:.2e}"),
            "r2_close_t1_pct": round((reg_close.rvalue ** 2) * 100, 2),
            "beta_overnight_t1": round(reg_open.slope, 4),
            "r2_overnight_t1_pct": round((reg_open.rvalue ** 2) * 100, 2),
        })

    return pd.DataFrame(lignes).set_index("marche_cible")


def erreur_robuste(x, y, regression):
    """Écart-type de la pente, robuste à l'hétéroscédasticité (White, HC1)."""
    residus = y - regression.intercept - regression.slope * x
    ecart = x - x.mean()
    n = len(x)
    return np.sqrt(n / (n - 2) * (ecart ** 2 * residus ** 2).sum()) / (ecart ** 2).sum()


def tester_asymetrie_transmission(donnees):
    """Teste si les baisses du S&P 500 (t) se transmettent plus fort à t+1 que les hausses."""
    r_close, _ = preparer_rendements(donnees)
    sp_lag = r_close["SP500"].shift(1)

    lignes = []
    for cible in ["CAC40", "NIKKEI"]:
        df = pd.DataFrame({"sp": sp_lag, "y": r_close[cible]}).dropna()
        baisses = df[df["sp"] < 0]
        hausses = df[df["sp"] >= 0]

        reg_b = stats.linregress(baisses["sp"], baisses["y"])
        reg_h = stats.linregress(hausses["sp"], hausses["y"])

        # Test de différence des pentes, avec des erreurs robustes
        diff_beta = reg_b.slope - reg_h.slope
        se_b = erreur_robuste(baisses["sp"], baisses["y"], reg_b)
        se_h = erreur_robuste(hausses["sp"], hausses["y"], reg_h)
        se_diff = np.sqrt(se_b ** 2 + se_h ** 2)
        t_stat = diff_beta / se_diff
        ddl = len(df) - 4
        p_val_diff = 2 * (1 - stats.t.cdf(abs(t_stat), df=ddl))

        lignes.append({
            "marche_cible": cible,
            "beta_baisses": round(reg_b.slope, 4),
            "corr_baisses": round(reg_b.rvalue, 4),
            "beta_hausses": round(reg_h.slope, 4),
            "corr_hausses": round(reg_h.rvalue, 4),
            "ecart_beta_b_moins_h": round(diff_beta, 4),
            "t_stat_asymetrie": round(t_stat, 2),
            "p_valeur_asymetrie": round(p_val_diff, 4),
        })

    return pd.DataFrame(lignes).set_index("marche_cible")


def corriger_forbes_rigobon(donnees):
    """Calcule les corrélations brutes et corrigées du biais de volatilité (Forbes-Rigobon, 2002)."""
    r_close, _ = preparer_rendements(donnees)
    # On aligne SP500(t) avec CAC40(t) et NIKKEI(t+1) pour respecter la chronologie des clôtures
    series = pd.DataFrame({
        "SP500": r_close["SP500"],
        "CAC40": r_close["CAC40"],
        "NIKKEI_t1": r_close["NIKKEI"].shift(-1),
    })

    calme = series.loc[PERIODE_CALME[0]:PERIODE_CALME[1]]
    var_sp_calme = calme["SP500"].var()

    lignes = []
    for cible in ["CAC40", "NIKKEI_t1"]:
        corr_calme = calme["SP500"].corr(calme[cible])

        for debut, fin, nom_crise in PERIODES_CONTAGION:
            sous_crise = series.loc[debut:fin, ["SP500", cible]].dropna()
            rho_brute = sous_crise["SP500"].corr(sous_crise[cible])
            var_sp_crise = sous_crise["SP500"].var()
            delta = (var_sp_crise / var_sp_calme) - 1.0

            rho_corrigee = rho_brute / np.sqrt(1.0 + delta * (1.0 - rho_brute ** 2))

            lignes.append({
                "paire": f"SP500 -> {cible}",
                "periode_crise": nom_crise,
                "ratio_variance": round(var_sp_crise / var_sp_calme, 2),
                "corr_calme": round(corr_calme, 4),
                "corr_brute_crise": round(rho_brute, 4),
                "corr_forbes_rigobon": round(rho_corrigee, 4),
                "ecart_fr_vs_calme": round(rho_corrigee - corr_calme, 4),
            })

    return pd.DataFrame(lignes)


def tracer_transmission_et_forbes_rigobon(donnees):
    """Génère la figure synthétique de transmission asymétrique et correction Forbes-Rigobon."""
    r_close, _ = preparer_rendements(donnees)
    sp_lag = r_close["SP500"].shift(1) * 100
    df_fr = corriger_forbes_rigobon(donnees)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Panneau gauche : nuage de points asymétrique SP500(t) -> NIKKEI(t+1)
    paire = pd.DataFrame({"sp": sp_lag, "nk": r_close["NIKKEI"] * 100}).dropna()
    baisses = paire[paire["sp"] < 0]
    hausses = paire[paire["sp"] >= 0]

    ax1.scatter(baisses["sp"], baisses["nk"], alpha=0.18, s=10, color="#d62728", label="Séances SP500 < 0")
    ax1.scatter(hausses["sp"], hausses["nk"], alpha=0.18, s=10, color="#1f77b4", label="Séances SP500 >= 0")

    x_b = np.linspace(baisses["sp"].min(), 0, 50)
    reg_b = stats.linregress(baisses["sp"], baisses["nk"])
    ax1.plot(x_b, reg_b.intercept + reg_b.slope * x_b, color="#8c1515", linewidth=2,
             label=f"Pente baisses : {reg_b.slope:.2f}")

    x_h = np.linspace(0, hausses["sp"].max(), 50)
    reg_h = stats.linregress(hausses["sp"], hausses["nk"])
    ax1.plot(x_h, reg_h.intercept + reg_h.slope * x_h, color="#0b3c6d", linewidth=2,
             label=f"Pente hausses : {reg_h.slope:.2f}")

    ax1.axhline(0, color="grey", linewidth=0.7, linestyle="--")
    ax1.axvline(0, color="grey", linewidth=0.7, linestyle="--")
    ax1.set_xlabel("Rendement S&P 500 jour t (%)")
    ax1.set_ylabel("Rendement Nikkei 225 jour t+1 (%)")
    ax1.set_title("Transmission décalée (New York -> Tokyo)")
    ax1.legend(loc="upper left", fontsize=8.5)
    ax1.grid(True, alpha=0.3)

    # Panneau droit : comparaison corrélation brute vs Forbes-Rigobon
    etiquettes = [
        f"{row['paire'].replace('SP500 -> ', '')}\n({row['periode_crise'].split('(')[0].strip()})"
        for _, row in df_fr.iterrows()
    ]
    x = np.arange(len(df_fr))
    largeur = 0.27

    ax2.bar(x - largeur, df_fr["corr_calme"], width=largeur, label="Période calme (2003-2007)", color="#7f7f7f")
    ax2.bar(x, df_fr["corr_brute_crise"], width=largeur, label="Corrélation brute en crise", color="#ff7f0e")
    ax2.bar(x + largeur, df_fr["corr_forbes_rigobon"], width=largeur, label="Corrélation corrigée (Forbes-Rigobon)", color="#2ca02c")

    ax2.set_xticks(x)
    ax2.set_xticklabels(etiquettes, rotation=30, ha="right", fontsize=8.5)
    ax2.set_ylabel("Coefficient de corrélation")
    ax2.set_ylim(0, 1.0)
    ax2.set_title("Correction du biais de volatilité (Forbes & Rigobon, 2002)")
    ax2.legend(loc="upper left", fontsize=8.5)
    ax2.grid(True, axis="y", alpha=0.3)

    fig.tight_layout()
    return fig


def analyse():
    """Point d'entrée standard : renvoie les trois tableaux d'analyse de transmission."""
    donnees = charger_tous_marches(telecharger=False)
    return {
        "decalage_horaire": analyser_decalage_horaire(donnees),
        "asymetrie": tester_asymetrie_transmission(donnees),
        "forbes_rigobon": corriger_forbes_rigobon(donnees),
    }


def figure():
    """Point d'entrée standard : génère la figure de transmission et Forbes-Rigobon."""
    donnees = charger_tous_marches(telecharger=False)
    fig = tracer_transmission_et_forbes_rigobon(donnees)
    plt.close(fig)
    return fig