"""
Importador de las bases municipales de la Superintendencia de Servicios Públicos Domiciliarios (SSPD).

Archivos esperados en data/raw/sspd/ (nombres normalizados por el observatorio):

  sspd_DF_<año>.xlsx           Informe nacional de disposición final, base de datos (2019-2024).
                               Una fila por municipio atendido y sitio de disposición.
  sspd_DF_2018_informe.txt     Texto extraído (pdftotext -layout) del informe nacional de disposición final 2018,
                               Anexo 1 «Disposición final por municipio».
  sspd_AA_<año>.xlsx           Informe nacional de aprovechamiento, base de datos (2020-2024): hojas de toneladas
                               por municipio y familia de material, y de Estaciones de Clasificación y Aprovechamiento (ECA).

Variables producidas (formato largo, solo para las 32 capitales):
  dispuesto_t, relleno_nombre, tipo_sitio, sitio_ubicacion, sitio_regional, n_sitios_disposicion,
  fecha_fin_vida_util, vida_util_reportada_anios, aprovechado_t, aprov_<familia>_t,
  eca_numero, eca_capacidad_t
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

CAPITAL_ALIASES = {
    "91001": ["LETICIA"], "05001": ["MEDELLIN"], "81001": ["ARAUCA"], "08001": ["BARRANQUILLA"],
    "13001": ["CARTAGENA", "CARTAGENA DE INDIAS"], "15001": ["TUNJA"], "17001": ["MANIZALES"], "18001": ["FLORENCIA"],
    "85001": ["YOPAL"], "19001": ["POPAYAN"], "20001": ["VALLEDUPAR"], "27001": ["QUIBDO"], "23001": ["MONTERIA"],
    "11001": ["BOGOTA", "BOGOTA D C", "BOGOTA DC", "BOGOTA DISTRITO CAPITAL"], "94001": ["INIRIDA", "PUERTO INIRIDA"],
    "95001": ["SAN JOSE DEL GUAVIARE"], "41001": ["NEIVA"], "44001": ["RIOHACHA"], "47001": ["SANTA MARTA"],
    "50001": ["VILLAVICENCIO"], "52001": ["PASTO", "SAN JUAN DE PASTO"], "54001": ["CUCUTA", "SAN JOSE DE CUCUTA"],
    "86001": ["MOCOA"], "63001": ["ARMENIA"], "66001": ["PEREIRA"], "88001": ["SAN ANDRES"], "68001": ["BUCARAMANGA"],
    "70001": ["SINCELEJO"], "73001": ["IBAGUE"], "76001": ["CALI", "SANTIAGO DE CALI"], "97001": ["MITU"], "99001": ["PUERTO CARRENO"],
}
# Departamento de cada capital (prefijo normalizado) para desambiguar homónimos (Armenia-Antioquia, Florencia-Cauca, ...)
CAPITAL_DEPT = {"91001": "AMAZONAS", "05001": "ANTIOQUIA", "81001": "ARAUCA", "08001": "ATLANTICO", "13001": "BOLIVAR", "15001": "BOYACA",
                "17001": "CALDAS", "18001": "CAQUETA", "85001": "CASANARE", "19001": "CAUCA", "20001": "CESAR", "27001": "CHOCO",
                "23001": "CORDOBA", "11001": "BOGOTA", "94001": "GUAINIA", "95001": "GUAVIARE", "41001": "HUILA", "44001": "LA GUAJIRA",
                "47001": "MAGDALENA", "50001": "META", "52001": "NARINO", "54001": "NORTE DE SANTANDER", "86001": "PUTUMAYO",
                "63001": "QUINDIO", "66001": "RISARALDA", "88001": "ARCHIPIELAGO", "68001": "SANTANDER", "70001": "SUCRE", "73001": "TOLIMA",
                "76001": "VALLE", "97001": "VAUPES", "99001": "VICHADA"}
FAMILY_KEYS = {"PAPEL Y CARTON": "papel_carton", "PLASTICOS": "plasticos", "METALES": "metales", "VIDRIO": "vidrio", "MADERA": "madera",
               "TEXTIL": "textil", "TEXTILES": "textil"}
DF_SOURCE = "SSPD, Informe Nacional de Disposición Final {y} (base de datos municipal)"
DF18_SOURCE = "SSPD, Informe Nacional de Disposición Final 2018, Anexo 1 (extraído del PDF)"
AA_SOURCE = "SSPD, Informe Nacional de Aprovechamiento {y} (base de toneladas por municipio y familia de material)"
ECA_SOURCE = "SSPD, Informe Nacional de Aprovechamiento {y} (base de Estaciones de Clasificación y Aprovechamiento)"


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]+", " ", s)).strip()


_ALIAS_INDEX = {norm(a): c for c, al in CAPITAL_ALIASES.items() for a in al}


def match_capital(dept, muni):
    c = _ALIAS_INDEX.get(norm(muni))
    if c is None:
        return None
    d = norm(dept)
    want = CAPITAL_DEPT[c]
    if c == "88001":
        return c if ("SAN ANDRES" in d or d.startswith("ARCHIPIELAGO")) else None
    return c if d.startswith(want) or (c == "11001" and "BOGOTA" in d) else None


def _code(series):
    return series.astype(str).str.extract(r"(\d+)")[0].str.zfill(5)


def _row(code, year, var, val, unit, src, quality="reportado_SSPD", note="", tipo="observado"):
    return dict(divipola=code, anio=int(year), variable=var, valor=val, unidad=unit, tipo_dato=tipo, calidad=quality, fuente=src, nota=note)


def _first(cols, *keys):
    for c in cols:
        n = norm(c)
        if all(k in n for k in keys):
            return c
    return None


# ---------------------------------------------------------------------------------------------- disposición final
def load_df_year(path: Path, year: int, codes: set, report: list) -> list[dict]:
    x = pd.ExcelFile(path)
    sheet = next(s for s in x.sheet_names if norm(s).startswith("DISPOSICION"))
    d = pd.read_excel(x, sheet, dtype=str)
    cols = list(d.columns)
    code_c = _first(cols, "COD DANE ATENDIDO")
    d["divipola"] = _code(d[code_c])
    d = d[d["divipola"].isin(codes)].copy()
    tot_c = _first(cols, "TOTAL ANUAL") or _first(cols, "TONELADAS TOTALES")
    pd_c = _first(cols, "PROMEDIO", "DIA")
    if tot_c is not None:
        d["t_anual"] = pd.to_numeric(d[tot_c], errors="coerce")
        how = f"columna '{tot_c}'"
    else:
        d["t_anual"] = pd.to_numeric(d[pd_c], errors="coerce") * 365
        how = f"'{pd_c}' × 365"
    life_c = _first(cols, "FECHA", "VIDA")
    site_c, type_c = _first(cols, "NOMBRE DEL SITIO"), _first(cols, "TIPO DE SITIO")
    loc_c, reg_c = _first(cols, "MUNICIPIO UBICACION"), _first(cols, "REGIONAL")
    src = DF_SOURCE.format(y=year)
    rows = []
    for code, g in d.groupby("divipola"):
        g = g.sort_values("t_anual", ascending=False)
        main = g.iloc[0]
        rows.append(_row(code, year, "dispuesto_t", float(g["t_anual"].sum()), "t/año", src, note=f"Suma de {len(g)} sitio(s); {how}"))
        rows.append(_row(code, year, "n_sitios_disposicion", int(len(g)), "número", src))
        rows.append(_row(code, year, "relleno_nombre", str(main[site_c]).strip(), "texto", src, note=f"Sitio principal ({main['t_anual'] / max(g['t_anual'].sum(), 1e-9):.0%} del total)"))
        rows.append(_row(code, year, "tipo_sitio", str(main[type_c]).strip(), "texto", src))
        if loc_c:
            rows.append(_row(code, year, "sitio_ubicacion", str(main[loc_c]).strip().title(), "texto", src))
        if reg_c:
            rows.append(_row(code, year, "sitio_regional", str(main[reg_c]).strip().upper(), "texto", src))
        if life_c and pd.notna(main[life_c]) and str(main[life_c]).strip() not in ("", "nan", "NaT"):
            dt = pd.to_datetime(str(main[life_c]).strip(), errors="coerce", dayfirst="/" in str(main[life_c]))
            if pd.notna(dt):
                yrs = (dt - pd.Timestamp(f"{year}-12-31")).days / 365.25
                rows.append(_row(code, year, "fecha_fin_vida_util", dt.date().isoformat(), "fecha", src, note="Sitio principal"))
                rows.append(_row(code, year, "vida_util_reportada_anios", round(yrs, 2), "años", src,
                                 note=f"Fecha final de vida útil del sitio principal menos el 31-dic-{year}" + ("; VENCIDA" if yrs < 0 else "")))
    report.append(f"DF {year}: {len({r['divipola'] for r in rows})} capitales; toneladas por {how}.")
    return rows


def load_df2018_text(path: Path, codes: set, report: list) -> list[dict]:
    """Anexo 1 del informe 2018: DEPARTAMENTO  MUNICIPIO  TIPO  NOMBRE  PROMEDIO_TON_DIA (formato 1.234,56)."""
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    start = next(i for i, l in enumerate(lines) if "Anexo 1. Disposición final por municipio" in l)
    end = next(i for i, l in enumerate(lines) if "Anexo 2. Disposición final a nivel departamental" in l and i > start)
    acc: dict[str, list] = {}
    num = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d+|\d+,\d+)\s*$")
    block = lines[start:end]
    has_num = [bool(num.search(l)) for l in block]
    for i, l in enumerate(block):
        if not has_num[i]:
            continue
        # filas envueltas: se agregan las líneas vecinas SIN valor numérico (continuaciones de departamento/municipio)
        win = [block[j] for j in (i - 1, i, i + 1) if 0 <= j < len(block) and (j == i or not has_num[j])]
        dept_txt = " " + norm(" ".join(w[:18] for w in win)) + " "
        muni_txt = " " + norm(" ".join(w[12:34] for w in win)) + " "
        best = None
        for alias, code in sorted(_ALIAS_INDEX.items(), key=lambda kv: -len(kv[0])):
            if code in codes and f" {alias} " in muni_txt:
                want = CAPITAL_DEPT[code]
                okd = all(f" {w} " in dept_txt for w in want.split()) or (code == "88001" and ("SAN ANDRES" in dept_txt or "ARCHIPIELAGO" in dept_txt)) or (code == "11001" and "BOGOTA" in dept_txt)
                if okd:
                    best = code
                    break
        if best is None:
            continue
        val = float(num.search(l).group(1).replace(".", "").replace(",", "."))
        parts = re.split(r"\s{2,}", l.strip())
        site = " ".join(norm(w[60:100]) for w in win).strip()
        stype = " ".join(norm(w[30:58]) for w in win).strip()
        acc.setdefault(best, []).append((val, stype, site))
    rows = []
    for code, items in acc.items():
        items.sort(reverse=True)
        tot = sum(v for v, *_ in items) * 365
        rows.append(_row(code, 2018, "dispuesto_t", tot, "t/año", DF18_SOURCE, quality="reportado_SSPD_pdf",
                         note=f"Promedio ton/día × 365; {len(items)} sitio(s). El informe advierte que algunos municipios fueron proyectados por la SSPD."))
    report.append(f"DF 2018 (PDF): {len(acc)} capitales extraídas del Anexo 1.")
    return rows


# ---------------------------------------------------------------------------------------------- aprovechamiento
def load_aa_year(path: Path, year: int, codes: set, report: list) -> list[dict]:
    x = pd.ExcelFile(path)
    tsheet = next(s for s in x.sheet_names if "TONELADAS" in norm(s) or norm(s).startswith("BASE APROVECHAMIENTO"))
    t = pd.read_excel(x, tsheet)
    cols = list(t.columns)
    fam_c, tot_c = _first(cols, "FAMILIA"), _first(cols, "TOTAL TONELADAS")
    dep_c, mun_c, div_c = _first(cols, "DEPARTAMENTO"), _first(cols, "MUNICIPIO"), _first(cols, "DIVIPOLA")
    if div_c is not None:
        t["divipola"] = _code(t[div_c])
        miss = t["divipola"].isna()
        t.loc[miss, "divipola"] = [match_capital(a, b) for a, b in zip(t.loc[miss, dep_c], t.loc[miss, mun_c])]
    else:
        t["divipola"] = [match_capital(a, b) for a, b in zip(t[dep_c], t[mun_c])]
    t = t[t["divipola"].isin(codes)].copy()
    t["ton"] = pd.to_numeric(t[tot_c], errors="coerce")
    t["fam"] = t[fam_c].map(lambda s: FAMILY_KEYS.get(norm(s), "otros"))
    src = AA_SOURCE.format(y=year)
    rows = []
    for code, g in t.groupby("divipola"):
        rows.append(_row(code, year, "aprovechado_t", float(g["ton"].sum()), "t/año", src,
                         note="Toneladas efectivamente aprovechadas reportadas por prestadores de la actividad de aprovechamiento (no incluye orgánicos)"))
        for fam, gg in g.groupby("fam"):
            rows.append(_row(code, year, f"aprov_{fam}_t", float(gg["ton"].sum()), "t/año", src))
    # ECA
    esheet = next((s for s in x.sheet_names if "ECA" in norm(s)), None)
    n_eca = 0
    if esheet:
        e = pd.read_excel(x, esheet)
        ec = list(e.columns)
        ed, em, cap_c = _first(ec, "DEPARTAMENTO"), _first(ec, "MUNICIPIO"), _first(ec, "CAPACIDAD OPERATIVA")
        e["divipola"] = [match_capital(a, b) for a, b in zip(e[ed], e[em])]
        e = e[e["divipola"].isin(codes)].copy()
        e["cap"] = pd.to_numeric(e[cap_c], errors="coerce")
        bad = e["cap"].isin([9999]) | (e["cap"] <= 0)
        for code, g in e.groupby("divipola"):
            ok = g[~bad.loc[g.index]]
            rows.append(_row(code, year, "eca_numero", int(len(g)), "número", ECA_SOURCE.format(y=year)))
            if len(ok):
                rows.append(_row(code, year, "eca_capacidad_t", float(ok["cap"].sum() * 12), "t/año", ECA_SOURCE.format(y=year),
                                 note=f"Capacidad operativa (t/mes × 12) de {len(ok)} ECA; se excluyen {int(bad.loc[g.index].sum())} registros con valor 9999 o ≤ 0"))
            n_eca += 1
    report.append(f"AA {year}: {t['divipola'].nunique()} capitales con toneladas; {n_eca} con ECA.")
    return rows


# ---------------------------------------------------------------------------------------------- genérico
def load_all_sspd(raw_dir: Path, report: list | None = None, codes: set | None = None) -> pd.DataFrame:
    report = report if report is not None else []
    codes = codes or set(CAPITAL_ALIASES)
    d = Path(raw_dir) / "sspd"
    rows: list[dict] = []
    if not d.exists():
        return pd.DataFrame()
    for p in sorted(d.glob("sspd_DF_*.xlsx")):
        rows += load_df_year(p, int(re.search(r"(\d{4})", p.stem).group(1)), codes, report)
    t18 = d / "sspd_DF_2018_informe.txt"
    if t18.exists():
        rows += load_df2018_text(t18, codes, report)
    for p in sorted(d.glob("sspd_AA_*.xlsx")):
        rows += load_aa_year(p, int(re.search(r"(\d{4})", p.stem).group(1)), codes, report)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["valor"] = df["valor"].astype(str)
    return df
