"""Verificación estructural: balances de materia, no negatividad, restricciones físicas e integración."""
import numpy as np
import pytest

from core.parameters import DEFAULTS, LEVER_DEFAULTS, PARAMS
from core.scenarios import SCENARIOS, levers_for
from core.system_dynamics import STOCKS, simulate

YEARS = np.arange(2024, 2051)
POP = np.tile(np.linspace(1.0e6, 1.1e6, len(YEARS)), (2, 1))
INIT = dict(R_obs=np.array([15e3, np.nan]), Q_obs=np.array([3e6, np.nan]))


@pytest.mark.parametrize("scen", list(SCENARIOS))
def test_balance_closes_every_step(scen):
    out = simulate(YEARS, POP, DEFAULTS, levers_for(scen), INIT)
    assert out["balance_max_rel_error"] < 1e-9


@pytest.mark.parametrize("scen", list(SCENARIOS))
def test_stocks_and_flows_nonnegative(scen):
    out = simulate(YEARS, POP, DEFAULTS, levers_for(scen), INIT)
    for k in STOCKS + ("G", "C", "U", "Sr", "So", "Mixed", "Prec", "Porg", "Rrec", "Kout", "Sales", "Ld", "Lf", "Overflow"):
        assert np.all(out[k] >= -1e-9), k


def test_physical_constraints():
    out = simulate(YEARS, POP, DEFAULTS, levers_for("S7"), INIT)
    assert np.all(out["C"] <= out["G"] + 1e-6)
    assert np.all(out["Sr"] + out["So"] <= out["C"] + 1e-6)
    # lo recuperado no supera el potencial material de reciclables recolectados
    assert np.all(out["Rrec"] <= out["C"] * DEFAULTS["s_rec"] + 1e-6)
    assert np.all(out["Kout"] <= out["C"] * DEFAULTS["s_org"] + 1e-6)
    # el tratamiento respeta la capacidad (capacidad máxima del año, inicio o final)
    K_start = np.column_stack([out["init"]["Krec0"], out["Krec"][:, :-1]])
    assert np.all(out["Prec"] <= np.maximum(K_start, out["Krec"]) * (1 + 1e-9))
    assert np.all(out["Lf"] <= out["Ld"] + 1e-6)


def test_landfill_capacity_only_changes_by_modelled_processes():
    out = simulate(YEARS, POP, DEFAULTS, levers_for("BAU"), INIT)
    Q0 = out["init"]["Q0"]
    # Q(t) = Q0 + ampliaciones − dispuesto acumulado
    np.testing.assert_allclose(out["Q"][:, -1], np.maximum(Q0 + out["CapAdd_Q"].sum(1) - out["CumL"][:, -1], 0), rtol=1e-9, atol=1e-6)
    out2 = simulate(YEARS, POP, DEFAULTS, levers_for("BAU", dict(landfill_add=5.0, landfill_add_year=2030)), INIT)
    assert out2["CapAdd_Q"].sum() > 0 and np.all(out2["life"] > out["life"])


def test_extreme_zero_population():
    out = simulate(YEARS, np.zeros_like(POP), DEFAULTS, levers_for("S7"), INIT)
    assert np.allclose(out["G"], 0) and np.allclose(out["Lf"], 0)


def test_extreme_zero_collection():
    P = dict(DEFAULTS, kappa0=0.0)
    out = simulate(YEARS, POP, P, levers_for("BAU"), dict(Q_obs=np.array([3e6, 3e6])))
    assert np.allclose(out["C"], 0) and np.allclose(out["U"], out["G"])


def test_extreme_no_processing_capacity_sends_separated_to_disposal():
    L = levers_for("BAU", dict(disrupt_year=2024, disrupt_dur=30, disrupt_loss=1.0))
    out = simulate(YEARS, POP, DEFAULTS, L, INIT)
    assert np.allclose(out["Prec"], 0) and np.allclose(out["Rrec"], 0)
    assert np.all(out["Excess_r"] >= out["Sr"] - 1e-6)


def test_extreme_no_landfill_capacity_creates_deficit():
    out = simulate(YEARS, POP, DEFAULTS, levers_for("BAU"), dict(Q_obs=np.array([0.0, 0.0])))
    assert np.allclose(out["Lf"], 0) and np.allclose(out["Overflow"], out["Ld"])
    assert np.all(out["life"] == 0)


def test_policy_reduces_disposal_relative_to_bau():
    bau = simulate(YEARS, POP, DEFAULTS, levers_for("BAU"), INIT)
    s7 = simulate(YEARS, POP, DEFAULTS, levers_for("S7"), INIT)
    assert np.all((s7["Lf"] + s7["Overflow"]).sum(1) < (bau["Lf"] + bau["Overflow"]).sum(1))


def test_time_step_convergence():
    a = simulate(YEARS, POP, DEFAULTS, levers_for("S7"), INIT, dt=0.25)
    b = simulate(YEARS, POP, DEFAULTS, levers_for("S7"), INIT, dt=1 / 16)
    rel = np.abs(a["CumL"][:, -1] - b["CumL"][:, -1]) / b["CumL"][:, -1]
    assert np.all(rel < 0.01), rel  # error de discretización < 1 % del acumulado


def test_initial_conditions_reproduce_observation():
    out = simulate(np.arange(2024, 2026), POP[:, :2], DEFAULTS, levers_for("BAU"), dict(R_obs=np.array([15e3, 15e3])))
    # el aprovechamiento del año base coincide con lo observado (tolerancia por la dinámica intra-anual)
    assert np.allclose(out["Rrec"][:, 0], 15e3, rtol=0.05)


def test_registry_ranges_contain_defaults():
    for p in PARAMS.values():
        assert p.low <= p.default <= p.high, p.key
