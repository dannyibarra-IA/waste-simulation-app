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
Elaborated by **Danny Ibarra Vega Ph.D**  
📧 danny.ibarra@udea.edu.co  

This interactive dashboard shows the simulation of **population growth** and **waste generation**  
in 10 Colombian cities from **2025 to 2050**, integrating **System Dynamics modeling** with  
**Generative AI** to explore **urban circularity scenarios**.
""")

# ==============================
# HELPERS (numéricos y utilitarios)
# ==============================
def to_num(x):
    """Convierte a array float y reemplaza NaN/inf por 0 (evita fallos en Plotly)."""
    if isinstance(x, (pd.Series, pd.Index)):
        v = pd.to_numeric(x, errors="coerce").fillna(0.0).to_numpy(dtype=float)
    elif isinstance(x, pd.DataFrame):
        v = pd.to_numeric(x.squeeze(), errors="coerce").fillna(0.0).to_numpy(dtype=float)
    else:
        v = np.asarray(x, dtype=float)
    v = np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0)
    return v


def bubble_sizes(values, min_size=6, max_size=50):
    """Escala robusta de tamaños (sin divisiones por cero)."""
    v = to_num(values)
    vmax = float(v.max()) if v.size else 0.0
    vmax = 1.0 if vmax <= 0 else vmax
    s = min_size + (max_size - min_size) * (v / vmax).clip(0, 1)
    return s.tolist()


def filter_by_year(df, year_range, city):
    """Filtra un DataFrame por rango de años e incluye solo la columna de una ciudad."""
    return df.loc[(df.index >= year_range[0]) & (df.index <= year_range[1]), [city]]


def get_year_bounds(df_pop, df_waste, min_default=2025, max_default=2050):
    """Obtiene los años mínimo y máximo razonables dados los DataFrames."""
    min_year = int(min(df_pop.index.min(), df_waste.index.min()))
    max_year = int(max(df_pop.index.max(), df_waste.index.max()))
    min_year = max(min_default, min_year)
    max_year = min(max_default, max_year)
    return min_year, max_year


# ==============================
# LOAD DATA (REAL EXCEL)
# ==============================
DATA_FILE = "simulacion_residuos_2025_2050.xlsx"


@st.cache_data
def load_data(source):
    """
    Carga datos desde un path (str/Path) o un archivo subido (UploadedFile).
    Valida estructura y lanza errores con mensajes claros si algo falta.
    """
    # Determinar origen: path local o archivo subido
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(
                f"El archivo por defecto '{path.name}' no se encontró en el directorio de la app."
            )
        excel_source = path
    else:
        # UploadedFile de Streamlit
        excel_source = source

    try:
        # Leer hojas
        pop = pd.read_excel(excel_source, sheet_name="Poblacion_2050", index_col=0)
        waste = pd.read_excel(excel_source, sheet_name="ResiduosTotales_t_anio", index_col=0)
        types = pd.read_excel(excel_source, sheet_name="Residuos_5Tipos_largo")
    except ValueError as e:
        # Error típico: nombres de hojas incorrectos
        raise ValueError(
            "Error al leer las hojas del archivo Excel. "
            "Asegúrate de que existan las hojas: 'Poblacion_2050', "
            "'ResiduosTotales_t_anio' y 'Residuos_5Tipos_largo'. "
            f"Detalle técnico: {e}"
        )

    # Limpieza numérica básica
    pop = pop.apply(pd.to_numeric, errors="coerce")
    waste = waste.apply(pd.to_numeric, errors="coerce")

    # Índices como años enteros
    pop.index = pop.index.astype(float).round().astype(int)
    waste.index = waste.index.astype(float).round().astype(int)

    # Limpiar nombres de columnas
    pop.columns = pop.columns.astype(str).str.strip()
    waste.columns = waste.columns.astype(str).str.strip()

    # Limpiar columnas de la tabla larga
    for col in ("Ciudad", "Tipo"):
        if col in types.columns:
            types[col] = types[col].astype(str).str.strip()

    # Validar columnas de la tabla larga
    expected_cols = {"Ciudad", "Año", "Tipo", "Toneladas_anio"}
    if not expected_cols.issubset(set(types.columns)):
        missing = expected_cols - set(types.columns)
        raise ValueError(
            "La hoja 'Residuos_5Tipos_largo' no tiene las columnas esperadas. "
            f"Faltan: {', '.join(missing)}. "
            "Se requieren exactamente: Ciudad, Año, Tipo, Toneladas_anio."
        )

    return pop, waste, types


# ==============================
# SIDEBAR: CARGA DE ARCHIVO
# ==============================
st.sidebar.title("Simulation Control")

st.sidebar.markdown("#### Data Source")
uploaded_file = st.sidebar.file_uploader(
    "Upload simulation Excel (.xlsx)", type=["xlsx"], help="If empty, the app will use the default file."
)

# Cargar datos con manejo de errores explícitos
try:
    if uploaded_file is not None:
        df_pop, df_waste, df_types = load_data(uploaded_file)
    else:
        df_pop, df_waste, df_types = load_data(DATA_FILE)
except FileNotFoundError as e:
    st.error(f"❌ {e}")
    st.stop()
except ValueError as e:
    st.error(f"⚠️ Problema en la estructura del archivo: {e}")
    st.stop()
except Exception as e:
    st.error(f"⚠️ Se produjo un error inesperado al leer el archivo: {e}")
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
    "Valledupar": (10.4631, -73.2532),
}

landfills = {
    "Medellín": "La Pradera",
    "Santiago de Cali": "Navarro",
    "Barranquilla": "Los Pocitos",
    "Cartagena de Indias": "Henequén",
    "Soacha": "Doña Juana (Bogotá)",
    "San José de Cúcuta": "Guayabal",
    "Soledad": "Los Pocitos (Metropolitano)",
    "Bucaramanga": "El Carrasco",
    "Bello": "La Pradera",
    "Valledupar": "Los Corazones",
}

# Asegurar que existan datos para estas ciudades
cities_available = sorted(list(set(df_pop.columns) & set(df_waste.columns) & set(city_coords.keys())))
if not cities_available:
    st.error("❌ Ninguna ciudad del Excel coincide con las coordenadas configuradas. Revisa nombres/acentos.")
    st.stop()

# ==============================
# SIDEBAR CONTROLS (city & years)
# ==============================
city = st.sidebar.selectbox("Select City", cities_available, index=0)

min_year, max_year = get_year_bounds(df_pop, df_waste)
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
    df_pop_plot = filter_by_year(df_pop, year_range, city)
    fig1 = px.line(
        df_pop_plot,
        x=df_pop_plot.index,
        y=city,
        markers=True,
        labels={"x": "Year", "y": "Population"},
        title="Population 2025–2050",
    )
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader(f"Total Waste Generation (tons/year): {city}")
    df_waste_plot = filter_by_year(df_waste, year_range, city)
    fig2 = px.line(
        df_waste_plot,
        x=df_waste_plot.index,
        y=city,
        markers=True,
        labels={"x": "Year", "y": "Tons/year"},
        title="Waste Generation 2025–2050",
    )
    st.plotly_chart(fig2, use_container_width=True)

# ==============================
# TAB 2 — Composition by Type
# ==============================
with tab2:
    st.subheader(f"Waste Composition by Type: {city}")

    expected_cols = {"Ciudad", "Año", "Tipo", "Toneladas_anio"}
    if expected_cols.issubset(set(df_types.columns)):
        df_city = df_types[
            (df_types["Ciudad"] == city)
            & (df_types["Año"].between(year_range[0], year_range[1]))
        ]

        if df_city.empty:
            st.info("No hay tabla de composición larga para esta ciudad en el rango seleccionado.")
        else:
            # Selector de modo de visualización
            view_mode = st.radio(
                "Visualization mode:",
                ("Time series (stacked area)", "Single year (bar chart)"),
                horizontal=False,
            )

            if view_mode == "Time series (stacked area)":
                pivot = df_city.pivot(index="Año", columns="Tipo", values="Toneladas_anio").sort_index()
                fig3 = px.area(
                    pivot,
                    x=pivot.index,
                    y=pivot.columns,
                    title="Composition of Waste by Type (Time Series)",
                    labels={"value": "Tons/year", "Año": "Year"},
                )
                st.plotly_chart(fig3, use_container_width=True)
            else:
                # Un solo año con gráfico de barras
                years_city = sorted(df_city["Año"].unique())
                year_single = st.slider(
                    "Select year to visualize composition:",
                    min_value=int(years_city[0]),
                    max_value=int(years_city[-1]),
                    value=int(years_city[0]),
                )
                df_single = df_city[df_city["Año"] == year_single]
                fig_bar = px.bar(
                    df_single,
                    x="Tipo",
                    y="Toneladas_anio",
                    title=f"Composition of Waste by Type — {year_single}",
                    labels={"Toneladas_anio": "Tons/year", "Tipo": "Type"},
                )
                st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info(
            "Hoja 'Residuos_5Tipos_largo' no tiene columnas esperadas "
            "(Ciudad, Año, Tipo, Toneladas_anio)."
        )

# ==============================
# TAB 3 — Geographic View
# ==============================
with tab3:
    st.subheader("Geographic View — Daily/Annual Waste, Population & Landfill")

    # Selector de año y unidades
    view_year = st.slider(
        "Select year to visualize:",
        min_value=min_year,
        max_value=max_year,
        value=min_year,
    )
    unit = st.radio("Units:", ["tons/day", "tons/year"], horizontal=True)

    cities = cities_available
    df_now = pd.DataFrame({
        "City": cities,
        "lat": [city_coords[c][0] for c in cities],
        "lon": [city_coords[c][1] for c in cities],
        "Landfill": [landfills.get(c, "N/A") for c in cities],
        "Population": [
            float(df_pop.loc[view_year, c]) if view_year in df_pop.index else np.nan
            for c in cities
        ],
        "Waste_tons_year": [
            float(df_waste.loc[view_year, c]) if view_year in df_waste.index else np.nan
            for c in cities
        ],
    })
    df_now["Daily_waste_tpd"] = df_now["Waste_tons_year"] / 365.0
    df_now["Value"] = df_now["Daily_waste_tpd"] if unit == "tons/day" else df_now["Waste_tons_year"]
    cbar_title = "t/day" if unit == "tons/day" else "t/year"

    sizes = bubble_sizes(df_now["Value"])

    fig_current = px.scatter_mapbox(
        df_now,
        lat="lat",
        lon="lon",
        color="Value",
        hover_name="City",
        hover_data={"Landfill": True, "Population": ":,.0f", "Value": ":,.1f"},
        color_continuous_scale="Turbo",
        zoom=5,
        mapbox_style="open-street-map",
        title=f"Geographic Distribution • {view_year}",
    )

    # Aplicar tamaños y opacidad a todas las trazas
    for tr in fig_current.data:
        tr.marker.update(size=sizes, opacity=0.9)

    fig_current.update_layout(
        margin=dict(l=0, r=0, t=50, b=0),
        coloraxis_colorbar=dict(title=cbar_title, thickness=12, len=0.75, y=0.55),
    )

    st.plotly_chart(fig_current, use_container_width=True)

# ==============================
# TAB 4 — Animated Map + Animated Line
# ==============================
with tab4:
    st.markdown("### Animated Simulation (2025–2050) + **Waste Generation of Ten Cities**")

    # Ciudades con datos y rango de años disponible
    cities_ok = cities_available
    years = [y for y in range(2025, 2051) if y in df_waste.index]

    # Tabla base (coords)
    base = pd.DataFrame({
        "City": cities_ok,
        "lat": [city_coords[c][0] for c in cities_ok],
        "lon": [city_coords[c][1] for c in cities_ok],
    })

    # Tabla larga para animación (ciudad-año)
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

    # Tendencia total (suma de las 10 ciudades) por año
    national = df_anim.groupby("Year")["Waste_tons"].sum().reset_index()

    # --- Subplots: mapa + línea (comparten frames) ---
    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "mapbox"}, {"type": "xy"}]],
        column_widths=[0.62, 0.38],
        horizontal_spacing=0.06,
        subplot_titles=("Geographic Projection", "Waste Generation of Ten Cities"),
    )

    # Estado inicial
    y0 = years[0]
    d0 = df_anim[df_anim["Year"] == y0]
    sizes0 = bubble_sizes(d0["Waste_tons"])
    nat0 = national[national["Year"] <= y0]

    # Trace 0 (MAPA) - estado inicial
    fig.add_trace(
        go.Scattermapbox(
            lat=d0["lat"],
            lon=d0["lon"],
            mode="markers",
            marker=dict(
                size=sizes0,
                color=to_num(d0["Waste_tons"]),
                colorscale="Turbo",
                showscale=True,
                opacity=0.9,
            ),
            text=d0["City"],
            showlegend=False,
            hovertemplate="<b>%{text}</b><br>Annual waste: %{marker.color:,.0f} t/year<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Trace 1 (LÍNEA) - estado inicial
    fig.add_trace(
        go.Scatter(
            x=nat0["Year"].astype(int),
            y=nat0["Waste_tons"],
            mode="lines+markers",
            line=dict(color="#3A86FF", width=3),
            marker=dict(color="#8338EC", size=7),
            name="Total",
            hovertemplate="Year: %{x}<br>t/year: %{y:,.0f}<extra></extra>",
        ),
        row=1,
        col=2,
    )

    # Frames sincronizados (mapa y línea avanzan juntos)
    frames = []
    for y in years:
        dy = df_anim[df_anim["Year"] == y]
        ny = national[national["Year"] <= y]
        frames.append(
            go.Frame(
                name=str(y),
                data=[
                    # Mapa para el año y
                    go.Scattermapbox(
                        lat=dy["lat"],
                        lon=dy["lon"],
                        mode="markers",
                        marker=dict(
                            size=bubble_sizes(dy["Waste_tons"]),
                            color=to_num(dy["Waste_tons"]),
                            colorscale="Turbo",
                            showscale=True,
                            opacity=0.9,
                        ),
                        text=dy["City"],
                        showlegend=False,
                        hovertemplate="<b>%{text}</b><br>Annual waste: %{marker.color:,.0f} t/year<extra></extra>",
                    ),
                    # Línea acumulada hasta y
                    go.Scatter(
                        x=ny["Year"].astype(int),
                        y=ny["Waste_tons"],
                        mode="lines+markers",
                        line=dict(color="#3A86FF", width=3),
                        marker=dict(color="#8338EC", size=7),
                        name="Total",
                        hovertemplate="Year: %{x}<br>t/year: %{y:,.0f}<extra></extra>",
                    ),
                ],
            )
        )
    fig.frames = frames

    # Layout + controles (Play/Pause + slider)
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_zoom=5,
        mapbox_center={"lat": 4.6, "lon": -74.1},
        margin=dict(l=10, r=10, t=60, b=10),
        font=dict(size=13, color="#1d3557"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        updatemenus=[
            {
                "type": "buttons",
                "direction": "left",
                "x": 0.12,
                "y": -0.08,
                "showactive": True,
                "buttons": [
                    {
                        "label": "▶ Play",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "frame": {"duration": 700, "redraw": True},
                                "fromcurrent": True,
                                "transition": {"duration": 250},
                            },
                        ],
                    },
                    {
                        "label": "⏸ Pause",
                        "method": "animate",
                        "args": [
                            [None],
                            {
                                "frame": {"duration": 0, "redraw": False},
                                "mode": "immediate",
                                "transition": {"duration": 0},
                            },
                        ],
                    },
                ],
            }
        ],
        sliders=[
            {
                "active": 0,
                "y": -0.05,
                "x": 0.12,
                "len": 0.7,
                "pad": {"b": 10, "t": 10},
                "currentvalue": {"prefix": "Year: ", "font": {"size": 16}},
                "steps": [
                    {
                        "args": [[str(y)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
                        "label": str(y),
                        "method": "animate",
                    }
                    for y in years
                ],
            }
        ],
        xaxis_title="Year",
        yaxis_title="tons/year",
    )

    # Ejes limpios para la LÍNEA (subplot derecho) + rango dinámico
    fig.update_xaxes(
        row=1,
        col=2,
        tickmode="linear",
        dtick=1,
        range=[years[0], years[-1]],
        tickformat="d",
    )

    y_min = float(national["Waste_tons"].min())
    y_max = float(national["Waste_tons"].max())
    y_lower = max(0.0, y_min * 0.9)
    y_upper = y_max * 1.05

    fig.update_yaxes(
        row=1,
        col=2,
        tickformat=",.0f",
        range=[y_lower, y_upper],
        rangemode="nonnegative",
        title_text="tons/year",
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
