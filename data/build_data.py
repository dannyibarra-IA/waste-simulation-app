"""
Construye las tablas procesadas del observatorio a partir de las fuentes crudas.

    python data/build_data.py

Entradas (data/raw/):
  - DANE_PPED_AreaMun_2018_2042_VP.xlsx  (DANE, Proyecciones de población municipal por área, 2018-2042,
    actualización del 30 de julio de 2025)
  - sspd_*.csv / sspd_*.xlsx  (opcional; bases municipales de la SSPD, ver core/sspd_import.py)

Salidas (data/processed/):
  - capitales.csv           metadatos de las 32 capitales (DIVIPOLA, departamento, región, coordenadas)
  - poblacion.csv           población total y cabecera 2018-2050 con tipo de dato por fila
  - residuos_observados.csv observaciones de residuos por ciudad, año y variable (con fuente y calidad)
  - data_version.json       huella (hash) de cada archivo procesado
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW, OUT = ROOT / "raw", ROOT / "processed"
DANE_FILE = RAW / "DANE_PPED_AreaMun_2018_2042_VP.xlsx"
DANE_SOURCE = ("DANE (2025). Proyecciones de población municipal por área geográfica 2018-2042, "
               "actualización 30-jul-2025. Modelo de componentes de cohortes.")
HORIZON = 2050
EXT_WINDOW = 5  # años finales de la serie DANE usados para extender a 2050

# Coordenadas aproximadas del casco urbano (grados decimales). Calidad "aproximada":
# se usan solo para ubicar marcadores en el mapa, no en cálculos.
CAPITALS = [
    # divipola, nombre corto, departamento, región (convención del observatorio), lat, lon
    ("91001", "Leticia", "Amazonas", "Amazonía", -4.2153, -69.9406),
    ("05001", "Medellín", "Antioquia", "Andina", 6.2442, -75.5812),
    ("81001", "Arauca", "Arauca", "Orinoquía", 7.0847, -70.7591),
    ("08001", "Barranquilla", "Atlántico", "Caribe", 10.9685, -74.7813),
    ("13001", "Cartagena de Indias", "Bolívar", "Caribe", 10.3910, -75.4794),
    ("15001", "Tunja", "Boyacá", "Andina", 5.5353, -73.3678),
    ("17001", "Manizales", "Caldas", "Andina", 5.0703, -75.5138),
    ("18001", "Florencia", "Caquetá", "Amazonía", 1.6144, -75.6062),
    ("85001", "Yopal", "Casanare", "Orinoquía", 5.3378, -72.3959),
    ("19001", "Popayán", "Cauca", "Pacífica", 2.4448, -76.6147),
    ("20001", "Valledupar", "Cesar", "Caribe", 10.4631, -73.2532),
    ("27001", "Quibdó", "Chocó", "Pacífica", 5.6947, -76.6611),
    ("23001", "Montería", "Córdoba", "Caribe", 8.7479, -75.8814),
    ("11001", "Bogotá D. C.", "Bogotá D. C. (capital de Cundinamarca)", "Andina", 4.7110, -74.0721),
    ("94001", "Inírida", "Guainía", "Amazonía", 3.8653, -67.9239),
    ("95001", "San José del Guaviare", "Guaviare", "Amazonía", 2.5729, -72.6459),
    ("41001", "Neiva", "Huila", "Andina", 2.9273, -75.2819),
    ("44001", "Riohacha", "La Guajira", "Caribe", 11.5444, -72.9072),
    ("47001", "Santa Marta", "Magdalena", "Caribe", 11.2408, -74.1990),
    ("50001", "Villavicencio", "Meta", "Orinoquía", 4.1420, -73.6266),
    ("52001", "Pasto", "Nariño", "Pacífica", 1.2136, -77.2811),
    ("54001", "San José de Cúcuta", "Norte de Santander", "Andina", 7.8939, -72.5078),
    ("86001", "Mocoa", "Putumayo", "Amazonía", 1.1522, -76.6460),
    ("63001", "Armenia", "Quindío", "Andina", 4.5339, -75.6811),
    ("66001", "Pereira", "Risaralda", "Andina", 4.8133, -75.6961),
    ("88001", "San Andrés", "Archipiélago de San Andrés, Providencia y Santa Catalina", "Insular", 12.5847, -81.7006),
    ("68001", "Bucaramanga", "Santander", "Andina", 7.1254, -73.1198),
    ("70001", "Sincelejo", "Sucre", "Caribe", 9.3047, -75.3978),
    ("73001", "Ibagué", "Tolima", "Andina", 4.4389, -75.2322),
    ("76001", "Cali", "Valle del Cauca", "Pacífica", 3.4516, -76.5320),
    ("97001", "Mitú", "Vaupés", "Amazonía", 1.2537, -70.2345),
    ("99001", "Puerto Carreño", "Vichada", "Orinoquía", 6.1890, -67.4859),
]


def build_capitals() -> pd.DataFrame:
    df = pd.DataFrame(CAPITALS, columns=["divipola", "ciudad", "departamento", "region", "lat", "lon"])
    df["coord_fuente"] = "Coordenadas aproximadas del casco urbano (referencia geográfica general)"
    df["coord_calidad"] = "aproximada"
    return df


def build_population(capitals: pd.DataFrame) -> pd.DataFrame:
    raw = pd.read_excel(DANE_FILE, sheet_name="PobMunicipalxÁrea", header=7, dtype={"DP": str, "MPIO": str})
    raw = raw.dropna(subset=["MPIO"])
    raw = raw[raw["MPIO"].isin(capitals["divipola"])]
    raw["AÑO"] = raw["AÑO"].astype(int)
    piv = raw.pivot_table(index=["MPIO", "AÑO"], columns="ÁREA GEOGRÁFICA", values="TOTAL", aggfunc="sum").reset_index()
    piv = piv.rename(columns={"MPIO": "divipola", "AÑO": "anio", "Total": "poblacion_total", "Cabecera Municipal": "poblacion_cabecera"})
    piv = piv[["divipola", "anio", "poblacion_total", "poblacion_cabecera"]]
    piv["tipo_dato"] = "proyeccion_oficial"
    piv.loc[piv["anio"] == 2018, "tipo_dato"] = "base_censal_conciliada"
    piv["fuente"] = DANE_SOURCE

    # Extensión 2043-2050: tasa media logarítmica de los últimos EXT_WINDOW años de la serie oficial.
    ext = []
    for code, g in piv.groupby("divipola"):
        g = g.sort_values("anio")
        last = g.iloc[-1]
        win = g.tail(EXT_WINDOW + 1)
        rate = {c: np.log(win[c].iloc[-1] / win[c].iloc[0]) / EXT_WINDOW for c in ("poblacion_total", "poblacion_cabecera")}
        for y in range(int(last["anio"]) + 1, HORIZON + 1):
            k = y - int(last["anio"])
            ext.append(dict(
                divipola=code, anio=y,
                poblacion_total=float(last["poblacion_total"] * np.exp(rate["poblacion_total"] * k)),
                poblacion_cabecera=float(last["poblacion_cabecera"] * np.exp(rate["poblacion_cabecera"] * k)),
                tipo_dato="estimado",
                fuente=f"Extensión del observatorio: tasa media log de {int(last['anio']) - EXT_WINDOW}-{int(last['anio'])} (DANE) aplicada a {int(last['anio']) + 1}-{HORIZON}",
            ))
    pop = pd.concat([piv, pd.DataFrame(ext)], ignore_index=True).sort_values(["divipola", "anio"])
    return pop.reset_index(drop=True)


def build_waste_observations() -> pd.DataFrame:
    """Une las observaciones de residuos disponibles: importaciones SSPD y registros documentales verificados."""
    from core.sspd_import import load_all_sspd  # import tardío para que el script funcione sin la app

    frames = [load_all_sspd(RAW)]
    doc = ROOT / "raw" / "registros_documentales.csv"
    if doc.exists():
        frames.append(pd.read_csv(doc, dtype={"divipola": str}))
    frames = [f for f in frames if f is not None and not f.empty]
    cols = ["divipola", "anio", "variable", "valor", "unidad", "tipo_dato", "calidad", "fuente", "nota"]
    if not frames:
        return pd.DataFrame(columns=cols)
    df = pd.concat(frames, ignore_index=True)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols].drop_duplicates(subset=["divipola", "anio", "variable", "fuente"], keep="last")
    return df.sort_values(["divipola", "variable", "anio"]).reset_index(drop=True)


def file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def main():
    import sys
    sys.path.insert(0, str(ROOT.parent))
    OUT.mkdir(parents=True, exist_ok=True)
    caps = build_capitals()
    caps.to_csv(OUT / "capitales.csv", index=False)
    pop = build_population(caps)
    missing = set(caps["divipola"]) - set(pop["divipola"])
    if missing:
        raise SystemExit(f"Faltan capitales en el archivo DANE: {missing}")
    pop.to_csv(OUT / "poblacion.csv", index=False)
    obs = build_waste_observations()
    obs.to_csv(OUT / "residuos_observados.csv", index=False)
    version = {p.name: file_hash(p) for p in sorted(OUT.glob("*.csv"))}
    version["generado_por"] = "data/build_data.py"
    (OUT / "data_version.json").write_text(json.dumps(version, indent=2, ensure_ascii=False))
    print(f"capitales: {len(caps)} · población: {len(pop)} filas · observaciones de residuos: {len(obs)} filas")


if __name__ == "__main__":
    main()
