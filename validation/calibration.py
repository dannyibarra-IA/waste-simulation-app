"""
Calibración por ciudad contra series históricas SSPD (dispuesto y aprovechado).

Principio de parsimonia: solo se calibran parámetros identificables con series anuales cortas:
  g_growth  crecimiento de la generación per cápita  ← tendencia de (dispuesto + aprovechado)
  p_base    adopción espontánea de la separación     ← tendencia del aprovechamiento
Con menos de 4 años de ajuste solo se calibra g_growth; con menos de 3 no se calibra.

Separación temporal: los últimos `n_val` años observados se reservan para validación fuera de muestra.
Todas las demás palancas se mantienen en BAU (sin políticas nuevas en el periodo histórico).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares

from core.parameters import PARAMS
from core.scenarios import levers_for
from core.simulation_engine import city_params
from core.system_dynamics import simulate
from validation.historical_validation import metrics, observed_targets


def _sim(repo, code, years, par, init):
    pop = repo.pop_series(code, years)[None, :]
    out = simulate(years, pop, par, levers_for("BAU"), init={k: np.array([v]) for k, v in init.items()}, track_balance=False)
    return out["Lf"][0] + out["Overflow"][0], out["Rrec"][0] + out["Kout"][0]


def calibrate_city(repo, code: str, n_val: int = 2, base_overrides: dict | None = None) -> dict:
    prof = repo.profile(code)
    obs = observed_targets(prof).dropna(subset=["dispuesto_t"])
    res = dict(divipola=code, ciudad=prof.ciudad, status="sin_datos", params={}, fit={}, validation={}, years_fit=[], years_val=[])
    if len(obs) < 3:
        res["status"] = "insuficiente" if len(obs) else "sin_datos"
        res["nota"] = f"{len(obs)} años observados; se requieren al menos 3 para calibrar."
        return res
    y0, y1 = int(obs.index.min()), int(obs.index.max())
    n_val = n_val if len(obs) - n_val >= 3 else 0
    fit_years = list(obs.index[: len(obs) - n_val]) if n_val else list(obs.index)
    val_years = list(obs.index[len(obs) - n_val:]) if n_val else []
    years = np.arange(y0, y1 + 1)
    init, _ = repo.base_observations(code, y0)
    par0, _ = city_params(repo, code, base_overrides)

    free = ["g_growth"] + (["p_base"] if len(fit_years) >= 4 and obs["aprovechado_t"].notna().sum() >= 4 else [])
    lo = [PARAMS[k].low for k in free]
    hi = [PARAMS[k].high for k in free]
    x0 = [par0[k] for k in free]
    mask = np.isin(years, fit_years)
    od, oa = obs["dispuesto_t"].reindex(years).to_numpy(), obs["aprovechado_t"].reindex(years).to_numpy()
    scale_d, scale_a = np.nanmean(od) or 1.0, (np.nanmean(oa) if np.isfinite(np.nanmean(oa)) and np.nanmean(oa) > 0 else 1.0)

    def resid(x):
        par = dict(par0, **dict(zip(free, x)))
        d, a = _sim(repo, code, years, par, init)
        r = [(d[mask] - od[mask]) / scale_d]
        if "p_base" in free:
            m2 = mask & np.isfinite(oa)
            r.append((a[m2] - oa[m2]) / scale_a)
        r = np.concatenate(r)
        return np.where(np.isfinite(r), r, 0.0)

    sol = least_squares(resid, x0, bounds=(lo, hi), method="trf")
    par = dict(par0, **dict(zip(free, sol.x)))
    d, a = _sim(repo, code, years, par, init)
    fm = np.isin(years, fit_years)
    vm = np.isin(years, val_years)
    res.update(status="calibrado", params=dict(zip(free, map(float, sol.x))), years_fit=fit_years, years_val=val_years,
               at_bound=[k for k, v, l, h in zip(free, sol.x, lo, hi) if np.isclose(v, l) or np.isclose(v, h)],
               fit=dict(dispuesto=metrics(od[fm], d[fm]), aprovechado=metrics(oa[fm], a[fm])),
               validation=dict(dispuesto=metrics(od[vm], d[vm]), aprovechado=metrics(oa[vm], a[vm])) if val_years else {},
               series=dict(years=years.tolist(), obs_disp=od.tolist(), sim_disp=d.tolist(), obs_apr=oa.tolist(), sim_apr=a.tolist()))
    if not val_years:
        res["nota"] = "Serie demasiado corta para reservar años de validación fuera de muestra."
    return res
