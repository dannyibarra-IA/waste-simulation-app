"""Manifiestos de ejecución, libro Excel, paquete reproducible e informe PDF."""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import subprocess
import uuid
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from core.parameters import PARAMS, param_table
from core.scenarios import SCENARIOS, levers_for
from core.simulation_engine import BASE_YEAR, END_YEAR, city_params

ROOT = Path(__file__).resolve().parents[1]

SOURCES = [
    "DANE (2025). Proyecciones de población municipal por área geográfica 2018-2042. Actualización del 30 de julio de 2025.",
    "SSPD. Informes nacionales de disposición final y de aprovechamiento; Sistema Único de Información (SUI). (Cuando se cargan en data/raw/.)",
    "DNP, CEMPRE y CEPAL (2021). Encuesta a municipios sobre gestión de residuos sólidos domiciliarios 2019 – Colombia. LC/TS.2021/67.",
    "CATF (2024). Colombia waste sector fact sheet.",
    "Bass, F. M. (1969). A new product growth for model consumer durables. Management Science, 15(5), 215-227.",
    "Sultan, F., Farley, J. U. y Lehmann, D. R. (1990). A meta-analysis of applications of diffusion models. Journal of Marketing Research, 27(1), 70-77.",
    "Argote, L. y Epple, D. (1990). Learning curves in manufacturing. Science, 247(4945), 920-924.",
    "Morris, M. D. (1991). Factorial sampling plans for preliminary computational experiments. Technometrics, 33(2), 161-174.",
    "Campolongo, F., Cariboni, J. y Saltelli, A. (2007). An effective screening design for sensitivity analysis of large models. Environmental Modelling & Software, 22(10), 1509-1518.",
]


def code_version(app_version: str) -> str:
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=3).stdout.strip()
    except Exception:
        h = ""
    if not h:
        h = hashlib.sha256((ROOT / "core" / "system_dynamics.py").read_bytes()).hexdigest()[:8]
    return f"{app_version}+{h}"


def data_version(repo) -> str:
    v = repo.data_version
    return hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest()[:10] if v else "sin-version"


def build_manifest(repo, codes, scenarios, lever_overrides, param_overrides, seed, app_version):
    scen = list(dict.fromkeys(["BAU"] + list(scenarios)))
    params = {}
    for c in codes:
        po = (param_overrides or {}).get(c)
        par, origin = city_params(repo, c, po)
        params[c] = {k: dict(valor=par[k], origen=origin[k]) for k in par}
    return dict(
        run_id=uuid.uuid4().hex[:12], fecha_ejecucion=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        aplicacion="Colombia Circular Waste Observatory — Waste Simulation App", autor_original="Danny Ibarra Vega, Ph.D., Universidad de Antioquia",
        code_version=code_version(app_version), data_version=data_version(repo), data_files=repo.data_version,
        ciudades=[dict(divipola=c, ciudad=repo.name(c)) for c in codes], escenarios=scen, horizonte=[BASE_YEAR, END_YEAR], paso_integracion_anios=0.25,
        palancas_por_escenario={s: levers_for(s, lever_overrides) for s in scen}, ajustes_palancas_usuario=lever_overrides or {},
        parametros=params, semilla_montecarlo=seed, fuentes=SOURCES,
    )


def excel_bytes(repo, df, man) -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        pd.DataFrame([dict(clave=k, valor=json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in man.items() if k != "parametros"]).to_excel(w, "manifiesto", index=False)
        df.to_excel(w, "resultados", index=False)
        ind = df[["divipola", "ciudad", "escenario", "anio", "pop", "G", "gpc_kg_dia", "C", "aprovechado_t", "tasa_aprovechamiento", "dispuesto_total_t", "disp_pc_kg_dia",
                  "Q", "util_rec"] + [c for c in ("desviacion_acum_vs_bau_t",) if c in df]]
        ind.to_excel(w, "indicadores_anuales", index=False)
        rows = [dict(divipola=c, parametro=k, **v) for c, pr in man["parametros"].items() for k, v in pr.items()]
        pd.DataFrame(rows).to_excel(w, "parametros", index=False)
        param_table("es").to_excel(w, "registro_parametros", index=False)
        codes = [c["divipola"] for c in man["ciudades"]]
        repo.population[repo.population.divipola.isin(codes)].to_excel(w, "poblacion_DANE", index=False)
        repo.observations[repo.observations.divipola.isin(codes)].to_excel(w, "observaciones", index=False)
        pd.DataFrame(dict(fuente=man["fuentes"])).to_excel(w, "fuentes", index=False)
    return bio.getvalue()


RERUN = '''"""Reproduce la ejecución descrita en manifest.json con el código del repositorio.

    python rerun.py manifest.json            (desde la raíz del repositorio waste-simulation-app)
"""
import json, sys
import pandas as pd
from core.data import Repository
from core.simulation_engine import run_scenarios

man = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "manifest.json", encoding="utf-8"))
po = {c: {k: v["valor"] for k, v in p.items() if v["origen"] == "ajustado por el usuario"} for c, p in man["parametros"].items()}
po = {c: v for c, v in po.items() if v}
df, _ = run_scenarios(Repository(), [c["divipola"] for c in man["ciudades"]], man["escenarios"], man["ajustes_palancas_usuario"] or None, po or None)
ref = pd.read_csv("resultados.csv", dtype={"divipola": str})
diff = (df["G"].to_numpy() - ref["G"].to_numpy())
print("filas:", len(df), "· máx. diferencia en generación (t):", float(abs(diff).max()))
'''


def zip_package(repo, df, man) -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(man, indent=2, ensure_ascii=False))
        z.writestr("resultados.csv", df.to_csv(index=False))
        z.writestr("escenarios.json", json.dumps({k: v for k, v in SCENARIOS.items()}, indent=2, ensure_ascii=False))
        z.writestr("registro_parametros.csv", param_table("es").to_csv(index=False))
        for p in sorted((ROOT / "data" / "processed").glob("*")):
            z.write(p, f"data/processed/{p.name}")
        z.writestr("rerun.py", RERUN)
        z.writestr("LEEME.txt", "Paquete reproducible del Colombia Circular Waste Observatory.\n"
                                f"Ejecución {man['run_id']} · código {man['code_version']} · datos {man['data_version']}.\n"
                                "Para reproducir: copie rerun.py, manifest.json y resultados.csv a la raíz del repositorio (versión indicada) y ejecute python rerun.py manifest.json.\n")
    return bio.getvalue()


def _fig_png(fn):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=200)
    fn(ax)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    b = io.BytesIO()
    fig.savefig(b, format="png")
    plt.close(fig)
    b.seek(0)
    return b


def pdf_report(repo, df, meta, man, code, lang="es") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    ss = getSampleStyleSheet()
    H1, H2, B = ss["Title"], ss["Heading2"], ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=13)
    small = ParagraphStyle("s", parent=B, fontSize=7.5, leading=10, textColor=colors.HexColor("#5d6b76"))
    name = repo.name(code)
    d = df[df.divipola == code]
    scen = man["escenarios"]
    m = {s: next(x for x in meta[s] if x["divipola"] == code) for s in scen if s in meta}
    els = [Paragraph("Colombia Circular Waste Observatory", small), Paragraph(f"Informe de simulación · {name}", H1),
           Paragraph(f"Ejecución <b>{man['run_id']}</b> · {man['fecha_ejecucion']} · código {man['code_version']} · datos {man['data_version']} · horizonte "
                     f"{man['horizonte'][0]}–{man['horizonte'][1]} · semilla {man['semilla_montecarlo']}", small), Spacer(1, 8)]
    mb = m.get("BAU", next(iter(m.values())))
    status = []
    if mb["exploratory"]:
        status.append("La ciudad no tiene series observadas de residuos cargadas: la generación usa la referencia nacional de 0,75 kg/hab/día. Simulación EXPLORATORIA.")
    if mb["capacity_assumed"]:
        status.append("La capacidad remanente de disposición es un SUPUESTO; la vida útil reportada no es un dato.")
    if status:
        els += [Paragraph("<b>Advertencias de datos.</b> " + " ".join(status), B), Spacer(1, 6)]

    els.append(Paragraph("1. Resultados por escenario", H2))
    hs = ParagraphStyle("h", parent=B, fontSize=7.2, leading=8.6, fontName="Helvetica-Bold")
    rows = [[Paragraph(h, hs) for h in ("Escenario", "Generación 2050 (t)", "Aprovechado 2050 (t)", "Tasa 2050", "Desviación acum. vs BAU (t)", "Vida útil (años)")]]
    for s in scen:
        x = d[d.escenario == s].set_index("anio")
        if x.empty:
            continue
        rows.append([Paragraph(SCENARIOS[s]["label_es"], ParagraphStyle("c", parent=B, fontSize=7.5, leading=9)), f"{x.loc[END_YEAR, 'G']:,.0f}", f"{x.loc[END_YEAR, 'aprovechado_t']:,.0f}", f"{x.loc[END_YEAR, 'tasa_aprovechamiento']:.1%}",
                     f"{x.loc[END_YEAR, 'desviacion_acum_vs_bau_t']:,.0f}" if "desviacion_acum_vs_bau_t" in x else "—", f"{min(m[s]['life'], 100):.1f}"])
    t = Table(rows, repeatRows=1, colWidths=[4.6 * cm, 2.6 * cm, 2.6 * cm, 1.6 * cm, 3.0 * cm, 2.0 * cm])
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 7.5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3ecf3")),
                           ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c8d0d6")), ("ALIGN", (1, 1), (-1, -1), "RIGHT")]))
    els += [t, Spacer(1, 8)]
    pal = ["#8c99a3", "#1f5f8b", "#2e7d5b", "#b8860b", "#6b5b95", "#b23a2e", "#3a9e8f", "#5b9bc8", "#a0522d", "#2f4f4f", "#c71585", "#556b2f"]

    def plot(col, ylabel, scale=1.0):
        def f(ax):
            for i, s in enumerate(scen):
                x = d[d.escenario == s]
                ax.plot(x["anio"], x[col] * scale, label=SCENARIOS[s]["label_es"], color=pal[i % len(pal)], lw=1.8, ls="--" if s == "BAU" else "-")
            ax.set_ylabel(ylabel, fontsize=8)
            ax.tick_params(labelsize=7)
            ax.legend(fontsize=6, ncol=3, frameon=False)
        return f

    for col, lab, sc in (("dispuesto_total_t", "Disposición (t/año)", 1), ("tasa_aprovechamiento", "Tasa de aprovechamiento (%)", 100), ("Q", "Capacidad remanente (t)", 1)):
        els += [Image(_fig_png(plot(col, lab, sc)), width=16.5 * cm, height=7.3 * cm), Spacer(1, 4)]
    els += [PageBreak(), Paragraph("2. Método", H2), Paragraph(
        "Modelo de Dinámica de Sistemas con ocho niveles (capacidad remanente de disposición, disposición acumulada, capacidad de clasificación, capacidad de tratamiento de orgánicos, "
        "inventario de materiales, capacidad organizativa de recicladores, adopción de la separación en la fuente y experiencia acumulada), integrado por Euler con paso de 0,25 años. "
        "Incluye cinco bucles de balance (saturación de capacidad, de mercado, de adopción, disponibilidad de materiales y agotamiento de la disposición) y tres de refuerzo "
        "(adopción social, aprendizaje operativo e incremento del aprovechamiento). El balance de materia G = U + L + Déficit + V + K + ΔI se verifica en cada paso.", B),
            Paragraph("3. Supuestos y parámetros", H2)]
    pr = man["parametros"][code]
    cs = ParagraphStyle("pc", parent=B, fontSize=6.8, leading=8)
    prow = [["Parámetro", "Valor", "Unidad", "Origen"]] + [[Paragraph(PARAMS[k].label_es, cs), f"{v['valor']:.4g}", Paragraph(PARAMS[k].unit, cs), Paragraph(v["origen"], cs)]
                                                       for k, v in pr.items()]
    pt = Table(prow, repeatRows=1, colWidths=[8.2 * cm, 2.0 * cm, 3.2 * cm, 3.4 * cm])
    pt.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 6.8), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3ecf3")),
                            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c8d0d6"))]))
    els += [pt, Paragraph("4. Limitaciones", H2), Paragraph(
        "Los resultados son simulaciones condicionadas a los supuestos declarados. Los parámetros de clase «supuesto» no tienen respaldo documental específico. "
        "Las bandas de Monte Carlo representan incertidumbre de parámetros, no la estructural ni la de escenario. La población 2043-2050 es una extensión estimada de la serie DANE. "
        "Un nivel de confiabilidad A o B exige validación fuera de muestra con series SSPD.", B),
            Paragraph("5. Reproducibilidad", H2), Paragraph(f"Palancas de usuario: {json.dumps(man['ajustes_palancas_usuario'], ensure_ascii=False) or '{}'}. "
                                                             "Descargue el paquete reproducible (ZIP) para repetir esta ejecución con rerun.py.", B),
            Paragraph("Fuentes", H2)] + [Paragraph(x, small) for x in man["fuentes"]]
    bio = io.BytesIO()
    SimpleDocTemplate(bio, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                      title=f"Informe {name}", author=man["autor_original"]).build(els)
    return bio.getvalue()
