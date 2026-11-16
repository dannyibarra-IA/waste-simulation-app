"""Regenera docs/data_dictionary.md desde el código.  Uso: python docs/build_dictionary.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.data import PROFILE_VARIABLES  # noqa: E402
from core.parameters import LEVERS, param_table  # noqa: E402
from core.simulation_engine import OUTPUT_COLUMNS  # noqa: E402

L = ["# Diccionario de datos", "", "Generado desde el código con `python docs/build_dictionary.py`.", "",
     "## Tablas procesadas", "", "| Archivo | Clave | Columnas |", "|---|---|---|",
     "| `capitales.csv` | divipola | ciudad, departamento, region, lat, lon, coord_fuente, coord_calidad |",
     "| `poblacion.csv` | divipola, anio | poblacion_total, poblacion_cabecera (hab), tipo_dato, fuente |",
     "| `residuos_observados.csv` | divipola, anio, variable | valor, unidad, tipo_dato, calidad, fuente, nota |", "",
     "**tipo_dato:** `base_censal_conciliada`, `proyeccion_oficial`, `observado`, `estimado`, `supuesto` o `simulado`. "
     "**calidad:** `reportado_SSPD`, `documental`, `oficial` o `aproximada`.", "",
     "## Variables del perfil de ciudad", "", "| Clave | Descripción | Unidad |", "|---|---|---|"]
L += [f"| {k} | {l} | {u} |" for k, l, u in PROFILE_VARIABLES]
L += ["", "## Salidas de simulación", "", "| Variable | Descripción | Unidad |", "|---|---|---|"]
L += [f"| {k} | {v[0]} | {v[2]} |" for k, v in OUTPUT_COLUMNS.items()]
L += ["| tasa_aprovechamiento | (Materiales recuperados + orgánicos tratados) / generación | fracción |",
      "| gpc_kg_dia | Generación per cápita | kg/hab/día |",
      "| disp_pc_kg_dia | Disposición per cápita (incluye déficit) | kg/hab/día |",
      "| desviacion_acum_vs_bau_t | Disposición evitada acumulada respecto al BAU | t |",
      "| vida_util_instantanea | Q / demanda de disposición | años |", "",
      "## Parámetros", "", param_table("es").to_markdown(index=False), "",
      "## Palancas de política", "", "| Palanca | Descripción | Unidad | Defecto |", "|---|---|---|---|"]
L += [f"| {k} | {v[0]} | {v[2]} | {v[3]} |" for k, v in LEVERS.items()]
(ROOT / "docs" / "data_dictionary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("docs/data_dictionary.md actualizado")
