"""Módulos 1-4: observatorio nacional, perfil de ciudad, tendencias históricas y composición."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from core.data import PROFILE_VARIABLES
from core.parameters import PARAMS
from core.simulation_engine import BASE_YEAR, city_params
from ui.common import exploratory_notice, fmt_t, hero, intro, kpi, life_text, repo, results, scen_label, show, table, tr
from validation.reliability import assess
from visualization.charts import C, city_map, line_obs_sim, population_fig


def _meta_of(meta, scen, code):
    return next(m for m in meta[scen] if m["divipola"] == code)


# ------------------------------------------------------------------------------------------------ 1
def page_national():
    s = st.session_state
    r = repo()
    hero(tr("Observatorio nacional · 32 capitales", "National observatory · 32 capitals"),
         tr("Generación, aprovechamiento y disposición final de residuos en las capitales departamentales de Colombia hasta 2050. "
            "Los marcadores translúcidos indican ciudades sin serie observada de residuos (simulación exploratoria).",
            "Waste generation, recovery and disposal across Colombia's 32 departmental capitals to 2050. Translucent markers: no observed waste series (exploratory)."))
    df, meta = results(r.codes, s.scenarios)
    scen = s.scenario_focus
    y = s.year
    d = df[(df.escenario == scen) & (df.anio == y)].merge(r.capitals, on=["divipola", "ciudad"])
    mm = {m["divipola"]: m for m in meta[scen]}
    d["exploratorio"] = d["divipola"].map(lambda c: mm[c]["exploratory"])
    d["vida_util"] = d["divipola"].map(lambda c: mm[c]["life"])
    d["capacidad_supuesta"] = d["divipola"].map(lambda c: mm[c]["capacity_assumed"])
    comp = r.completeness_table().set_index("divipola")
    d["cobertura_datos"] = d["divipola"].map(comp["_score"])
    n_obs = int((~d["exploratorio"]).sum())

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi(tr("Población 32 capitales", "Population, 32 capitals") + f" ({y})", fmt_t(d["pop"].sum()),
            tr("proyección oficial DANE", "DANE official projection") if y <= 2042 else tr("extensión estimada desde DANE", "estimated extension"), tag="proj" if y <= 2042 else "est")
    with c2:
        kpi(tr("Generación", "Generation") + f" ({y})", fmt_t(d["G"].sum()) + " t", scen_label(scen), tag="sim")
    with c3:
        kpi(tr("Tasa de aprovechamiento", "Recovery rate"), f"{d['aprovechado_t'].sum() / d['G'].sum():.1%}", tr("agregado simulado", "simulated aggregate"), tag="sim")
    with c4:
        kpi(tr("Dispuesto + déficit", "Landfilled + deficit"), fmt_t(d["dispuesto_total_t"].sum()) + " t", tr("incluye déficit de capacidad", "incl. capacity deficit"), tag="sim")
    with c5:
        kpi(tr("Ciudades con datos de residuos", "Cities with waste data"), f"{n_obs} / 32",
            tr("el resto es exploratorio", "others exploratory"), tone="bad" if n_obs < 16 else "good")
    if n_obs < 32:
        st.info(tr(f"**Comparabilidad.** {32 - n_obs} capitales no tienen series observadas de residuos cargadas; sus valores dependen de supuestos "
                   "y no deben compararse como datos. Los agregados nacionales mezclan ciudades con y sin datos.",
                   f"**Comparability.** {32 - n_obs} capitals lack observed waste series; their values rest on assumptions."), icon="ℹ️")

    ind = {tr("Generación (t/año)", "Generation (t/yr)"): "G", tr("Generación per cápita (kg/hab/día)", "Per-capita generation"): "gpc_kg_dia",
           tr("Tasa de aprovechamiento", "Recovery rate"): "tasa_aprovechamiento", tr("Disposición per cápita (kg/hab/día)", "Disposal per capita"): "disp_pc_kg_dia",
           tr("Vida útil de disposición (años)", "Landfill life (years)"): "vida_util", tr("Cobertura de datos (%)", "Data coverage (%)"): "cobertura_datos",
           tr("Población", "Population"): "pop"}
    a, b = st.columns([2, 1])
    with a:
        lab = st.selectbox(tr("Indicador del mapa", "Map indicator"), list(ind), key="nat_ind")
    col = ind[lab]
    d["vida_util_cap"] = d["vida_util"].clip(upper=100)
    vcol = "vida_util_cap" if col == "vida_util" else col
    d["_v"] = d[vcol].round(3)
    hover = ["departamento", "region", "_v", "cobertura_datos"]
    m1, m2 = st.columns([1.6, 1])
    with m1:
        show(city_map(d, vcol, f"{lab} · {y} · {scen_label(scen)}", lab.split("(")[0], hover), "nat_map")
    with m2:
        rk = d.sort_values(vcol, ascending=True)
        rk["etiqueta"] = rk["ciudad"] + np.where(rk["exploratorio"], " *", "")
        rk["estado"] = np.where(rk["exploratorio"], tr("Exploratorio", "Exploratory"), tr("Con datos", "With data"))
        f = px.bar(rk, x=vcol, y="etiqueta", orientation="h", color="estado",
                   color_discrete_map={tr("Con datos", "With data"): C["blue"], tr("Exploratorio", "Exploratory"): C["sand"]},
                   labels={vcol: lab, "etiqueta": "", "estado": ""}, title=tr("Ranking nacional (* exploratorio)", "National ranking (* exploratory)"))
        f.update_layout(height=640, showlegend=True, legend=dict(y=-0.08))
        f.update_yaxes(automargin=True, tickfont=dict(size=11))
        show(f, "nat_rank")
    if col == "vida_util" and d["capacidad_supuesta"].any():
        st.warning(tr(f"La vida útil de {int(d['capacidad_supuesta'].sum())} ciudades se calcula con capacidad remanente SUPUESTA; no es comparable.",
                      f"Landfill life for {int(d['capacidad_supuesta'].sum())} cities uses ASSUMED capacity."))

    st.markdown("#### " + tr("Trayectoria nacional animada", "Animated national trajectory"))
    allf = df[df.escenario == scen].merge(r.capitals[["divipola", "lat", "lon"]], on="divipola")
    years = sorted(allf["anio"].unique())
    nat = allf.groupby("anio")[["G", "dispuesto_total_t", "aprovechado_t"]].sum()
    vmax = float(allf["G"].max())
    fa = make_subplots(rows=1, cols=2, specs=[[{"type": "map"}, {"type": "xy"}]], column_widths=[0.55, 0.45],
                       subplot_titles=(tr("Generación por ciudad", "Generation by city"), tr("Total 32 capitales (t/año)", "Total 32 capitals (t/yr)")))

    def mt(yr):
        v = allf[allf.anio == yr]
        return go.Scattermap(lat=v["lat"], lon=v["lon"], text=v["ciudad"], mode="markers", showlegend=False,
                             marker=dict(size=(8 + 30 * np.sqrt(v["G"] / vmax)).tolist(), color=v["G"], colorscale="Viridis", cmin=0, cmax=vmax),
                             hovertemplate="<b>%{text}</b><br>%{marker.color:,.0f} t/año<extra></extra>")

    def lt(yr):
        n = nat.loc[:yr]
        return go.Scatter(x=n.index, y=n["G"], mode="lines+markers", line=dict(color=C["green"], width=3), name=tr("Generación", "Generation"))

    fa.add_trace(mt(years[0]), 1, 1)
    fa.add_trace(lt(years[0]), 1, 2)
    fa.add_trace(go.Scatter(x=nat.index, y=nat["dispuesto_total_t"], line=dict(color=C["grey"], dash="dash"), name=tr("Dispuesto", "Landfilled")), 1, 2)
    fa.frames = [go.Frame(name=str(yr), data=[mt(yr), lt(yr)], traces=[0, 1]) for yr in years]
    fa.update_layout(map=dict(style="carto-positron", zoom=4.0, center=dict(lat=5.5, lon=-73.5)), height=520,
                     updatemenus=[dict(type="buttons", x=0.0, y=-0.05, buttons=[dict(label="▶", method="animate", args=[None, dict(frame=dict(duration=500, redraw=True), fromcurrent=True)]),
                                                                                dict(label="⏸", method="animate", args=[[None], dict(mode="immediate")])])],
                     sliders=[dict(x=0.08, y=-0.05, len=0.9, steps=[dict(label=str(yr), method="animate", args=[[str(yr)], dict(mode="immediate", frame=dict(duration=0, redraw=True))]) for yr in years])])
    fa.update_yaxes(range=[0, float(max(nat["G"].max(), nat["dispuesto_total_t"].max()) * 1.05)], tickformat=",.3s", row=1, col=2)
    fa.update_xaxes(tickformat="d", range=[years[0], years[-1]], row=1, col=2)
    show(fa, "nat_anim")

    st.markdown("#### " + tr("Completitud de datos por capital", "Data completeness by capital"))
    ct = r.completeness_table()
    lab_map = {k: l for k, l, _ in PROFILE_VARIABLES}
    mat = ct.set_index("ciudad")[[k for k, *_ in PROFILE_VARIABLES]].astype(int).rename(columns=lab_map)
    fh = px.imshow(mat, color_continuous_scale=[[0, "#f2e6d0"], [1, "#1f5f8b"]], aspect="auto", zmin=0, zmax=1, labels=dict(color=tr("disponible", "available")))
    fh.update_layout(height=820, coloraxis_showscale=False, title=tr("Azul = dato disponible con fuente; arena = faltante", "Blue = available with source; sand = missing"))
    fh.update_xaxes(side="top", tickangle=-35)
    show(fh, "nat_comp")


# ------------------------------------------------------------------------------------------------ 2
def page_profile():
    s = st.session_state
    r = repo()
    p = r.profile(s.city)
    hero(f"{p.ciudad} · {p.departamento}", tr(f"Perfil de ciudad. DIVIPOLA {p.divipola} · Región {p.region} · {p.lat:.4f}, {p.lon:.4f} (coordenadas aproximadas)",
                                               f"City profile. DIVIPOLA {p.divipola} · Region {p.region}"))
    df, meta = results([s.city], ["BAU"])
    m = meta["BAU"][0]
    exploratory_notice(m)
    from validation.calibration import calibrate_city
    calib = calibrate_city(r, s.city)
    rel = assess(p, calib)
    pop24 = p.pop.loc[BASE_YEAR, "poblacion_total"]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi(tr("Población", "Population") + f" {BASE_YEAR}", fmt_t(pop24), "DANE PPED 2025", tag="proj")
    with c2:
        kpi(tr("Población 2042", "Population 2042"), fmt_t(p.pop.loc[2042, "poblacion_total"]), f"{(p.pop.loc[2042, 'poblacion_total'] / pop24 - 1):+.1%} vs {BASE_YEAR}", tag="proj")
    with c3:
        kpi(tr("Cobertura de datos", "Data coverage"), f"{p.completeness['_score']:.0f} %", tr(f"{p.completeness['_anios_historicos']} años con residuos 2018-2024",
                                                                                              f"{p.completeness['_anios_historicos']} years with waste data"))
    with c4:
        kpi(tr("Confiabilidad del modelo", "Model reliability"), tr("Nivel ", "Level ") + rel["nivel"], rel["descripcion"], tone="good" if rel["nivel"] in "AB" else "bad")

    st.markdown("#### " + tr("Inventario de variables", "Variable inventory"))
    rows = []
    for key, label, unit in PROFILE_VARIABLES:
        if key == "poblacion":
            rows.append(dict(Variable=label, Valor=f"{fmt_t(pop24)} ({BASE_YEAR})", Unidad=unit, Año="2018-2042 (+2043-2050 est.)",
                             Tipo="proyeccion_oficial / estimado", Calidad="oficial", Fuente=p.pop["fuente"].iloc[0]))
            continue
        srckey = {"generacion_pc": "dispuesto_t", "generacion_t": "dispuesto_t", "composicion": "frac_organicos"}.get(key, key)
        d = p.obs[p.obs["variable"] == srckey].sort_values("anio")
        if d.empty:
            rows.append(dict(Variable=label, Valor="— " + tr("faltante", "missing"), Unidad=unit, Año="", Tipo="faltante", Calidad="", Fuente=""))
        else:
            last = d.iloc[-1]
            val = last["valor"]
            if key == "generacion_pc":
                try:
                    val = f"{float(val) * 1000 / p.pop.loc[int(last['anio']), 'poblacion_total'] / 365:.2f} (" + tr("solo dispuesto", "disposal only") + ")"
                except Exception:
                    pass
            rows.append(dict(Variable=label, Valor=val, Unidad=unit, Año=int(last["anio"]), Tipo=last["tipo_dato"], Calidad=last["calidad"], Fuente=last["fuente"]))
    table(pd.DataFrame(rows), hide_index=True)

    st.markdown("#### " + tr("Parámetros usados para esta ciudad", "Parameters used for this city"))
    par, origin = city_params(r, s.city, s.get("param_overrides", {}).get(s.city))
    origin.update(m["origin"])
    pt = pd.DataFrame([dict(Parámetro=k, Descripción=PARAMS[k].label_es if s.lang == "es" else PARAMS[k].label_en, Valor=par[k], Unidad=PARAMS[k].unit,
                            Origen=origin.get(k, PARAMS[k].kind)) for k in par])
    if not (s.mode in ("Científico", "Scientific")):
        pt = pt[pt["Parámetro"].isin(["g_pc0", "s_org", "s_rec", "kappa0", "A0", "Q0_years"])]
    table(pt, hide_index=True)
    st.markdown("#### " + tr("Limitaciones", "Limitations"))
    lim = list(rel["limitaciones"])
    if m["capacity_assumed"]:
        lim.append(tr("Capacidad de disposición supuesta.", "Assumed disposal capacity."))
    lim.append(tr("Coordenadas aproximadas del casco urbano; solo de uso cartográfico.", "Approximate coordinates; mapping only."))
    st.markdown("\n".join(f"- {x}" for x in lim))


# ------------------------------------------------------------------------------------------------ 3
def page_trends():
    s = st.session_state
    r = repo()
    p = r.profile(s.city)
    hero(tr(f"Tendencias históricas y proyectadas · {p.ciudad}", f"Historical and projected trends · {p.ciudad}"),
         tr("Línea continua y marcadores: observado u oficial. Línea discontinua: simulado. Punteado dorado: estimado por el observatorio.",
            "Solid + markers: observed/official. Dashed: simulated. Gold dotted: estimated."))
    labels = {"base_censal_conciliada": tr("Base censal 2018 (DANE)", "2018 census base"), "proyeccion_oficial": tr("Proyección oficial DANE", "DANE projection"),
              "estimado": tr("Extensión estimada 2043-2050", "Estimated extension 2043-2050")}
    c1, c2 = st.columns(2)
    with c1:
        show(population_fig(p.pop, tr("Población total", "Total population"), labels), "tr_pop")
    with c2:
        pc = p.pop[["poblacion_cabecera", "poblacion_total"]]
        f = go.Figure(go.Scatter(x=pc.index, y=100 * pc["poblacion_cabecera"] / pc["poblacion_total"], line=dict(color=C["blue"], width=3)))
        f.update_layout(title=tr("Población en cabecera (%)", "Urban (cabecera) share (%)"), height=360, yaxis_ticksuffix=" %")
        f.update_xaxes(tickformat="d")
        show(f, "tr_cab")
    df, meta = results([s.city], s.scenarios)
    dsim = df[df.escenario == s.scenario_focus].set_index("anio")
    obs_d, obs_a = p.series("dispuesto_t"), p.series("aprovechado_t")
    exploratory_notice(_meta_of(meta, s.scenario_focus, s.city))
    c3, c4 = st.columns(2)
    with c3:
        show(line_obs_sim(dsim["dispuesto_total_t"], obs_d, tr("Disposición final (t/año)", "Final disposal (t/yr)"), "t/año",
                          tr(f"Simulado · {scen_label(s.scenario_focus)}", "Simulated"), tr("Observado SSPD", "Observed SSPD"), C["grey"]), "tr_disp")
    with c4:
        show(line_obs_sim(dsim["aprovechado_t"], obs_a, tr("Aprovechamiento (t/año)", "Recovery (t/yr)"), "t/año",
                          tr(f"Simulado · {scen_label(s.scenario_focus)}", "Simulated"), tr("Observado SSPD", "Observed SSPD"), C["green"]), "tr_apr")
    if obs_d.empty:
        st.caption(tr("No hay series SSPD cargadas para esta ciudad: solo se muestra la trayectoria simulada.", "No SSPD series loaded for this city."))
    c5, c6 = st.columns(2)
    with c5:
        obs_pc = (obs_d + obs_a.reindex(obs_d.index).fillna(0)) * 1000 / p.pop["poblacion_total"].reindex(obs_d.index) / 365 if len(obs_d) else None
        show(line_obs_sim(dsim["gpc_kg_dia"], obs_pc, tr("Generación per cápita (kg/hab/día)", "Per-capita generation"), "kg/hab/día",
                          tr("Simulado", "Simulated"), tr("Observado (dispuesto + aprovechado)", "Observed"), C["gold"], fmt=".2f"), "tr_pc")
    with c6:
        base = dsim.index.min()
        f = go.Figure()
        for col, name, color in (("pop", tr("Población", "Population"), C["blue"]), ("G", tr("Generación", "Generation"), C["green"]),
                                 ("dispuesto_total_t", tr("Disposición", "Disposal"), C["grey"])):
            f.add_trace(go.Scatter(x=dsim.index, y=100 * dsim[col] / dsim[col].iloc[0], name=name, line=dict(color=color, width=3)))
        f.update_layout(title=tr(f"Desacoplamiento (índice {base} = 100)", f"Decoupling (index {base} = 100)"), height=380, hovermode="x unified")
        f.update_xaxes(tickformat="d")
        show(f, "tr_idx")


# ------------------------------------------------------------------------------------------------ 4
def page_composition():
    s = st.session_state
    r = repo()
    p = r.profile(s.city)
    hero(tr(f"Composición de residuos · {p.ciudad}", f"Waste composition · {p.ciudad}"),
         tr("Fracciones que determinan el potencial material de reciclaje y de tratamiento de orgánicos.", "Fractions that set the material potential."))
    par, origin = city_params(r, s.city, s.get("param_overrides", {}).get(s.city))
    so, sr = par["s_org"], par["s_rec"]
    oth = max(1 - so - sr, 0)
    measured = str(origin["s_org"]).startswith("medido") or str(origin["s_rec"]).startswith("medido")
    if not measured:
        st.warning(tr("No hay caracterización física cargada para esta ciudad. Se usan **70 % orgánicos** (CATF, 2024, referencia nacional) y **20 % reciclables** "
                      "(supuesto). Cargue la caracterización del PGIRS en `data/raw/` para sustituirlos.",
                      "No physical characterisation loaded: 70 % organics (CATF 2024) and 20 % recyclables (assumption)."), icon="⚠️")
    c1, c2, c3 = st.columns(3)
    with c1:
        kpi(tr("Orgánicos", "Organics"), f"{so:.0%}", origin["s_org"], tag="obs" if measured else "est")
    with c2:
        kpi(tr("Reciclables", "Recyclables"), f"{sr:.0%}", origin["s_rec"], tag="obs" if measured else "sup")
    with c3:
        kpi(tr("Otros / no aprovechables", "Other"), f"{oth:.0%}", tr("por diferencia", "by difference"))
    df, _ = results([s.city], s.scenarios)
    d = df[(df.escenario == s.scenario_focus)].set_index("anio")
    a, b = st.columns(2)
    with a:
        f = px.pie(names=[tr("Orgánicos", "Organics"), tr("Reciclables", "Recyclables"), tr("Otros", "Other")], values=[so, sr, oth], hole=0.55,
                   color_discrete_sequence=[C["green"], C["gold"], C["grey"]], title=tr("Composición usada en el modelo", "Composition used"))
        f.update_layout(height=380)
        show(f, "co_pie")
    with b:
        f = go.Figure()
        f.add_trace(go.Scatter(x=d.index, y=d["C"] * sr, name=tr("Potencial reciclable recolectado", "Collected recyclable potential"), line=dict(color=C["gold"], dash="dot")))
        f.add_trace(go.Scatter(x=d.index, y=d["Rrec"], name=tr("Reciclables recuperados", "Recovered recyclables"), line=dict(color=C["gold"], width=3), fill="tozeroy"))
        f.add_trace(go.Scatter(x=d.index, y=d["C"] * so, name=tr("Potencial orgánico recolectado", "Collected organic potential"), line=dict(color=C["green"], dash="dot")))
        f.add_trace(go.Scatter(x=d.index, y=d["Kout"], name=tr("Orgánicos tratados", "Treated organics"), line=dict(color=C["green"], width=3), fill="tozeroy"))
        f.update_layout(title=tr(f"Potencial material vs recuperado · {scen_label(s.scenario_focus)}", "Material potential vs recovered"), height=380, yaxis_tickformat=",.3s",
                        hovermode="x unified")
        f.update_xaxes(tickformat="d")
        show(f, "co_pot")
    st.caption(tr("La recuperación nunca supera el potencial material recolectado (restricción física verificada en las pruebas automáticas).",
                  "Recovery never exceeds the collected material potential (verified by automated tests)."))
