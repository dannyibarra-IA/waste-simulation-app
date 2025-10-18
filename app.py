import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import numpy as np

# -------------------------------------------------
# PAGE CONFIGURATION
# -------------------------------------------------
st.set_page_config(page_title='Urban Waste Simulation and Circularity', layout='wide')

# -------------------------------------------------
# HEADER / BANNER
# -------------------------------------------------
st.markdown(
    """
    # 🌎 Urban Waste Simulation and Circularity Dashboard  
    This interactive dashboard shows the simulation of **population growth** and **waste generation**  
    in 10 Colombian cities from **2025 to 2050**, integrating **System Dynamics modeling** with  
    **Generative AI** to explore **urban circularity scenarios**.
    """
)

# -------------------------------------------------
# LOAD DATA
# -------------------------------------------------
DATA_FILE = 'simulacion_residuos_2025_2050.xlsx'

@st.cache_data
def load_data(path: str):
    p = Path(path)
    if p.exists():
        pop = pd.read_excel(path, sheet_name='Poblacion_2050', index_col=0)
        waste = pd.read_excel(path, sheet_name='ResiduosTotales_t_anio', index_col=0)
        types = pd.read_excel(path, sheet_name='Residuos_5Tipos_largo')
        return pop, waste, types, True
    else:
        # DEMO fallback
        cities_demo = ['Medellín','Santiago de Cali','Barranquilla','Cartagena de Indias',
                       'Soacha','San José de Cúcuta','Soledad','Bucaramanga','Bello','Valledupar']
        years = list(range(2025, 2051))
        pop_df = pd.DataFrame(index=years, data={c: np.linspace(0.5e6, 2.5e6, len(years)) for c in cities_demo})
        waste_df = (pop_df * 0.365).rename_axis('Año')
        rows = []
        shares = {'Organicos':0.60, 'Plasticos':0.12, 'Papel_Carton':0.10, 'Vidrio':0.04, 'Metales':0.02}
        for c in cities_demo:
            for y in years:
                total = waste_df.loc[y, c]
                for k, v in shares.items():
                    rows.append({'Ciudad': c, 'Año': y, 'Tipo': k, 'Toneladas_anio': total * v})
        types_df = pd.DataFrame(rows)
        return pop_df, waste_df, types_df, False

df_pop, df_waste, df_types, loaded_from_file = load_data(DATA_FILE)
cities = df_pop.columns.tolist()

city_coords = {
    'Medellín': (6.2442, -75.5812),
    'Santiago de Cali': (3.4516, -76.5320),
    'Barranquilla': (10.9685, -74.7813),
    'Cartagena de Indias': (10.3910, -75.4794),
    'Soacha': (4.5833, -74.2167),
    'San José de Cúcuta': (7.8939, -72.5078),
    'Soledad': (10.9184, -74.7646),
    'Bucaramanga': (7.1254, -73.1198),
    'Bello': (6.3373, -75.5540),
    'Valledupar': (10.4631, -73.2532)
}

# -------------------------------------------------
# SIDEBAR CONTROLS
# -------------------------------------------------
st.sidebar.title('Simulation Control')
city = st.sidebar.selectbox('Select City', cities, index=0)
year_range = st.sidebar.slider('Select Year Range', 2025, 2050, (2025, 2050))

# -------------------------------------------------
# MAIN TABS
# -------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    '📈 Population & Waste',
    '♻️ Composition by Type',
    '🗺️ Geographic View',
    '🎞️ Animated Simulation + Chart',
    'ℹ️ About'
])

# -------------------------------------------------
# TAB 1: Population & Waste
# -------------------------------------------------
with tab1:
    st.subheader(f'Population Projection: {city}')
    df_pop_plot = df_pop[(df_pop.index >= year_range[0]) & (df_pop.index <= year_range[1])]
    fig1 = px.line(df_pop_plot, x=df_pop_plot.index, y=city, markers=True,
                   labels={'x':'Year','y':'Population'}, title='Population 2025–2050')
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader(f'Total Waste Generation (tons/year): {city}')
    df_waste_plot = df_waste[(df_waste.index >= year_range[0]) & (df_waste.index <= year_range[1])]
    fig2 = px.line(df_waste_plot, x=df_waste_plot.index, y=city, markers=True,
                   labels={'x':'Year','y':'Tons/year'}, title='Waste Generation 2025–2050')
    st.plotly_chart(fig2, use_container_width=True)

    if not loaded_from_file:
        st.warning("⚠️ Demo data is being used because 'simulacion_residuos_2025_2050.xlsx' was not found. Upload the real file to the repo for real results.")

# -------------------------------------------------
# TAB 2: Composition by Type
# -------------------------------------------------
with tab2:
    st.subheader(f'Waste Composition by Type: {city}')
    df_city = df_types[df_types['Ciudad'] == city]
    if df_city.empty and city in df_waste.columns:
        st.info('Composition data not found; showing total waste instead.')
        st.line_chart(df_waste[city])
    else:
        df_city = df_city[(df_city['Año'] >= year_range[0]) & (df_city['Año'] <= year_range[1])]
        pivot = df_city.pivot(index='Año', columns='Tipo', values='Toneladas_anio')
        fig3 = px.area(pivot, x=pivot.index, y=pivot.columns,
                       title='Composition of Waste by Type (2025–2050)',
                       labels={'value': 'Tons/year', 'Año': 'Year'})
        st.plotly_chart(fig3, use_container_width=True)

# -------------------------------------------------
# TAB 3: Geographic Distribution (2050)
# -------------------------------------------------
with tab3:
    st.subheader("Geographic View — Current Daily Waste, Population & Landfill (2025)")

    # Año "actual" (ajústalo a 2024 si lo manejas en tu Excel)
    current_year = 2025 if 2025 in df_waste.index else int(df_waste.index.min())

    # Diccionario de rellenos (ajústalo si tienes nombres oficiales distintos)
    rellenos = {
        "Medellín": "La Pradera",
        "Santiago de Cali": "Navarro",
        "Barranquilla": "Los Pocitos",
        "Cartagena de Indias": "Henequén",
        "Soacha": "Doña Juana (Bogotá)",
        "San José de Cúcuta": "Guayabal",
        "Soledad": "Los Pocitos (Metropolitano)",
        "Bucaramanga": "El Carrasco",
        "Bello": "La Pradera",
        "Valledupar": "Los Corazones"
    }

    # Base con coordenadas + rellenos
    df_base = pd.DataFrame({
        "City": list(city_coords.keys()),
        "lat": [v[0] for v in city_coords.values()],
        "lon": [v[1] for v in city_coords.values()],
        "Landfill": [rellenos.get(c, "N/A") for c in city_coords.keys()]
    })

    # Construir datos 2025
    df_now = pd.DataFrame({
        "City": df_base["City"],
        "lat": df_base["lat"],
        "lon": df_base["lon"],
        "Population": [float(df_pop.loc[current_year, c]) if current_year in df_pop.index and c in df_pop.columns else float("nan")
                       for c in df_base["City"]],
        "Waste_tons_year": [float(df_waste.loc[current_year, c]) if current_year in df_waste.index and c in df_waste.columns else float("nan")
                            for c in df_base["City"]],
        "Landfill": df_base["Landfill"]
    })
    df_now["Daily_waste_tpd"] = df_now["Waste_tons_year"] / 365.0

    # Mapa (tamaño/color por t/día)
    fig_current = px.scatter_mapbox(
        df_now,
        lat="lat", lon="lon",
        size="Daily_waste_tpd",
        color="Daily_waste_tpd",
        hover_name="City",
        hover_data={
            "Landfill": True,
            "Population": ":.0f",
            "Daily_waste_tpd": ":.1f"
        },
        color_continuous_scale="Viridis",
        zoom=5,
        mapbox_style="carto-positron",
        title=f"Current Daily Waste (tons/day) • {current_year}"
    )
    st.plotly_chart(fig_current, use_container_width=True)

# -------------------------------------------------
# TAB 4: Animated Map + National Chart
# -------------------------------------------------
with tab4:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    st.markdown("### Animated Simulation (2025–2050) + National Trend (synchronized)")

    # Rellenos
    rellenos = {
        "Medellín": "La Pradera", "Santiago de Cali": "Navarro",
        "Barranquilla": "Los Pocitos", "Cartagena de Indias": "Henequén",
        "Soacha": "Doña Juana (Bogotá)", "San José de Cúcuta": "Guayabal",
        "Soledad": "Los Pocitos (Metropolitano)", "Bucaramanga": "El Carrasco",
        "Bello": "La Pradera", "Valledupar": "Los Corazones"
    }

    # Base
    df_base = pd.DataFrame({
        "City": list(city_coords.keys()),
        "lat": [v[0] for v in city_coords.values()],
        "lon": [v[1] for v in city_coords.values()],
        "Landfill": [rellenos.get(c, "N/A") for c in city_coords.keys()]
    })

    # Construir tabla larga 2025–2050
    frames_list = []
    years = [y for y in range(2025, 2051) if y in df_waste.index]
    for y in years:
        df_temp = pd.DataFrame({
            "City": df_base["City"],
            "lat": df_base["lat"],
            "lon": df_base["lon"],
            "Year": y,
            "Population": [float(df_pop.loc[y, c]) if y in df_pop.index and c in df_pop.columns else float("nan")
                           for c in df_base["City"]],
            "Waste_tons": [float(df_waste.loc[y, c]) if y in df_waste.index and c in df_waste.columns else float("nan")
                           for c in df_base["City"]],
            "Landfill": df_base["Landfill"]
        })
        df_temp["Daily_waste_tpd"] = df_temp["Waste_tons"] / 365.0
        frames_list.append(df_temp)
    df_anim = pd.concat(frames_list, ignore_index=True)

    # Tendencia nacional (acumulada hasta cada año para animar la línea)
    national = (df_anim.groupby("Year")["Waste_tons"].sum().reset_index())
    national.rename(columns={"Waste_tons": "Total_tons"}, inplace=True)

    # --- Figura con 2 subplots: mapbox + xy ---
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "mapbox"}, {"type": "xy"}]],
        column_widths=[0.62, 0.38],
        horizontal_spacing=0.06,
        subplot_titles=("Geographic Projection", "National Waste Generation")
    )

    # Datos iniciales (primer año)
    y0 = years[0]
    df0 = df_anim[df_anim["Year"] == y0]
    nat0 = national[national["Year"] <= y0]

    # Trace 0: Mapa (scattermapbox)
    fig.add_trace(
        go.Scattermapbox(
            lat=df0["lat"], lon=df0["lon"],
            mode="markers",
            marker=dict(size=np.clip(df0["Waste_tons"].fillna(0)/df0["Waste_tons"].max()*50, 6, 50),
                        color=df0["Waste_tons"], colorscale="Viridis", showscale=True,
                        colorbar=dict(title="tons/year")),
            text=df0["City"],
            hovertemplate=(
                "<b>%{text}</b><br>" +
                "Landfill: %{customdata[0]}<br>" +
                "Population: %{customdata[1]:,.0f}<br>" +
                "Daily waste: %{customdata[2]:.1f} t/day<br>" +
                "Annual waste: %{marker.color:,.0f} t/year"
            ),
            customdata=np.stack([df0["Landfill"], df0["Population"], df0["Daily_waste_tpd"]], axis=-1)
        ),
        row=1, col=1
    )

    # Trace 1: Línea nacional (hasta y0)
    fig.add_trace(
        go.Scatter(
            x=nat0["Year"], y=nat0["Total_tons"],
            mode="lines+markers",
            line=dict(color="#2A9D8F", width=3),
            marker=dict(color="#264653", size=7),
            name="National total"
        ),
        row=1, col=2
    )

    # Frames (actualizan ambos traces)
    frames = []
    for y in years:
        dfy = df_anim[df_anim["Year"] == y]
        naty = national[national["Year"] <= y]
        frames.append(go.Frame(
            name=str(y),
            data=[
                # Trace 0 (mapa)
                go.Scattermapbox(
                    lat=dfy["lat"], lon=dfy["lon"],
                    mode="markers",
                    marker=dict(size=np.clip(dfy["Waste_tons"].fillna(0)/dfy["Waste_tons"].max()*50, 6, 50),
                                color=dfy["Waste_tons"], colorscale="Viridis", showscale=True),
                    text=dfy["City"],
                    customdata=np.stack([dfy["Landfill"], dfy["Population"], dfy["Daily_waste_tpd"]], axis=-1),
                    hovertemplate=(
                        "<b>%{text}</b><br>" +
                        "Landfill: %{customdata[0]}<br>" +
                        "Population: %{customdata[1]:,.0f}<br>" +
                        "Daily waste: %{customdata[2]:.1f} t/day<br>" +
                        "Annual waste: %{marker.color:,.0f} t/year"
                    )
                ),
                # Trace 1 (línea nacional)
                go.Scatter(
                    x=naty["Year"], y=naty["Total_tons"],
                    mode="lines+markers",
                    line=dict(color="#2A9D8F", width=3),
                    marker=dict(color="#264653", size=7),
                    name="National total"
                )
            ]
        ))

    fig.frames = frames

    # Layout + controles Play/Pause
    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_zoom=5,
        mapbox_center={"lat": 4.6, "lon": -74.1},
        margin=dict(l=10, r=10, t=60, b=10),
        updatemenus=[{
            "type": "buttons",
            "direction": "left",
            "x": 0.15, "y": -0.08,
            "showactive": True,
            "buttons": [
                {"label": "▶ Play",
                 "method": "animate",
                 "args": [None, {"frame": {"duration": 800, "redraw": True},
                                 "fromcurrent": True,
                                 "transition": {"duration": 300}}]},
                {"label": "⏸ Pause",
                 "method": "animate",
                 "args": [[None], {"frame": {"duration": 0, "redraw": False},
                                   "mode": "immediate",
                                   "transition": {"duration": 0}}]}
            ]
        }],
        sliders=[{
            "active": 0,
            "y": -0.05,
            "x": 0.15,
            "len": 0.7,
            "pad": {"b": 10, "t": 10},
            "currentvalue": {"prefix": "Year: ", "font": {"size": 16}},
            "steps": [{"args": [[str(y)], {"frame": {"duration": 0, "redraw": True},
                                          "mode": "immediate"}],
                       "label": str(y),
                       "method": "animate"} for y in years]
        }],
        xaxis_title="Year",
        yaxis_title="Total waste (tons/year)"
    )

    st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------
# TAB 5: About
# -------------------------------------------------
with tab5:
    st.markdown(
        '''
        ### About  
        **Developer:** Dr. Danny Ibarra Vega — Universidad de Antioquia (2025)  
        **Method:** System Dynamics (logistic population growth, bounded PPC), 2025–2050 simulations.  
        **Data:** DANE projections (2018–2042), SSPD (2023), city-specific compositions.  
        **AI Layer:** Generative AI for parameter exploration, scenario generation, and narrative visualization.
        '''
    )
