"""Comparación del modelo con observaciones históricas y métricas de error."""
from __future__ import annotations

import numpy as np
import pandas as pd


def metrics(obs, sim) -> dict:
    o, s = np.asarray(obs, float), np.asarray(sim, float)
    m = np.isfinite(o) & np.isfinite(s)
    o, s = o[m], s[m]
    if o.size == 0:
        return dict(n=0, MAE=np.nan, RMSE=np.nan, sMAPE=np.nan, sesgo_medio=np.nan, sesgo_pct=np.nan, R2=np.nan)
    e = s - o
    denom = (np.abs(o) + np.abs(s)) / 2
    smape = float(np.mean(np.where(denom > 0, np.abs(e) / denom, 0)) * 100)
    ss_tot = float(np.sum((o - o.mean()) ** 2))
    return dict(n=int(o.size), MAE=float(np.mean(np.abs(e))), RMSE=float(np.sqrt(np.mean(e ** 2))), sMAPE=smape,
                sesgo_medio=float(np.mean(e)), sesgo_pct=float(np.mean(e) / np.mean(o) * 100) if np.mean(o) else np.nan,
                R2=float(1 - np.sum(e ** 2) / ss_tot) if ss_tot > 0 else np.nan)


def observed_targets(profile) -> pd.DataFrame:
    d = pd.DataFrame({"dispuesto_t": profile.series("dispuesto_t"), "aprovechado_t": profile.series("aprovechado_t")})
    return d[(d.index >= 2018)].sort_index()


def compare(profile, sim_years, sim_disposal, sim_recovered) -> pd.DataFrame:
    obs = observed_targets(profile)
    sim = pd.DataFrame({"dispuesto_sim": sim_disposal, "aprovechado_sim": sim_recovered}, index=sim_years)
    return obs.join(sim, how="inner")
