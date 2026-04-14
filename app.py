import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import numpy as np

# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="Urban Waste Simulation and Circularity",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# CUSTOM STYLES
# =========================================================
st.markdown(
    """
    <style>
        :root {
            --bg: #f6f8fb;
            --card: #ffffff;
            --soft: #e9eef5;
            --text: #17324d;
            --muted: #5f6b7a;
            --accent: #1f77b4;
            --accent-2: #2ca58d;
            --shadow: 0 4px 18px rgba(23, 50, 77, 0.08);
            --radius: 16px;
        }

        [data-testid="stAppViewContainer"] {
            background: linear-gradient(180deg, #f7f9fc 0%, #eef4f9 100%);
        }

        [data-testid="stSidebar"] {
            background: #eef3f8;
            border-right: 1px solid rgba(23, 50, 77, 0.08);
        }

        h1, h2, h3, h4 {
            color: var(--text);
        }

        .hero {
            background: linear-gradient(135deg, rgba(31,119,180,0.10), rgba(44,165,141,0.12));
            border: 1px solid rgba(23, 50, 77, 0.08);
            border-radius: 22px;
            padding: 1.4rem 1.5rem 1.1rem 1.5rem;
            box-shadow: var(--shadow);
            margin-bottom: 1rem;
        }

        .metric-card {
            background: var(--card);
            border-radius: var(--radius);
            padding: 0.9rem 1rem;
            box-shadow: var(--shadow);
            border: 1px solid rgba(23, 50, 77, 0.05);
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.9rem;
            margin-bottom: 0.2rem;
        }

        .metric-value {
            color: var(--text);
            font-size: 1.5rem;
            font-weight: 700;
        }

        .stTabs [data-baseweb="tab"] {
            font-size: 15px;
            font-weight: 600;
            padding-top: 0.65rem;
            padding-bottom: 0.65rem;
        }

        .small-note {
            color: var(--muted);
            font-size: 0.9rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# CONSTANTS
# =========================================================
DATA_FILE = "simulacion_residuos_2025_2050.xlsx"
EXPECTED_LONG_COLS = {"Ciudad", "Año", "Tipo", "Toneladas_anio"}
PLOT_TEMPLATE = "plotly_white"
SCENARIO_OPTIONS = {
    "BAU": {"waste_multiplier": 1.00, "diversion_multiplier": 1.00, "label": "Business as usual"},
    "Moderate Circularity": {"waste_multiplier": 0.92, "diversion_multiplier": 1.18, "label": "Moderate intervention"},
    "Accelerated Circularity": {"waste_multiplier": 0.82, "diversion_multiplier": 1.35, "label": "High circularity push"},
}

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

# =========================================================
# HELPERS
# =========================================================
def to_num(values):
    """Convert input to numeric numpy array, replacing NaN/inf with zero."""
    if isinstance(values, (pd.Series, pd.Index)):
        arr = pd.to_numeric(values, errors="coerce").fillna(0.0).to_numpy(dtype=float)
    elif isinstance(values, pd.DataFrame):
        arr = pd.to_numeric(values.squeeze(), errors="coerce").fillna(0.0).to_numpy(dtype=float)
    else:
        arr = np.asarray(values, dtype=float)
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)


def safe_bubble_sizes(values, min_size=10, max_size=42):
    """Scale bubble sizes robustly avoiding zero-division."""
    arr = to_num(values)
    if arr.size == 0:
        return []
    vmax = max(float(arr.max()), 1.0)
    scaled = min_size + (max_size - min_size) * np.clip(arr / vmax, 0, 1)
    return scaled.tolist()


def human_format(value, decimals=0):
    try:
        return f"{value:,.{decimals}f}"
    except Exception:
        return str(value)


def filter_year_range(df, year_range, cols=None):
    data = df.loc[(df.index >= year_range[0]) & (df.index <= year_range[1])]
    if cols is not None:
        data = data[cols]
    return data


def get_year_bounds(df_pop, df_waste):
    min_year = int(min(df_pop.index.min(), df_waste.index.min()))
    max_year = int(max(df_pop.index.max(), df_waste.index.max()))
    return min_year, max_year


def compute_growth_pct(series):
    arr = to_num(series)
    if arr.size < 2 or arr[0] == 0:
        return 0.0
    return ((arr[-1] - arr[0]) / arr[0]) * 100


def validate_columns(df, required, table_name):
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(
            f"La tabla '{table_name}' no contiene las columnas requeridas: {', '.join(sorted(missing))}."
        )


def build_kpi_card(label, value):
    st.markdown(
        f"""
        <div class='metric-card'>
            <div class='metric-label'>{label}</div>
            <div class='metric-value'>{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def line_chart(df, y_col, title, y_label, color="#1f77b4"):
    fig = px.line(
        df,
        x=df.index,
        y=y_col,
        markers=True,
        template=PLOT_TEMPLATE,
        title=title,
        labels={"x": "Year", y_col: y_label},
    )
    fig.update_traces(line=dict(width=3, color=color), marker=dict(size=7))
    fig.update_layout(
        hovermode="x unified",
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis=dict(dtick=1),
    )
    return fig


def export_dataframe(df, name):
    return df.to_csv(index=True).encode("utf-8"), f"{name}.csv"


def apply_scenario_to_waste(df_waste, scenario_name, base_year=None):
    scenario = SCENARIO_OPTIONS[scenario_name]
    adjusted = df_waste.copy()
    if base_year is None:
        base_year = int(adjusted.index.min())

    for year in adjusted.index:
        years_from_base = max(0, int(year - base_year))
        progressive_factor = 1 - ((1 - scenario["waste_multiplier"]) * (years_from_base / max(1, int(adjusted.index.max() - base_year))))
        adjusted.loc[year] = adjusted.loc[year] * progressive_factor
    return adjusted


def build_insights(city, year, pop_value, waste_value, per_capita_value, df_waste_selected, df_types_selected):
    insights = []
    try:
        first_year = int(df_waste_selected.index.min())
        last_year = int(df_waste_selected.index.max())
        growth = compute_growth_pct(df_waste_selected[city])
        insights.append(f"Waste generation in **{city}** changes by **{human_format(growth, 1)}%** between **{first_year}** and **{last_year}**.")
    except Exception:
        pass

    insights.append(f"For **{year}**, the estimated generation is **{human_format(waste_value, 0)} t/year**, equivalent to **{human_format(per_capita_value, 2)} kg/person/day**.")

    if not df_types_selected.empty:
        latest_mix = df_types_selected[df_types_selected["Año"] == year].copy()
        if not latest_mix.empty:
            top_row = latest_mix.sort_values("Toneladas_anio", ascending=False).iloc[0]
            share = 100 * top_row["Toneladas_anio"] / latest_mix["Toneladas_anio"].sum()
            insights.append(
                f"The dominant fraction is **{top_row['Tipo']}**, representing approximately **{human_format(share, 1)}%** of the waste mix in **{year}**."
            )

    return insights[:3]


def add_section_intro(title, text):
    st.markdown(f"<div class='small-note'><b>{title}</b> — {text}</div>", unsafe_allow_html=True)


def scenario_summary_text(scenario_name):
    scenario = SCENARIO_OPTIONS[scenario_name]
    return (
        f"Scenario: **{scenario['label']}**. Relative long-run waste pressure factor: "
        f"**{human_format(scenario['waste_multiplier'] * 100, 0)}%** of BAU."
    )


# =========================================================
# DATA LOADING
# =========================================================
@st.cache_data(show_spinner=False)
def load_data(source):
    if isinstance(source, (str, Path)):
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(
                f"No se encontró el archivo por defecto '{source.name}' en el directorio de la app."
            )
        excel_source = source
    else:
        excel_source = source

    try:
        pop = pd.read_excel(excel_source, sheet_name="Poblacion_2050", index_col=0)
        waste = pd.read_excel(excel_source, sheet_name="ResiduosTotales_t_anio", index_col=0)
        types = pd.read_excel(excel_source, sheet_name="Residuos_5Tipos_largo")
    except ValueError as exc:
        raise ValueError(
            "No fue posible leer las hojas esperadas. Verifica que existan: "
            "'Poblacion_2050', 'ResiduosTotales_t_anio' y 'Residuos_5Tipos_largo'. "
            f"Detalle: {exc}"
        ) from exc

    pop = pop.apply(pd.to_numeric, errors="coerce")
    waste = waste.apply(pd.to_numeric, errors="coerce")
    pop.index = pd.to_numeric(pop.index, errors="coerce").round().astype("Int64")
    waste.index = pd.to_numeric(waste.index, errors="coerce").round().astype("Int64")

    pop = pop[~pop.index.isna()].copy()
    waste = waste[~waste.index.isna()].copy()
    pop.index = pop.index.astype(int)
    waste.index = waste.index.astype(int)

    pop.columns = pop.columns.astype(str).str.strip()
    waste.columns = waste.columns.astype(str).str.strip()

    validate_columns(types, EXPECTED_LONG_COLS, "Residuos_5Tipos_largo")
    types["Ciudad"] = types["Ciudad"].astype(str).str.strip()
    types["Tipo"] = types["Tipo"].astype(str).str.strip()
    types["Año"] = pd.to_numeric(types["Año"], errors="coerce").astype("Int64")
    types["Toneladas_anio"] = pd.to_numeric(types["Toneladas_anio"], errors="coerce")
    types = types.dropna(subset=["Año", "Toneladas_anio"]).copy()
    types["Año"] = types["Año"].astype(int)

    if pop.empty or waste.empty:
        raise ValueError("Las tablas principales quedaron vacías después de la limpieza de datos.")

    return pop.sort_index(), waste.sort_index(), types


# =========================================================
# HEADER
# =========================================================
st.markdown(
    """
    <div class="hero">
        <h1 style="margin-bottom:0.2rem;">🌎 Urban Waste Simulation and Circularity Dashboard</h1>
        <p style="margin:0.15rem 0;"><b>Elaborated by Danny Ibarra Vega, Ph.D.</b></p>
        <p style="margin:0.15rem 0; color:#415466;">
            Interactive platform for exploring population growth, waste generation, composition patterns,
            territorial distribution and dynamic trends for Colombian cities under a system dynamics perspective.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.title("Simulation Control")
st.sidebar.markdown("Adjust the data source and visualization parameters.")

uploaded_file = st.sidebar.file_uploader(
    "Upload simulation Excel (.xlsx)",
    type=["xlsx"],
    help="If no file is uploaded, the dashboard will use the default dataset.",
)

try:
    if uploaded_file is not None:
        df_pop, df_waste, df_types = load_data(uploaded_file)
        data_source_label = f"Custom file: {uploaded_file.name}"
    else:
        df_pop, df_waste, df_types = load_data(DATA_FILE)
        data_source_label = f"Default file: {DATA_FILE}"
except FileNotFoundError as exc:
    st.error(f"❌ {exc}")
    st.stop()
except ValueError as exc:
    st.error(f"⚠️ Error de estructura o calidad de datos: {exc}")
    st.stop()
except Exception as exc:
    st.error(f"⚠️ Ocurrió un error inesperado al cargar los datos: {exc}")
    st.stop()

cities_available = sorted(set(df_pop.columns) & set(df_waste.columns) & set(city_coords.keys()))
if not cities_available:
    st.error("❌ No hay coincidencia entre las ciudades del archivo y las ciudades configuradas.")
    st.stop()

min_year, max_year = get_year_bounds(df_pop, df_waste)
default_city = "Medellín" if "Medellín" in cities_available else cities_available[0]

selected_city = st.sidebar.selectbox("Select city", cities_available, index=cities_available.index(default_city))
selected_scenario = st.sidebar.selectbox("Scenario", list(SCENARIO_OPTIONS.keys()), index=0)
year_range = st.sidebar.slider("Select year range", min_year, max_year, (min_year, max_year))
comparison_cities = st.sidebar.multiselect(
    "Compare cities",
    options=cities_available,
    default=[selected_city],
    help="Choose one or more cities for comparison charts.",
)
show_raw_data = st.sidebar.toggle("Show raw filtered data", value=False)
show_method_note = st.sidebar.toggle("Show methodology note", value=False)

st.sidebar.markdown("---")
st.sidebar.caption(data_source_label)

# =========================================================
# TOP KPIs
# =========================================================
df_waste_scenario = apply_scenario_to_waste(df_waste, selected_scenario, base_year=min_year)
pop_city = filter_year_range(df_pop, year_range, [selected_city])[selected_city]
waste_city = filter_year_range(df_waste_scenario, year_range, [selected_city])[selected_city]

pop_growth = compute_growth_pct(pop_city)
waste_growth = compute_growth_pct(waste_city)
latest_year = year_range[1]
latest_pop = float(pop_city.loc[latest_year]) if latest_year in pop_city.index else float(pop_city.iloc[-1])
latest_waste = float(waste_city.loc[latest_year]) if latest_year in waste_city.index else float(waste_city.iloc[-1])
per_capita_kg_day = (latest_waste * 1000 / latest_pop / 365) if latest_pop > 0 else 0

hero_left, hero_right = st.columns([1.35, 1])
with hero_left:
    st.markdown(
        f"""
        <div class='metric-card'>
            <div class='metric-label'>Dashboard focus</div>
            <div class='metric-value' style='font-size:1.2rem;'>Urban waste dynamics in {selected_city}</div>
            <div class='small-note'>Explore trajectories, composition, territorial concentration and scenario-sensitive outcomes from {year_range[0]} to {year_range[1]}.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with hero_right:
    st.markdown(
        f"""
        <div class='metric-card'>
            <div class='metric-label'>Active scenario</div>
            <div class='metric-value' style='font-size:1.2rem;'>{selected_scenario}</div>
            <div class='small-note'>{SCENARIO_OPTIONS[selected_scenario]['label']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
with k1:
    build_kpi_card("Selected city", selected_city)
with k2:
    build_kpi_card(f"Population ({latest_year})", human_format(latest_pop, 0))
with k3:
    build_kpi_card(f"Waste ({latest_year})", f"{human_format(latest_waste, 0)} t/year")
with k4:
    build_kpi_card("Per capita waste", f"{human_format(per_capita_kg_day, 2)} kg/person/day")

st.caption(scenario_summary_text(selected_scenario))

if show_method_note:
    st.info(
        "Scenario mode applies a progressive modifier to waste generation over time to emulate different circularity intensities. "
        "Population remains unchanged, while waste trajectories are adjusted for exploration and communication purposes."
    )

insight_types = df_types[(df_types["Ciudad"] == selected_city) & (df_types["Año"].between(year_range[0], year_range[1]))].copy()
insights = build_insights(selected_city, latest_year, latest_pop, latest_waste, per_capita_kg_day, waste_city.to_frame(), insight_types)

ibox_left, ibox_right = st.columns([1.15, 1])
with ibox_left:
    st.markdown("#### Executive insights")
    for item in insights:
        st.markdown(f"- {item}")
with ibox_right:
    st.markdown("#### Quick reading")
    st.markdown(
        f"""
        - **Main question:** How does waste evolve under the selected scenario?
        - **Current focus city:** **{selected_city}**
        - **Selected window:** **{year_range[0]}–{year_range[1]}**
        - **Recommended use:** compare composition, geography and relative performance across cities.
        """
    )

st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "📈 Population & Waste",
        "♻️ Composition",
        "🗺️ Geographic View",
        "🎞️ Dynamic Simulation",
        "📊 City Comparison",
        "ℹ️ About & Data",
    ]
)

# =========================================================
# TAB 1 - POPULATION & WASTE
# =========================================================
with tab1:
    st.subheader(f"Population and Waste Trends — {selected_city}")
    add_section_intro("What this tab answers", "How population, total waste and per-capita pressure evolve over time.")

    c1, c2 = st.columns(2)
    with c1:
        st.caption(f"Population growth across selected period: {human_format(pop_growth, 1)}%")
        fig_pop = line_chart(pop_city.to_frame(), selected_city, "Population Projection", "Population", color="#1f77b4")
        st.plotly_chart(fig_pop, use_container_width=True)

    with c2:
        st.caption(f"Waste growth across selected period: {human_format(waste_growth, 1)}%")
        fig_waste = line_chart(waste_city.to_frame(), selected_city, "Total Waste Generation", "Tons/year", color="#2ca58d")
        st.plotly_chart(fig_waste, use_container_width=True)

    derived = pd.DataFrame(index=pop_city.index)
    derived["Population"] = pop_city
    derived["Waste_tons_year"] = waste_city
    derived["Waste_kg_person_day"] = (derived["Waste_tons_year"] * 1000 / derived["Population"] / 365).replace([np.inf, -np.inf], np.nan)

    st.markdown("#### Derived indicator")
    fig_pc = px.line(
        derived,
        x=derived.index,
        y="Waste_kg_person_day",
        markers=True,
        template=PLOT_TEMPLATE,
        title="Per Capita Waste Generation",
        labels={"x": "Year", "Waste_kg_person_day": "kg/person/day"},
    )
    fig_pc.update_traces(line=dict(width=3, color="#ff7f0e"), marker=dict(size=7))
    fig_pc.update_layout(hovermode="x unified", margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_pc, use_container_width=True)

# =========================================================
# TAB 2 - COMPOSITION
# =========================================================
with tab2:
    st.subheader(f"Waste Composition by Type — {selected_city}")
    add_section_intro("What this tab answers", "Which fractions dominate the waste mix and how their shares change across time.")
    df_city = df_types[
        (df_types["Ciudad"] == selected_city)
        & (df_types["Año"].between(year_range[0], year_range[1]))
    ].copy()

    if df_city.empty:
        st.info("No composition data is available for the selected city and year range.")
    else:
        left, right = st.columns([1, 1])
        with left:
            view_mode = st.radio(
                "Visualization mode",
                ["Time series", "Single year", "Share by type"],
                horizontal=True,
            )
        with right:
            sort_mode = st.selectbox("Sort types", ["Alphabetical", "By value (desc)"])

        pivot = df_city.pivot_table(
            index="Año", columns="Tipo", values="Toneladas_anio", aggfunc="sum"
        ).sort_index()

        if view_mode == "Time series":
            fig_area = px.area(
                pivot,
                x=pivot.index,
                y=pivot.columns,
                template=PLOT_TEMPLATE,
                title="Composition of Waste by Type Over Time",
                labels={"value": "Tons/year", "Año": "Year", "variable": "Type"},
            )
            fig_area.update_layout(hovermode="x unified", margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_area, use_container_width=True)

        elif view_mode == "Single year":
            years_city = sorted(df_city["Año"].unique())
            year_single = st.select_slider("Select year", options=years_city, value=years_city[0])
            df_single = df_city[df_city["Año"] == year_single].copy()
            if sort_mode == "By value (desc)":
                df_single = df_single.sort_values("Toneladas_anio", ascending=False)
            else:
                df_single = df_single.sort_values("Tipo")

            fig_bar = px.bar(
                df_single,
                x="Tipo",
                y="Toneladas_anio",
                text_auto=".2s",
                template=PLOT_TEMPLATE,
                title=f"Composition by Type — {year_single}",
                labels={"Toneladas_anio": "Tons/year", "Tipo": "Type"},
            )
            fig_bar.update_layout(margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_bar, use_container_width=True)

        else:
            year_share = st.select_slider("Select year for share", options=sorted(df_city["Año"].unique()))
            df_share = df_city[df_city["Año"] == year_share].copy()
            if sort_mode == "By value (desc)":
                df_share = df_share.sort_values("Toneladas_anio", ascending=False)
            else:
                df_share = df_share.sort_values("Tipo")

            fig_pie = px.pie(
                df_share,
                names="Tipo",
                values="Toneladas_anio",
                hole=0.45,
                template=PLOT_TEMPLATE,
                title=f"Waste Share by Type — {year_share}",
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_pie, use_container_width=True)

# =========================================================
# TAB 3 - GEOGRAPHIC VIEW
# =========================================================
with tab3:
    st.subheader("Geographic Distribution of Waste and Population")
    add_section_intro("What this tab answers", "Where waste generation is concentrated and how territorial pressure differs among cities.")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        view_year = st.slider("Select year", min_value=min_year, max_value=max_year, value=min_year, key="geo_year")
    with col_b:
        unit = st.radio("Units", ["tons/day", "tons/year"], horizontal=True)

    geo_df = pd.DataFrame(
        {
            "City": cities_available,
            "lat": [city_coords[c][0] for c in cities_available],
            "lon": [city_coords[c][1] for c in cities_available],
            "Landfill": [landfills.get(c, "N/A") for c in cities_available],
            "Population": [float(df_pop.loc[view_year, c]) if view_year in df_pop.index else np.nan for c in cities_available],
            "Waste_tons_year": [float(df_waste_scenario.loc[view_year, c]) if view_year in df_waste_scenario.index else np.nan for c in cities_available],
        }
    )
    geo_df["Waste_tons_day"] = geo_df["Waste_tons_year"] / 365
    geo_df["Value"] = geo_df["Waste_tons_day"] if unit == "tons/day" else geo_df["Waste_tons_year"]
    geo_df["Per_capita_kg_day"] = (geo_df["Waste_tons_year"] * 1000 / geo_df["Population"] / 365).replace([np.inf, -np.inf], np.nan)

    fig_map = px.scatter_mapbox(
        geo_df,
        lat="lat",
        lon="lon",
        color="Value",
        size="Value",
        size_max=35,
        hover_name="City",
        hover_data={
            "Landfill": True,
            "Population": ":,.0f",
            "Waste_tons_year": ":,.0f",
            "Waste_tons_day": ":,.1f",
            "Per_capita_kg_day": ":.2f",
            "lat": False,
            "lon": False,
            "Value": False,
        },
        color_continuous_scale="Viridis",
        mapbox_style="open-street-map",
        zoom=4.8,
        center={"lat": 6.5, "lon": -74.5},
        title=f"Geographic Distribution — {view_year}",
    )
    fig_map.update_layout(margin=dict(l=0, r=0, t=50, b=0))
    st.plotly_chart(fig_map, use_container_width=True)

    st.dataframe(
        geo_df[["City", "Population", "Waste_tons_year", "Waste_tons_day", "Per_capita_kg_day", "Landfill"]]
        .sort_values("Waste_tons_year", ascending=False)
        .style.format(
            {
                "Population": "{:,.0f}",
                "Waste_tons_year": "{:,.0f}",
                "Waste_tons_day": "{:,.1f}",
                "Per_capita_kg_day": "{:,.2f}",
            }
        ),
        use_container_width=True,
    )

# =========================================================
# TAB 4 - DYNAMIC SIMULATION
# =========================================================
with tab4:
    st.subheader("Animated Waste Simulation (Cities + Aggregate Trend)")
    add_section_intro("What this tab answers", "How the spatial footprint and aggregate waste trajectory evolve together year by year.")

    years = [y for y in range(min_year, max_year + 1) if y in df_waste_scenario.index]
    anim_base = pd.DataFrame(
        {
            "City": cities_available,
            "lat": [city_coords[c][0] for c in cities_available],
            "lon": [city_coords[c][1] for c in cities_available],
        }
    )

    anim_frames = []
    for year in years:
        anim_frames.append(
            pd.DataFrame(
                {
                    "City": anim_base["City"],
                    "lat": anim_base["lat"],
                    "lon": anim_base["lon"],
                    "Year": year,
                    "Waste_tons": [float(df_waste_scenario.loc[year, c]) for c in cities_available],
                }
            )
        )

    df_anim = pd.concat(anim_frames, ignore_index=True)
    national = df_anim.groupby("Year", as_index=False)["Waste_tons"].sum()

    initial_year = years[0]
    d0 = df_anim[df_anim["Year"] == initial_year]
    n0 = national[national["Year"] <= initial_year]

    fig_anim = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "mapbox"}, {"type": "xy"}]],
        column_widths=[0.58, 0.42],
        horizontal_spacing=0.05,
        subplot_titles=("Geographic projection", "Total waste trend"),
    )

    fig_anim.add_trace(
        go.Scattermapbox(
            lat=d0["lat"],
            lon=d0["lon"],
            mode="markers",
            marker=dict(
                size=safe_bubble_sizes(d0["Waste_tons"]),
                color=to_num(d0["Waste_tons"]),
                colorscale="Turbo",
                showscale=True,
                opacity=0.88,
                colorbar=dict(title="t/year"),
            ),
            text=d0["City"],
            hovertemplate="<b>%{text}</b><br>Waste: %{marker.color:,.0f} t/year<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    fig_anim.add_trace(
        go.Scatter(
            x=n0["Year"],
            y=n0["Waste_tons"],
            mode="lines+markers",
            line=dict(width=3, color="#1f77b4"),
            marker=dict(size=7, color="#2ca58d"),
            hovertemplate="Year %{x}<br>Total: %{y:,.0f} t/year<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=2,
    )

    frames = []
    for year in years:
        dy = df_anim[df_anim["Year"] == year]
        ny = national[national["Year"] <= year]
        frames.append(
            go.Frame(
                name=str(year),
                data=[
                    go.Scattermapbox(
                        lat=dy["lat"],
                        lon=dy["lon"],
                        mode="markers",
                        marker=dict(
                            size=safe_bubble_sizes(dy["Waste_tons"]),
                            color=to_num(dy["Waste_tons"]),
                            colorscale="Turbo",
                            showscale=True,
                            opacity=0.88,
                        ),
                        text=dy["City"],
                        hovertemplate="<b>%{text}</b><br>Waste: %{marker.color:,.0f} t/year<extra></extra>",
                        showlegend=False,
                    ),
                    go.Scatter(
                        x=ny["Year"],
                        y=ny["Waste_tons"],
                        mode="lines+markers",
                        line=dict(width=3, color="#1f77b4"),
                        marker=dict(size=7, color="#2ca58d"),
                        hovertemplate="Year %{x}<br>Total: %{y:,.0f} t/year<extra></extra>",
                        showlegend=False,
                    ),
                ],
            )
        )
    fig_anim.frames = frames

    y_min = float(national["Waste_tons"].min())
    y_max = float(national["Waste_tons"].max())

    fig_anim.update_layout(
        mapbox_style="open-street-map",
        mapbox_zoom=4.8,
        mapbox_center={"lat": 6.5, "lon": -74.5},
        template=PLOT_TEMPLATE,
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis_title="Year",
        yaxis_title="tons/year",
        updatemenus=[
            {
                "type": "buttons",
                "direction": "left",
                "x": 0.1,
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
                        "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}],
                    },
                ],
            }
        ],
        sliders=[
            {
                "active": 0,
                "x": 0.1,
                "y": -0.04,
                "len": 0.75,
                "currentvalue": {"prefix": "Year: ", "font": {"size": 16}},
                "steps": [
                    {
                        "label": str(year),
                        "method": "animate",
                        "args": [[str(year)], {"mode": "immediate", "frame": {"duration": 0, "redraw": True}}],
                    }
                    for year in years
                ],
            }
        ],
    )

    fig_anim.update_xaxes(row=1, col=2, tickmode="linear", dtick=1, range=[years[0], years[-1]], tickformat="d")
    fig_anim.update_yaxes(row=1, col=2, range=[max(0, y_min * 0.95), y_max * 1.05], tickformat=",.0f")
    st.plotly_chart(fig_anim, use_container_width=True)

# =========================================================
# TAB 5 - CITY COMPARISON
# =========================================================
with tab5:
    st.subheader("Multi-city comparison")
    add_section_intro("What this tab answers", "Which cities generate more waste in absolute and per-capita terms under the selected scenario.")
    selected_compare = comparison_cities if comparison_cities else [selected_city]
    compare_df = filter_year_range(df_waste_scenario, year_range, selected_compare)

    fig_compare = px.line(
        compare_df,
        x=compare_df.index,
        y=compare_df.columns,
        markers=True,
        template=PLOT_TEMPLATE,
        title="Waste Generation by City",
        labels={"x": "Year", "value": "Tons/year", "variable": "City"},
    )
    fig_compare.update_layout(hovermode="x unified", margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_compare, use_container_width=True)

    latest_compare = pd.DataFrame(
        {
            "City": selected_compare,
            "Waste_tons_year": [float(df_waste_scenario.loc[latest_year, c]) for c in selected_compare],
            "Population": [float(df_pop.loc[latest_year, c]) for c in selected_compare],
        }
    )
    latest_compare["kg_person_day"] = latest_compare["Waste_tons_year"] * 1000 / latest_compare["Population"] / 365
    latest_compare = latest_compare.sort_values("Waste_tons_year", ascending=False)

    c1, c2 = st.columns(2)
    with c1:
        fig_rank = px.bar(
            latest_compare,
            x="City",
            y="Waste_tons_year",
            text_auto=".2s",
            template=PLOT_TEMPLATE,
            title=f"Ranking by Waste Generation ({latest_year})",
            labels={"Waste_tons_year": "Tons/year"},
        )
        fig_rank.update_layout(xaxis_tickangle=-20, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_rank, use_container_width=True)

    with c2:
        fig_pc_comp = px.bar(
            latest_compare,
            x="City",
            y="kg_person_day",
            text_auto=".2f",
            template=PLOT_TEMPLATE,
            title=f"Per Capita Waste ({latest_year})",
            labels={"kg_person_day": "kg/person/day"},
        )
        fig_pc_comp.update_layout(xaxis_tickangle=-20, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_pc_comp, use_container_width=True)

# =========================================================
# TAB 6 - ABOUT & DATA
# =========================================================
with tab6:
    st.subheader("About the Platform")
    add_section_intro("What this tab answers", "What the dashboard does, what data it expects and how to export results.")
    st.markdown(
        """
        **Purpose.** This platform supports the exploration of urban waste dynamics and circularity potential
        for Colombian cities using structured simulation outputs.

        **Methodological core.** The interface is designed to visualize simulation trajectories, compare cities,
        inspect waste composition, and communicate results in a more decision-oriented way.

        **Expected data sheets.**
        - `Poblacion_2050`
        - `ResiduosTotales_t_anio`
        - `Residuos_5Tipos_largo`

        **Good UX changes introduced in this version.**
        - Cleaner visual hierarchy and dashboard cards
        - Better error handling and data validation
        - Per capita indicator
        - Multi-city comparison
        - Executive insights block
        - Scenario selector for communication-ready exploration
        - More consistent chart layout
        - Optional data inspection and export
        """
    )

    st.markdown("#### Filtered data export")
    filtered_pop = filter_year_range(df_pop, year_range, [selected_city])
    filtered_waste = filter_year_range(df_waste, year_range, [selected_city])
    csv_pop, pop_name = export_dataframe(filtered_pop, f"population_{selected_city}_{year_range[0]}_{year_range[1]}")
    csv_waste, waste_name = export_dataframe(filtered_waste, f"waste_{selected_city}_{year_range[0]}_{year_range[1]}")

    d1, d2 = st.columns(2)
    with d1:
        st.download_button("Download population CSV", data=csv_pop, file_name=pop_name, mime="text/csv")
    with d2:
        st.download_button("Download waste CSV", data=csv_waste, file_name=waste_name, mime="text/csv")

    if show_raw_data:
        st.markdown("#### Raw filtered tables")
        st.write("Population")
        st.dataframe(filtered_pop.style.format("{:,.0f}"), use_container_width=True)
        st.write("Waste")
        st.dataframe(filtered_waste.style.format("{:,.0f}"), use_container_width=True)

st.caption("Designed to be more robust, readable, and decision-friendly. A dashboard should explain itself before the user has to fight it.")
