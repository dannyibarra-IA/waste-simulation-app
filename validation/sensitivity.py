"""
Sensibilidad local (un factor a la vez, tornado) y global (cribado de Morris, efectos elementales).

Morris (1991), con la medida μ* de Campolongo, Cariboni y Saltelli (2007): r trayectorias en una rejilla de p niveles
sobre el rango del registro de parámetros. Se eligió Morris y no Sobol porque, con ~35 parámetros, Sobol requiere
del orden de N·(k+2) ≳ 10⁴ simulaciones, inviable en la nube gratuita en tiempo interactivo; Morris ordena la
influencia con r·(k+1) simulaciones vectorizadas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.parameters import PARAMS
from core.scenarios import levers_for
from core.simulation_engine import city_params
from core.system_dynamics import consistent_init, simulate

OUTPUTS = {
    "dispuesto_acum": "Disposición acumulada a 2050 (Mt)",
    "tasa_aprov_2050": "Tasa de aprovechamiento 2050 (%)",
    "vida_util": "Vida útil de disposición (años, tope 100)",
}


def _batch(repo, code, scenario, P, n, lever_overrides, base_year, end_year):
    years = np.arange(base_year, end_year + 1)
    init, _ = repo.base_observations(code, base_year)
    pop = np.tile(repo.pop_series(code, years), (n, 1))
    ini = consistent_init(years, pop, P, levers_for("BAU"), {k: np.full(n, v, dtype=float) for k, v in init.items()})
    out = simulate(years, pop, P, levers_for(scenario, lever_overrides), init=ini, track_balance=False)
    disp = out["Lf"] + out["Overflow"]
    return dict(dispuesto_acum=disp.sum(1) / 1e6, tasa_aprov_2050=100 * (out["Rrec"][:, -1] + out["Kout"][:, -1]) / np.maximum(out["G"][:, -1], 1e-9),
                vida_util=np.minimum(out["life"], 100.0))


def tornado(repo, code, scenario, output="dispuesto_acum", keys=None, lever_overrides=None, param_overrides=None, base_year=2024, end_year=2050):
    base, origin = city_params(repo, code, param_overrides)
    keys = keys or [k for k in PARAMS if not str(origin.get(k, "")).startswith("medido")]
    runs = [dict(base)]
    for k in keys:
        runs += [dict(base, **{k: PARAMS[k].low}), dict(base, **{k: PARAMS[k].high})]
    n = len(runs)
    P = {k: np.array([r[k] for r in runs]) for k in base}
    y = _batch(repo, code, scenario, P, n, lever_overrides, base_year, end_year)[output]
    rows = [dict(parametro=k, descripcion=PARAMS[k].label_es, bajo=y[1 + 2 * i] - y[0], alto=y[2 + 2 * i] - y[0], clase=PARAMS[k].kind)
            for i, k in enumerate(keys)]
    df = pd.DataFrame(rows)
    df["rango"] = (df["alto"] - df["bajo"]).abs()
    return float(y[0]), df.sort_values("rango")


def morris(repo, code, scenario, r=20, levels=4, seed=20261116, keys=None, lever_overrides=None, param_overrides=None, base_year=2024, end_year=2050):
    base, origin = city_params(repo, code, param_overrides)
    keys = keys or [k for k in PARAMS if not str(origin.get(k, "")).startswith("medido")]
    k = len(keys)
    rng = np.random.default_rng(seed)
    delta = levels / (2 * (levels - 1))
    grid = np.arange(levels) / (levels - 1)
    X = []
    order = []
    for _ in range(r):
        x = rng.choice(grid[grid <= 1 - delta + 1e-12], size=k)
        traj = [x.copy()]
        perm = rng.permutation(k)
        for j in perm:
            x = x.copy()
            x[j] = x[j] + delta if x[j] + delta <= 1 + 1e-12 else x[j] - delta
            traj.append(x)
        X.append(np.array(traj))
        order.append(perm)
    U = np.vstack(X)  # (r*(k+1), k) en [0,1]
    n = U.shape[0]
    P = {kk: np.full(n, base[kk]) for kk in base}
    for j, kk in enumerate(keys):
        P[kk] = PARAMS[kk].low + U[:, j] * (PARAMS[kk].high - PARAMS[kk].low)
    Y = _batch(repo, code, scenario, P, n, lever_overrides, base_year, end_year)
    res = {}
    for out_key, y in Y.items():
        ee = np.zeros((r, k))
        for t in range(r):
            yt = y[t * (k + 1):(t + 1) * (k + 1)]
            ut = U[t * (k + 1):(t + 1) * (k + 1)]
            for step, j in enumerate(order[t]):
                d = ut[step + 1, j] - ut[step, j]
                ee[t, j] = (yt[step + 1] - yt[step]) / d
        res[out_key] = pd.DataFrame(dict(parametro=keys, descripcion=[PARAMS[x].label_es for x in keys], clase=[PARAMS[x].kind for x in keys],
                                         mu_star=np.abs(ee).mean(0), mu=ee.mean(0), sigma=ee.std(0, ddof=1))).sort_values("mu_star", ascending=False)
    return dict(results=res, n_runs=n, r=r, levels=levels, seed=seed, design=pd.DataFrame(U, columns=keys))
