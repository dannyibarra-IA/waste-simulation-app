"""
Acceso a datos del observatorio: capitales, población y observaciones de residuos, con trazabilidad.

Clasificación del dato (columna `tipo_dato`):
  observado            reportado por una fuente oficial o documental
  base_censal_conciliada / proyeccion_oficial   DANE
  estimado             derivado por el observatorio con un método documentado
  supuesto             valor exploratorio sin fuente específica
  simulado             salida del motor
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"

# Variables del perfil de ciudad pedidas por el protocolo, para medir completitud
PROFILE_VARIABLES = [
    ("poblacion", "Población histórica y proyectada", "hab"),
    ("generacion_pc", "Generación per cápita", "kg/hab/día"),
    ("generacion_t", "Generación total", "t/año"),
    ("composicion", "Composición física", "fracción"),
    ("aprovechado_t", "Cantidad aprovechada", "t/año"),
    ("dispuesto_t", "Cantidad dispuesta", "t/año"),
    ("cobertura_recoleccion", "Cobertura de recolección", "fracción"),
    ("eca_numero", "Instalaciones de aprovechamiento (ECA)", "número"),
    ("relleno_nombre", "Sistema de disposición final", "texto"),
    ("capacidad_remanente_t", "Capacidad remanente de disposición", "t"),
    ("vida_util_reportada_anios", "Vida útil reportada", "años"),
]
COMPOSITION_VARS = ("frac_organicos", "frac_reciclables")


@dataclass
class CityProfile:
    divipola: str
    ciudad: str
    departamento: str
    region: str
    lat: float
    lon: float
    pop: pd.DataFrame
    obs: pd.DataFrame
    completeness: dict = field(default_factory=dict)

    def series(self, variable: str) -> pd.Series:
        d = self.obs[self.obs["variable"] == variable]
        v = pd.to_numeric(d["valor"], errors="coerce")
        return pd.Series(v.values, index=d["anio"].astype(int).values).dropna().sort_index()

    def text(self, variable: str):
        d = self.obs[self.obs["variable"] == variable].sort_values("anio")
        return None if d.empty else d.iloc[-1]

    def latest(self, variable: str, max_year: int | None = None):
        s = self.series(variable)
        if max_year is not None:
            s = s[s.index <= max_year]
        return (int(s.index[-1]), float(s.iloc[-1])) if len(s) else (None, np.nan)


class Repository:
    def __init__(self, proc_dir: Path = PROC):
        self.capitals = pd.read_csv(proc_dir / "capitales.csv", dtype={"divipola": str})
        self.population = pd.read_csv(proc_dir / "poblacion.csv", dtype={"divipola": str})
        obs_path = proc_dir / "residuos_observados.csv"
        self.observations = pd.read_csv(obs_path, dtype={"divipola": str, "valor": str}) if obs_path.exists() else pd.DataFrame(
            columns=["divipola", "anio", "variable", "valor", "unidad", "tipo_dato", "calidad", "fuente", "nota"])
        vpath = proc_dir / "data_version.json"
        self.data_version = json.loads(vpath.read_text()) if vpath.exists() else {}
        self._profiles: dict[str, CityProfile] = {}

    @property
    def codes(self):
        return list(self.capitals["divipola"])

    def name(self, code):
        return self.capitals.set_index("divipola").loc[code, "ciudad"]

    def code_of(self, name):
        return self.capitals.set_index("ciudad").loc[name, "divipola"]

    def profile(self, code: str) -> CityProfile:
        if code not in self._profiles:
            r = self.capitals.set_index("divipola").loc[code]
            pop = self.population[self.population["divipola"] == code].set_index("anio").sort_index()
            obs = self.observations[self.observations["divipola"] == code].copy()
            prof = CityProfile(code, r["ciudad"], r["departamento"], r["region"], float(r["lat"]), float(r["lon"]), pop, obs)
            prof.completeness = self._completeness(prof)
            self._profiles[code] = prof
        return self._profiles[code]

    def _completeness(self, prof: CityProfile) -> dict:
        have = set(prof.obs["variable"])
        res = {}
        for key, label, unit in PROFILE_VARIABLES:
            if key == "poblacion":
                ok = not prof.pop.empty
            elif key in ("generacion_pc", "generacion_t"):
                ok = "dispuesto_t" in have
            elif key == "composicion":
                ok = any(v in have for v in COMPOSITION_VARS)
            else:
                ok = key in have
            res[key] = bool(ok)
        hist = prof.series("dispuesto_t")
        res["_anios_historicos"] = int(hist[(hist.index >= 2018) & (hist.index <= 2024)].size)
        res["_score"] = round(100 * sum(v for k, v in res.items() if not k.startswith("_")) / len(PROFILE_VARIABLES), 0)
        return res

    def completeness_table(self) -> pd.DataFrame:
        rows = []
        for c in self.codes:
            p = self.profile(c)
            rows.append({"divipola": c, "ciudad": p.ciudad, "region": p.region, **p.completeness})
        return pd.DataFrame(rows)

    # ---------------------------------------------------------------- entradas del motor
    def pop_series(self, code: str, years, col: str = "poblacion_total") -> np.ndarray:
        s = self.profile(code).pop[col]
        return s.reindex(years).interpolate(limit_direction="both").to_numpy(float)

    def base_observations(self, code: str, base_year: int, kappa_default: float = np.nan) -> tuple[dict, dict]:
        """Observaciones del año base (o el más reciente anterior) y su procedencia."""
        p = self.profile(code)
        prov = {}
        y_d, disp = p.latest("dispuesto_t", base_year)
        y_a, apr = p.latest("aprovechado_t", base_year)
        y_k, kap = p.latest("cobertura_recoleccion", base_year)
        y_q, cap = p.latest("capacidad_remanente_t", base_year + 1)
        init = dict(W_obs=np.nan, R_obs=np.nan, O_obs=np.nan, Q_obs=np.nan, kappa_obs=np.nan)
        if np.isfinite(kap):
            init["kappa_obs"] = kap
            prov["kappa"] = f"observado {y_k}"
        k_used = kap if np.isfinite(kap) else kappa_default
        if np.isfinite(disp):
            tot = disp + (apr if np.isfinite(apr) else 0.0)
            # escalar la observación al año base con la población si es de un año anterior
            scale = 1.0
            if y_d != base_year:
                pp = self.pop_series(code, [y_d, base_year])
                scale = pp[1] / pp[0]
            init["W_obs"] = tot * scale / (k_used if np.isfinite(k_used) and k_used > 0 else 1.0)
            prov["generacion"] = f"estimada de dispuesto+aprovechado SSPD {y_d}" + (" (escalada por población)" if scale != 1 else "")
        if np.isfinite(apr):
            init["R_obs"] = apr
            prov["aprovechado"] = f"observado SSPD {y_a}"
        if np.isfinite(cap):
            init["Q_obs"] = cap
            prov["capacidad"] = f"reportada {y_q}"
        else:
            y_v, vida = p.latest("vida_util_reportada_anios", base_year + 2)
            if np.isfinite(vida):
                init["Q_years_obs"] = vida
                prov["capacidad"] = f"derivada de la vida útil reportada ({vida:g} años, {y_v})"
        return init, prov
