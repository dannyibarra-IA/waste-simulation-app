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
    page_title="Urban Waste Simulation and Circularity Observatory",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# STYLES - INSTITUTIONAL / ACADEMIC
# =========================================================
st.markdown(
    """
    <style>
        :root {
            --bg: #f4f7fb;
            --card: #ffffff;
            --soft: #e8eef6;
            --soft-2: #d7e3f1;
            --text: #14324a;
            --muted: #5a6c7d;
            --accent: #0d5c91;
            --accent-2: #2f7d6b;
            --accent-3: #b98900;
            --border: rgba(20, 50, 74, 0.10);
            --shadow: 0 6px 24px rgba(20, 50, 74, 0.08);
            --radius: 18px;
        }

        .stApp {
            font-family: "Inter", "Segoe UI", sans-serif;
        }

        [data-testid="stAppViewContainer"] {
            background: linear-gradient(180deg, #f8fbfe 0%, #eef4f9 42%, #f7f9fc 100%);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #edf3f9 0%, #e7eef6 100%);
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] * {
            color: var(--text);
        }

        h1, h2, h3, h4 {
            color: var(--text);
            letter-spacing: -0.02em;
        }

        .hero {
            background: linear-gradient(135deg, rgba(13,92,145,0.12), rgba(47,125,107,0.11), rgba(185,137,0,0.08));
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 1.55rem 1.6rem 1.2rem 1.6rem;
            box-shadow: var(--shadow);
            margin-bottom: 1rem;
            position: relative;
            overflow: hidden;
        }

        .hero::after {
            content: "";
            position: absolute;
            right: -60px;
            top: -40px;
            width: 180px;
            height: 180px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(255,255,255,0.45) 0%, rgba(255,255,255,0.0) 70%);
        }

        .hero-kicker {
            display: inline-block;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--accent);
            background: rgba(255,255,255,0.72);
            border: 1px solid rgba(13,92,145,0.12);
            border-radius: 999px;
            padding: 0.35rem 0.7rem;
            margin-bottom: 0.65rem;
        }

        .hero-title {
            font-size: 2.1rem;
            line-height: 1.1;
            font-weight: 800;
            color: var(--text);
            margin-bottom: 0.35rem;
        }

        .hero-subtitle {
            color: #375268;
            font-size: 1rem;
            max-width: 980px;
            line-height: 1.55;
            margin-bottom: 0.55rem;
        }

        .hero-meta {
            color: var(--muted);
            font-size: 0.92rem;
        }

        .metric-card {
            background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
            border-radius: var(--radius);
            padding: 1rem 1.05rem;
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.84rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.22rem;
            font-weight: 700;
        }

        .metric-value {
            color: var(--text);
            font-size: 1.52rem;
            font-weight: 800;
            line-height: 1.15;
        }

        .small-note {
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.5;
        }

        .section-panel {
            background: rgba(255,255,255,0.88);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 0.7rem 0.9rem;
            margin-bottom: 0.9rem;
        }

        .section-title {
            font-size: 0.86rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--accent);
            margin-bottom: 0.15rem;
        }

        .section-text {
            color: var(--muted);
            font-size: 0.94rem;
            line-height: 1.5;
        }

        .insight-box {
            background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(246,249,252,0.96));
            border: 1px solid var(--border);
            border-left: 5px solid var(--accent);
            border-radius: 16px;
            padding: 0.9rem 1rem;
            box-shadow: var(--shadow);
        }

        .stTabs [data-baseweb="tab"] {
            font-size: 14px;
            font-weight: 700;
            padding-top: 0.7rem;
            padding-bottom: 0.7rem;
            color: var(--text);
        }

        .stTabs [aria-selected="true"] {
            color: var(--accent) !important;
        }

        .footer-note {
            color: var(--muted);
            font-size: 0.88rem;
            text-align: center;
            padding: 0.8rem 0;
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
    "BAU": {
        "source_reduction": 0.00,
        "collection": 0.85,
        "recycling": 0.18,
        "composting": 0.08,
        "education_bonus": 0.00,
        "formalization_bonus": 0.00,
        "label": "Business as usual",
    },
    "Moderate Circularity": {
        "source_reduction": 0.05,
        "collection": 0.90,
        "recycling": 0.28,
        "composting": 0.16,
        "education_bonus": 0.03,
        "formalization_bonus": 0.04,
        "label": "Moderate intervention",
    },
    "Accelerated Circularity": {
        "source_reduction": 0.12,
        "collection": 0.96,
        "recycling": 0.40,
        "composting": 0.28,
        "education_bonus": 0.06,
        "formalization_bonus": 0.08,
        "label": "High circularity push",
    },
}

BASE_POLICY_DEFAULTS = {
    "collection_coverage": 0.85,
    "recycling_capture": 0.18,
    "composting_capture": 0.08,
    "source_reduction": 0.00,
    "education_bonus": 0.00,
    "formalization_bonus": 0.00,
}

LANDFILL_CAPACITY_T = {
    "Medellín": 12_000_000,
    "Santiago de Cali": 8_500_000,
    "Barranquilla": 7_000_000,
    "Cartagena de Indias": 5_500_000,
    "Soacha": 4_000_000,
    "San José de Cúcuta": 4_500_000,
    "Soledad": 4_200_000,
    "Bucaramanga": 5_200_000,
    "Bello": 3_600_000,
    "Valledupar": 3_300_000,
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
    if isinstance(values, (pd.Series, pd.Index)):
        arr = pd.to_numeric(values, errors="coerce").fillna(0.0).to_numpy(dtype=float)
    elif isinstance(values, pd.DataFrame):
        arr = pd.to_numeric(values.squeeze(), errors="coerce").fillna(0.0).to_numpy(dtype=float)
    else:
        arr = np.asarray(values, dtype=float)
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)


def safe_bubble_sizes(values, min_size=10, max_size=42):
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
    out = df.loc[(df.index >= year_range[0]) & (df.index <= year_range[1])]
    if cols is not None:
        out = out[cols]
    return out


def get_year_bounds(df_pop, df_waste):
    return int(min(df_pop.index.min(), df_waste.index.min())), int(max(df_pop.index.max(), df_waste.index.max()))


def compute_growth_pct(series):
    arr = to_num(series)
    if arr.size < 2 or arr[0] == 0:
        return 0.0
    return ((arr[-1] - arr[0]) / arr[0]) * 100


def validate_columns(df, required, table_name):
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"La tabla '{table_name}' no contiene las columnas requeridas: {', '.join(sorted(missing))}.")


def build_kpi_card(label, value, note=None):
    note_html = f"<div class='small-note'>{note}</div>" if note else ""
    st.markdown(
        f"""
        <div class='metric-card'>
            <div class='metric-label'>{label}</div>
            <div class='metric-value'>{value}</div>
            {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def add_section_intro(title, text):
    st.markdown(
        f"""
        <div class='section-panel'>
            <div class='section-title'>{title}</div>
            <div class='section-text'>{text}</div>
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
    fig.update_layout(hovermode="x unified", margin=dict(l=10, r=10, t=50, b=10), xaxis=dict(dtick=1))
    return fig


def export_dataframe(df, name):
    return df.to_csv(index=True).encode("utf-8"), f"{name}.csv"


def min_max_norm(series):
    s = pd.Series(series, dtype=float)
    if s.max() == s.min():
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - s.min()) / (s.max() - s.min())


def category_shares(df_types, city, year):
    city_df = df_types[(df_types["Ciudad"] == city) & (df_types["Año"] == year)].copy()
    if city_df.empty:
        return {"organics": 0.5, "recoverables": 0.25, "others": 0.25}

    city_df["tipo_lower"] = city_df["Tipo"].str.lower()
    total = city_df["Toneladas_anio"].sum()
    if total <= 0:
        return {"organics": 0.5, "recoverables": 0.25, "others": 0.25}

    organics_mask = city_df["tipo_lower"].str.contains("org")
    recoverables_mask = city_df["tipo_lower"].str.contains("pl[aá]st|paper|papel|cart|vidr|metal|text")

    organics = city_df.loc[organics_mask, "Toneladas_anio"].sum() / total
    recoverables = city_df.loc[recoverables_mask, "Toneladas_anio"].sum() / total
    others = max(0.0, 1 - organics - recoverables)
    return {"organics": organics, "recoverables": recoverables, "others": others}


def effective_policy_params(source_reduction, collection_coverage, recycling_capture, composting_capture, education_bonus, formalization_bonus):
    eff_recycling = min(0.95, recycling_capture + education_bonus * 0.35 + formalization_bonus * 0.65)
    eff_composting = min(0.90, composting_capture + education_bonus * 0.50)
    eff_collection = min(0.99, collection_coverage + education_bonus * 0.20)
    eff_source = min(0.35, source_reduction + education_bonus * 0.15)
    return eff_source, eff_collection, eff_recycling, eff_composting


def policy_simulation(base_waste_t, shares, source_reduction, collection_coverage, recycling_capture, composting_capture, education_bonus, formalization_bonus, remaining_capacity_t):
    eff_source, eff_collection, eff_recycling, eff_composting = effective_policy_params(
        source_reduction,
        collection_coverage,
        recycling_capture,
        composting_capture,
        education_bonus,
        formalization_bonus,
    )

    generated = max(0.0, base_waste_t * (1 - eff_source))
    collected = generated * eff_collection
    uncollected = max(0.0, generated - collected)

    recoverable_pool = generated * shares["recoverables"]
    organics_pool = generated * shares["organics"]

    recycled = min(collected, recoverable_pool * eff_recycling)
    remaining_after_recycling = max(0.0, collected - recycled)
    composted = min(remaining_after_recycling, organics_pool * eff_composting)

    diverted = recycled + composted
    landfilled = max(0.0, collected - diverted)

    diversion_rate = diverted / generated if generated > 0 else 0.0
    controlled_rate = landfilled / generated if generated > 0 else 0.0
    collection_rate = collected / generated if generated > 0 else 0.0
    landfill_life = remaining_capacity_t / landfilled if landfilled > 0 else np.inf

    return {
        "generated_t": generated,
        "collected_t": collected,
        "uncollected_t": uncollected,
        "recycled_t": recycled,
        "composted_t": composted,
        "diverted_t": diverted,
        "landfilled_t": landfilled,
        "diversion_rate": diversion_rate,
        "controlled_rate": controlled_rate,
        "collection_rate": collection_rate,
        "landfill_life_years": landfill_life,
        "effective_source_reduction": eff_source,
        "effective_collection": eff_collection,
        "effective_recycling": eff_recycling,
        "effective_composting": eff_composting,
    }


def progressive_waste_adjustment(df_waste, scenario_name, base_year=None):
    scenario = SCENARIO_OPTIONS[scenario_name]
    adjusted = df_waste.copy()
    if base_year is None:
        base_year = int(adjusted.index.min())

    for year in adjusted.index:
        years_from_base = max(0, int(year - base_year))
        horizon = max(1, int(adjusted.index.max() - base_year))
        annual_factor = 1 - (scenario["source_reduction"] * (years_from_base / horizon))
        adjusted.loc[year] = adjusted.loc[year] * annual_factor
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
            insights.append(f"The dominant fraction is **{top_row['Tipo']}**, representing approximately **{human_format(share, 1)}%** of the waste mix in **{year}**.")

    return insights[:3]


def scenario_summary_text(scenario_name):
    s = SCENARIO_OPTIONS[scenario_name]
    return f"Scenario: **{s['label']}** · source reduction {human_format(s['source_reduction']*100,0)}% · collection {human_format(s['collection']*100,0)}% · recycling {human_format(s['recycling']*100,0)}% · composting {human_format(s['composting']*100,0)}%."


def peer_group(df_pop, city, year):
    selected_pop = float(df_pop.loc[year, city])
    lower = selected_pop * 0.5
    upper = selected_pop * 1.5
    peers = [c for c in df_pop.columns if lower <= float(df_pop.loc[year, c]) <= upper]
    return sorted(set(peers))


def alert_messages(policy_results, waste_growth_pct, per_capita_kg_day):
    alerts = []
    if policy_results["landfill_life_years"] < 5:
        alerts.append(("High", "Estimated landfill life is below 5 years under the selected policy conditions."))
    elif policy_results["landfill_life_years"] < 10:
        alerts.append(("Medium", "Estimated landfill life is below 10 years; medium-term disposal stress is likely."))

    if policy_results["collection_rate"] < 0.85:
        alerts.append(("High", "Collection coverage is below 85%, implying leakage or unmanaged waste risks."))
    elif policy_results["collection_rate"] < 0.95:
        alerts.append(("Medium", "Collection coverage is improving but still below high-service thresholds."))

    if policy_results["diversion_rate"] < 0.20:
        alerts.append(("High", "Diversion rate is below 20%, indicating strong dependence on final disposal."))
    elif policy_results["diversion_rate"] < 0.35:
        alerts.append(("Medium", "Diversion rate remains moderate; stronger organics and recycling interventions may be needed."))

    if waste_growth_pct > 30:
        alerts.append(("High", "Projected waste growth exceeds 30% across the selected horizon."))
    elif waste_growth_pct > 15:
        alerts.append(("Medium", "Projected waste growth is material and may strain collection and disposal systems."))

    if per_capita_kg_day > 1.1:
        alerts.append(("Medium", "Per-capita waste generation is relatively high and may justify prevention measures."))

    if not alerts:
        alerts.append(("Low", "No immediate structural alert is triggered under the selected assumptions."))
    return alerts


def priority_index_table(df_pop, df_waste, df_types, selected_year, collection_assumption, recycling_assumption, composting_assumption):
    rows = []
    for city in df_waste.columns:
        waste_now = float(df_waste.loc[selected_year, city])
        pop_now = float(df_pop.loc[selected_year, city])
        per_capita = waste_now * 1000 / pop_now / 365 if pop_now > 0 else 0
        growth = compute_growth_pct(df_waste[[city]][city])
        shares = category_shares(df_types, city, selected_year)
        diversion_potential = shares["recoverables"] * recycling_assumption + shares["organics"] * composting_assumption
        landfill_stress = waste_now / max(LANDFILL_CAPACITY_T.get(city, 1), 1)
        collection_gap = max(0.0, 1 - collection_assumption)
        rows.append(
            {
                "City": city,
                "Waste_tons_year": waste_now,
                "Population": pop_now,
                "kg_person_day": per_capita,
                "Growth_pct": growth,
                "Diversion_potential": diversion_potential,
                "Landfill_stress": landfill_stress,
                "Collection_gap": collection_gap,
            }
        )

    rank_df = pd.DataFrame(rows)
    rank_df["n_per_capita"] = min_max_norm(rank_df["kg_person_day"])
    rank_df["n_growth"] = min_max_norm(rank_df["Growth_pct"])
    rank_df["n_landfill_stress"] = min_max_norm(rank_df["Landfill_stress"])
    rank_df["n_collection_gap"] = min_max_norm(rank_df["Collection_gap"])
    rank_df["n_low_diversion"] = 1 - min_max_norm(rank_df["Diversion_potential"])
    rank_df["Priority_score"] = (
        0.28 * rank_df["n_per_capita"]
        + 0.22 * rank_df["n_growth"]
        + 0.22 * rank_df["n_landfill_stress"]
        + 0.14 * rank_df["n_collection_gap"]
        + 0.14 * rank_df["n_low_diversion"]
    ) * 100
    rank_df["Priority_level"] = pd.cut(
        rank_df["Priority_score"],
        bins=[-0.01, 33, 66, 100],
        labels=["Low", "Medium", "High"],
    )
    return rank_df.sort_values("Priority_score", ascending=False)


# =========================================================
# DATA LOADING
# =========================================================
@st.cache_data(show_spinner=False)
def load_data(source):
    if isinstance(source, (str, Path)):
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(f"No se encontró el archivo por defecto '{source.name}' en el directorio de la app.")
        excel_source = source
    else:
        excel_source = source

    pop = pd.read_excel(excel_source, sheet_name="Poblacion_2050", index_col=0)
    waste = pd.read_excel(excel_source, sheet_name="ResiduosTotales_t_anio", index_col=0)
    types = pd.read_excel(excel_source, sheet_name="Residuos_5Tipos_largo")

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

    return pop.sort_index(), waste.sort_index(), types


# HEADER
st.markdown(
    """
    <div class="hero">
        <div class="hero-kicker">Academic decision-support platform</div>
        <div class="hero-title">Urban Waste Simulation and Circularity Observatory</div>
        <div class="hero-subtitle">
            Institutional-academic dashboard for the exploration of population growth, waste generation,
            composition patterns, territorial pressure and scenario-based circularity trajectories across Colombian cities.
        </div>
        <div class="hero-meta">
            Developed by <b>Danny Ibarra Vega, Ph.D.</b> · Universidad de Antioquia · System Dynamics, waste systems and circular economy
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# SIDEBAR
st.sidebar.title("Simulation Control")
uploaded_file = st.sidebar.file_uploader("Upload simulation Excel (.xlsx)", type=["xlsx"])

try:
    if uploaded_file is not None:
        df_pop, df_waste, df_types = load_data(uploaded_file)
        data_source_label = f"Custom file: {uploaded_file.name}"
    else:
        df_pop, df_waste, df_types = load_data(DATA_FILE)
        data_source_label = f"Default file: {DATA_FILE}"
except Exception as exc:
    st.error(f"Error loading data: {exc}")
    st.stop()

cities_available = sorted(set(df_pop.columns) & set(df_waste.columns) & set(city_coords.keys()))
if not cities_available:
    st.error("No matching cities were found between the Excel file and the configured city list.")
    st.stop()

min_year, max_year = get_year_bounds(df_pop, df_waste)
default_city = "Medellín" if "Medellín" in cities_available else cities_available[0]

selected_city = st.sidebar.selectbox("Select city", cities_available, index=cities_available.index(default_city))
selected_scenario = st.sidebar.selectbox("Scenario preset", list(SCENARIO_OPTIONS.keys()), index=0)
year_range = st.sidebar.slider("Select year range", min_year, max_year, (min_year, max_year))
comparison_cities = st.sidebar.multiselect("Compare cities", options=cities_available, default=[selected_city])
show_raw_data = st.sidebar.toggle("Show raw filtered data", value=False)
show_method_note = st.sidebar.toggle("Show methodology note", value=False)
st.sidebar.caption(data_source_label)

# CORE SERIES
df_waste_scenario = progressive_waste_adjustment(df_waste, selected_scenario, base_year=min_year)
pop_city = filter_year_range(df_pop, year_range, [selected_city])[selected_city]
waste_city = filter_year_range(df_waste_scenario, year_range, [selected_city])[selected_city]

pop_growth = compute_growth_pct(pop_city)
waste_growth = compute_growth_pct(waste_city)
latest_year = year_range[1]
latest_pop = float(pop_city.loc[latest_year]) if latest_year in pop_city.index else float(pop_city.iloc[-1])
latest_waste = float(waste_city.loc[latest_year]) if latest_year in waste_city.index else float(waste_city.iloc[-1])
per_capita_kg_day = (latest_waste * 1000 / latest_pop / 365) if latest_pop > 0 else 0
remaining_capacity_default = LANDFILL_CAPACITY_T.get(selected_city, 4_000_000)
selected_shares = category_shares(df_types, selected_city, latest_year)
scenario_preset = SCENARIO_OPTIONS[selected_scenario]

hero_left, hero_right = st.columns([1.35, 1])
with hero_left:
    build_kpi_card(
        "Observatory focus",
        f"Urban waste dynamics in {selected_city}",
        note=f"Decision-oriented exploration of trajectories, composition, territorial concentration and scenario-sensitive outcomes between {year_range[0]} and {year_range[1]}.",
    )
with hero_right:
    build_kpi_card("Scenario configuration", selected_scenario, note=SCENARIO_OPTIONS[selected_scenario]["label"])

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
        "The dashboard reads projected population and waste from the uploaded workbook. Scenario presets apply a progressive reduction factor to waste generation over time for exploratory policy analysis."
    )

insight_types = df_types[(df_types["Ciudad"] == selected_city) & (df_types["Año"].between(year_range[0], year_range[1]))].copy()
insights = build_insights(selected_city, latest_year, latest_pop, latest_waste, per_capita_kg_day, waste_city.to_frame(), insight_types)

ibox_left, ibox_right = st.columns([1.15, 1])
with ibox_left:
    st.markdown("#### Executive insights")
    st.markdown("<div class='insight-box'>", unsafe_allow_html=True)
    for item in insights:
        st.markdown(f"- {item}")
    st.markdown("</div>", unsafe_allow_html=True)
with ibox_right:
    st.markdown("#### Analytical reading guide")
    st.markdown(
        f"""
- **Main question:** How does waste evolve under the selected scenario?
- **Current focus city:** **{selected_city}**
- **Selected window:** **{year_range[0]}–{year_range[1]}**
- **Recommended use:** compare composition, geography and relative performance across cities.
- **Institutional use case:** academic communication, diagnostics, scenario discussion and decision support.
        """
    )

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(
    [
        "📈 Population & Waste",
        "♻️ Composition",
        "🗺️ Geographic View",
        "🎞️ Dynamic Simulation",
        "🧭 Policy Simulator",
        "🚨 Alerts & Priorities",
        "🏙️ Benchmarking",
        "📐 Methodology & Equations",
        "ℹ️ About & Data",
    ]
)

with tab1:
    st.subheader(f"Population and Waste Trends — {selected_city}")
    add_section_intro("What this tab answers", "How population, total waste and per-capita pressure evolve over time.")

    c1, c2 = st.columns(2)
    with c1:
        st.caption(f"Population growth across selected period: {human_format(pop_growth, 1)}%")
        st.plotly_chart(line_chart(pop_city.to_frame(), selected_city, "Population Projection", "Population", color="#0d5c91"), use_container_width=True)

    with c2:
        st.caption(f"Waste growth across selected period: {human_format(waste_growth, 1)}%")
        st.plotly_chart(line_chart(waste_city.to_frame(), selected_city, "Total Waste Generation", "Tons/year", color="#2f7d6b"), use_container_width=True)

    derived = pd.DataFrame(index=pop_city.index)
    derived["Population"] = pop_city
    derived["Waste_tons_year"] = waste_city
    derived["Waste_kg_person_day"] = (derived["Waste_tons_year"] * 1000 / derived["Population"] / 365).replace([np.inf, -np.inf], np.nan)

    fig_pc = px.line(
        derived,
        x=derived.index,
        y="Waste_kg_person_day",
        markers=True,
        template=PLOT_TEMPLATE,
        title="Per Capita Waste Generation",
        labels={"x": "Year", "Waste_kg_person_day": "kg/person/day"},
    )
    fig_pc.update_traces(line=dict(width=3, color="#b98900"), marker=dict(size=7))
    fig_pc.update_layout(hovermode="x unified", margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_pc, use_container_width=True)

with tab2:
    st.subheader(f"Waste Composition by Type — {selected_city}")
    add_section_intro("What this tab answers", "Which fractions dominate the waste mix and how their shares change across time.")
    df_city = df_types[(df_types["Ciudad"] == selected_city) & (df_types["Año"].between(year_range[0], year_range[1]))].copy()

    if df_city.empty:
        st.info("No composition data is available for the selected city and year range.")
    else:
        left, right = st.columns([1, 1])
        with left:
            view_mode = st.radio("Visualization mode", ["Time series", "Single year", "Share by type"], horizontal=True)
        with right:
            sort_mode = st.selectbox("Sort types", ["Alphabetical", "By value (desc)"])

        pivot = df_city.pivot_table(index="Año", columns="Tipo", values="Toneladas_anio", aggfunc="sum").sort_index()

        if view_mode == "Time series":
            fig_area = px.area(pivot, x=pivot.index, y=pivot.columns, template=PLOT_TEMPLATE, title="Composition of Waste by Type Over Time", labels={"value": "Tons/year", "Año": "Year", "variable": "Type"})
            fig_area.update_layout(hovermode="x unified", margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_area, use_container_width=True)
        elif view_mode == "Single year":
            year_single = st.select_slider("Select year", options=sorted(df_city["Año"].unique()), value=sorted(df_city["Año"].unique())[0])
            df_single = df_city[df_city["Año"] == year_single].copy()
            df_single = df_single.sort_values("Toneladas_anio", ascending=False) if sort_mode == "By value (desc)" else df_single.sort_values("Tipo")
            fig_bar = px.bar(df_single, x="Tipo", y="Toneladas_anio", text_auto=".2s", template=PLOT_TEMPLATE, title=f"Composition by Type — {year_single}", labels={"Toneladas_anio": "Tons/year", "Tipo": "Type"})
            fig_bar.update_layout(margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            year_share = st.select_slider("Select year for share", options=sorted(df_city["Año"].unique()))
            df_share = df_city[df_city["Año"] == year_share].copy()
            df_share = df_share.sort_values("Toneladas_anio", ascending=False) if sort_mode == "By value (desc)" else df_share.sort_values("Tipo")
            fig_pie = px.pie(df_share, names="Tipo", values="Toneladas_anio", hole=0.45, template=PLOT_TEMPLATE, title=f"Waste Share by Type — {year_share}")
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_pie, use_container_width=True)

with tab3:
    st.subheader("Geographic Distribution of Waste and Population")
    add_section_intro("What this tab answers", "Where waste generation is concentrated and how territorial pressure differs among cities.")

    col_a, col_b = st.columns(2)
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
            "Population": [float(df_pop.loc[view_year, c]) for c in cities_available],
            "Waste_tons_year": [float(df_waste_scenario.loc[view_year, c]) for c in cities_available],
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
        hover_data={"Landfill": True, "Population": ":,.0f", "Waste_tons_year": ":,.0f", "Waste_tons_day": ":,.1f", "Per_capita_kg_day": ":.2f", "lat": False, "lon": False, "Value": False},
        color_continuous_scale="Viridis",
        mapbox_style="open-street-map",
        zoom=4.8,
        center={"lat": 6.5, "lon": -74.5},
        title=f"Geographic Distribution — {view_year}",
    )
    fig_map.update_layout(margin=dict(l=0, r=0, t=50, b=0))
    st.plotly_chart(fig_map, use_container_width=True)

with tab4:
    st.subheader("Animated Waste Simulation (Cities + Aggregate Trend)")
    add_section_intro("What this tab answers", "How the spatial footprint and aggregate waste trajectory evolve together year by year.")

    years = [y for y in range(min_year, max_year + 1) if y in df_waste_scenario.index]
    anim_frames = []
    for year in years:
        anim_frames.append(pd.DataFrame({"City": cities_available, "lat": [city_coords[c][0] for c in cities_available], "lon": [city_coords[c][1] for c in cities_available], "Year": year, "Waste_tons": [float(df_waste_scenario.loc[year, c]) for c in cities_available]}))
    df_anim = pd.concat(anim_frames, ignore_index=True)
    national = df_anim.groupby("Year", as_index=False)["Waste_tons"].sum()

    initial_year = years[0]
    d0 = df_anim[df_anim["Year"] == initial_year]
    n0 = national[national["Year"] <= initial_year]

    fig_anim = make_subplots(rows=1, cols=2, specs=[[{"type": "mapbox"}, {"type": "xy"}]], column_widths=[0.58, 0.42], horizontal_spacing=0.05, subplot_titles=("Geographic projection", "Total waste trend"))
    fig_anim.add_trace(go.Scattermapbox(lat=d0["lat"], lon=d0["lon"], mode="markers", marker=dict(size=safe_bubble_sizes(d0["Waste_tons"]), color=to_num(d0["Waste_tons"]), colorscale="Turbo", showscale=True, opacity=0.88, colorbar=dict(title="t/year")), text=d0["City"], hovertemplate="<b>%{text}</b><br>Waste: %{marker.color:,.0f} t/year<extra></extra>", showlegend=False), row=1, col=1)
    fig_anim.add_trace(go.Scatter(x=n0["Year"], y=n0["Waste_tons"], mode="lines+markers", line=dict(width=3, color="#0d5c91"), marker=dict(size=7, color="#2f7d6b"), hovertemplate="Year %{x}<br>Total: %{y:,.0f} t/year<extra></extra>", showlegend=False), row=1, col=2)

    frames = []
    for year in years:
        dy = df_anim[df_anim["Year"] == year]
        ny = national[national["Year"] <= year]
        frames.append(go.Frame(name=str(year), data=[go.Scattermapbox(lat=dy["lat"], lon=dy["lon"], mode="markers", marker=dict(size=safe_bubble_sizes(dy["Waste_tons"]), color=to_num(dy["Waste_tons"]), colorscale="Turbo", showscale=True, opacity=0.88), text=dy["City"], hovertemplate="<b>%{text}</b><br>Waste: %{marker.color:,.0f} t/year<extra></extra>", showlegend=False), go.Scatter(x=ny["Year"], y=ny["Waste_tons"], mode="lines+markers", line=dict(width=3, color="#0d5c91"), marker=dict(size=7, color="#2f7d6b"), hovertemplate="Year %{x}<br>Total: %{y:,.0f} t/year<extra></extra>", showlegend=False)]))
    fig_anim.frames = frames
    fig_anim.update_layout(mapbox_style="open-street-map", mapbox_zoom=4.8, mapbox_center={"lat": 6.5, "lon": -74.5}, template=PLOT_TEMPLATE, margin=dict(l=10, r=10, t=60, b=10), xaxis_title="Year", yaxis_title="tons/year", updatemenus=[{"type": "buttons", "direction": "left", "x": 0.1, "y": -0.08, "showactive": True, "buttons": [{"label": "▶ Play", "method": "animate", "args": [None, {"frame": {"duration": 700, "redraw": True}, "fromcurrent": True, "transition": {"duration": 250}}]}, {"label": "⏸ Pause", "method": "animate", "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}]}]}], sliders=[{"active": 0, "x": 0.1, "y": -0.04, "len": 0.75, "currentvalue": {"prefix": "Year: ", "font": {"size": 16}}, "steps": [{"label": str(year), "method": "animate", "args": [[str(year)], {"mode": "immediate", "frame": {"duration": 0, "redraw": True}}]} for year in years]}])
    fig_anim.update_xaxes(row=1, col=2, tickmode="linear", dtick=1, range=[years[0], years[-1]], tickformat="d")
    fig_anim.update_yaxes(row=1, col=2, range=[max(0, float(national["Waste_tons"].min()) * 0.95), float(national["Waste_tons"].max()) * 1.05], tickformat=",.0f")
    st.plotly_chart(fig_anim, use_container_width=True)

with tab5:
    st.subheader("Policy Simulator for Municipal Decision-Making")
    add_section_intro("What this tab answers", "What happens if the city changes collection coverage, source reduction, recycling or composting intensity.")

    st.markdown("#### Policy levers")
    p1, p2, p3 = st.columns(3)
    with p1:
        source_reduction = st.slider("Source reduction (%)", 0, 35, int(scenario_preset["source_reduction"] * 100), 1) / 100
        collection_coverage = st.slider("Collection coverage (%)", 50, 99, int(scenario_preset["collection"] * 100), 1) / 100
    with p2:
        recycling_capture = st.slider("Recycling capture of recoverables (%)", 0, 95, int(scenario_preset["recycling"] * 100), 1) / 100
        composting_capture = st.slider("Composting capture of organics (%)", 0, 90, int(scenario_preset["composting"] * 100), 1) / 100
    with p3:
        education_bonus = st.slider("Education & behavior change bonus (%)", 0, 15, int(scenario_preset["education_bonus"] * 100), 1) / 100
        formalization_bonus = st.slider("Recycler formalization bonus (%)", 0, 15, int(scenario_preset["formalization_bonus"] * 100), 1) / 100

    remaining_capacity_t = st.number_input("Remaining landfill capacity (tons)", min_value=100000, value=int(remaining_capacity_default), step=100000)
    base_waste_t = float(df_waste_scenario.loc[latest_year, selected_city])

    results = policy_simulation(
        base_waste_t,
        selected_shares,
        source_reduction,
        collection_coverage,
        recycling_capture,
        composting_capture,
        education_bonus,
        formalization_bonus,
        remaining_capacity_t,
    )

    st.markdown("#### Scenario outputs")
    r1, r2, r3, r4, r5, r6 = st.columns(6)
    with r1:
        st.metric("Generated", f"{human_format(results['generated_t'], 0)} t/y")
    with r2:
        st.metric("Collected", f"{human_format(results['collected_t'], 0)} t/y")
    with r3:
        st.metric("Diverted", f"{human_format(results['diverted_t'], 0)} t/y")
    with r4:
        st.metric("Landfilled", f"{human_format(results['landfilled_t'], 0)} t/y")
    with r5:
        st.metric("Diversion rate", f"{human_format(results['diversion_rate']*100, 1)}%")
    with r6:
        landfill_life_text = "∞" if np.isinf(results["landfill_life_years"]) else f"{human_format(results['landfill_life_years'], 1)} years"
        st.metric("Estimated landfill life", landfill_life_text)

    flow_df = pd.DataFrame(
        {
            "Stage": ["Generated", "Collected", "Uncollected", "Recycled", "Composted", "Landfilled"],
            "Tons_year": [results["generated_t"], results["collected_t"], results["uncollected_t"], results["recycled_t"], results["composted_t"], results["landfilled_t"]],
        }
    )
    fig_flow = px.bar(flow_df, x="Stage", y="Tons_year", text_auto=".2s", template=PLOT_TEMPLATE, title="Policy scenario flow balance", labels={"Tons_year": "tons/year"})
    fig_flow.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_flow, use_container_width=True)

    st.markdown("#### Effective parameters after soft-policy bonuses")
    st.markdown(
        f"""
- Effective source reduction: **{human_format(results['effective_source_reduction']*100, 1)}%**
- Effective collection coverage: **{human_format(results['effective_collection']*100, 1)}%**
- Effective recycling capture: **{human_format(results['effective_recycling']*100, 1)}%**
- Effective composting capture: **{human_format(results['effective_composting']*100, 1)}%**
        """
    )

with tab6:
    st.subheader("Alerts, Risk Flags and Priority Ranking")
    add_section_intro("What this tab answers", "Which cities are under greater operational stress and what warnings should a mayor see immediately.")

    current_results = policy_simulation(
        base_waste_t=float(df_waste_scenario.loc[latest_year, selected_city]),
        shares=selected_shares,
        source_reduction=source_reduction,
        collection_coverage=collection_coverage,
        recycling_capture=recycling_capture,
        composting_capture=composting_capture,
        education_bonus=education_bonus,
        formalization_bonus=formalization_bonus,
        remaining_capacity_t=remaining_capacity_t,
    )

    alerts = alert_messages(current_results, waste_growth, per_capita_kg_day)
    st.markdown("#### Alert console")
    for severity, message in alerts:
        if severity == "High":
            st.error(f"{severity} · {message}")
        elif severity == "Medium":
            st.warning(f"{severity} · {message}")
        else:
            st.success(f"{severity} · {message}")

    ranking_df = priority_index_table(df_pop, df_waste_scenario, df_types, latest_year, collection_coverage, recycling_capture, composting_capture)

    st.markdown("#### City priority ranking")
    fig_priority = px.bar(
        ranking_df,
        x="City",
        y="Priority_score",
        color="Priority_level",
        color_discrete_map={"Low": "#2f7d6b", "Medium": "#d99a00", "High": "#c44536"},
        template=PLOT_TEMPLATE,
        title=f"Priority index by city ({latest_year})",
        labels={"Priority_score": "Priority score (0-100)"},
    )
    fig_priority.update_layout(xaxis_tickangle=-20, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_priority, use_container_width=True)

    st.dataframe(
        ranking_df[["City", "Priority_score", "Priority_level", "Waste_tons_year", "kg_person_day", "Growth_pct", "Diversion_potential"]]
        .style.format({"Priority_score": "{:,.1f}", "Waste_tons_year": "{:,.0f}", "kg_person_day": "{:,.2f}", "Growth_pct": "{:,.1f}", "Diversion_potential": "{:,.1%}"}),
        use_container_width=True,
    )

with tab7:
    st.subheader("Benchmarking Against Peer Cities")
    add_section_intro("What this tab answers", "How the selected city compares with similar cities by population size and operational pressure.")

    peers = peer_group(df_pop, selected_city, latest_year)
    benchmark_cities = sorted(set(peers + comparison_cities + [selected_city]))
    bench = pd.DataFrame(
        {
            "City": benchmark_cities,
            "Population": [float(df_pop.loc[latest_year, c]) for c in benchmark_cities],
            "Waste_tons_year": [float(df_waste_scenario.loc[latest_year, c]) for c in benchmark_cities],
        }
    )
    bench["kg_person_day"] = bench["Waste_tons_year"] * 1000 / bench["Population"] / 365
    bench["Selected"] = np.where(bench["City"] == selected_city, "Selected city", "Peer")
    bench = bench.sort_values("Population", ascending=False)

    c1, c2 = st.columns(2)
    with c1:
        fig_scatter = px.scatter(bench, x="Population", y="Waste_tons_year", color="Selected", text="City", template=PLOT_TEMPLATE, title=f"Population vs waste ({latest_year})", labels={"Population": "Population", "Waste_tons_year": "tons/year"})
        fig_scatter.update_traces(textposition="top center")
        st.plotly_chart(fig_scatter, use_container_width=True)

    with c2:
        fig_pc = px.bar(bench.sort_values("kg_person_day", ascending=False), x="City", y="kg_person_day", color="Selected", template=PLOT_TEMPLATE, title=f"Per-capita waste comparison ({latest_year})", labels={"kg_person_day": "kg/person/day"})
        fig_pc.update_layout(xaxis_tickangle=-20)
        st.plotly_chart(fig_pc, use_container_width=True)

    st.dataframe(bench.style.format({"Population": "{:,.0f}", "Waste_tons_year": "{:,.0f}", "kg_person_day": "{:,.2f}"}), use_container_width=True)

with tab8:
    st.subheader("Methodology, Data Structure and Equations")
    add_section_intro("What this tab answers", "Which mathematical relations, assumptions and workbook structures are used to compute the dashboard indicators.")
    st.markdown("See methodology and equations in the app source code block included for deployment. You can expand this section further with citations and local calibration.")

with tab9:
    st.subheader("About the Platform")
    add_section_intro("What this tab answers", "What the dashboard does, what data it expects and how to export results.")
    st.markdown(
        """
**Purpose.** This platform supports the exploration of urban waste dynamics and circularity potential for Colombian cities using structured simulation outputs.

**Methodological core.** The interface is designed to visualize simulation trajectories, compare cities, inspect waste composition, support policy exploration and communicate results in a more decision-oriented way.

**Current advanced modules.**
- Population and waste trajectories
- Waste composition explorer
- Geographic distribution
- Animated multi-city simulation
- Policy simulator for municipal decision-making
- Alerts and priority ranking
- Peer-city benchmarking
- Full methodology and equations tab
        """
    )

    filtered_pop = filter_year_range(df_pop, year_range, [selected_city])
    filtered_waste = filter_year_range(df_waste_scenario, year_range, [selected_city])
    csv_pop, pop_name = export_dataframe(filtered_pop, f"population_{selected_city}_{year_range[0]}_{year_range[1]}")
    csv_waste, waste_name = export_dataframe(filtered_waste, f"waste_{selected_city}_{year_range[0]}_{year_range[1]}")
    d1, d2 = st.columns(2)
    with d1:
        st.download_button("Download population CSV", data=csv_pop, file_name=pop_name, mime="text/csv")
    with d2:
        st.download_button("Download waste CSV", data=csv_waste, file_name=waste_name, mime="text/csv")

    if show_raw_data:
        st.write("Population")
        st.dataframe(filtered_pop.style.format("{:,.0f}"), use_container_width=True)
        st.write("Waste")
        st.dataframe(filtered_waste.style.format("{:,.0f}"), use_container_width=True)

st.markdown(
    """
    <div class='footer-note'>
        Designed as an institutional-academic observatory interface: robust, interpretable and communication-ready.
    </div>
    """,
    unsafe_allow_html=True,
)
