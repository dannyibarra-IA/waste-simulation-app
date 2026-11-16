import numpy as np

from core.data import Repository
from core.simulation_engine import run

EXPECTED = {"91001", "05001", "81001", "08001", "13001", "15001", "17001", "18001", "85001", "19001", "20001", "27001", "23001", "11001", "94001",
            "95001", "41001", "44001", "47001", "50001", "52001", "54001", "86001", "63001", "66001", "88001", "68001", "70001", "73001", "76001",
            "97001", "99001"}


def test_exactly_32_capitals():
    r = Repository()
    assert set(r.codes) == EXPECTED and len(r.codes) == 32


def test_population_2018_2050_for_every_capital():
    r = Repository()
    for c in r.codes:
        p = r.profile(c).pop
        assert set(range(2018, 2051)) <= set(p.index), c
        assert (p["poblacion_total"] > 0).all()
        assert set(p.loc[2043:2050, "tipo_dato"]) == {"estimado"}
        assert set(p.loc[2019:2042, "tipo_dato"]) == {"proyeccion_oficial"}


def test_every_capital_simulates_to_2050():
    r = Repository()
    out, meta = run(r, r.codes, "S7")
    assert out["years"][-1] == 2050 and out["G"].shape == (32, 27)
    assert np.isfinite(out["G"]).all() and out["balance_max_rel_error"] < 1e-9
    assert all("exploratory" in m for m in meta)
