
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import numpy as np

st.set_page_config(page_title='Urban Waste Simulation and Circularity', layout='wide')

# Banner (emoji + headline)
st.markdown(
    """
    # 🌎 Urban Waste Simulation and Circularity Dashboard  
    This interactive dashboard shows the simulation of **population growth** and **waste generation**  
    in 10 Colombian cities from **2025 to 2050**, integrating **System Dynamics modeling** with  
    **Generative AI** to explore **urban circularity scenarios**.
    """
)

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
        # DEMO fallback (small synthetic dataset)
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

st.sidebar.title('Simulation Control')
city = st.sidebar.selectbox('Select City', cities, index=0)
year_range = st.sidebar.slider('Select Year Range', 2025, 2050, (2025, 2050))

tab1, tab2, tab3, tab4 = st.tabs(['📈 Population & Waste', '♻️ Composition by Type', '🗺️ Geographic View', 'ℹ️ About'])

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
        st.warning("Demo data is being used because 'simulacion_residuos_2025_2050.xlsx' was not found. Upload the file to the repo for real results.")

with tab2:
    st.subheader(f'Waste Composition by Type: {city}')
    df_city = df_types[df_types['Ciudad'] == city]
    if df_city.empty and city in df_waste.columns:
        st.info('Composition long table not found for this city; showing only total series.')
        st.line_chart(df_waste[city])
    else:
        df_city = df_city[(df_city['Año'] >= year_range[0]) & (df_city['Año'] <= year_range[1])]
        pivot = df_city.pivot(index='Año', columns='Tipo', values='Toneladas_anio')
        fig3 = px.area(pivot, x=pivot.index, y=pivot.columns,
                       title='Composition of Waste by Type (2025–2050)',
                       labels={'value': 'Tons/year', 'Año': 'Year'})
        st.plotly_chart(fig3, use_container_width=True)

with tab3:
    st.subheader('Geographic Distribution of Waste Generation (2050)')
    if 2050 in df_waste.index:
        df_2050 = df_waste.loc[2050].reset_index().rename(columns={'index':'City', 2050: 'Waste_tons'})
    else:
        last_year = int(df_waste.index.max())
        df_2050 = df_waste.loc[last_year].reset_index().rename(columns={'index':'City', last_year: 'Waste_tons'})

    df_map = pd.DataFrame({
        'City': list(city_coords.keys()),
        'lat': [v[0] for v in city_coords.values()],
        'lon': [v[1] for v in city_coords.values()],
        'Waste_tons': [float(df_2050[df_2050['City']==c][city].values[0]) if c in df_2050['City'].values else None for c in city_coords.keys()]
            if city in df_2050.columns else [None]*len(city_coords)
    })

    fig_map = px.scatter_mapbox(df_map, lat='lat', lon='lon', size='Waste_tons', color='Waste_tons',
                                hover_name='City', color_continuous_scale='Viridis',
                                zoom=5, mapbox_style='carto-positron',
                                title=f'Simulated Waste Generation in {2050 if 2050 in df_waste.index else int(df_waste.index.max())}')
    st.plotly_chart(fig_map, use_container_width=True)

with tab4:
    st.markdown(
        '''
        ### About  
        **Developer:** Dr. Danny Ibarra Vega — Universidad de Antioquia (2025)  
        **Method:** System Dynamics (logistic population growth, bounded PPC), 2025–2050 simulations.  
        **Data:** DANE projections (2018–2042), SSPD (2023), city-specific compositions.  
        **AI Layer:** Generative AI for parameter exploration, scenario generation, and narrative visualization.
        '''
    )
