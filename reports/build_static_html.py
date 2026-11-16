"""
Genera una versión HTML autónoma del observatorio (sin servidor, sin internet).

    python reports/build_static_html.py  [salida.html]

Precalcula los 12 escenarios para las 32 capitales con el motor y los incrusta junto con plotly.js y los
límites departamentales simplificados (Natural Earth, dominio público). La interacción (ciudad, escenarios,
año, indicador) se resuelve en el navegador sobre los resultados precalculados; para cambiar parámetros o
palancas use la aplicación Streamlit.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.data import Repository  # noqa: E402
from core.quality import LABELS, city_flags  # noqa: E402
from core.scenarios import SCENARIOS  # noqa: E402
from core.simulation_engine import run_scenarios  # noqa: E402
from reports.report_generator import code_version, data_version  # noqa: E402
from validation.reliability import assess  # noqa: E402

VARS_INT = ["W", "G", "C", "U", "Sr", "So", "Mixed", "Rrec", "Kout", "Rej_r", "Rej_o", "Excess_r", "Excess_o", "Spill", "Ld", "Lf", "Overflow",
            "Prevented", "Q", "Krec", "Korg", "Prec", "Porg", "aprovechado_t", "dispuesto_total_t", "desviacion_acum_vs_bau_t", "pop"]
VARS_DEC = ["tasa_aprovechamiento", "gpc_kg_dia", "disp_pc_kg_dia", "util_rec", "util_org", "A", "P", "kappa"]


def build_payload():
    r = Repository()
    scen = list(SCENARIOS)
    df, meta = run_scenarios(r, r.codes, scen)
    years = sorted(df["anio"].unique().tolist())
    cities = {}
    for c in r.codes:
        p = r.profile(c)
        cal = r.calibration.get(c, {})
        rel = assess(p, cal)
        res = {}
        d = df[df.divipola == c]
        for s in scen:
            x = d[d.escenario == s].sort_values("anio")
            m = next(mm for mm in meta[s] if mm["divipola"] == c)
            res[s] = {"life": round(float(min(m["life"], 999)), 2)}
            for v in VARS_INT:
                res[s][v] = [int(round(float(z))) for z in x[v].fillna(0)]
            for v in VARS_DEC:
                res[s][v] = [round(float(z), 4) for z in x[v].fillna(0)]
        mb = next(mm for mm in meta["BAU"] if mm["divipola"] == c)
        site = {k: (None if p.text(k) is None else str(p.text(k)["valor"])) for k in ("relleno_nombre", "tipo_sitio", "sitio_ubicacion", "sitio_regional", "fecha_fin_vida_util")}
        fams = {v.replace("aprov_", "").replace("_t", ""): {int(k): round(float(val)) for k, val in p.series(v).items()}
                for v in p.obs["variable"].unique() if str(v).startswith("aprov_")}
        cities[c] = dict(
            ciudad=p.ciudad, departamento=p.departamento, region=p.region, lat=p.lat, lon=p.lon,
            pop_hist={int(k): int(v) for k, v in p.pop["poblacion_total"].items()},
            pop_tipo={int(k): v for k, v in p.pop["tipo_dato"].items()},
            obs_disp={int(k): round(float(v)) for k, v in p.series("dispuesto_t").items()},
            obs_apr={int(k): round(float(v)) for k, v in p.series("aprovechado_t").items()},
            obs_life={int(k): round(float(v), 2) for k, v in p.series("vida_util_reportada_anios").items()},
            familias=fams, sitio=site,
            calib=dict(status=cal.get("status"), years=cal.get("series", {}).get("years", []), sim_disp=[round(v) for v in cal.get("series", {}).get("sim_disp", [])],
                       sim_apr=[round(v) for v in cal.get("series", {}).get("sim_apr", [])], years_fit=cal.get("years_fit", []), years_val=cal.get("years_val", []),
                       uso_apr=cal.get("uso_aprovechamiento", True), params={k: round(v, 4) for k, v in cal.get("params", {}).items()},
                       g_fin=round(cal.get("g_growth_fin_serie", 0) or 0, 4)),
            nivel=rel["nivel"], nivel_desc=rel["descripcion"], smape_fit=rel.get("calibracion_sMAPE"), smape_val=rel.get("validacion_sMAPE"),
            limitaciones=rel["limitaciones"],
            flags=[dict(alerta=LABELS[f["codigo"]][0], severidad=f["severidad"], detalle=f["detalle"]) for f in city_flags(p)],
            procedencia=mb["provenance"], a0_topado=mb["A0_clipped"], capacidad_supuesta=mb["capacity_assumed"],
            init={k: round(v, 4) for k, v in mb["init_values"].items()}, res=res)
    return dict(
        generado=dt.datetime.now().strftime("%Y-%m-%d %H:%M"), version_codigo=code_version("3.0.0"), version_datos=data_version(r),
        years=years, escenarios={k: dict(label=v["label_es"], desc=v["desc_es"]) for k, v in SCENARIOS.items()}, cities=cities,
        orden=sorted(r.codes, key=lambda c: cities[c]["ciudad"]),
    )


def main(out_path: str | None = None):
    import plotly.offline
    payload = build_payload()
    geo = (ROOT / "data" / "geo" / "colombia_departamentos_ne10m_simplificado.json").read_text()
    tpl = (ROOT / "reports" / "static_template.html").read_text(encoding="utf-8")
    html = (tpl.replace("/*__PLOTLY__*/", plotly.offline.get_plotlyjs())
               .replace("/*__DATA__*/null", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
               .replace("/*__GEO__*/null", geo))
    out = Path(out_path or ROOT / "dist" / "observatorio_residuos_v3.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"{out} · {out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
