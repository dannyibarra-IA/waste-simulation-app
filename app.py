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
    st.subheader("Geographic Distribution of Waste Generation (2050)")
    if 2050 in df_waste.index:
        df_2050 = df_waste.loc[2050].reset_index().rename(columns={"index": "City", 2050: "Waste_tons"})
    else:
        last_year = int(df_waste.index.max())
        df_2050 = df_waste.loc[last_year].reset_index().rename(columns={"index": "City", last_year: "Waste_tons"})

    df_map = pd.DataFrame({
        "City": list(city_coords.keys()),
        "lat": [v[0] for v in city_coords.values()],
        "lon": [v[1] for v in city_coords.values()],
    })
    df_map["Waste_tons"] = df_map["City"].apply(
        lambda c: float(df_2050.loc[df_2050["City"] == c, "Waste_tons"].values[0])
        if c in df_2050["City"].values and not df_2050.loc[df_2050["City"] == c, "Waste_tons"].isna().all()
        else 0.0
    )
    fig_map = px.scatter_mapbox(
        df_map, lat="lat", lon="lon", size="Waste_tons", color="Waste_tons",
        hover_name="City", color_continuous_scale="Viridis", zoom=5,
        mapbox_style="carto-positron",
        title=f"Simulated Waste Generation in {2050 if 2050 in df_waste.index else last_year}"
    )
    st.plotly_chart(fig_map, use_container_width=True)

# -------------------------------------------------
# TAB 4: Animated Map + National Chart
# -------------------------------------------------
with tab4:
    st.markdown("### Animated Simulation of Urban Waste Generation (2025–2050) with National Trend")

    rellenos = {
        "Medellín": "La Pradera", "Santiago de Cali": "Navarro",
        "Barranquilla": "Los Pocitos", "Cartagena de Indias": "Henequén",
        "Soacha": "Doña Juana (Bogotá)", "San José de Cúcuta": "Guayabal",
        "Soledad": "Los Pocitos (Metropolitano)", "Bucaramanga": "El Carrasco",
        "Bello": "La Pradera", "Valledupar": "Los Corazones"
    }

    df_base = pd.DataFrame({
        "City": list(city_coords.keys()),
        "lat": [v[0] for v in city_coords.values()],
        "lon": [v[1] for v in city_coords.values()],
        "Landfill": [rellenos[c] for c in city_coords.keys()]
    })

    frames = []
    for year in range(2025, 2051):
        if year in df_waste.index:
            df_temp = pd.DataFrame({
                "City": df_base["City"], "lat": df_base["lat"], "lon": df_base["lon"],
                "Year": year,
                "Population": [df_pop.loc[year, c] for c in df_base["City"]],
                "Waste_tons": [df_waste.loc[year, c] for c in df_base["City"]],
                "Landfill": df_base["Landfill"]
            })
            df_temp["Daily_waste_tpd"] = df_temp["Waste_tons"] / 365
            frames.append(df_temp)
    df_anim = pd.concat(frames, ignore_index=True)
    national_trend = df_anim.groupby("Year")["Waste_tons"].sum().reset_index()

    col1, col2 = st.columns([3, 1.5])
    with col1:
        fig_anim = px.scatter_mapbox(
            df_anim, lat="lat", lon="lon", size="Waste_tons", color="Waste_tons",
            hover_name="City", hover_data={
                "Year": True, "Population": ":.0f",
                "Daily_waste_tpd": ":.1f", "Landfill": True
            },
            animation_frame="Year", color_continuous_scale="Viridis",
            mapbox_style="carto-positron", zoom=5,
            title="Animated Projection of Waste Generation in Colombian Cities (2025–2050)"
        )
        fig_anim.update_layout(margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig_anim, use_container_width=True)

    with col2:
        fig_trend = px.line(
            national_trend, x="Year", y="Waste_tons", markers=True,
            title="National Waste Generation Trend",
            labels={"Waste_tons": "tons/year", "Year": "Year"}
        )
        fig_trend.update_traces(line_color="#2A9D8F", marker_color="#264653")
        st.plotly_chart(fig_trend, use_container_width=True)

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
