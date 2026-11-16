"""
Orquestación: arma los parámetros por ciudad desde el repositorio de datos, ejecuta el motor y
devuelve resultados ordenados. Es la única puerta de entrada que usa la interfaz.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.data import Repository
from core.parameters import DEFAULTS, PARAMS
from core.scenarios import levers_for
from core.system_dynamics import simulate

BASE_YEAR = 2024
END_YEAR = 2050

OUTPUT_COLUMNS = {
    "pop": ("Población", "Population", "hab"),
    "W": ("Generación sin prevención", "Generation before prevention", "t/año"),
    "G": ("Generación", "Generation", "t/año"),
    "C": ("Recolectado", "Collected", "t/año"),
    "U": ("No recolectado", "Uncollected", "t/año"),
    "Sr": ("Reciclables separados", "Separated recyclables", "t/año"),
    "So": ("Orgánicos separados", "Separated organics", "t/año"),
    "Mixed": ("Residuo mezclado", "Mixed waste", "t/año"),
    "Prec": ("Procesado en clasificación", "Sorted", "t/año"),
    "Porg": ("Procesado orgánicos", "Organics treated (input)", "t/año"),
    "Excess_r": ("Reciclables sin capacidad", "Recyclables over capacity", "t/año"),
    "Excess_o": ("Orgánicos sin capacidad", "Organics over capacity", "t/año"),
    "Rej_r": ("Rechazo de clasificación", "Sorting rejects", "t/año"),
    "Rej_o": ("Rechazo de orgánicos", "Organics rejects", "t/año"),
    "Rrec": ("Materiales recuperados", "Recovered materials", "t/año"),
    "Kout": ("Orgánicos tratados", "Treated organics", "t/año"),
    "Sales": ("Materiales comercializados", "Materials sold", "t/año"),
    "Spill": ("Inventario no comercializado a disposición", "Unsold stock to disposal", "t/año"),
    "Ld": ("Demanda de disposición", "Disposal demand", "t/año"),
    "Lf": ("Dispuesto en relleno", "Landfilled", "t/año"),
    "Overflow": ("Déficit de capacidad de disposición", "Disposal capacity deficit", "t/año"),
    "Prevented": ("Prevenido en la fuente", "Prevented at source", "t/año"),
    "Q": ("Capacidad remanente de disposición", "Remaining disposal capacity", "t"),
    "CumL": ("Disposición acumulada", "Cumulative landfilled", "t"),
    "Krec": ("Capacidad de clasificación", "Sorting capacity", "t/año"),
    "Korg": ("Capacidad de orgánicos", "Organics capacity", "t/año"),
    "I": ("Inventario de materiales", "Material inventory", "t"),
    "E": ("Capacidad organizativa recicladores", "Waste-picker organisational capacity", "0-1"),
    "A": ("Adopción de separación", "Source-separation adoption", "fracción"),
    "P": ("Índice de precio de materiales", "Material price index", "base=1"),
    "rho_r": ("Tasa de rechazo en clasificación", "Sorting reject rate", "fracción"),
    "kappa": ("Cobertura de recolección", "Collection coverage", "fracción"),
    "pressure": ("Presión institucional", "Institutional pressure", "0-1"),
    "util_rec": ("Utilización de capacidad de clasificación", "Sorting utilization", "fracción"),
    "util_org": ("Utilización de capacidad de orgánicos", "Organics utilization", "fracción"),
}


def city_params(repo: Repository, code: str, overrides: dict | None = None) -> tuple[dict, dict]:
    """Parámetros de una ciudad: defectos del registro, sustituidos por datos medidos y por ajustes del usuario."""
    prof = repo.profile(code)
    par = dict(DEFAULTS)
    origin = {k: PARAMS[k].kind for k in par}
    for var, key in (("frac_organicos", "s_org"), ("frac_reciclables", "s_rec")):
        y, v = prof.latest(var)
        if np.isfinite(v):
            par[key], origin[key] = v, f"medido ({y})"
    if overrides:
        for k, v in overrides.items():
            if k in par and v is not None:
                par[k], origin[k] = float(v), "ajustado por el usuario"
    return par, origin


def _overrides_for(po: dict | None, code: str):
    """`po` puede ser global ({parámetro: valor}) o por ciudad ({divipola: {parámetro: valor}})."""
    if not po:
        return None
    if any(isinstance(v, dict) for v in po.values()):
        merged = dict(po.get("*", {}))
        merged.update(po.get(code, {}))
        return merged
    return po


def run(repo: Repository, codes, scenario: str = "BAU", lever_overrides: dict | None = None, param_overrides: dict | None = None,
        base_year: int = BASE_YEAR, end_year: int = END_YEAR, dt: float = 0.25, pop_col: str = "poblacion_total"):
    """Simula varias ciudades en un solo lote. Devuelve (salida cruda del motor, metadatos por ciudad)."""
    codes = list(codes)
    years = np.arange(base_year, end_year + 1)
    pops, plist, inits, meta = [], [], [], []
    for c in codes:
        par, origin = city_params(repo, c, _overrides_for(param_overrides, c))
        init, prov = repo.base_observations(c, base_year)
        origin["A0"] = "derivado del aprovechamiento observado" if np.isfinite(init["R_obs"]) else "supuesto"
        if np.isfinite(init["W_obs"]):
            origin["g_pc0"] = "medido (SSPD)"
        if np.isfinite(init["kappa_obs"]):
            origin["kappa0"] = "medido"
        pops.append(repo.pop_series(c, years, pop_col))
        plist.append(par)
        inits.append(init)
        meta.append(dict(divipola=c, ciudad=repo.name(c), origin=origin, provenance=prov,
                         exploratory=not np.isfinite(init.get("W_obs", np.nan))))
    P = {k: np.array([p[k] for p in plist]) for k in plist[0]}
    keys = ("W_obs", "R_obs", "O_obs", "Q_obs", "kappa_obs", "Q_years_obs")
    I = {k: np.array([i.get(k, np.nan) for i in inits], dtype=float) for k in keys}
    L = levers_for(scenario, lever_overrides)
    out = simulate(years, np.vstack(pops), P, L, init=I, dt=dt)
    out["pop"] = np.vstack(pops)
    for i, m in enumerate(meta):
        m["capacity_assumed"] = bool(out["init"]["Q_assumed"][i])
        m["A0_clipped"] = bool(out["init"]["A0_clipped"][i])
        m["life"] = float(out["life"][i])
    return out, meta


def to_frame(out, meta, scenario: str) -> pd.DataFrame:
    years = out["years"]
    rows = []
    for i, m in enumerate(meta):
        d = {k: out[k][i] for k in OUTPUT_COLUMNS}
        df = pd.DataFrame(d, index=pd.Index(years, name="anio"))
        df.insert(0, "escenario", scenario)
        df.insert(0, "ciudad", m["ciudad"])
        df.insert(0, "divipola", m["divipola"])
        rows.append(df.reset_index())
    df = pd.concat(rows, ignore_index=True)
    return add_indicators(df)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    g = df["G"].where(df["G"] > 0)
    df["tasa_aprovechamiento"] = (df["Rrec"] + df["Kout"]) / g
    df["gpc_kg_dia"] = df["G"] * 1000 / df["pop"].where(df["pop"] > 0) / 365
    df["disp_pc_kg_dia"] = (df["Lf"] + df["Overflow"]) * 1000 / df["pop"].where(df["pop"] > 0) / 365
    df["aprovechado_t"] = df["Rrec"] + df["Kout"]
    df["dispuesto_total_t"] = df["Lf"] + df["Overflow"]
    df["vida_util_instantanea"] = df["Q"] / df["Ld"].where(df["Ld"] > 0)
    df["tipo_dato"] = "simulado"
    return df


def run_scenarios(repo, codes, scenarios, lever_overrides=None, param_overrides=None, **kw) -> tuple[pd.DataFrame, dict]:
    frames, metas = [], {}
    for s in scenarios:
        out, meta = run(repo, codes, s, lever_overrides, param_overrides, **kw)
        frames.append(to_frame(out, meta, s))
        metas[s] = meta
    df = pd.concat(frames, ignore_index=True)
    if "BAU" in scenarios:
        bau = df[df["escenario"] == "BAU"].set_index(["divipola", "anio"])["dispuesto_total_t"]
        key = pd.MultiIndex.from_frame(df[["divipola", "anio"]])
        df["desviacion_vs_bau_t"] = bau.reindex(key).to_numpy() - df["dispuesto_total_t"].to_numpy()
        df["desviacion_acum_vs_bau_t"] = df.groupby(["divipola", "escenario"])["desviacion_vs_bau_t"].cumsum()
    return df, metas
