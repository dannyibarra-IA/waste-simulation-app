import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import numpy as np

# ==============================
# PAGE CONFIG & GLOBAL STYLE
# ==============================
st.set_page_config(page_title="Urban Waste Simulation and Circularity", layout="wide")

# Modern UI Styling
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #f8f9fb; }
        [data-testid="stSidebar"] { background-color: #eef2f6; }
        h1, h2, h3, h4 { color: #1d3557; }
        .stTabs [data-baseweb="tab"] { font-size:16px; font-weight:600; }
    </style>
""", unsafe_allow_html=True)

# ==============================
# HEADER / BANNER
# ==============================
st.markdown("""
# 🌎 Urban Waste Simulation and Circularity Dashboard  
This interactive dashboard shows the simulation of **population growth** and **waste generation**  
in 10 Colombian cities from **2025 to 2050**, integrating **System Dynamics modeling** with  
**Generative AI** to explore **urban circularity scenarios**.
""")

# ==============================
# LOAD DATA (REAL EXCEL)
# ==============================
DATA_FILE = "simulacion_residuos_2025_2050.xlsx"

@st.cache_data
def load_data(path: str):
    p = Path(path)
    if not p.exists():
        return None, None, None, False

    pop = pd.read_excel(path, sheet_name="Poblacion_2050", index_col=0)
    waste = pd.read_excel(path, sheet_name="ResiduosTotales_t_anio", index_col=0)
    types = pd.read_excel(path, sheet_name="Residuos_5Tipos_largo")

    # Numeric & tidy
    pop = pop.apply(pd.to_numeric, errors="coerce")
    waste = waste.apply(pd.to_numeric, errors="coerce")
    pop.index = pop.index.astype(float).round().astype(int)
    waste.index = waste.index.astype(float).round().astype(int)
    pop.columns = pop.columns.str.strip()
    waste.columns = waste.columns.str.strip()
    if "Ciudad" in types.columns:
        types["Ciudad"] = types["Ciudad"].astype(str).str.strip()
    if "Tipo" in types.columns:
        types["Tipo"] = types["Tipo"].astype(str).str.strip()

    return pop, waste, types, True

df_pop, df_waste, df_types, has_real_data = load_data(DATA_FILE)
if not has_real_data:
    st.error("❌ Archivo 'simulacion_residuos_2025_2050.xlsx' no encontrado. Súbelo al mismo nivel del script.")
    st.stop()

# ==============================
# CONFIG (coords & landfills)
# ==============================
city_coords = {
    "Medellín": (6.2442, -75.5812),
    "Santiago de Cali": (3.4516, -76.5320),
    "Barranquilla": (10.9685, -74.7813),
    "Cartagena de Indias": (10.3910, -75.4794),
    "Soacha": (4.5833, -74.2167),
    "San José de Cúcuta": (7.8939, -72.5078),
    "Soledad": (10.9184, -74.7646),
    "Bucaramanga": (7.1254, -73.1198),
    "Bello": (6.3373, -75.5540),
    "Valledupar": (10.4631, -73.2532)
}
landfills = {
    "Medellín": "La Pradera", "Santiago de Cali": "Navarro",
    "Barranquilla": "Los Pocitos", "Cartagena de Indias": "Henequén",
    "Soacha": "Doña Juana (Bogotá)", "San José de Cúcuta": "Guayabal",
    "Soledad": "Los Pocitos (Metropolitano)", "Bucaramanga": "El Carrasco",
    "Bello": "La Pradera", "Valledupar": "Los Corazones"
}

# Asegurar que existan datos para estas ciudades
cities_available = sorted(list(set(df_pop.columns) & set(df_waste.columns) & set(city_coords.keys())))
if not cities_available:
    st.error("❌ Ninguna ciudad del Excel coincide con las coordenadas configuradas. Revisa nombres/acentos.")
    st.stop()

# ==============================
# SIDEBAR CONTROLS
# ==============================
st.sidebar.title("Simulation Control")
city = st.sidebar.selectbox("Select City", cities_available, index=0)
min_year = max(2025, int(min(df_pop.index.min(), df_waste.index.min())))
max_year = min(2050, int(max(df_pop.index.max(), df_waste.index.max())))
year_range = st.sidebar.slider("Select Year Range", min_year, max_year, (min_year, max_year))

# ==============================
# TABS
# ==============================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Population & Waste",
    "♻️ Composition by Type",
    "🗺️ Geographic View",
    "🎞️ Animated Simulation + Chart",
    "ℹ️ About",
])

# ==============================
# TAB 1 — Population & Waste
# ==============================
with tab1:
    st.subheader(f"Population Projection: {city}")
    df_pop_plot = df_pop.loc[(df_pop.index >= year_range[0]) & (df_pop.index <= year_range[1]), [city]]
    fig1 = px.line(df_pop_plot, x=df_pop_plot.index, y=city, markers=True,
                   labels={"x": "Year", "y": "Population"}, title="Population 2025–2050")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader(f"Total Waste Generation (tons/year): {city}")
    df_waste_plot = df_waste.loc[(df_waste.index >= year_range[0]) & (df_waste.index <= year_range[1]), [city]]
    fig2 = px.line(df_waste_plot, x=df_waste_plot.index, y=city, markers=True,
                   labels={"x": "Year", "y": "Tons/year"}, title="Waste Generation 2025–2050")
    st.plotly_chart(fig2, use_container_width=True)

# ==============================
# TAB 2 — Composition by Type
# ==============================
with tab2:
    st.subheader(f"Waste Composition by Type: {city}")
    expected_cols = {"Ciudad", "Año", "Tipo", "Toneladas_anio"}
    if expected_cols.issubset(set(df_types.columns)):
        df_city = df_types[(df_types["Ciudad"] == city) &
                           (df_types["Año"].between(year_range[0], year_range[1]))]
        if df_city.empty:
            st.info("No hay tabla de composición larga para esta ciudad en el rango seleccionado.")
        else:
            pivot = df_city.pivot(index="Año", columns="Tipo", values="Toneladas_anio").sort_index()
            fig3 = px.area(pivot, x=pivot.index, y=pivot.columns,
                           title="Composition of Waste by Type",
                           labels={"value": "Tons/year", "Año": "Year"})
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Hoja 'Residuos_5Tipos_largo' no tiene columnas esperadas (Ciudad, Año, Tipo, Toneladas_anio).")

# ==============================
# TAB 3 — Geographic View (selector año + toggle unidades)
# ==============================
with tab3:
    st.subheader("Geographic View — Daily/Annual Waste, Population & Landfill")
    # Selector de año y unidades
    view_year = st.slider("Select year to visualize:", min_value=min_year, max_value=max_year, value=min_year)
    unit = st.radio("Units:", ["tons/day", "tons/year"], horizontal=True)

    cities = cities_available
    df_now = pd.DataFrame({
        "City": cities,
        "lat": [city_coords[c][0] for c in cities],
        "lon": [city_coords[c][1] for c in cities],
        "Landfill": [landfills.get(c, "N/A") for c in cities],
        "Population": [float(df_pop.loc[view_year, c]) if view_year in df_pop.index else np.nan for c in cities],
        "Waste_tons_year": [float(df_waste.loc[view_year, c]) if view_year in df_waste.index else np.nan for c in cities],
    })
    df_now["Daily_waste_tpd"] = df_now["Waste_tons_year"] / 365.0
    df_now["Value"] = df_now["Daily_waste_tpd"] if unit == "tons/day" else df_now["Waste_tons_year"]
    cbar_title = "t/day" if unit == "tons/day" else "t/year"

    # Tamaños robustos (evita división por 0)
    m = float(df_now["Value"].fillna(0).max()); m = 1.0 if m == 0 else m
    sizes = 6 + 44 * (df_now["Value"].fillna(0) / m).clip(0, 1)

    fig_current = px.scatter_mapbox(
        df_now, lat="lat", lon="lon",
        size=None,  # control manual
        color="Value",
        hover_name="City",
        hover_data={"Landfill": True, "Population": ":,.0f", "Value": ":,.1f"},
        color_continuous_scale="Turbo",  # más vibrante
        zoom=5, mapbox_style="open-street-map",
        title=f"Geographic Distribution • {view_year}"
    )
    fig_current.update_traces(marker=dict(size=sizes, line=dict(width=1, color="white"), opacity=0.9))
    fig_current.update_layout(margin=dict(l=0, r=0, t=50, b=0),
                              coloraxis_colorbar=dict(title=cbar_title, thickness=12, len=0.75, y=0.55))
    st.plotly_chart(fig_current, use_container_width=True)

# ==============================
# TAB 4 — Animated Map + Animated Line (mismo Play)
# ==============================
with tab4:
    st.markdown("### Animated Simulation (2025–2050) + **Waste Generation of Ten Cities**")

    cities_ok = cities_available
    years = [y for y in range(2025, 2051) if y in df_waste.index]

    base = pd.DataFrame({
        "City": cities_ok,
        "lat": [city_coords[c][0] for c in cities_ok],
        "lon": [city_coords[c][1] for c in cities_ok],
    })

    frames_list = []
    for y in years:
        frames_list.append(pd.DataFrame({
            "City": base["City"],
            "lat": base["lat"],
            "lon": base["lon"],
            "Year": y,
            "Waste_tons": [float(df_waste.loc[y, c]) for c in cities_ok],
        }))
    df_anim = pd.concat(frames_list, ignore_index=True)
    national = df_anim.groupby("Year")["Waste_tons"].sum().reset_index()

    # Subplots: mapa + línea (comparten frames)
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "mapbox"}, {"type": "xy"}]],
        column_widths=[0.62, 0.38],
        horizontal_spacing=0.06,
        subplot_titles=("Geographic Projection", "Waste Generation of Ten Cities")
    )

    def bubble_sizes(sub):
        m = float(sub["Waste_tons"].fillna(0).max()); m = 1.0 if m == 0 else m
        return 6 + 44 * (sub["Waste_tons"].fillna(0) / m).clip(0, 1)

    y0 = years[0]
    d0 = df_anim[df_anim["Year"] == y0]
    nat0 = national[national["Year"] <= y0]

    # Trace 0: mapa
    fig.add_trace(
        go.Scattermapbox(
            lat=d0["lat"], lon=d0["lon"], mode="markers",
            marker=dict(size=bubble_sizes(d0), color=d0["Waste_tons"],
                        colorscale="Turbo", showscale=True,
                        colorbar=dict(title="t/year", thickness=12, len=0.75, y=0.55),
                        line=dict(width=1, color="white"), opacity=0.9),
            text=d0["City"],
            hovertemplate="<b>%{text}</b><br>Annual waste: %{marker.color:,.0f} t/year<extra></extra>"
        ),
        row=1, col=1
    )

    # Trace 1: línea (hasta y0)
    fig.add_trace(
        go.Scatter(
            x=nat0["Year"], y=nat0["Waste_tons"],
            mode="lines+markers",
            line=dict(color="#3A86FF", width=3),
            marker=dict(color="#8338EC", size=7),
            name="Total",
            hovertemplate="Year: %{x}<br>t/year: %{y:,.0f}<extra></extra>"
        ),
        row=1, col=2
    )

    # Frames sincronizados
    frames = []
    for y in years:
        dy = df_anim[df_anim["Year"] == y]
        ny = national[national["Year"] <= y]
        frames.append(go.Frame(
            name=str(y),
            data=[
                go.Scattermapbox(
                    lat=dy["lat"], lon=dy["lon"], mode="markers",
                    marker=dict(size=bubble_sizes(dy), color=dy["Waste_tons"],
                                colorscale="Turbo", showscale=True,
                                line=dict(width=1, color="white"), opacity=0.9),
                    text=dy["City"],
                    hovertemplate="<b>%{text}</b><br>Annual waste: %{marker.color:,.0f} t/year<extra></extra>"
                ),
                go.Scatter(
                    x=ny["Year"], y=ny["Waste_tons"],
                    mode="lines+markers",
                    line=dict(color="#3A86FF", width=3),
                    marker=dict(color="#8338EC", size=7),
                    name="Total",
                    hovertemplate="Year: %{x}<br>t/year: %{y:,.0f}<extra></extra>"
                )
            ]
        ))
    fig.frames = frames

    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_zoom=5, mapbox_center={"lat": 4.6, "lon": -74.1},
        margin=dict(l=10, r=10, t=60, b=10),
        font=dict(size=13, color="#1d3557"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        updatemenus=[{
            "type": "buttons", "direction": "left", "x": 0.12, "y": -0.08, "showactive": True,
            "buttons": [
                {"label": "▶ Play", "method": "animate",
                 "args": [None, {"frame": {"duration": 800, "redraw": True},
                                 "fromcurrent": True, "transition": {"duration": 300}}]},
                {"label": "⏸ Pause", "method": "animate",
                 "args": [[None], {"frame": {"duration": 0, "redraw": False},
                                   "mode": "immediate", "transition": {"duration": 0}}]}
            ]
        }],
        sliders=[{
            "active": 0, "y": -0.05, "x": 0.12, "len": 0.7,
            "pad": {"b": 10, "t": 10},
            "currentvalue": {"prefix": "Year: ", "font": {"size": 16}},
            "steps": [{"args": [[str(y)], {"frame": {"duration": 0, "redraw": True},
                                          "mode": "immediate"}],
                       "label": str(y), "method": "animate"} for y in years]
        }],
        xaxis_title="Year", yaxis_title="tons/year"
    )

    st.plotly_chart(fig, use_container_width=True)

# ==============================
# TAB 5 — About
# ==============================
with tab5:
    st.markdown("""
### About
**Developer:** Dr. Danny Ibarra Vega — Universidad de Antioquia (2025)**  
**Method:** System Dynamics (logistic population growth, bounded PPC), 2025–2050 simulations.  
**Data:** DANE projections (2018–2042), SSPD (2023), city-specific compositions.  
**AI Layer:** Generative AI for parameter exploration, scenario generation, and narrative visualization.
""")

