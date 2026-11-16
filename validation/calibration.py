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
from core.system_dynamics import consistent_init, simulate
from validation.historical_validation import metrics, observed_targets


def _sim(repo, code, years, par, init):
    pop = repo.pop_series(code, years)[None, :]
    L = levers_for("BAU")
    ini = consistent_init(years, pop, par, L, {k: np.array([v], dtype=float) for k, v in init.items()})
    out = simulate(years, pop, par, L, init=ini, track_balance=False)
    # operador de observación: la SSPD reporta como «aprovechado» solo materiales inorgánicos (papel, plástico, vidrio,
    # metales, madera, textil); por eso se compara con R (materiales recuperados), no con R + orgánicos tratados
    return out["Lf"][0] + out["Overflow"][0], out["Rrec"][0]


def calibrate_city(repo, code: str, n_val: int = 2, base_overrides: dict | None = None) -> dict:
    from core.quality import recovery_usable
    prof = repo.profile(code)
    obs = observed_targets(prof).dropna(subset=["dispuesto_t"])
    use_apr = recovery_usable(prof)
    if not use_apr:
        obs["aprovechado_t"] = np.nan
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
    par0, _ = city_params(repo, code, base_overrides, use_calibration=False)
    init, _ = repo.base_observations(code, y0)
    apr_obs = obs["aprovechado_t"].dropna()
    if not np.isfinite(init.get("R_obs", np.nan)) and len(apr_obs):
        # el aprovechamiento empieza a reportarse después del año inicial: se usa el primer valor reportado como condición inicial
        init["R_obs"] = float(apr_obs.iloc[0])
        k = init.get("kappa_obs") if np.isfinite(init.get("kappa_obs", np.nan)) else par0["kappa0"]
        init["W_obs"] = (float(obs["dispuesto_t"].iloc[0]) + init["R_obs"]) / k   # generación coherente con la condición inicial
        res["nota_inicial"] = f"Condición inicial de aprovechamiento tomada de {int(apr_obs.index[0])} (primer año reportado)."

    n_apr_fit = int(obs.loc[obs.index.isin(fit_years), "aprovechado_t"].notna().sum())
    free = ["g_growth"] + (["p_base"] if len(fit_years) >= 4 and n_apr_fit >= 3 else [])
    lo = [PARAMS[k].low for k in free]
    hi = [PARAMS[k].high for k in free]
    x0 = [par0[k] for k in free]
    mask = np.isin(years, fit_years)
    od, oa = obs["dispuesto_t"].reindex(years).to_numpy(), obs["aprovechado_t"].reindex(years).to_numpy()
    scale_d = float(np.nanmean(od)) or 1.0
    scale_a = float(np.nanmean(oa)) if np.isfinite(oa).any() and np.nanmean(oa) > 0 else 1.0

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
    # tasa de corto plazo vigente al final de la serie (punto de partida de las proyecciones)
    g_end = par["g_lr"] + (par["g_growth"] - par["g_lr"]) * np.exp(-(y1 - y0) / par["tau_g"])
    res.update(status="calibrado", uso_aprovechamiento=use_apr, anio_inicial=y0, anio_final=y1, g_growth_fin_serie=float(g_end), params=dict(zip(free, map(float, sol.x))), years_fit=fit_years, years_val=val_years,
               at_bound=[k for k, v, l, h in zip(free, sol.x, lo, hi) if np.isclose(v, h, atol=1e-6) or (np.isclose(v, l, atol=1e-6) and l != 0)],
               fit=dict(dispuesto=metrics(od[fm], d[fm]), aprovechado=metrics(oa[fm], a[fm])),
               validation=dict(dispuesto=metrics(od[vm], d[vm]), aprovechado=metrics(oa[vm], a[vm])) if val_years else {},
               series=dict(years=years.tolist(), obs_disp=od.tolist(), sim_disp=d.tolist(), obs_apr=oa.tolist(), sim_apr=a.tolist()))
    if not val_years:
        res["nota"] = "Serie demasiado corta para reservar años de validación fuera de muestra."
    return res
