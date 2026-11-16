"""Optional visual module for Waste Simulation App v2.

No modifications to the mass-balance engine or its source datasets.
Call render_visual_dashboard(results, city_coords, ... ) after the existing tabs.
"""
from __future__ import annotations
from datetime import datetime, timezone
from io import BytesIO
import html
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

METRICS = {
    "Generación total": ("Generated_t", "t/año", False),
    "Residuos aprovechados": ("Diverted_t", "t/año", False),
    "Disposición final": ("Landfilled_t", "t/año", False),
    "Generación per cápita": ("kg_person_day", "kg/hab·día", False),
    "Tasa de aprovechamiento": ("Diversion_rate", "%", True),
    "Cobertura de recolección": ("Collection_rate", "%", True),
}
PALETTE = {"blue": "#155e82", "green": "#16836a", "gold": "#cf9a37", "grey": "#64748b", "red": "#b44743"}


def _safe_value(result: pd.DataFrame, year: int, field: str):
    if result is None or field not in result.columns or year not in result.index:
        return np.nan
    value = pd.to_numeric(pd.Series([result.loc[year, field]]), errors="coerce").iloc[0]
    return float(value) if np.isfinite(value) else np.nan


def build_comparison_table(results: dict, coords: dict, year: int):
    """Preserves missing values; does not infer observations or geography."""
    rows = []
    for city, df in sorted(results.items()):
        lat, lon = coords.get(city, (np.nan, np.nan))
        row = {"Ciudad": city, "Año": year, "Latitud": lat, "Longitud": lon}
        for _, (field, _, _) in METRICS.items():
            row[field] = _safe_value(df, year, field)
        row["Population"] = _safe_value(df, year, "Population")
        rows.append(row)
    return pd.DataFrame(rows)


def _metric_values(frame: pd.DataFrame, field: str, percentage: bool):
    values = frame[field].astype(float)
    return values * 100 if percentage else values


def _fig_map(frame: pd.DataFrame, field: str, label: str, unit: str, percentage: bool):
    geo = frame.dropna(subset=["Latitud", "Longitud", field]).copy()
    if geo.empty:
        return None
    geo["Valor"] = _metric_values(geo, field, percentage)
    # Stable log-like marker sizes prevent one large city hiding smaller cities.
    base = np.sqrt(np.clip(geo["Valor"].abs(), 0, None))
    upper = float(base.max())
    geo["Tamaño"] = 12 + 27 * (base / upper if upper > 0 else 0)
    fig = go.Figure(go.Scattermap(
        lat=geo["Latitud"], lon=geo["Longitud"], mode="markers",
        text=geo["Ciudad"], customdata=np.stack([geo["Valor"].to_numpy()], axis=1),
        marker=dict(size=geo["Tamaño"], color=geo["Valor"], colorscale="YlGnBu", opacity=.86,
                    showscale=True, colorbar=dict(title=unit, thickness=12)),
        hovertemplate=f"<b>%{{text}}</b><br>{label}: %{{customdata[0]:,.2f}} {unit}<extra></extra>",
    ))
    fig.update_layout(map=dict(style="carto-positron", center=dict(lat=4.8, lon=-73.8), zoom=3.65),
                      height=555, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor="white")
    return fig


def _fig_ranking(frame: pd.DataFrame, field: str, title: str, unit: str, percentage: bool):
    ranked = frame[["Ciudad", field]].dropna().copy()
    ranked["Valor"] = _metric_values(ranked, field, percentage)
    ranked = ranked.sort_values("Valor", ascending=True)
    f = px.bar(ranked, x="Valor", y="Ciudad", orientation="h", title=title,
               labels={"Valor": unit, "Ciudad": ""}, color_discrete_sequence=[PALETTE["blue"]])
    f.update_layout(height=max(390, 28 * len(ranked) + 130), margin=dict(l=10,r=15,t=55,b=30),
                    plot_bgcolor="white", paper_bgcolor="white", showlegend=False)
    f.update_xaxes(showgrid=True, gridcolor="#e9eef2")
    f.update_yaxes(showgrid=False)
    return f


def _fig_trends(results: dict, selected: list, field: str, label: str, unit: str, percentage: bool, year_from: int, year_to: int):
    rows = []
    for city in selected:
        if city not in results or field not in results[city]:
            continue
        for year, value in results[city].loc[year_from:year_to,field].items():
            if pd.notna(value):
                rows.append({"Ciudad": city, "Año": int(year), "Valor": float(value)*(100 if percentage else 1)})
    if not rows:
        return None
    df = pd.DataFrame(rows)
    f = px.line(df, x="Año", y="Valor", color="Ciudad", markers=True,
                title=f"Evolución de {label.lower()}", labels={"Valor": unit})
    f.update_traces(line_width=2.8, marker_size=5)
    f.update_layout(height=430, hovermode="x unified", legend=dict(orientation="h",y=-.2),
                    margin=dict(l=10,r=10,t=55,b=90), paper_bgcolor="white", plot_bgcolor="white")
    f.update_xaxes(dtick=max(1, round((year_to-year_from)/6)), showgrid=False)
    f.update_yaxes(gridcolor="#e9eef2", rangemode="tozero")
    return f


def _pdf_report(frame: pd.DataFrame, city: str, year: int, scenario: str, source_label: str):
    """One-page factual PDF; labels these numbers as model outputs, not observations."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    out=BytesIO()
    doc=SimpleDocTemplate(out,pagesize=A4,rightMargin=19*mm,leftMargin=19*mm,topMargin=20*mm,bottomMargin=20*mm)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Sub",parent=styles["Normal"],fontSize=9,leading=14,textColor=colors.HexColor("#536779")))
    story=[Paragraph("Waste Simulation App | Reporte de simulación",styles["Title"]),Spacer(1,10),
           Paragraph(f"Ciudad: <b>{html.escape(city)}</b> &nbsp;&nbsp; Año: <b>{year}</b>",styles["Normal"]),Spacer(1,6),
           Paragraph(f"Escenario: {html.escape(scenario)}",styles["Sub"]),Spacer(1,12)]
    match=frame.loc[frame["Ciudad"]==city]
    if match.empty: raise ValueError("Ciudad no disponible en el año seleccionado")
    rec=match.iloc[0]
    table_data=[["Indicador", "Valor del modelo", "Unidad"]]
    for label,(field,unit,percentage) in METRICS.items():
        v=rec.get(field,np.nan)
        table_data.append([label, f"{v*100 if percentage else v:,.2f}" if pd.notna(v) else "Sin dato",unit])
    t=Table(table_data,colWidths=[73*mm,58*mm,39*mm],repeatRows=1,hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#173b55")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f1f5f9")]),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("TOPPADDING",(0,0),(-1,-1),10),("FONTSIZE",(0,0),(-1,-1),9)]))
    story.extend([t,Spacer(1,18),Paragraph("Alcance y trazabilidad",styles["Heading2"]),
       Paragraph("Los valores reflejan salidas del modelo bajo los parámetros y el escenario activos. "
                 "No constituyen observaciones oficiales ni resultados calibrados o validados por sí solos.",styles["Sub"]),Spacer(1,7),
       Paragraph("Fuente de entrada: "+html.escape(str(source_label)),styles["Sub"]),
       Paragraph("Generado: "+datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),styles["Sub"]),
       Spacer(1,15),Paragraph("Desarrollado por Danny Ibarra Vega, Ph.D. | Universidad de Antioquia",styles["Sub"])])
    doc.build(story)
    out.seek(0)
    return out.getvalue()


def render_visual_dashboard(results: dict, city_coords: dict, selected_year: int, selected_city: str,
                            scenario_label: str="Escenario actual", source_label: str="Archivo del proyecto"):
    """Visual extension; use after existing v2 tabs. No run_city calls are made here."""
    if not results:
        st.warning("No hay simulaciones disponibles para visualizar.")
        return
    years=sorted(set.intersection(*(set(map(int,df.index)) for df in results.values())))
    if not years:
        st.warning("Las ciudades no comparten un periodo de simulación.")
        return
    if selected_year not in years: selected_year=years[-1]
    st.markdown("---")
    st.header("🗺️ Observatorio geográfico y comparativo")
    st.caption("Módulo visual v3.0 · Resultados del motor de simulación vigente; cobertura limitada a las ciudades presentes en los datos.")
    city_count=len(results)
    geo_count=sum(c in city_coords for c in results)
    st.info(f"Cobertura actual: {city_count} ciudades con simulación; {geo_count} con coordenadas. No equivale necesariamente a las 32 capitales.")
    c1,c2,c3=st.columns([1.5,1,1])
    with c1: indicator=st.selectbox("Indicador para mapa y clasificación",list(METRICS),key="visual_indicator")
    with c2: year=st.select_slider("Año",options=years,value=selected_year,key="visual_year")
    with c3: comparison=st.multiselect("Comparar ciudades (máximo 6)",sorted(results),
                   default=[selected_city] if selected_city in results else sorted(results)[:1],max_selections=6,key="visual_comparison")
    field,unit,percent=METRICS[indicator]
    frame=build_comparison_table(results,city_coords,year)
    valid=frame.dropna(subset=[field])
    m1,m2,m3=st.columns(3)
    m1.metric("Ciudades con indicador",f"{len(valid)}/{city_count}")
    m2.metric("Ciudades georreferenciadas",f"{geo_count}/{city_count}")
    m3.metric("Mediana entre ciudades",f"{_metric_values(valid,field,percent).median():,.2f} {unit}" if len(valid) else "Sin dato")
    st.caption("La mediana es por ciudad, no un agregado poblacional. Los totales corresponden solo a la cobertura actual.")
    left,right=st.columns([1.15,1])
    with left:
        fig=_fig_map(frame,field,indicator,unit,percent)
        if fig is None: st.warning("No hay coordenadas verificadas para las ciudades seleccionadas.")
        else: st.plotly_chart(fig,use_container_width=True,key="visual_map")
    with right:
        st.plotly_chart(_fig_ranking(frame,field,f"Comparación · {year}",unit,percent),
                        use_container_width=True,key="visual_ranking")
    st.subheader("Series comparativas")
    if comparison:
        fig=_fig_trends(results,comparison,field,indicator,unit,percent,years[0],years[-1])
        if fig is not None: st.plotly_chart(fig,use_container_width=True,key="visual_trends")
    else: st.caption("Selecciona al menos una ciudad.")
    view=frame[["Ciudad","Año",field,"Population"]].rename(columns={field:indicator,"Population":"Población"})
    if percent: view[indicator]=view[indicator]*100
    st.dataframe(view,hide_index=True,use_container_width=True)
    st.subheader("Descarga de resultados y reporte")
    x,y=st.columns(2)
    with x:
        st.download_button("⬇ Descargar tabla comparativa CSV",data=view.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"comparacion_ciudades_{year}.csv",mime="text/csv",key="visual_csv")
    with y:
        target=selected_city if selected_city in results else sorted(results)[0]
        st.download_button(f"⬇ Reporte PDF · {target}",data=_pdf_report(frame,target,year,scenario_label,source_label),
                           file_name=f"reporte_{year}_{target.replace(' ','_')}.pdf",mime="application/pdf",key="visual_pdf")
    st.caption("Los informes identifican las cifras como resultados de simulación. No atribuyen origen oficial a series sin metadatos verificados.")
