import numpy as np

from core.data import Repository
from core.scenarios import SCENARIOS
from core.simulation_engine import run_scenarios


def test_all_scenarios_run_and_compare():
    r = Repository()
    codes = r.codes[:4]
    df, _ = run_scenarios(r, codes, list(SCENARIOS))
    assert set(df["escenario"]) == set(SCENARIOS)
    bau = df[df.escenario == "BAU"]
    assert np.allclose(bau["desviacion_vs_bau_t"], 0)
    s7 = df[(df.escenario == "S7") & (df.anio == 2050)]
    assert (s7["desviacion_acum_vs_bau_t"] > 0).all()


def test_levers_close_city_specific_gaps():
    """Un mismo escenario no impone el mismo valor: cierra una fracción de la brecha de cada ciudad."""
    from core.parameters import DEFAULTS
    from core.scenarios import levers_for
    from core.system_dynamics import simulate
    yrs = np.arange(2024, 2051)
    pop = np.full((2, len(yrs)), 5e5)
    out = simulate(yrs, pop, DEFAULTS, levers_for("S7", dict(collection=0.5)), dict(kappa_obs=np.array([0.80, 0.98])))
    k = out["kappa"][:, -1]
    kmax = DEFAULTS["kappa_max"]
    np.testing.assert_allclose(k, [0.80 + 0.5 * (kmax - 0.80), 0.98 + 0.5 * (kmax - 0.98)], rtol=1e-3)


def test_disruption_reduces_processing_during_window():
    r = Repository()
    df, _ = run_scenarios(r, r.codes[:2], ["BAU", "S9"])
    a = df[(df.escenario == "BAU") & (df.anio == 2030)]["Prec"].to_numpy()
    b = df[(df.escenario == "S9") & (df.anio == 2030)]["Prec"].to_numpy()
    assert np.all(b < a)
