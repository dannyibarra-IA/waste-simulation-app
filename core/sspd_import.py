"""
Importador de bases municipales de la Superintendencia de Servicios Públicos Domiciliarios (SSPD).

Acepta archivos `data/raw/sspd_*.csv` o `data/raw/sspd_*.xlsx`. Las columnas se reconocen por
palabras clave (sin tildes ni mayúsculas), de modo que distintas versiones de los informes nacionales
de disposición final y de aprovechamiento puedan cargarse sin editar código. Las filas se agregan a
nivel (municipio, año) y se devuelven en formato largo con fuente y calidad.

Si una columna no se reconoce, se ignora y se informa en `report`.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

# variable de salida -> (palabras clave que deben aparecer todas en el nombre de columna, unidad)
COLUMN_RULES = {
    "dispuesto_t": ([("dispuest",), ("disposicion", "ton"), ("toneladas", "dispuest")], "t/año"),
    "aprovechado_t": ([("aprovechad",), ("aprovechamiento", "ton"), ("toneladas", "aprovech")], "t/año"),
    "cobertura_recoleccion": ([("cobertura", "recole"), ("cobertura", "aseo")], "fracción"),
    "capacidad_remanente_t": ([("capacidad", "remanente"), ("capacidad", "disponible")], "t"),
    "vida_util_reportada_anios": ([("vida", "util"),], "años"),
    "relleno_nombre": ([("nombre", "sitio"), ("sitio", "disposicion"), ("relleno",)], "texto"),
    "tipo_sitio": ([("tipo", "sitio"),], "texto"),
    "eca_numero": ([("eca",), ("estaciones", "clasificacion")], "número"),
}
CODE_KEYS = [("divipola",), ("cod", "dane"), ("codigo", "municipio"), ("cod", "mpio"), ("dane",)]
YEAR_KEYS = [("anio",), ("ano",), ("vigencia",), ("year",)]
PERIOD_KEYS = [("mes",), ("periodo",)]


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def _match(col: str, key_sets) -> bool:
    c = _norm(col)
    return any(all(k in c for k in ks) for ks in key_sets)


def _find(cols, key_sets):
    for c in cols:
        if _match(c, key_sets):
            return c
    return None


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path)
    for enc in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(path, sep=None, engine="python", encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"No se pudo leer {path.name}")


def parse_sspd_table(df: pd.DataFrame, source_label: str, report: list | None = None) -> pd.DataFrame:
    report = report if report is not None else []
    cols = list(df.columns)
    code_c, year_c = _find(cols, CODE_KEYS), _find(cols, YEAR_KEYS)
    if code_c is None or year_c is None:
        report.append(f"{source_label}: no se encontró columna de código DIVIPOLA o de año; archivo omitido.")
        return pd.DataFrame()
    period_c = _find([c for c in cols if c not in (code_c, year_c)], PERIOD_KEYS)
    found = {}
    for var, (keys, unit) in COLUMN_RULES.items():
        c = _find([x for x in cols if x not in (code_c, year_c, period_c)], keys)
        if c is not None and c not in found.values():
            found[var] = c
    report.append(f"{source_label}: columnas reconocidas {found}" + (f"; periodo mensual en '{period_c}'" if period_c else ""))
    d = df.copy()
    d["divipola"] = d[code_c].astype(str).str.extract(r"(\d+)")[0].str.zfill(5)
    d["anio"] = pd.to_numeric(d[year_c], errors="coerce")
    d = d.dropna(subset=["anio"])
    d["anio"] = d["anio"].astype(int)
    out = []
    for var, c in found.items():
        unit = COLUMN_RULES[var][1]
        if unit == "texto":
            g = d.groupby(["divipola", "anio"])[c].agg(lambda s: "; ".join(sorted({str(v) for v in s.dropna()})))
        else:
            vals = pd.to_numeric(d[c].astype(str).str.replace(",", ".", regex=False).str.replace(r"[^\d.\-]", "", regex=True), errors="coerce")
            tmp = d.assign(_v=vals)
            # toneladas: se suman (varios sitios o meses); tasas y vidas útiles: promedio
            how = "sum" if var.endswith("_t") or var == "eca_numero" else "mean"
            g = tmp.groupby(["divipola", "anio"])["_v"].agg(how)
            if var == "cobertura_recoleccion":
                g = g.where(g <= 1.0, g / 100.0)
        g = g.reset_index().rename(columns={g.name if hasattr(g, "name") else c: "valor"})
        g.columns = ["divipola", "anio", "valor"]
        g["variable"], g["unidad"] = var, unit
        out.append(g)
    if not out:
        return pd.DataFrame()
    res = pd.concat(out, ignore_index=True)
    res["tipo_dato"] = "observado"
    res["calidad"] = "reportado_SSPD"
    res["fuente"] = source_label
    res["nota"] = ""
    return res


def load_all_sspd(raw_dir: Path, report: list | None = None) -> pd.DataFrame:
    frames = []
    for p in sorted(list(Path(raw_dir).glob("sspd_*.csv")) + list(Path(raw_dir).glob("sspd_*.xlsx"))):
        frames.append(parse_sspd_table(read_table(p), f"SSPD · {p.stem}", report))
    frames = [f for f in frames if not f.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
