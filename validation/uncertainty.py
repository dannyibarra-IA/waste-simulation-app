"""
Incertidumbre de PARÁMETROS mediante Monte Carlo (muestreo triangular en el rango del registro, moda en el valor
por defecto o en el valor medido/calibrado). Es distinta de:
  - incertidumbre de ESCENARIO: se explora comparando escenarios, no se muestrea;
  - incertidumbre ESTRUCTURAL: forma de las ecuaciones; se documenta y se explora con pruebas alternativas, no aquí.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.parameters import PARAMS
from core.scenarios import levers_for
from core.simulation_engine import city_params
from core.system_dynamics import simulate

# Parámetros que no se muestrean porque se miden o determinan el estado observado
FIXED_IF_MEASURED = {"g_pc0", "kappa0", "A0"}


def sample_params(base: dict, origin: dict, n: int, seed: int, rel_width: float = 1.0, keys=None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cols = {}
    for k, p in PARAMS.items():
        if keys is not None and k not in keys:
            continue
        if k in FIXED_IF_MEASURED and str(origin.get(k, "")).startswith(("medido", "derivado")):
            continue
        mode = float(np.clip(base[k], p.low, p.high))
        lo = mode - rel_width * (mode - p.low)
        hi = mode + rel_width * (p.high - mode)
        cols[k] = rng.triangular(lo, mode, hi, size=n) if hi > lo else np.full(n, mode)
    return pd.DataFrame(cols)


def monte_carlo(repo, code: str, scenario: str, n: int = 300, seed: int = 20261116, lever_overrides=None, param_overrides=None,
                base_year: int = 2024, end_year: int = 2050, rel_width: float = 1.0):
    years = np.arange(base_year, end_year + 1)
    base, origin = city_params(repo, code, param_overrides)
    samples = sample_params(base, origin, n, seed, rel_width)
    P = {k: (samples[k].to_numpy() if k in samples else np.full(n, base[k])) for k in base}
    init, _ = repo.base_observations(code, base_year)
    pop = np.tile(repo.pop_series(code, years), (n, 1))
    out = simulate(years, pop, P, levers_for(scenario, lever_overrides), init={k: np.full(n, v) for k, v in init.items()}, track_balance=False)
    disp = out["Lf"] + out["Overflow"]
    rate = (out["Rrec"] + out["Kout"]) / np.maximum(out["G"], 1e-9)
    q = lambda a: dict(p05=np.percentile(a, 5, 0), p25=np.percentile(a, 25, 0), p50=np.percentile(a, 50, 0),
                       p75=np.percentile(a, 75, 0), p95=np.percentile(a, 95, 0))
    life = np.minimum(out["life"], 100.0)
    samples = samples.assign(vida_util=life, dispuesto_acum_2050=disp.sum(1), tasa_aprov_2050=rate[:, -1])
    return dict(years=years, disposal=q(disp), cum_disposal=q(np.cumsum(disp, 1)), recovery_rate=q(rate), Q=q(out["Q"]),
                life=life, samples=samples, seed=seed, n=n, scenario=scenario, rel_width=rel_width)
