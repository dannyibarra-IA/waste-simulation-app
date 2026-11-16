"""Pruebas del protocolo de calibración, validación e incertidumbre (experimento gemelo con datos sintéticos)."""
import shutil

import numpy as np
import pandas as pd
import pytest

from core.data import PROC, Repository
from core.parameters import DEFAULTS
from core.scenarios import levers_for
from core.system_dynamics import simulate
from validation.calibration import calibrate_city
from validation.historical_validation import metrics
from validation.reliability import assess
from validation.sensitivity import morris, tornado
from validation.uncertainty import monte_carlo

CODE = "17001"  # Manizales; las observaciones son SINTÉTICAS y solo existen dentro de esta prueba


@pytest.fixture
def twin_repo(tmp_path):
    for f in ("capitales.csv", "poblacion.csv"):
        shutil.copy(PROC / f, tmp_path / f)
    r0 = Repository(tmp_path)
    years = np.arange(2018, 2025)
    pop = r0.pop_series(CODE, years)[None, :]
    true = dict(DEFAULTS, g_growth=0.012, p_base=0.02)
    out = simulate(years, pop, true, levers_for("BAU"), init=dict(W_obs=np.array([140e3]), R_obs=np.array([9e3]), kappa_obs=np.array([0.95])))
    d, a = out["Lf"][0] + out["Overflow"][0], out["Rrec"][0] + out["Kout"][0]
    rows = []
    for i, y in enumerate(years):
        rows += [dict(divipola=CODE, anio=y, variable="dispuesto_t", valor=d[i], unidad="t/año", tipo_dato="sintetico", calidad="prueba", fuente="test", nota=""),
                 dict(divipola=CODE, anio=y, variable="aprovechado_t", valor=a[i], unidad="t/año", tipo_dato="sintetico", calidad="prueba", fuente="test", nota=""),
                 dict(divipola=CODE, anio=y, variable="cobertura_recoleccion", valor=0.95, unidad="fracción", tipo_dato="sintetico", calidad="prueba", fuente="test", nota="")]
    pd.DataFrame(rows).to_csv(tmp_path / "residuos_observados.csv", index=False)
    return Repository(tmp_path), true


def test_metrics_known_values():
    m = metrics([100, 200], [110, 190])
    assert m["MAE"] == 10 and np.isclose(m["RMSE"], 10) and np.isclose(m["sesgo_medio"], 0)


def test_twin_calibration_recovers_parameters(twin_repo):
    repo, true = twin_repo
    res = calibrate_city(repo, CODE, n_val=2)
    assert res["status"] == "calibrado" and res["years_val"] == [2023, 2024]
    assert abs(res["params"]["g_growth"] - true["g_growth"]) < 0.004
    assert res["validation"]["dispuesto"]["sMAPE"] < 3
    rel = assess(repo.profile(CODE), res)
    assert rel["nivel"] in ("A", "B")


def test_no_data_is_exploratory():
    repo = Repository()
    res = calibrate_city(repo, "97001")
    assert res["status"] in ("sin_datos", "insuficiente")
    assert assess(repo.profile("97001"), res)["nivel"] == "D"


def test_monte_carlo_reproducible_with_seed():
    repo = Repository()
    a = monte_carlo(repo, "05001", "S7", n=60, seed=1)
    b = monte_carlo(repo, "05001", "S7", n=60, seed=1)
    c = monte_carlo(repo, "05001", "S7", n=60, seed=2)
    assert np.allclose(a["life"], b["life"]) and not np.allclose(a["life"], c["life"])
    assert np.all(a["cum_disposal"]["p05"] <= a["cum_disposal"]["p95"])


def test_sensitivity_runs():
    repo = Repository()
    base, tor = tornado(repo, "05001", "BAU")
    assert np.isfinite(base) and len(tor) > 10
    m = morris(repo, "05001", "BAU", r=6, seed=3)
    df = m["results"]["dispuesto_acum"]
    assert m["n_runs"] == 6 * (len(df) + 1) and (df["mu_star"] >= 0).all()
