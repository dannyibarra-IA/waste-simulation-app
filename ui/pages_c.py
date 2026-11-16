"""Módulos 9-12: riesgos y alertas, sensibilidad e incertidumbre, metodología y fuentes, descargas."""
from __future__ import annotations

import io
import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.data import PROFILE_VARIABLES
from core.parameters import LEVERS, PARAMS, param_table
from core.scenarios import SCENARIOS
from ui.common import APP_VERSION, exploratory_notice, fmt_t, hero, intro, kpi, life_text, repo, results, scen_label, show, table, tr
from visualization.charts import C, band_fig, morris_fig, tornado_fig

RISK_REFS = dict(per_capita=(0.60, 1.30), growth=(0.0, 3.0), landfill_life=(30.0, 5.0), collection_gap=(0.0, 0.30), diversion=(0.50, 0.10))
DEFAULT_WEIGHTS = dict(per_capita=20, growth=20, landfill_life=30, collection_gap=15, diversion=15)


def _risk(x, good, bad):
    return float(np.clip((x - good) / (bad - good), 0, 1))


def risk_labels():
    return dict(per_capita=tr("Generación per cápita", "Per-capita generation"), growth=tr("Crecimiento de la generación (TCAC)", "Generation growth (CAGR)"),
                landfill_life=tr("Agotamiento de disposición", "Landfill exhaustion"), collection_gap=tr("Brecha de recolección", "Collection gap"),
                diversion=tr("Bajo aprovechamiento", "Low recovery"))


def priority_table(df, meta, scen, year, weights):
    d = df[df.escenario == scen]
    mm = {m["divipola"]: m for m in meta[scen]}
    rows = []
    for c, g in d.groupby("divipola"):
        g = g.set_index("anio")
        r_ = g.loc[year]
        cagr = ((g.loc[year, "G"] / g["G"].iloc[0]) ** (1 / max(year - g.index[0], 1)) - 1) * 100
        comp = dict(per_capita=_risk(r_["gpc_kg_dia"], *RISK_REFS["per_capita"]), growth=_risk(cagr, *RISK_REFS["growth"]),
                    landfill_life=_risk(min(mm[c]["life"], 100), *RISK_REFS["landfill_life"]), collection_gap=_risk(1 - r_["kappa"], *RISK_REFS["collection_gap"]),
                    diversion=_risk(r_["tasa_aprovechamiento"], *RISK_REFS["diversion"]))
        score = 100 * sum(weights[k] * comp[k] for k in comp) / max(sum(weights.values()), 1e-9)
        rows.append(dict(divipola=c, ciudad=r_["ciudad"], puntaje=score, exploratorio=mm[c]["exploratory"], capacidad_supuesta=mm[c]["capacity_assumed"],
                         vida_util=min(mm[c]["life"], 100), tcac_pct=cagr, gpc=r_["gpc_kg_dia"], tasa=r_["tasa_aprovechamiento"], cobertura=r_["kappa"],
                         **{f"r_{k}": v for k, v in comp.items()}))
    t = pd.DataFrame(rows)
    t["nivel"] = pd.cut(t["puntaje"].clip(0, 100), [-0.01, 33, 66, 100], labels=[tr("Bajo", "Low"), tr("Medio", "Medium"), tr("Alto", "High")])
    return t.sort_values("puntaje", ascending=False).reset_index(drop=True)


def alerts(row, life, cagr, capacity_assumed):
    a = []
    sfx = tr(" (capacidad supuesta: interpretar como exploratorio)", " (assumed capacity: exploratory)") if capacity_assumed else ""
    if life < 5:
        a.append(("Alta", tr(f"Vida útil estimada de {life_text(life)} años (< 5)", f"Estimated life {life_text(life)} yr (< 5)") + sfx))
    elif life < 10:
        a.append(("Media", tr(f"Vida útil estimada de {life_text(life)} años (< 10)", f"Estimated life {life_text(life)} yr (< 10)") + sfx))
    if row["Overflow"] > 0:
        a.append(("Alta", tr(f"Déficit de capacidad de disposición de {fmt_t(row['Overflow'])} t en el año de referencia.", f"Disposal deficit of {fmt_t(row['Overflow'])} t.")))
    if row["kappa"] < 0.90:
        a.append(("Alta", tr("Cobertura de recolección < 90 %.", "Collection coverage < 90 %.")))
    if row["tasa_aprovechamiento"] < 0.10:
        a.append(("Alta", tr(f"Tasa de aprovechamiento de {row['tasa_aprovechamiento']:.1%} (< 10 %).", f"Recovery rate {row['tasa_aprovechamiento']:.1%} (< 10 %).")))
    elif row["tasa_aprovechamiento"] < 0.25:
        a.append(("Media", tr(f"Tasa de aprovechamiento de {row['tasa_aprovechamiento']:.1%} (< 25 %).", f"Recovery rate {row['tasa_aprovechamiento']:.1%} (< 25 %).")))
    if row["util_rec"] > 0.97:
        a.append(("Media", tr("Capacidad de clasificación saturada (> 97 %).", "Sorting capacity saturated (> 97 %).")))
    if row["P"] < 0.7:
        a.append(("Media", tr("Índice de precio de materiales < 0,7: saturación de mercado.", "Material price index < 0.7: market saturation.")))
    if cagr > 1.5:
        a.append(("Media", tr(f"La generación crece {cagr:.2f} %/año.", f"Generation grows {cagr:.2f} %/yr.")))
    return a or [("Baja", tr("No se activan alertas estructurales.", "No structural alerts."))]


# ------------------------------------------------------------------------------------------------ 9
def page_risks():
    s = st.session_state
    r = repo()
    hero(tr("Riesgos y alertas", "Risks and alerts"), tr("Índice de prioridad con umbrales absolutos (no relativos al grupo) y consola de alertas de la ciudad de análisis.",
                                                         "Absolute-threshold priority index and alert console."))
    df, meta = results(r.codes, s.scenarios)
    scen = s.scenario_focus
    d = df[(df.escenario == scen) & (df.divipola == s.city)].set_index("anio")
    m = next(x for x in meta[scen] if x["divipola"] == s.city)
    cagr = ((d.loc[s.year, "G"] / d["G"].iloc[0]) ** (1 / max(s.year - d.index[0], 1)) - 1) * 100
    st.markdown("#### " + tr(f"Consola de alertas · {r.name(s.city)} · {s.year} · {scen_label(scen)}", f"Alert console · {r.name(s.city)}"))
    exploratory_notice(m)
    for sev, msg in alerts(d.loc[s.year], m["life"], cagr, m["capacity_assumed"]):
        {"Alta": st.error, "Media": st.warning}.get(sev, st.success)(f"**{sev}** · {msg}")
    rl = risk_labels()
    with st.expander(tr("Pesos del índice de prioridad", "Priority index weights")):
        cols = st.columns(5)
        w = {k: cols[i].slider(rl[k], 0, 100, DEFAULT_WEIGHTS[k], 5, key=f"w_{k}") for i, k in enumerate(rl)}
        if sum(w.values()) == 0:
            w = dict(DEFAULT_WEIGHTS)
    t = priority_table(df, meta, scen, s.year, w)
    t["etiqueta"] = t["ciudad"] + np.where(t["exploratorio"], " *", "")
    f = px.bar(t, x="etiqueta", y="puntaje", color="nivel", color_discrete_map={tr("Bajo", "Low"): C["green"], tr("Medio", "Medium"): "#d9a400", tr("Alto", "High"): C["red"]},
               title=tr(f"Índice de prioridad {s.year} (* exploratorio)", f"Priority index {s.year} (* exploratory)"), labels=dict(puntaje="0-100", etiqueta=""))
    f.update_layout(height=430, xaxis_tickangle=-40)
    show(f, "rk_bar")
    n_exp = int(t["exploratorio"].sum())
    if n_exp:
        st.warning(tr(f"{n_exp} ciudades del ranking son exploratorias: su posición refleja supuestos comunes, no diferencias observadas. "
                      "El ranking no es comparable rigurosamente hasta cargar sus series SSPD.",
                      f"{n_exp} ranked cities are exploratory; the ranking is not rigorously comparable."))
    sel = t[t.divipola == s.city]
    theta = list(rl.values())
    fr = go.Figure()
    fr.add_trace(go.Scatterpolar(r=[t[f"r_{k}"].mean() for k in rl] + [t[f"r_{list(rl)[0]}"].mean()], theta=theta + theta[:1], name=tr("Promedio 32 capitales", "32-capital mean"),
                                 line=dict(color=C["grey"], dash="dash")))
    if not sel.empty:
        fr.add_trace(go.Scatterpolar(r=[float(sel.iloc[0][f"r_{k}"]) for k in rl] + [float(sel.iloc[0][f"r_{list(rl)[0]}"])], theta=theta + theta[:1], name=r.name(s.city),
                                     fill="toself", line=dict(color=C["red"], width=3)))
    fr.update_layout(polar=dict(radialaxis=dict(range=[0, 1])), height=420, title=tr("Perfil de riesgo (0 = bueno, 1 = crítico)", "Risk profile"))
    a, b = st.columns([1, 1.4])
    with a:
        show(fr, "rk_radar")
    with b:
        table(t[["ciudad", "puntaje", "nivel", "vida_util", "tcac_pct", "gpc", "tasa", "exploratorio", "capacidad_supuesta"]], hide_index=True, height=420,
              column_config={"puntaje": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"), "tasa": st.column_config.NumberColumn(format="percent"),
                             "gpc": st.column_config.NumberColumn(format="%.2f"), "tcac_pct": st.column_config.NumberColumn(format="%.2f"), "vida_util": st.column_config.NumberColumn(format="%.1f")})


# ------------------------------------------------------------------------------------------------ 10
@st.cache_data(show_spinner=False, max_entries=24)
def _mc(code, scen, n, seed, width, lever_json, param_json):
    from ui.common import get_repo
    from validation.uncertainty import monte_carlo
    return monte_carlo(get_repo(), code, scen, n=n, seed=seed, rel_width=width, lever_overrides=json.loads(lever_json) or None, param_overrides=json.loads(param_json) or None)


@st.cache_data(show_spinner=False, max_entries=24)
def _tornado(code, scen, output, lever_json, param_json):
    from ui.common import get_repo
    from validation.sensitivity import tornado
    return tornado(get_repo(), code, scen, output, lever_overrides=json.loads(lever_json) or None, param_overrides=json.loads(param_json) or None)


@st.cache_data(show_spinner=False, max_entries=12)
def _morris(code, scen, rr, seed, lever_json, param_json):
    from ui.common import get_repo
    from validation.sensitivity import morris
    return morris(get_repo(), code, scen, r=rr, seed=seed, lever_overrides=json.loads(lever_json) or None, param_overrides=json.loads(param_json) or None)


def page_uncertainty():
    s = st.session_state
    r = repo()
    hero(tr(f"Sensibilidad e incertidumbre · {r.name(s.city)}", f"Sensitivity and uncertainty · {r.name(s.city)}"),
         tr("Incertidumbre de PARÁMETROS (Monte Carlo), sensibilidad local (tornado) y global (Morris). La incertidumbre de ESCENARIO se explora comparando escenarios; "
            "la ESTRUCTURAL no se representa con estas bandas.",
            "PARAMETER uncertainty (Monte Carlo), local (tornado) and global (Morris) sensitivity. Scenario and structural uncertainty are not in these bands."))
    lj = json.dumps(s.get("lever_overrides", {}), sort_keys=True)
    pj = json.dumps(s.get("param_overrides", {}).get(s.city, {}), sort_keys=True)
    c1, c2, c3, c4 = st.columns(4)
    n = c1.slider(tr("Simulaciones", "Runs"), 100, 2000, 400, 100, key="mc_n")
    seed = int(c2.number_input(tr("Semilla", "Seed"), 0, 10 ** 9, 20261116, key="mc_seed"))
    width = c3.slider(tr("Amplitud del rango (1 = rango completo)", "Range width"), 0.2, 1.0, 1.0, 0.1, key="mc_w")
    scen = c4.selectbox(tr("Escenario", "Scenario"), s.scenarios, index=s.scenarios.index(s.scenario_focus), format_func=scen_label, key="mc_sc")
    mc = _mc(s.city, scen, n, seed, width, lj, pj)
    df, meta = results([s.city], s.scenarios)
    det = df[(df.escenario == scen)].set_index("anio")
    m = next(x for x in meta[scen] if x["divipola"] == s.city)
    exploratory_notice(m)
    a, b = st.columns(2)
    with a:
        show(band_fig(mc["years"], mc["cum_disposal"], tr("Disposición acumulada", "Cumulative disposal"), "t", det["dispuesto_total_t"].cumsum().to_numpy(),
                      tr("Determinista", "Deterministic"), med_label=tr("Mediana", "Median")), "mc_cum")
    with b:
        q = {k: v * 100 for k, v in mc["recovery_rate"].items()}
        show(band_fig(mc["years"], q, tr("Tasa de aprovechamiento (%)", "Recovery rate (%)"), "%", det["tasa_aprovechamiento"].to_numpy() * 100, tr("Determinista", "Deterministic"),
                      med_label=tr("Mediana", "Median"), fmt=".1f"), "mc_rate")
    p5, p50, p95 = np.percentile(mc["life"], [5, 50, 95])
    k1, k2, k3 = st.columns(3)
    with k1:
        kpi(tr("Vida útil · mediana", "Life · median"), life_text(p50) + tr(" años", " yr"), tag="sim")
    with k2:
        kpi(tr("Vida útil · P5 – P95", "Life · P5–P95"), f"{life_text(p5)} – {life_text(p95)}", tag="sim")
    with k3:
        kpi(tr("P(agotamiento antes de 2050)", "P(exhaustion before 2050)"), f"{np.mean(mc['life'] <= len(mc['years'])):.0%}", tag="sim")
    st.markdown("##### " + tr("Comparación de incertidumbre entre escenarios", "Uncertainty across scenarios"))
    rows = []
    for sc in s.scenarios:
        mm = _mc(s.city, sc, min(n, 300), seed, width, lj, pj)
        cum = mm["cum_disposal"]
        rows.append({tr("Escenario", "Scenario"): scen_label(sc), "P5 (Mt)": cum["p05"][-1] / 1e6, "P50 (Mt)": cum["p50"][-1] / 1e6, "P95 (Mt)": cum["p95"][-1] / 1e6,
                     tr("Amplitud relativa", "Relative width"): (cum["p95"][-1] - cum["p05"][-1]) / cum["p50"][-1]})
    table(pd.DataFrame(rows).round(3), hide_index=True)
    st.download_button(tr("Descargar muestras de parámetros y resultados (CSV)", "Download parameter samples (CSV)"), mc["samples"].to_csv(index=False).encode("utf-8"),
                       f"montecarlo_{s.city}_{scen}_seed{seed}.csv", "text/csv", key="dl_mc")

    st.markdown("##### " + tr("Sensibilidad local (un factor a la vez, extremos del rango)", "Local sensitivity (one-at-a-time)"))
    outs = {"dispuesto_acum": tr("Disposición acumulada (Mt)", "Cumulative disposal (Mt)"), "tasa_aprov_2050": tr("Tasa de aprovechamiento 2050 (%)", "Recovery rate 2050 (%)"),
            "vida_util": tr("Vida útil (años)", "Life (yr)")}
    out_k = st.radio(tr("Resultado", "Output"), list(outs), format_func=outs.get, horizontal=True, key="tor_out")
    base, tor = _tornado(s.city, scen, out_k, lj, pj)
    tor = tor.tail(15)
    if s.lang == "en":
        tor = tor.assign(descripcion=tor["parametro"].map(lambda k: PARAMS[k].label_en))
    show(tornado_fig(tor, base, outs[out_k], tr(f"Δ respecto al valor base ({base:,.2f})", f"Δ vs base ({base:,.2f})"), tr("Extremo bajo", "Low end"), tr("Extremo alto", "High end")), "tor")
    st.markdown("##### " + tr("Sensibilidad global (Morris)", "Global sensitivity (Morris)"))
    rr = st.slider(tr("Trayectorias r", "Trajectories r"), 5, 40, 12, key="mor_r")
    mo = _morris(s.city, scen, rr, seed, lj, pj)
    res = mo["results"][out_k]
    show(morris_fig(res.head(20), tr(f"Morris: μ* vs σ · {mo['n_runs']} simulaciones · semilla {seed}", f"Morris: μ* vs σ · {mo['n_runs']} runs")), "mor")
    table(res.head(15).round(4), hide_index=True)
    st.caption(tr("Sobol no se ofrece en línea: con ~35 parámetros requiere más de 10⁴ simulaciones. Morris ordena la influencia con r·(k+1) simulaciones.",
                  "Sobol is not offered online (≥10⁴ runs); Morris ranks influence with r·(k+1) runs."))


def _calibration_table():
    from validation.reliability import assess
    r = repo()
    rows = []
    for c in r.codes:
        res = r.calibration.get(c, {"status": "sin_datos", "params": {}})
        a = assess(r.profile(c), res)
        rows.append(dict(ciudad=r.name(c), estado=res["status"], nivel=a["nivel"],
                         ajuste=f"{res['years_fit'][0]}-{res['years_fit'][-1]}" if res.get("years_fit") else "",
                         validacion=f"{res['years_val'][0]}-{res['years_val'][-1]}" if res.get("years_val") else "",
                         sMAPE_ajuste=a.get("calibracion_sMAPE"), sMAPE_validacion=a.get("validacion_sMAPE"),
                         g_growth_inicial=res.get("params", {}).get("g_growth"), g_growth_fin_serie=res.get("g_growth_fin_serie"),
                         p_base=res.get("params", {}).get("p_base"), usa_aprovechamiento=res.get("uso_aprovechamiento"),
                         en_limite=", ".join(res.get("at_bound", []))))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ 11
def page_methods():
    s = st.session_state
    r = repo()
    hero(tr("Metodología y fuentes", "Methodology and sources"), tr("Ecuaciones, niveles, flujos, parámetros, fuentes, diccionario de datos y protocolo de verificación.",
                                                                   "Equations, stocks, flows, parameters, sources, data dictionary and verification."))
    t1, t2, t3, t4, t5 = st.tabs([tr("Ecuaciones", "Equations"), tr("Parámetros", "Parameters"), tr("Fuentes y datos", "Sources and data"),
                                  tr("Verificación y validación", "Verification and validation"), tr("Cambios v2 → v3", "Changes v2 → v3")])
    with t1:
        st.markdown(tr("**Integración.** Euler explícito con paso interno Δt = 0,25 años; los flujos se acumulan por año. Prueba de convergencia: el acumulado de disposición "
                       "con Δt = 1/16 difiere menos de 1 % (prueba automática `test_time_step_convergence`).",
                       "**Integration.** Explicit Euler, Δt = 0.25 yr; convergence test vs Δt = 1/16 < 1 %."))
        st.markdown("**" + tr("Generación y recolección", "Generation and collection") + "**")
        st.latex(r"W(t)=\text{Pob}(t)\cdot g_{pc,0}\,e^{\gamma (t-t_0)}\cdot 0{,}365,\quad G=W(1-\pi_{prev}),\quad C=\kappa\,G,\quad U=G-C")
        st.markdown("**" + tr("Separación en la fuente (difusión de Bass)", "Source separation (Bass diffusion)") + "**")
        st.latex(r"\frac{dA}{dt}=(p+p_{camp}+q\,A)(A_{max}-A)-\delta_A A,\qquad S_r=C\,s_{rec}\,A\,\eta,\qquad S_o=C\,s_{org}\,\omega\,A\,\eta_o")
        st.markdown("**" + tr("Clasificación, aprendizaje y orgánicos", "Sorting, learning and organics") + "**")
        st.latex(r"P_{rec}=\min(S_r,K_{rec}\,a),\quad \rho=\rho_{min}+(\rho_0-\rho_{min})(X/X_0)^{-b},\quad R=P_{rec}(1-\rho),\quad \frac{dX}{dt}=P_{rec}")
        st.latex(r"P_{org}=\min(S_o,K_{org}\,a),\qquad K_{out}=P_{org}(1-\rho_o)")
        st.markdown("**" + tr("Capacidad instalada (niveles)", "Installed capacity (stocks)") + "**")
        st.latex(r"\frac{dK}{dt}=\underbrace{\frac{K}{L}+\frac{\max(0,(1+m)S-K)}{\tau}\,\mu\,(1+\pi)\,\min(P,1{,}5)}_{\text{inversión}}+\text{plan}(t)-\frac{K}{L}")
        st.markdown("**" + tr("Mercado e inventario", "Market and inventory") + "**")
        st.latex(r"\frac{dI}{dt}=R-V-D_{err},\quad V=\min(I/\tau_s,D(t)),\quad P=\frac{D(t)}{\bar R\,(1+h)},\quad D_{err}=\frac{\max(0,I-I_{max})}{0{,}25}")
        st.markdown("**" + tr("Disposición final", "Final disposal") + "**")
        st.latex(r"L_d=M+E_r+E_o+\rho P_{rec}+\rho_o P_{org}+D_{err},\quad L_f=\min(L_d,Q/\Delta t),\quad \frac{dQ}{dt}=\text{Amp}(t)-L_f,\quad \text{Déficit}=L_d-L_f")
        st.latex(r"\pi=\alpha\cdot\operatorname{clip}\!\left(\frac{T_{crit}-Q/\bar L_d}{T_{crit}},0,1\right)")
        st.markdown("**" + tr("Balance de materia verificado en cada paso", "Mass balance verified at every step") + "**")
        st.latex(r"G=U+L_f+\text{Déficit}+V+K_{out}+\Delta I")
        st.markdown("**" + tr("Palancas de política", "Policy levers") + "**")
        st.latex(r"\theta(t)=\theta_0+\lambda\,\iota\,r(t)\,(\theta_{max}-\theta_0),\qquad r(t)=\text{logística normalizada entre }t_{impl}\text{ y }t_{impl}+T_{adop}")
        st.caption(tr("λ: intensidad de la palanca en el escenario; ι: intensidad global. Al cerrar una fracción de la brecha de cada ciudad, el mismo escenario produce efectos distintos por ciudad.",
                      "λ: lever intensity; ι: global intensity."))
        from ui.pages_b import LOOPS
        table(pd.DataFrame([dict(Bucle=a, Nombre=b if s.lang == "es" else c, Polaridad=d, Ecuación=e) for a, b, c, d, e, _ in LOOPS]), hide_index=True)
        st.markdown(tr("**Niveles:** Q, CumL, K_rec, K_org, I, E, A, X. **Flujos:** generación, prevención, recolección, separación, clasificación, reciclaje, tratamiento de orgánicos, "
                       "rechazos, disposición, comercialización, incorporación y retiro de capacidad. **Auxiliares:** P, ρ, κ, π, utilización. **Parámetros:** ver pestaña siguiente.",
                       "**Stocks:** Q, CumL, K_rec, K_org, I, E, A, X."))
    with t2:
        st.markdown(tr("Clases: **medido** (dato de la ciudad), **calibrado** (ajustado a series), **referencia** (fuente secundaria), **supuesto** (sin respaldo específico; "
                       "siempre visible como tal), **política** (palanca de escenario).", "Classes: measured, calibrated, reference, assumed, policy."))
        table(param_table(s.lang), hide_index=True)
        st.markdown("##### " + tr("Palancas de política", "Policy levers"))
        table(pd.DataFrame([dict(Palanca=k, Descripción=v[0] if s.lang == "es" else v[1], Unidad=v[2], Defecto=v[3]) for k, v in LEVERS.items()]), hide_index=True)
    with t3:
        st.markdown(tr("""
**Población.** DANE, *Proyecciones de población municipal por área geográfica 2018-2042* (actualización del 30 de julio de 2025; modelo de componentes de cohortes).
2018 = base censal conciliada; 2019-2042 = proyección oficial; 2043-2050 = **estimado** por el observatorio (tasa media logarítmica 2037-2042 de cada municipio).

**Residuos (SSPD).** Bases de los Informes Nacionales de Disposición Final 2019-2024 (toneladas por municipio atendido y sitio, tipo de sitio, regionalidad,
fecha final de vida útil); Anexo 1 del Informe de Disposición Final 2018 (extraído del PDF; promedio ton/día × 365); bases de los Informes Nacionales de
Aprovechamiento 2020-2024 (toneladas por familia de material; Estaciones de Clasificación y Aprovechamiento con su capacidad operativa). Importadas con
`core/sspd_import.py`; controles de calidad en `core/quality.py`. Registros documentales puntuales en `data/raw/registros_documentales.csv` (con URL).
La generación observada se estima como (dispuesto + aprovechado) / cobertura; la cobertura de recolección no está en estas bases y se mantiene como supuesto (95 %).

**Referencias nacionales usadas como respaldo** (solo cuando la ciudad no tiene dato propio): 0,75 kg/hab/día (DNP, CEMPRE y CEPAL, 2021, *Encuesta a municipios sobre gestión
de residuos sólidos domiciliarios 2019*); 70 % de orgánicos (CATF, 2024, *Colombia waste sector fact sheet*).

**Coordenadas.** Aproximadas del casco urbano; uso exclusivamente cartográfico.
""", """**Population.** DANE municipal projections 2018-2042 (July 2025); 2043-2050 estimated. **Waste.** SSPD national reports / SUI."""))
        st.markdown("##### " + tr("Registro de observaciones cargadas", "Loaded observations register"))
        obs = r.observations
        st.caption(tr(f"{len(obs)} observaciones · {obs['divipola'].nunique()} ciudades · versión de datos {r.data_version.get('residuos_observados.csv', '—')}",
                      f"{len(obs)} observations"))
        table(obs, hide_index=True, height=260)
        st.markdown("##### " + tr("Diccionario de variables", "Data dictionary"))
        from core.simulation_engine import OUTPUT_COLUMNS
        dd = [dict(Variable=k, Descripción=v[0] if s.lang == "es" else v[1], Unidad=v[2], Tipo="simulado") for k, v in OUTPUT_COLUMNS.items()]
        dd += [dict(Variable=k, Descripción=l, Unidad=u, Tipo="observado/perfil") for k, l, u in PROFILE_VARIABLES]
        table(pd.DataFrame(dd), hide_index=True, height=300)
    with t4:
        st.markdown(tr("""
**Verificación estructural (pruebas automáticas, `pytest`):** cierre del balance de materia en cada paso y cada año (error relativo < 10⁻⁹), no negatividad de niveles y flujos,
restricciones físicas (recolectado ≤ generado; separado ≤ recolectado; recuperado ≤ potencial material; procesado ≤ capacidad), capacidad de disposición que solo cambia por
disposición y ampliaciones, condiciones extremas (población cero, cobertura cero, capacidad de proceso cero, relleno lleno), convergencia del paso temporal y reproducción de la
condición inicial observada.

**Calibración.** Por ciudad, con mínimos cuadrados acotados sobre dispuesto y aprovechado SSPD. Solo se calibran parámetros identificables (crecimiento per cápita y, con
≥ 4 años, adopción espontánea). Los dos últimos años observados se reservan para validación fuera de muestra cuando la serie lo permite.

**Métricas.** MAE, RMSE, sMAPE, sesgo medio y R².

**Confiabilidad.** A: validado fuera de muestra (sMAPE ≤ 10 %); B: validado con error moderado (≤ 25 %); C: calibrado sin validar; D: exploratorio.
Un modelo que solo superó pruebas de programación **no** se presenta como validado.

**Incertidumbre.** Monte Carlo (distribución triangular sobre el rango del registro; semilla reproducible y exportable), tornado y Morris. La incertidumbre de escenario y la
estructural se tratan por separado.
""", "Structural verification, calibration, metrics, reliability levels and uncertainty protocol."))
        cal = _calibration_table()
        st.markdown(tr(f"**Resultado actual:** {(cal.nivel == 'A').sum()} capitales en nivel A, {(cal.nivel == 'B').sum()} en B, {(cal.nivel == 'C').sum()} en C y "
                       f"{(cal.nivel == 'D').sum()} en D.", f"**Current:** A={(cal.nivel == 'A').sum()}, B={(cal.nivel == 'B').sum()}, C={(cal.nivel == 'C').sum()}."))
        table(cal, hide_index=True, height=420, column_config={"g_growth_inicial": st.column_config.NumberColumn(format="%.4f"),
                                                                "g_growth_fin_serie": st.column_config.NumberColumn(format="%.4f"),
                                                                "p_base": st.column_config.NumberColumn(format="%.4f")})
        st.markdown("##### " + tr("Control de calidad de las series SSPD", "SSPD data-quality checks"))
        from core.quality import quality_table
        table(quality_table(r, s.lang), hide_index=True, height=320)
    with t5:
        st.markdown(tr("""
- Motor separado de la interfaz (`core/`), con niveles, flujos y bucles explícitos; la v2 era un balance de masa con rampas exógenas sin realimentación.
- 32 capitales (antes 10 ciudades, 3 de ellas no capitales) con población oficial DANE.
- Datos con tipo, fuente y calidad por fila; la v2 usaba un libro sintético con per cápita y composición idénticas en todas las ciudades.
- Rellenos sanitarios: se eliminan las asignaciones desactualizadas de la v2 (p. ej. Navarro para Cali, Henequén para Cartagena); solo se muestran registros con fuente.
- Capacidad de disposición: si no está reportada se declara SUPUESTA y la vida útil se marca como exploratoria.
- Monte Carlo sobre todos los parámetros con rango, incluida la capacidad de disposición; semillas exportables; Morris añadido.
- La v2 se conserva íntegra en `legacy/app_v2.py` (ejecutable con `streamlit run legacy/app_v2.py`).
""", "- Engine separated from UI; 32 capitals; traceable data; v2 preserved in legacy/."))


# ------------------------------------------------------------------------------------------------ 12
def page_downloads():
    s = st.session_state
    r = repo()
    hero(tr("Descarga de resultados", "Downloads"), tr("Cada descarga incluye un manifiesto de ejecución con identificador único, versión de código y de datos, parámetros, fuentes y semilla.",
                                                       "Every download carries a run manifest."))
    from reports.report_generator import build_manifest, excel_bytes, pdf_report, zip_package
    codes = st.multiselect(tr("Ciudades", "Cities"), [r.name(c) for c in r.codes], default=[r.name(s.city)], key="dl_cities")
    codes = [r.code_of(x) for x in codes] or [s.city]
    df, meta = results(codes, s.scenarios)
    seed = int(s.get("mc_seed", 20261116))
    man = build_manifest(r, codes, s.scenarios, s.get("lever_overrides", {}), s.get("param_overrides", {}), seed, APP_VERSION)
    st.markdown(f"**{tr('Identificador de ejecución', 'Run ID')}:** `{man['run_id']}` · {tr('código', 'code')} `{man['code_version']}` · {tr('datos', 'data')} `{man['data_version']}`")
    c1, c2, c3 = st.columns(3)
    c1.download_button(tr("Resultados de simulación (CSV)", "Simulation results (CSV)"), df.to_csv(index=False).encode("utf-8"), f"simulacion_{man['run_id']}.csv", "text/csv")
    c2.download_button(tr("Libro Excel (resultados, parámetros, fuentes, población)", "Excel workbook"), excel_bytes(r, df, man), f"observatorio_{man['run_id']}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    c3.download_button(tr("Manifiesto y configuración (JSON)", "Manifest and configuration (JSON)"), json.dumps(man, indent=2, ensure_ascii=False).encode("utf-8"),
                       f"manifiesto_{man['run_id']}.json", "application/json")
    c4, c5, c6 = st.columns(3)
    c4.download_button(tr("Paquete reproducible (ZIP)", "Reproducible package (ZIP)"), zip_package(r, df, man), f"paquete_{man['run_id']}.zip", "application/zip")
    c5.download_button(tr("Base histórica (población + observaciones, CSV)", "Historical database (CSV)"),
                       pd.concat([r.population.assign(variable="poblacion_total", valor=r.population["poblacion_total"]), r.observations]).to_csv(index=False).encode("utf-8"),
                       "base_historica.csv", "text/csv")
    with c6:
        if st.button(tr("Generar informe PDF", "Build PDF report"), key="pdf_btn"):
            with st.spinner(tr("Generando informe…", "Building report…")):
                s["pdf_bytes"] = pdf_report(r, df, meta, man, s.city, s.lang)
        if s.get("pdf_bytes"):
            st.download_button(tr("Descargar informe PDF", "Download PDF"), s["pdf_bytes"], f"informe_{man['run_id']}.pdf", "application/pdf", key="pdf_dl")
    st.caption(tr("Los gráficos se descargan en alta resolución (PNG ×3) desde el ícono de cámara de cada figura.", "Charts download as high-res PNG from each figure's camera icon."))
    with st.expander(tr("Ver manifiesto", "View manifest")):
        st.json(man)
