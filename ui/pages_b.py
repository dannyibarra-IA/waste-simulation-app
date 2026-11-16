"""Módulos 5-8: simulación dinámica, escenarios, flujos de materiales y comparación de ciudades."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from core.simulation_engine import OUTPUT_COLUMNS
from ui.common import exploratory_notice, fmt_t, hero, intro, kpi, life_text, repo, results, scen_label, show, table, tr
from visualization.charts import C, gauge, sankey, scen_color_map, scenario_lines


def _scientific():
    return st.session_state.get("mode") in ("Científico", "Scientific")


def _city_frames():
    s = st.session_state
    df, meta = results([s.city], s.scenarios)
    return df, meta


LOOPS = [
    ("R1", "Adopción social", "Social adoption", "+", "dA/dt = (p + q·A)·(A_max − A) − δ_A·A", "A, q_imit"),
    ("R2", "Aprendizaje operativo", "Operational learning", "+", "ρ = ρ_min + (ρ₀ − ρ_min)·(X/X₀)^(−b); dX/dt = P_rec", "X, ρ, b_learn"),
    ("R3", "Incremento del aprovechamiento", "Growth of recovery", "+", "Inv = K/vida + máx(0,(1+m)·S_r − K)/τ · mult · P", "Krec, S_r"),
    ("B1", "Saturación de capacidad", "Capacity saturation", "−", "P_rec = mín(S_r, K·disp); Exceso = S_r − P_rec → disposición", "Krec"),
    ("B2", "Saturación de mercados", "Market saturation", "−", "P = D / (R̄·(1+h)); η ∝ P^ε; Inv ∝ P; Derrame = máx(0, I − I_max)/0,25", "I, P, D"),
    ("B3", "Disponibilidad de materiales", "Material availability", "−", "S_r = C·s_rec·A·η ≤ C·s_rec; S_r + S_o ≤ C", "C, s_rec"),
    ("B4", "Agotamiento de disposición final", "Disposal exhaustion", "−", "π = α·clip((T_crit − Q/L̄)/T_crit, 0, 1) → campañas e inversión", "Q, π"),
    ("B5", "Saturación de la adopción", "Adoption saturation", "−", "(A_max − A) → 0 ⇒ dA/dt → 0", "A, A_max"),
]


# ------------------------------------------------------------------------------------------------ 5
def page_dynamics():
    s = st.session_state
    r = repo()
    name = r.name(s.city)
    hero(tr(f"Simulación dinámica · {name}", f"Dynamic simulation · {name}"),
         tr("Niveles (acumulaciones) y flujos del motor de Dinámica de Sistemas, integrados con paso trimestral y reportados por año.",
            "Stocks and flows of the System Dynamics engine (quarterly step, annual output)."))
    df, meta = _city_frames()
    scen = s.scenario_focus
    m = next(x for x in meta[scen] if x["divipola"] == s.city)
    exploratory_notice(m)
    d = df[df.escenario == scen].set_index("anio")
    row = d.loc[s.year]
    c = st.columns(6)
    vals = [(tr("Generación", "Generation"), fmt_t(row["G"]) + " t"), (tr("Aprovechado", "Recovered"), fmt_t(row["aprovechado_t"]) + " t"),
            (tr("Tasa de aprovechamiento", "Recovery rate"), f"{row['tasa_aprovechamiento']:.1%}"), (tr("Dispuesto", "Landfilled"), fmt_t(row["Lf"]) + " t"),
            (tr("Déficit de capacidad", "Capacity deficit"), fmt_t(row["Overflow"]) + " t"), (tr("Vida útil", "Landfill life"), life_text(m["life"]) + tr(" años", " yr"))]
    for col, (l, v) in zip(c, vals):
        with col:
            kpi(f"{l} ({s.year})" if l != tr("Vida útil", "Landfill life") else l, v, scen_label(scen), tag="sim")

    if _scientific():
        stocks = [("Q", 1), ("Krec", 1), ("Korg", 1), ("I", 1), ("A", 100), ("E", 100), ("rho_r", 100), ("P", 1), ("pressure", 1)]
    else:
        stocks = [("Q", 1), ("Krec", 1), ("A", 100), ("P", 1)]
    ncol = 3 if _scientific() else 2
    titles = [f"{OUTPUT_COLUMNS[k][0 if s.lang == 'es' else 1]} [{'%' if mul == 100 else OUTPUT_COLUMNS[k][2]}]" for k, mul in stocks]
    rows = int(np.ceil(len(stocks) / ncol))
    f = make_subplots(rows=rows, cols=ncol, subplot_titles=titles, vertical_spacing=0.12)
    cmap = scen_color_map(s.scenarios)
    for i, (k, mul) in enumerate(stocks):
        for sc, dd in df.groupby("escenario", sort=False):
            f.add_trace(go.Scatter(x=dd["anio"], y=dd[k] * mul, name=scen_label(sc), legendgroup=sc, showlegend=i == 0, line=dict(color=cmap.get(sc), width=2.5,
                                                                                                                              dash="dash" if sc == "BAU" else "solid")),
                        row=i // ncol + 1, col=i % ncol + 1)
    f.update_layout(height=290 * rows, hovermode="x unified", title=tr("Niveles y variables de estado por escenario", "Stocks and state variables by scenario"))
    for i, (k, mul) in enumerate(stocks):
        f.update_yaxes(tickformat=".2f" if k in ("P", "pressure") else (".0f" if mul == 100 else ",.3~s"), row=i // ncol + 1, col=i % ncol + 1)
    show(f, "dyn_stocks")

    st.markdown("#### " + tr("Bucles de realimentación implementados", "Implemented feedback loops"))
    lt = pd.DataFrame([dict(Bucle=a, Nombre=b if s.lang == "es" else c, Polaridad=d, Ecuación=e, Variables=f_) for a, b, c, d, e, f_ in LOOPS])
    table(lt, hide_index=True)
    if _scientific():
        st.markdown("#### " + tr("Diagnóstico de la ejecución", "Run diagnostics"))
        st.markdown(tr(f"- Error relativo máximo de balance de materia en todos los pasos: **{m['balance']:.1e}** (ver pruebas automáticas).\n"
                       f"- Condiciones iniciales: {', '.join(f'{k}: {v}' for k, v in m['provenance'].items()) or 'sin observaciones de residuos; valores de referencia y supuestos'}.",
                       f"- Initial conditions: {m['provenance'] or 'no waste observations; reference values and assumptions'}."))


# ------------------------------------------------------------------------------------------------ 6
def page_scenarios():
    s = st.session_state
    r = repo()
    name = r.name(s.city)
    hero(tr(f"Escenarios de política · {name}", f"Policy scenarios · {name}"),
         tr("Compare hasta 12 escenarios. Las palancas cierran una fracción de la brecha de CADA ciudad, por lo que un escenario no impone valores homogéneos.",
            "Compare up to 12 scenarios; levers close a share of each city's own gap."))
    if len(s.scenarios) < 4:
        st.info(tr("Seleccione al menos cuatro escenarios en la barra lateral para una comparación completa.", "Select at least four scenarios in the sidebar."))
    from core.scenarios import SCENARIOS
    with st.expander(tr("Descripción de los escenarios seleccionados", "Selected scenario descriptions")):
        for k in s.scenarios:
            st.markdown(f"**{scen_label(k)}** — {SCENARIOS[k]['desc_' + s.lang]}  \n`{SCENARIOS[k]['levers']}`")
    df, meta = _city_frames()
    cmap = scen_color_map(s.scenarios)
    labels = {k: scen_label(k) for k in s.scenarios}
    m0 = next(x for x in meta["BAU"] if x["divipola"] == s.city)
    exploratory_notice(m0)
    c1, c2 = st.columns(2)
    with c1:
        show(scenario_lines(df, "dispuesto_total_t", tr("Toneladas dispuestas (incluye déficit)", "Tonnes landfilled (incl. deficit)"), "t/año", labels, cmap), "sc_disp")
    with c2:
        d2 = df.assign(tasa=df["tasa_aprovechamiento"] * 100)
        show(scenario_lines(d2, "tasa", tr("Tasa de aprovechamiento (%)", "Recovery rate (%)"), "%", labels, cmap, fmt=".1f"), "sc_rate")
    c3, c4 = st.columns(2)
    with c3:
        show(scenario_lines(df, "Q", tr("Capacidad remanente de disposición", "Remaining disposal capacity"), "t", labels, cmap), "sc_Q")
    with c4:
        show(scenario_lines(df, "desviacion_acum_vs_bau_t", tr("Desviación acumulada de disposición respecto al BAU", "Cumulative diversion vs BAU"), "t", labels, cmap), "sc_dev")
    c5, c6 = st.columns(2)
    with c5:
        show(scenario_lines(df, "gpc_kg_dia", tr("Generación per cápita", "Per-capita generation"), "kg/hab/día", labels, cmap, fmt=".2f"), "sc_gpc")
    with c6:
        show(scenario_lines(df, "util_rec", tr("Utilización de capacidad de clasificación", "Sorting capacity utilization"), "fracción", labels, cmap, fmt=".0%"), "sc_util")
    st.markdown("#### " + tr("Resumen por escenario", "Scenario summary"))
    rows = []
    for sc in s.scenarios:
        d = df[df.escenario == sc].set_index("anio")
        mm = next(x for x in meta[sc] if x["divipola"] == s.city)
        rows.append({tr("Escenario", "Scenario"): scen_label(sc), tr("Generación 2050 (t)", "Generation 2050"): d.loc[2050, "G"],
                     tr("Aprovechado 2050 (t)", "Recovered 2050"): d.loc[2050, "aprovechado_t"], tr("Tasa 2050", "Rate 2050"): d.loc[2050, "tasa_aprovechamiento"] * 100,
                     tr("Disposición per cápita 2050 (kg/día)", "Disposal pc 2050"): d.loc[2050, "disp_pc_kg_dia"],
                     tr("Desviación acumulada vs BAU (t)", "Cum. diversion vs BAU"): d.loc[2050, "desviacion_acum_vs_bau_t"],
                     tr("Vida útil (años)", "Life (yr)"): min(mm["life"], 100), tr("Déficit acumulado (t)", "Cum. deficit"): d["Overflow"].sum()})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={
        c: st.column_config.NumberColumn(format="%.1f" if "Tasa" in c or "Rate" in c or "años" in c or "yr" in c or "kg" in c else "%,.0f") for c in pd.DataFrame(rows).columns[1:]})
    if m0["capacity_assumed"]:
        st.caption(tr("Vida útil calculada con capacidad remanente supuesta.", "Life computed with assumed capacity."))


# ------------------------------------------------------------------------------------------------ 7
def page_flows():
    s = st.session_state
    r = repo()
    name = r.name(s.city)
    hero(tr(f"Flujos de materiales · {name}", f"Material flows · {name}"),
         tr("Balance de materia anual: cada tonelada generada termina prevenida, no recolectada, recuperada, tratada, dispuesta o en déficit de disposición.",
            "Annual mass balance."))
    df, meta = _city_frames()
    a, b = st.columns(2)
    with a:
        sc = st.selectbox(tr("Escenario", "Scenario"), s.scenarios, index=s.scenarios.index(s.scenario_focus), format_func=scen_label, key="fl_sc")
    with b:
        yr = st.slider(tr("Año", "Year"), int(df.anio.min()), int(df.anio.max()), s.year, key="fl_y")
    row = df[(df.escenario == sc) & (df.anio == yr)].iloc[0]
    L = dict(W=tr("Generación potencial", "Potential generation"), Prevented=tr("Prevenido", "Prevented"), G=tr("Generado", "Generated"), U=tr("No recolectado", "Uncollected"),
             C=tr("Recolectado", "Collected"), Mixed=tr("Mezclado", "Mixed"), Sr=tr("Reciclables separados", "Separated recyclables"), So=tr("Orgánicos separados", "Separated organics"),
             Rrec=tr("Materiales recuperados", "Recovered materials"), Kout=tr("Orgánicos tratados", "Treated organics"), Rej=tr("Rechazos", "Rejects"),
             Excess=tr("Sin capacidad de proceso", "Over processing capacity"), Landfill=tr("Relleno sanitario", "Landfill"), Deficit=tr("Déficit de disposición", "Disposal deficit"))
    show(sankey(row, L, tr(f"Balance de materia {yr} · {scen_label(sc)} (t/año)", f"Mass balance {yr} (t/yr)")), "fl_sankey")
    resid = row["G"] - (row["U"] + row["Lf"] + row["Overflow"] + row["Sales"] + row["Kout"]) - (row["I"] - df[(df.escenario == sc) & (df.anio == yr - 1)]["I"].sum()
                                                                                                if yr > df.anio.min() else 0)
    st.caption(tr(f"Cierre del balance anual (G − U − dispuesto − déficit − vendido − tratado − ΔInventario): {resid:,.3f} t", f"Annual balance closure: {resid:,.3f} t"))
    d = df[df.escenario == sc].set_index("anio")
    g1, g2, g3 = st.columns(3)
    with g1:
        show(gauge(100 * row["util_rec"], tr("Utilización clasificación", "Sorting utilization"), 0, 100, [(0, 70, "#e8f1ec"), (70, 95, "#f6ead3"), (95, 100, "#f3d6d2")], " %"), "fl_g1")
    with g2:
        show(gauge(100 * row["util_org"], tr("Utilización orgánicos", "Organics utilization"), 0, 100, [(0, 70, "#e8f1ec"), (70, 95, "#f6ead3"), (95, 100, "#f3d6d2")], " %"), "fl_g2")
    with g3:
        q0 = d["Q"].iloc[0] + d["Lf"].iloc[0]
        show(gauge(100 * (1 - row["Q"] / max(q0 + d["CapAdd_Q"].sum(), 1)), tr("Capacidad de disposición usada", "Disposal capacity used"), 0, 100,
                   [(0, 60, "#e8f1ec"), (60, 85, "#f6ead3"), (85, 100, "#f3d6d2")], " %"), "fl_g3")
    f = go.Figure()
    f.add_trace(go.Scatter(x=d.index, y=d["Krec"], name=tr("Capacidad de clasificación", "Sorting capacity"), line=dict(color=C["gold"], dash="dash")))
    f.add_trace(go.Scatter(x=d.index, y=d["Prec"], name=tr("Procesado", "Processed"), line=dict(color=C["gold"], width=3)))
    f.add_trace(go.Scatter(x=d.index, y=d["Korg"], name=tr("Capacidad de orgánicos", "Organics capacity"), line=dict(color=C["green"], dash="dash")))
    f.add_trace(go.Scatter(x=d.index, y=d["Porg"], name=tr("Orgánicos procesados", "Organics processed"), line=dict(color=C["green"], width=3)))
    f.add_trace(go.Bar(x=d.index, y=d["Excess_r"] + d["Excess_o"], name=tr("Excedente sin capacidad", "Excess over capacity"), marker_color=C["red"], opacity=0.5))
    f.update_layout(title=tr("Curvas de utilización de capacidad", "Capacity utilization curves"), yaxis_tickformat=",.3s", hovermode="x unified", height=400)
    f.update_xaxes(tickformat="d")
    show(f, "fl_cap")


# ------------------------------------------------------------------------------------------------ 8
def page_compare():
    s = st.session_state
    r = repo()
    hero(tr("Comparación de ciudades", "City comparison"),
         tr("Compare capitales seleccionadas o el conjunto filtrado. Las ciudades exploratorias se marcan con *; sus diferencias no son evidencia empírica.",
            "Compare capitals; exploratory cities are flagged with *."))
    names = list(r.capitals.sort_values("ciudad")["ciudad"])
    default = [r.name(c) for c in s.codes_filtered][:8] if len(s.codes_filtered) < 32 else [s.city_name, "Bogotá D. C.", "Cali", "Barranquilla", "Bucaramanga"]
    sel = st.multiselect(tr("Ciudades", "Cities"), names, default=[x for x in default if x in names], key="cmp_sel")
    if not sel:
        st.stop()
    codes = [r.code_of(x) for x in sel]
    df, meta = results(r.codes, s.scenarios)
    scen = st.selectbox(tr("Escenario", "Scenario"), s.scenarios, index=s.scenarios.index(s.scenario_focus), format_func=scen_label, key="cmp_sc")
    mm = {m["divipola"]: m for m in meta[scen]}
    d = df[(df.escenario == scen) & df.divipola.isin(codes)].copy()
    d["etiqueta"] = d["ciudad"] + np.where(d["divipola"].map(lambda c: mm[c]["exploratory"]), " *", "")
    y = d[d.anio == s.year]
    comp = r.completeness_table().set_index("divipola")["_score"]
    c1, c2 = st.columns(2)
    with c1:
        f = px.scatter(y, x="pop", y="G", text="etiqueta", size="gpc_kg_dia", color="tasa_aprovechamiento", color_continuous_scale="Viridis",
                       labels=dict(pop=tr("Población", "Population"), G=tr("Generación (t/año)", "Generation (t/yr)"), tasa_aprovechamiento=tr("Tasa aprov.", "Rec. rate")),
                       title=tr(f"Población vs generación ({s.year})", f"Population vs generation ({s.year})"))
        f.update_traces(textposition="top center")
        f.update_layout(height=430, xaxis_tickformat=",.2s", yaxis_tickformat=",.2s")
        show(f, "cmp_scatter")
    with c2:
        yy = y.sort_values("disp_pc_kg_dia", ascending=False)
        f = px.bar(yy, x="etiqueta", y=["gpc_kg_dia", "disp_pc_kg_dia"], barmode="group", title=tr("Generación y disposición per cápita", "Per-capita generation and disposal"),
                   labels=dict(value="kg/hab/día", etiqueta="", variable=""), color_discrete_sequence=[C["gold"], C["grey"]])
        f.update_layout(height=430, xaxis_tickangle=-30)
        show(f, "cmp_bar")
    ind = st.selectbox(tr("Mapa de calor", "Heatmap"), ["tasa_aprovechamiento", "gpc_kg_dia", "disp_pc_kg_dia", "vida_util_instantanea"], key="cmp_hm",
                       format_func=lambda k: {"tasa_aprovechamiento": tr("Tasa de aprovechamiento", "Recovery rate"), "gpc_kg_dia": tr("Generación per cápita", "Per-capita generation"),
                                              "disp_pc_kg_dia": tr("Disposición per cápita", "Disposal per capita"), "vida_util_instantanea": tr("Vida útil instantánea (años)", "Instant life")}[k])
    hm = d.pivot_table(index="etiqueta", columns="anio", values=ind)
    f = px.imshow(hm, aspect="auto", color_continuous_scale="YlGnBu", title=tr("Evolución por ciudad", "Evolution by city"))
    f.update_layout(height=max(300, 34 * len(hm) + 120))
    show(f, "cmp_heat")
    t = y[["ciudad", "pop", "G", "gpc_kg_dia", "aprovechado_t", "tasa_aprovechamiento", "dispuesto_total_t"]].copy()
    t["cobertura_datos_%"] = y["divipola"].map(comp).values
    t["vida_util"] = [min(mm[c]["life"], 100) for c in y["divipola"]]
    t["exploratorio"] = [mm[c]["exploratory"] for c in y["divipola"]]
    table(t, hide_index=True, column_config={"tasa_aprovechamiento": st.column_config.NumberColumn(format="percent"), "pop": st.column_config.NumberColumn(format="%,.0f"),
                                              "G": st.column_config.NumberColumn(format="%,.0f"), "aprovechado_t": st.column_config.NumberColumn(format="%,.0f"),
                                              "dispuesto_total_t": st.column_config.NumberColumn(format="%,.0f"), "gpc_kg_dia": st.column_config.NumberColumn(format="%.2f"),
                                              "vida_util": st.column_config.NumberColumn(format="%.1f")})
