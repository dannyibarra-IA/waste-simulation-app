"""Pruebas de la integración de las bases SSPD y de la caracterización ingresada por el usuario."""
import numpy as np
import pytest

from core.data import Repository
from core.quality import city_flags, recovery_usable
from core.simulation_engine import city_params, composition_fractions, run


@pytest.fixture(scope="module")
def repo():
    return Repository()


def test_disposal_series_complete_2018_2024(repo):
    for c in repo.codes:
        s = repo.profile(c).series("dispuesto_t")
        assert set(range(2018, 2025)) <= set(s.index), repo.name(c)
        assert (s > 0).all()


def test_known_values_match_source(repo):
    # valores tomados directamente de las bases SSPD (columna de total anual)
    assert np.isclose(repo.profile("05001").series("dispuesto_t")[2024], 698532.5, rtol=1e-4)
    assert np.isclose(repo.profile("11001").series("dispuesto_t")[2021], 2239711.358, rtol=1e-6)
    # 2018: Anexo 1 del PDF, promedio ton/día × 365 (Bogotá 6.454,66 t/día)
    assert np.isclose(repo.profile("11001").series("dispuesto_t")[2018], 6454.66 * 365, rtol=1e-6)


def test_recovery_quality_flags(repo):
    assert not recovery_usable(repo.profile("11001"))   # Bogotá: aprovechado ≈ 40-50 % del flujo
    assert recovery_usable(repo.profile("05001"))
    assert any(f["codigo"] == "vida_util_vencida" for f in city_flags(repo.profile("68001")))   # Bucaramanga


def test_every_capital_calibrated_and_not_exploratory(repo):
    out, meta = run(repo, repo.codes, "BAU")
    assert all(not m["exploratory"] for m in meta)
    assert all(repo.calibration[c]["status"] == "calibrado" for c in repo.codes)
    assert out["balance_max_rel_error"] < 1e-9


def test_base_year_reproduces_sspd_disposal(repo):
    """El primer año simulado reproduce el total anual observado de 2024 (salvo ciudades con aprovechamiento acotado o sobre el potencial)."""
    out, meta = run(repo, repo.codes, "BAU")
    for i, c in enumerate(repo.codes):
        m = meta[i]
        if "aprovechado_ajuste" in m["provenance"] or m["A0_clipped"]:
            continue   # casos señalados al usuario: aprovechamiento acotado o por encima del potencial estructural
        obs = repo.profile(c).series("dispuesto_t")[2024]
        sim = out["Lf"][i, 0] + out["Overflow"][i, 0]
        assert abs(sim / obs - 1) < 0.02, (repo.name(c), sim, obs)


def test_composition_fractions_and_override(repo):
    fr = dict(organicos=55, papel_carton=12, plasticos=13, vidrio=4, metales=2, textiles=3, madera=1, otros=10)
    so, sr = composition_fractions(fr)
    assert np.isclose(so, 0.55) and np.isclose(sr, 0.35)
    par, origin = city_params(repo, "05001", {"caracterizacion": {"fracciones": fr, "fuente": "PGIRS de prueba"}})
    assert np.isclose(par["s_rec"], 0.35) and "PGIRS de prueba" in origin["s_rec"]
    a, _ = run(repo, ["05001"], "S7")
    b, _ = run(repo, ["05001"], "S7", param_overrides={"05001": {"caracterizacion": {"fracciones": fr}}})
    assert b["Rrec"][0, -1] > a["Rrec"][0, -1]   # más fracción reciclable → mayor potencial recuperable


def test_flagged_cities_are_reported(repo):
    out, meta = run(repo, repo.codes, "BAU")
    flagged = {m["ciudad"] for m in meta if m["A0_clipped"] or "aprovechado_ajuste" in m["provenance"]}
    assert {"Bogotá D. C.", "Villavicencio"} <= flagged
