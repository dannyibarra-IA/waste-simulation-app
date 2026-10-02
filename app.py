"""
Urban Waste Simulation and Circularity Observatory  ·  v2
Developed by Danny Ibarra Vega, Ph.D. · Universidad de Antioquia

v2 replaces the static, single-year policy calculation with a dynamic mass-balance
model (year-by-year, policy ramp-in, rejects, cumulative landfill filling), adds
sensitivity / Monte Carlo analysis, an absolute-threshold priority index and a
refreshed visual layer.  See the "Methodology & Equations" tab for details.
"""
from __future__ import annotations

import inspect
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
from plotly.subplots import make_subplots

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
# VISUAL SYSTEM
# =========================================================
C = dict(
    blue="#0d5c91", green="#2f7d6b", gold="#b98900", red="#c44536",
    slate="#14324a", sky="#5aa9d6", teal="#3bb3a0", grey="#8aa0b3", purple="#7a5c99",
)
SOFT = dict(red="#f3c6c0", amber="#f6e2a8", green="#cfe8df")

pio.templates["obs"] = go.layout.Template(
    layout=dict(
        font=dict(family="Inter, Segoe UI, sans-serif", color=C["slate"], size=13),
        colorway=[C["blue"], C["green"], C["gold"], C["red"], C["sky"], C["purple"], C["teal"], C["grey"]],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(20,50,74,0.07)", zeroline=False, linecolor="rgba(20,50,74,0.25)", ticks="outside", tickcolor="rgba(20,50,74,0.25)"),
        yaxis=dict(gridcolor="rgba(20,50,74,0.07)", zeroline=False, linecolor="rgba(20,50,74,0.25)"),
        hoverlabel=dict(bgcolor="white", font_size=12, bordercolor="rgba(20,50,74,0.2)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, bgcolor="rgba(0,0,0,0)"),
        title=dict(font=dict(size=16, color=C["slate"]), x=0.0, xanchor="left", y=0.97, yanchor="top"),
        margin=dict(l=10, r=10, t=80, b=10),
    )
)
pio.templates.default = "obs"

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{--bg:#f4f7fb;--card:#fff;--text:#14324a;--muted:#5a6c7d;--accent:#0d5c91;--accent-2:#2f7d6b;--accent-3:#b98900;
--bad:#c44536;--good:#2f7d6b;--border:rgba(20,50,74,.10);--shadow:0 6px 24px rgba(20,50,74,.08);--radius:18px;}
html, body, .stApp{font-family:"Inter","Segoe UI",sans-serif;color:var(--text);}
[data-testid="stAppViewContainer"]{background:linear-gradient(180deg,#f8fbfe 0%,#eef4f9 42%,#f7f9fc 100%);}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#edf3f9 0%,#e3ecf5 100%);border-right:1px solid var(--border);}
[data-testid="stSidebar"] *{color:var(--text);}
h1,h2,h3,h4{color:var(--text);letter-spacing:-.02em;}
footer{visibility:hidden;}
.block-container{padding-top:1.6rem;}

.hero{background:linear-gradient(135deg,rgba(13,92,145,.14),rgba(47,125,107,.12),rgba(185,137,0,.08));border:1px solid var(--border);
border-radius:24px;padding:1.5rem 1.7rem 1.2rem;box-shadow:var(--shadow);margin-bottom:1rem;position:relative;overflow:hidden;}
.hero::after{content:"";position:absolute;right:-60px;top:-50px;width:210px;height:210px;border-radius:50%;
background:radial-gradient(circle,rgba(255,255,255,.55) 0%,rgba(255,255,255,0) 70%);}
.hero-kicker{display:inline-block;font-size:.76rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent);
background:rgba(255,255,255,.75);border:1px solid rgba(13,92,145,.14);border-radius:999px;padding:.32rem .7rem;margin-bottom:.6rem;}
.hero-title{font-size:2.05rem;line-height:1.1;font-weight:800;margin-bottom:.35rem;}
.hero-subtitle{color:#375268;font-size:1rem;max-width:980px;line-height:1.55;margin-bottom:.7rem;}
.hero-meta{color:var(--muted);font-size:.9rem;margin-top:.6rem;}
.badge{display:inline-block;font-size:.8rem;font-weight:600;color:var(--text);background:rgba(255,255,255,.82);
border:1px solid var(--border);border-radius:999px;padding:.25rem .65rem;margin:0 .35rem .35rem 0;}

.kpi{background:linear-gradient(180deg,#fff 0%,#fbfdff 100%);border-radius:var(--radius);padding:.95rem 1.05rem .8rem;
box-shadow:var(--shadow);border:1px solid var(--border);border-top:4px solid var(--kc,var(--accent));height:100%;
transition:transform .15s ease, box-shadow .15s ease;}
.kpi:hover{transform:translateY(-2px);box-shadow:0 10px 28px rgba(20,50,74,.13);}
.kpi-label{color:var(--muted);font-size:.74rem;text-transform:uppercase;letter-spacing:.06em;font-weight:700;margin-bottom:.2rem;}
.kpi-value{font-size:1.5rem;font-weight:800;line-height:1.15;}
.kpi-row{display:flex;align-items:flex-end;justify-content:space-between;gap:.5rem;margin-top:.35rem;}
.chip{display:inline-block;font-size:.76rem;font-weight:700;border-radius:999px;padding:.12rem .5rem;}
.chip.good{color:#1d6b57;background:#dcf0e9;} .chip.bad{color:#a5372b;background:#f8e0dc;} .chip.neutral{color:#4b5f72;background:#e6edf4;}
.spark{width:96px;height:30px;flex:none;}

.section-panel{background:rgba(255,255,255,.88);border:1px solid var(--border);border-left:4px solid var(--accent);
border-radius:14px;padding:.65rem .95rem;margin-bottom:.9rem;}
.section-title{font-size:.8rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:var(--accent);margin-bottom:.1rem;}
.section-text{color:var(--muted);font-size:.93rem;line-height:1.5;}
.insight-box{background:linear-gradient(180deg,rgba(255,255,255,.96),rgba(246,249,252,.97));border:1px solid var(--border);
border-left:5px solid var(--accent-2);border-radius:16px;padding:.8rem 1.1rem;box-shadow:var(--shadow);}
.insight-box ul{margin:.2rem 0 .1rem 1rem;padding:0;} .insight-box li{margin:.3rem 0;line-height:1.5;}
.guide-box{background:rgba(255,255,255,.7);border:1px dashed rgba(20,50,74,.2);border-radius:16px;padding:.8rem 1.1rem;}
.guide-box ul{margin:.2rem 0 .1rem 1rem;padding:0;} .guide-box li{margin:.3rem 0;line-height:1.5;color:var(--muted);}

[data-testid="stMetric"]{background:#fff;border:1px solid var(--border);border-radius:14px;padding:.7rem .9rem;box-shadow:0 3px 14px rgba(20,50,74,.06);}
[data-testid="stMetricLabel"] p{font-size:.74rem;text-transform:uppercase;letter-spacing:.05em;font-weight:700;color:var(--muted);}
[data-testid="stMetricValue"]{font-weight:800;}

.stTabs [data-baseweb="tab-list"]{gap:6px;flex-wrap:wrap;}
.stTabs [data-baseweb="tab"]{font-size:14px;font-weight:700;padding:.6rem .95rem;color:var(--text);background:rgba(255,255,255,.65);
border-radius:12px 12px 0 0;border:1px solid var(--border);border-bottom:none;}
.stTabs [aria-selected="true"]{color:var(--accent)!important;background:#fff;}
.footer-note{color:var(--muted);font-size:.88rem;text-align:center;padding:1rem 0;}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# CONSTANTS
# =========================================================
DATA_FILE = "simulacion_residuos_2025_2050.xlsx"
EXPECTED_LONG_COLS = {"Ciudad", "Año", "Tipo", "Toneladas_anio"}

# Current-system levers: the starting point of every policy ramp.
BASE_LEVERS = dict(source_reduction=0.0, collection=0.85, recycling=0.18, composting=0.08, education=0.0, formalization=0.0)

SCENARIO_OPTIONS = {
    "BAU": dict(source_reduction=0.00, collection=0.85, recycling=0.18, composting=0.08, education=0.00, formalization=0.00, label="Business as usual"),
    "Moderate Circularity": dict(source_reduction=0.05, collection=0.90, recycling=0.28, composting=0.16, education=0.03, formalization=0.04, label="Moderate intervention"),
    "Accelerated Circularity": dict(source_reduction=0.12, collection=0.96, recycling=0.40, composting=0.28, education=0.06, formalization=0.08, label="High circularity push"),
}

# Physical ceilings for every (effective) lever.
CAPS = dict(source=0.35, collection=0.99, recycling=0.95, composting=0.90)

# Elasticities of the soft levers: share of the remaining gap-to-ceiling closed per unit of bonus.
ELASTICITIES = dict(el_src_edu=0.65, el_rec_edu=1.00, el_rec_form=0.90, el_com_edu=0.80)

LANDFILL_CAPACITY_T = {
    "Medellín": 12_000_000, "Santiago de Cali": 8_500_000, "Barranquilla": 7_000_000, "Cartagena de Indias": 5_500_000,
    "Soacha": 4_000_000, "San José de Cúcuta": 4_500_000, "Soledad": 4_200_000, "Bucaramanga": 5_200_000,
    "Bello": 3_600_000, "Valledupar": 3_300_000,
}
DEFAULT_CAPACITY_T = 4_000_000

city_coords = {
    "Medellín": (6.2442, -75.5812), "Santiago de Cali": (3.4516, -76.5320), "Barranquilla": (10.9685, -74.7813),
    "Cartagena de Indias": (10.3910, -75.4794), "Soacha": (4.5833, -74.2167), "San José de Cúcuta": (7.8939, -72.5078),
    "Soledad": (10.9184, -74.7646), "Bucaramanga": (7.1254, -73.1198), "Bello": (6.3373, -75.5540), "Valledupar": (10.4631, -73.2532),
}
landfills = {
    "Medellín": "La Pradera", "Santiago de Cali": "Navarro", "Barranquilla": "Los Pocitos", "Cartagena de Indias": "Henequén",
    "Soacha": "Doña Juana (Bogotá)", "San José de Cúcuta": "Guayabal", "Soledad": "Los Pocitos (Metropolitano)",
    "Bucaramanga": "El Carrasco", "Bello": "La Pradera", "Valledupar": "Los Corazones",
}

# Priority index: (good, bad) reference values -> risk 0..1 (linear, clipped). Absolute, not relative to the peer set.
RISK_REFS = dict(per_capita=(0.60, 1.30), growth=(0.0, 3.0), landfill_life=(30.0, 5.0), collection_gap=(0.0, 0.30), diversion=(0.50, 0.10))
RISK_LABELS = dict(per_capita="Per-capita generation", growth="Waste growth (CAGR)", landfill_life="Landfill exhaustion",
                   collection_gap="Collection gap", diversion="Low diversion")
DEFAULT_WEIGHTS = dict(per_capita=20, growth=20, landfill_life=30, collection_gap=15, diversion=15)

MODEL_COLS = dict(
    Generated_t="Generated", Collected_t="Collected", Uncollected_t="Unmanaged", Recycled_t="Recycled",
    Composted_t="Composted", Rejects_t="Process rejects", Landfilled_t="Landfilled",
)

# =========================================================
# GENERIC HELPERS
# =========================================================
_HAS_WIDTH = "width" in inspect.signature(st.plotly_chart).parameters


def show(fig, key):
    """Render a Plotly figure honouring our template, compatible with old and new Streamlit APIs."""
    kw = dict(width="stretch") if _HAS_WIDTH else dict(use_container_width=True)
    st.plotly_chart(fig, theme=None, key=key, **kw)


def show_df(df, **kwargs):
    try:
        st.dataframe(df, width="stretch", **kwargs)
    except Exception:
        st.dataframe(df, use_container_width=True, **kwargs)


def human_format(value, decimals=0):
    try:
        return f"{value:,.{decimals}f}"
    except Exception:
        return str(value)


def fmt_t(x):
    """Compact tonnage: 1.23M, 456.7k."""
    try:
        x = float(x)
    except Exception:
        return str(x)
    for lim, suf in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
        if abs(x) >= lim:
            return f"{x / lim:,.2f}{suf}"
    return f"{x:,.0f}"


def pct(x):
    return int(round(float(x) * 100))


def cagr_pct(series):
    s = pd.Series(series).dropna()
    if len(s) < 2 or s.iloc[0] <= 0 or s.iloc[-1] <= 0:
        return 0.0
    n = float(s.index[-1] - s.index[0])
    return ((s.iloc[-1] / s.iloc[0]) ** (1 / n) - 1) * 100 if n > 0 else 0.0


def change_pct(series):
    s = pd.Series(series).dropna()
    if len(s) < 2 or s.iloc[0] == 0:
        return 0.0
    return (s.iloc[-1] / s.iloc[0] - 1) * 100


def life_text(life):
    return "∞" if not np.isfinite(life) or life > 200 else f"{life:,.1f} yr"


def sparkline(values, color):
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if len(v) < 2 or v.max() == v.min():
        return ""
    w, h = 96, 30
    xs = np.linspace(2, w - 2, len(v))
    ys = h - 3 - (v - v.min()) / (v.max() - v.min()) * (h - 6)
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    return (f"<svg viewBox='0 0 {w} {h}' class='spark' preserveAspectRatio='none'><polyline points='{pts}' fill='none' "
            f"stroke='{color}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>")


def kpi_card(label, value, delta=None, tone="neutral", spark=None, color=None):
    chip = f"<span class='chip {tone}'>{delta}</span>" if delta else "<span></span>"
    sp = sparkline(spark, color or C["blue"]) if spark is not None else ""
    st.markdown(
        f"<div class='kpi' style='--kc:{color or C['blue']}'><div class='kpi-label'>{label}</div>"
        f"<div class='kpi-value'>{value}</div><div class='kpi-row'>{chip}{sp}</div></div>",
        unsafe_allow_html=True,
    )


def add_section_intro(title, text):
    st.markdown(f"<div class='section-panel'><div class='section-title'>{title}</div><div class='section-text'>{text}</div></div>", unsafe_allow_html=True)


def validate_columns(df, required, table_name):
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"La tabla '{table_name}' no contiene las columnas requeridas: {', '.join(sorted(missing))}.")


def min_max_norm(series):
    s = pd.Series(series, dtype=float)
    if s.max() == s.min():
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - s.min()) / (s.max() - s.min())


def risk_score(x, good, bad):
    """Linear risk 0 (at `good`) .. 1 (at `bad`); works for both directions."""
    return float(np.clip((x - good) / (bad - good), 0.0, 1.0))


# =========================================================
# WASTE-TYPE CLASSIFICATION AND DATA LOADING
# =========================================================
ORG_KEYS = ("organ", "biorres", "aliment", "food", "poda")
REC_KEYS = ("plast", "papel", "paper", "carton", "vidri", "glass", "metal", "textil", "caucho", "aluminio")


def _norm_text(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()


def classify_type(tipo):
    t = _norm_text(tipo)
    if any(k in t for k in ORG_KEYS):
        return "org"
    if any(k in t for k in REC_KEYS):
        return "rec"
    return "oth"


@st.cache_data(show_spinner=False)
def load_data(source):
    if isinstance(source, (str, Path)):
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(f"No se encontró el archivo por defecto '{source.name}' en el directorio de la app.")

    pop = pd.read_excel(source, sheet_name="Poblacion_2050", index_col=0)
    waste = pd.read_excel(source, sheet_name="ResiduosTotales_t_anio", index_col=0)
    types = pd.read_excel(source, sheet_name="Residuos_5Tipos_largo")

    def clean(df):
        df = df.apply(pd.to_numeric, errors="coerce")
        df.index = pd.to_numeric(df.index, errors="coerce").round().astype("Int64")
        df = df[~df.index.isna()].copy()
        df.index = df.index.astype(int)
        df.columns = df.columns.astype(str).str.strip()
        return df.sort_index()

    pop, waste = clean(pop), clean(waste)

    validate_columns(types, EXPECTED_LONG_COLS, "Residuos_5Tipos_largo")
    types["Ciudad"] = types["Ciudad"].astype(str).str.strip()
    types["Tipo"] = types["Tipo"].astype(str).str.strip()
    types["Año"] = pd.to_numeric(types["Año"], errors="coerce").astype("Int64")
    types["Toneladas_anio"] = pd.to_numeric(types["Toneladas_anio"], errors="coerce")
    types = types.dropna(subset=["Año", "Toneladas_anio"]).copy()
    types = types[types["Toneladas_anio"] >= 0]
    types["Año"] = types["Año"].astype(int)
    types["Cat"] = types["Tipo"].map(classify_type)

    g = (types.groupby(["Ciudad", "Año", "Cat"])["Toneladas_anio"].sum().unstack("Cat")
         .reindex(columns=["org", "rec", "oth"]).fillna(0.0))
    shares = g.div(g.sum(axis=1).replace(0, np.nan), axis=0).dropna()
    return pop, waste, types, shares


def shares_for(city, years, shares_df):
    default = pd.DataFrame({"org": 0.5, "rec": 0.25, "oth": 0.25}, index=years)
    if city not in shares_df.index.get_level_values(0):
        return default
    s = shares_df.loc[city].reindex(years)
    s = s.interpolate(method="index", limit_direction="both")
    return s.fillna(default)


def city_inputs(city, df_pop, df_waste, shares_df):
    years = df_waste.index.intersection(df_pop.index).to_numpy()
    waste = np.nan_to_num(df_waste.loc[years, city].to_numpy(float))
    pop = np.nan_to_num(df_pop.loc[years, city].to_numpy(float))
    s = shares_for(city, years, shares_df)
    return years, waste, pop, s["org"].to_numpy(float), s["rec"].to_numpy(float)


# =========================================================
# DYNAMIC MASS-BALANCE MODEL (pure numpy, vectorised over years)
# =========================================================
def ramp_curve(years, start, target, kind):
    """Policy adoption r(t): 0 at `start`, 1 at `target`; linear or logistic (S-curve)."""
    t = np.asarray(years, dtype=float)
    if target <= start:
        return np.ones_like(t)
    x = np.clip((t - start) / (target - start), 0.0, 1.0)
    if str(kind).startswith("Linear"):
        return x
    k = 8.0
    s = 1 / (1 + np.exp(-k * (x - 0.5)))
    s0, s1 = 1 / (1 + np.exp(k * 0.5)), 1 / (1 + np.exp(-k * 0.5))
    return (s - s0) / (s1 - s0)


def _close_gap(x, cap, k):
    """Move x toward its ceiling by a fraction k of the remaining gap (diminishing returns, never exceeds cap)."""
    return x + max(cap - x, 0.0) * min(1.0, max(k, 0.0))


def effective_levers(lv, a):
    edu, frm = lv["education"], lv["formalization"]
    return dict(
        source=_close_gap(lv["source_reduction"], CAPS["source"], a["el_src_edu"] * edu),
        collection=min(lv["collection"], CAPS["collection"]),
        recycling=_close_gap(lv["recycling"], CAPS["recycling"], a["el_rec_edu"] * edu + a["el_rec_form"] * frm),
        composting=_close_gap(lv["composting"], CAPS["composting"], a["el_com_edu"] * edu),
    )


def simulate_arrays(years, waste, s_org, s_rec, target, a, base=None):
    """Year-by-year mass balance. `waste` is the baseline (no-policy) generation trajectory."""
    base = base or BASE_LEVERS
    years = np.asarray(years, dtype=float)
    r = ramp_curve(years, years[0], a["target_year"], a["ramp"])
    e_t, e_b = effective_levers(target, a), effective_levers(base, a)
    lev = {k: e_b[k] + (e_t[k] - e_b[k]) * r for k in e_t}

    gen = waste * (1 - lev["source"])
    col = gen * lev["collection"]
    unc = gen - col
    rec_in = col * s_rec * lev["recycling"]
    com_in = col * s_org * lev["composting"]
    rec_rej = rec_in * a["recycling_reject"]
    com_rej = com_in * a["composting_reject"]
    recycled, composted = rec_in - rec_rej, com_in - com_rej
    diverted = recycled + composted
    landfilled = col - diverted                      # includes the rejects of both treatment streams
    safe_gen = np.where(gen > 0, gen, np.nan)
    return dict(
        ramp=r, lev=lev, gen=gen, col=col, unc=unc, rec_in=rec_in, com_in=com_in, rejects=rec_rej + com_rej,
        recycled=recycled, composted=composted, diverted=diverted, landfilled=landfilled, cum=np.cumsum(landfilled),
        div_rate=np.nan_to_num(diverted / safe_gen), col_rate=np.nan_to_num(col / safe_gen),
    )


def landfill_life(years, landfilled, capacity):
    """Years from the first model year until cumulative disposal reaches the remaining capacity."""
    years = np.asarray(years, dtype=float)
    landfilled = np.asarray(landfilled, dtype=float)
    cum = np.cumsum(landfilled)
    hit = np.nonzero(cum >= capacity)[0]
    if hit.size:
        i = hit[0]
        prev = cum[i - 1] if i > 0 else 0.0
        frac = (capacity - prev) / landfilled[i] if landfilled[i] > 0 else 0.0
        return float(years[i] - years[0] + frac)
    last = landfilled[-1]
    if last <= 0:
        return float("inf")
    return float(years[-1] - years[0] + 1 + (capacity - cum[-1]) / last)  # extrapolate at the final-year rate


def results_df(years, sim, pop, waste):
    idx = pd.Index(np.asarray(years).astype(int), name="Year")
    df = pd.DataFrame(
        {
            "Population": pop, "Baseline_t": waste, "Generated_t": sim["gen"], "Collected_t": sim["col"],
            "Uncollected_t": sim["unc"], "Recycling_input_t": sim["rec_in"], "Composting_input_t": sim["com_in"],
            "Recycled_t": sim["recycled"], "Composted_t": sim["composted"], "Rejects_t": sim["rejects"],
            "Diverted_t": sim["diverted"], "Landfilled_t": sim["landfilled"], "Cum_landfilled_t": sim["cum"],
            "Diversion_rate": sim["div_rate"], "Collection_rate": sim["col_rate"], "Ramp": sim["ramp"],
            "Eff_source": sim["lev"]["source"], "Eff_collection": sim["lev"]["collection"],
            "Eff_recycling": sim["lev"]["recycling"], "Eff_composting": sim["lev"]["composting"],
        },
        index=idx,
    )
    p = df["Population"].where(df["Population"] > 0)
    df["kg_person_day"] = df["Generated_t"] * 1000 / p / 365
    df["kg_person_day_baseline"] = df["Baseline_t"] * 1000 / p / 365
    return df


@st.cache_data(show_spinner=False)
def run_all(df_pop, df_waste, shares_df, cities, target, assum, capacities):
    out = {}
    for c in cities:
        years, waste, pop, s_org, s_rec = city_inputs(c, df_pop, df_waste, shares_df)
        out[c] = results_df(years, simulate_arrays(years, waste, s_org, s_rec, target, assum), pop, waste)
    return out


def run_city(inputs, target, assum):
    years, waste, pop, s_org, s_rec = inputs
    return results_df(years, simulate_arrays(years, waste, s_org, s_rec, target, assum), pop, waste)


def metric_value(sim, years, capacity, metric):
    if metric.startswith("Cumulative"):
        return float(sim["cum"][-1] / 1e6)
    return float(min(landfill_life(years, sim["landfilled"], capacity), 100.0))


TORNADO_PARAMS = [
    ("Source reduction", "lever", "source_reduction", 0.35), ("Collection coverage", "lever", "collection", 0.99),
    ("Recycling capture", "lever", "recycling", 0.95), ("Composting capture", "lever", "composting", 0.90),
    ("Education bonus", "lever", "education", 0.15), ("Formalization bonus", "lever", "formalization", 0.15),
    ("Recycling reject rate", "assum", "recycling_reject", 0.60), ("Composting reject rate", "assum", "composting_reject", 0.60),
]


def tornado_table(inputs, target, assum, capacity, metric, pp):
    years, waste, _pop, s_org, s_rec = inputs

    def run(tgt, a, w=waste):
        return metric_value(simulate_arrays(years, w, s_org, s_rec, tgt, a), years, capacity, metric)

    base = run(target, assum)
    rows = []
    for label, kind, key, hi in TORNADO_PARAMS:
        vals = []
        for sign in (-1, 1):
            tgt, a = dict(target), dict(assum)
            d = tgt if kind == "lever" else a
            d[key] = float(np.clip(d[key] + sign * pp / 100, 0.0, hi))
            vals.append(run(tgt, a) - base)
        rows.append((label, vals[0], vals[1]))
    tn = (years - years[0]) / max(years[-1] - years[0], 1)
    w_vals = [run(target, assum, waste * (1 + s * 0.10 * tn)) - base for s in (-1, 1)]
    rows.append(("Baseline waste (±10% by horizon)", w_vals[0], w_vals[1]))
    df = pd.DataFrame(rows, columns=["Parameter", "Low", "High"])
    df["Swing"] = (df["High"] - df["Low"]).abs()
    return base, df.sort_values("Swing")


@st.cache_data(show_spinner=False)
def mc_run(years, waste, s_org, s_rec, target, assum, capacity, n, sigma, seed=7):
    rng = np.random.default_rng(seed)
    tn = (years - years[0]) / max(years[-1] - years[0], 1)
    caps_map = dict(source_reduction=CAPS["source"], recycling=CAPS["recycling"], composting=CAPS["composting"])
    landf = np.empty((n, len(years)))
    life = np.empty(n)
    for i in range(n):
        tgt = dict(target)
        for k, hi in caps_map.items():
            tgt[k] = float(np.clip(target[k] * rng.normal(1, sigma), 0.0, hi))
        tgt["collection"] = float(np.clip(target["collection"] * rng.normal(1, sigma / 3), 0.5, CAPS["collection"]))
        a = dict(assum)
        a["recycling_reject"] = float(np.clip(assum["recycling_reject"] * rng.normal(1, sigma), 0.0, 0.6))
        a["composting_reject"] = float(np.clip(assum["composting_reject"] * rng.normal(1, sigma), 0.0, 0.6))
        w = waste * (1 + rng.normal(0, sigma / 2) * tn)
        sim = simulate_arrays(years, w, s_org, s_rec, tgt, a)
        landf[i] = sim["landfilled"]
        life[i] = min(landfill_life(years, sim["landfilled"], capacity), 100.0)
    cum = np.cumsum(landf, axis=1)
    return dict(p10=np.percentile(cum, 10, axis=0), p50=np.percentile(cum, 50, axis=0), p90=np.percentile(cum, 90, axis=0), life=life)


# =========================================================
# ALERTS AND PRIORITY INDEX
# =========================================================
def alert_messages(row, life, cagr, per_capita):
    alerts = []
    if life < 5:
        alerts.append(("High", f"Estimated landfill life is {life_text(life)} (<5 years) under the selected policy trajectory."))
    elif life < 10:
        alerts.append(("Medium", f"Estimated landfill life is {life_text(life)} (<10 years); medium-term disposal stress is likely."))

    if row["Collection_rate"] < 0.85:
        alerts.append(("High", "Collection coverage is below 85%, implying leakage or unmanaged waste risks."))
    elif row["Collection_rate"] < 0.95:
        alerts.append(("Medium", "Collection coverage is improving but still below high-service thresholds (95%)."))

    if row["Diversion_rate"] < 0.20:
        alerts.append(("High", f"Diversion rate is {row['Diversion_rate']:.0%} (<20%), indicating strong dependence on final disposal."))
    elif row["Diversion_rate"] < 0.35:
        alerts.append(("Medium", f"Diversion rate is {row['Diversion_rate']:.0%}; stronger organics and recycling interventions may be needed."))

    if cagr > 1.5:
        alerts.append(("High", f"Waste generation grows {cagr:.2f}%/yr (CAGR), a rate that strains collection and disposal systems."))
    elif cagr > 0.75:
        alerts.append(("Medium", f"Waste generation grows {cagr:.2f}%/yr (CAGR); capacity planning should anticipate it."))

    if per_capita > 1.1:
        alerts.append(("Medium", "Per-capita waste generation is relatively high and may justify prevention measures."))
    if not alerts:
        alerts.append(("Low", "No immediate structural alert is triggered under the selected assumptions."))
    return alerts


def priority_table(results, caps, year_range, weights):
    y0, y1 = year_range
    rows = []
    for city, df in results.items():
        if y1 not in df.index:
            continue
        r = df.loc[y1]
        life = landfill_life(df.index.to_numpy(), df["Landfilled_t"].to_numpy(), caps[city])
        growth = cagr_pct(df["Generated_t"].loc[y0:y1])
        comp = dict(
            per_capita=risk_score(r["kg_person_day"], *RISK_REFS["per_capita"]),
            growth=risk_score(growth, *RISK_REFS["growth"]),
            landfill_life=risk_score(min(life, 100.0), *RISK_REFS["landfill_life"]),
            collection_gap=risk_score(1 - r["Collection_rate"], *RISK_REFS["collection_gap"]),
            diversion=risk_score(r["Diversion_rate"], *RISK_REFS["diversion"]),
        )
        wsum = max(sum(weights.values()), 1e-9)
        score = 100 * sum(weights[k] * comp[k] for k in comp) / wsum
        rows.append(dict(City=city, Priority_score=score, Waste_tons_year=r["Generated_t"], kg_person_day=r["kg_person_day"],
                         Growth_cagr_pct=growth, Diversion_rate=r["Diversion_rate"], Landfill_life_years=min(life, 100.0),
                         **{f"s_{k}": v for k, v in comp.items()}))
    df = pd.DataFrame(rows)
    df["Priority_level"] = pd.cut(df["Priority_score"].clip(0, 100), bins=[-0.01, 33, 66, 100], labels=["Low", "Medium", "High"])
    return df.sort_values("Priority_score", ascending=False).reset_index(drop=True)


def peer_group(df_pop, city, year):
    p = float(df_pop.loc[year, city])
    return sorted(c for c in df_pop.columns if 0.5 * p <= float(df_pop.loc[year, c]) <= 1.5 * p)


# =========================================================
# FIGURE BUILDERS
# =========================================================
def gauge(value, title, vmin, vmax, steps, suffix="", fmt=".1f"):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=float(min(max(value, vmin), vmax)),
        number=dict(suffix=suffix, valueformat=fmt, font=dict(size=30)),
        title=dict(text=title, font=dict(size=14)),
        gauge=dict(axis=dict(range=[vmin, vmax]), bar=dict(color=C["slate"], thickness=0.28), bgcolor="white", borderwidth=0,
                   steps=[dict(range=[a, b], color=col) for a, b, col in steps]),
    ))
    fig.update_layout(height=215, margin=dict(l=25, r=25, t=55, b=5))
    return fig


def sankey_fig(row):
    labels = ["Generated", "Collected", "Unmanaged", "Recycling stream", "Composting stream", "Landfill", "Recovered materials", "Treated organics"]
    colors = [C["slate"], C["blue"], C["red"], C["gold"], C["teal"], C["grey"], C["green"], C["green"]]
    direct = max(row["Collected_t"] - row["Recycling_input_t"] - row["Composting_input_t"], 0.0)
    flows = [
        (0, 1, row["Collected_t"]), (0, 2, row["Uncollected_t"]),
        (1, 3, row["Recycling_input_t"]), (1, 4, row["Composting_input_t"]), (1, 5, direct),
        (3, 6, row["Recycled_t"]), (3, 5, row["Recycling_input_t"] - row["Recycled_t"]),
        (4, 7, row["Composted_t"]), (4, 5, row["Composting_input_t"] - row["Composted_t"]),
    ]
    flows = [(s, t, max(float(v), 0.0)) for s, t, v in flows]

    def rgba(hex_, a=0.35):
        h = hex_.lstrip("#")
        return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, color=colors, pad=22, thickness=18, line=dict(color="white", width=0.5),
                  hovertemplate="%{label}: %{value:,.0f} t/yr<extra></extra>"),
        link=dict(source=[f[0] for f in flows], target=[f[1] for f in flows], value=[f[2] for f in flows],
                  color=[rgba(colors[f[1]]) for f in flows], hovertemplate="%{source.label} → %{target.label}<br>%{value:,.0f} t/yr<extra></extra>"),
    ))
    fig.update_layout(title="Material flow balance (t/year)", height=420, margin=dict(l=10, r=10, t=60, b=10))
    return fig


def landfill_fill_fig(res, capacity, life):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=res.index, y=res["Cum_landfilled_t"], name="Cumulative landfilled", mode="lines", line=dict(color=C["slate"], width=3),
                             fill="tozeroy", fillcolor="rgba(20,50,74,0.10)"))
    fig.add_hline(y=capacity, line=dict(color=C["red"], dash="dash"), annotation_text=f"Remaining capacity {fmt_t(capacity)} t", annotation_position="top left")
    if np.isfinite(life) and life <= (res.index[-1] - res.index[0] + 1):
        fig.add_vline(x=res.index[0] + life, line=dict(color=C["red"], dash="dot"),
                      annotation_text=f"Exhausted ≈ {res.index[0] + life:.1f}", annotation_position="bottom right")
    fig.update_layout(title="Landfill filling trajectory", yaxis_title="tons", yaxis_tickformat=",.2s", hovermode="x unified", height=380)
    return fig


# =========================================================
# SIDEBAR AND DATA
# =========================================================
st.sidebar.markdown("### ⚙️ Simulation control")
uploaded_file = st.sidebar.file_uploader("Upload simulation Excel (.xlsx)", type=["xlsx"])

try:
    if uploaded_file is not None:
        df_pop, df_waste, df_types, shares_df = load_data(uploaded_file)
        data_source_label = f"Custom file: {uploaded_file.name}"
    else:
        df_pop, df_waste, df_types, shares_df = load_data(DATA_FILE)
        data_source_label = f"Default file: {DATA_FILE}"
except Exception as exc:
    st.error(f"Error loading data: {exc}")
    st.stop()

cities_available = sorted(set(df_pop.columns) & set(df_waste.columns) & set(city_coords.keys()))
if not cities_available:
    st.error("No matching cities were found between the Excel file and the configured city list.")
    st.stop()

common_years = df_pop.index.intersection(df_waste.index)
if len(common_years) < 3:
    st.error("The population and waste sheets must share at least 3 years.")
    st.stop()
min_year, max_year = int(common_years.min()), int(common_years.max())

default_city = "Medellín" if "Medellín" in cities_available else cities_available[0]
selected_city = st.sidebar.selectbox("City", cities_available, index=cities_available.index(default_city))
selected_scenario = st.sidebar.selectbox("Scenario preset", list(SCENARIO_OPTIONS.keys()), index=0)
year_range = st.sidebar.slider("Year window", min_year, max_year, (min_year, max_year))
comparison_cities = st.sidebar.multiselect("Benchmark against", options=cities_available, default=[selected_city])

preset = SCENARIO_OPTIONS[selected_scenario]
with st.sidebar.expander("🎛️ Policy levers (target values)", expanded=False):
    k = selected_scenario
    levers = dict(
        source_reduction=st.slider("Source reduction (%)", 0, 35, pct(preset["source_reduction"]), 1, key=f"sr_{k}") / 100,
        collection=st.slider("Collection coverage (%)", 50, 99, pct(preset["collection"]), 1, key=f"co_{k}") / 100,
        recycling=st.slider("Recycling capture of recoverables (%)", 0, 95, pct(preset["recycling"]), 1, key=f"re_{k}") / 100,
        composting=st.slider("Composting capture of organics (%)", 0, 90, pct(preset["composting"]), 1, key=f"cm_{k}") / 100,
        education=st.slider("Education & behaviour bonus (%)", 0, 15, pct(preset["education"]), 1, key=f"ed_{k}") / 100,
        formalization=st.slider("Recycler formalization bonus (%)", 0, 15, pct(preset["formalization"]), 1, key=f"fo_{k}") / 100,
    )
    target_year = st.slider("Year targets are reached", min_year + 1, max_year, int(min(max(2035, min_year + 1), max_year)), 1, key="ty")
    ramp_kind = st.radio("Adoption curve", ["Logistic (S-curve)", "Linear"], horizontal=True)

with st.sidebar.expander("🧪 Advanced assumptions", expanded=False):
    rec_reject = st.slider("Recycling rejects (% of input)", 0, 40, 15, 1) / 100
    com_reject = st.slider("Composting rejects (% of input)", 0, 40, 10, 1) / 100
    capacity = st.number_input(
        f"Remaining landfill capacity at {min_year} — {selected_city} (t)", min_value=100_000,
        value=int(LANDFILL_CAPACITY_T.get(selected_city, DEFAULT_CAPACITY_T)), step=100_000, key=f"cap_{selected_city}",
    )

show_raw_data = st.sidebar.toggle("Show raw filtered data", value=False)
show_method_note = st.sidebar.toggle("Show methodology note", value=False)
st.sidebar.caption(data_source_label)

assum = dict(recycling_reject=rec_reject, composting_reject=com_reject, ramp=ramp_kind, target_year=int(target_year), **ELASTICITIES)
caps = {c: float(LANDFILL_CAPACITY_T.get(c, DEFAULT_CAPACITY_T)) for c in cities_available}
caps[selected_city] = float(capacity)

# =========================================================
# CORE SIMULATION (single source of truth for every tab)
# =========================================================
results = run_all(df_pop, df_waste, shares_df, tuple(cities_available), levers, assum, caps)
res = results[selected_city]
y0, y1 = year_range
res_w = res.loc[y0:y1]
row = res.loc[y1]
inputs = city_inputs(selected_city, df_pop, df_waste, shares_df)
life = landfill_life(res.index.to_numpy(), res["Landfilled_t"].to_numpy(), capacity)
exhaust_year = res.index[0] + life if np.isfinite(life) else None
gen_cagr = cagr_pct(res_w["Generated_t"])
selected_shares = shares_for(selected_city, res.index.to_numpy(), shares_df)
latest_shares = selected_shares.loc[y1]
avoided_pct = (1 - row["Generated_t"] / row["Baseline_t"]) * 100 if row["Baseline_t"] > 0 else 0.0

# =========================================================
# HEADER
# =========================================================
st.markdown(
    f"<div class='hero'><div class='hero-kicker'>Academic decision-support platform · v2 dynamic model</div>"
    f"<div class='hero-title'>Urban Waste Simulation and Circularity Observatory</div>"
    f"<div class='hero-subtitle'>Institutional-academic dashboard for the exploration of population growth, waste generation, composition patterns, "
    f"territorial pressure and scenario-based circularity trajectories across Colombian cities, driven by a year-by-year mass-balance model.</div>"
    f"<span class='badge'>📍 {selected_city}</span><span class='badge'>🎚️ {selected_scenario}</span>"
    f"<span class='badge'>🗓️ {y0}–{y1}</span><span class='badge'>🎯 Targets reached by {assum['target_year']}</span>"
    f"<span class='badge'>📈 {ramp_kind}</span>"
    f"<div class='hero-meta'>Developed by <b>Danny Ibarra Vega, Ph.D.</b> · Universidad de Antioquia · System Dynamics, waste systems and circular economy</div></div>",
    unsafe_allow_html=True,
)

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    kpi_card(f"Population ({y1})", fmt_t(row["Population"]), f"{change_pct(res_w['Population']):+.1f}% in window", "neutral", res_w["Population"], C["blue"])
with k2:
    d = change_pct(res_w["Generated_t"])
    kpi_card(f"Waste generated ({y1})", f"{fmt_t(row['Generated_t'])} t/yr", f"{d:+.1f}% in window", "bad" if d > 0 else "good", res_w["Generated_t"], C["green"])
with k3:
    d = change_pct(res_w["kg_person_day"])
    kpi_card("Per-capita waste", f"{row['kg_person_day']:.2f} kg/day", f"{d:+.1f}% in window", "bad" if d > 0 else "good", res_w["kg_person_day"], C["gold"])
with k4:
    dd = (row["Diversion_rate"] - res_w["Diversion_rate"].iloc[0]) * 100
    kpi_card("Diversion rate", f"{row['Diversion_rate']:.1%}", f"{dd:+.1f} pp in window", "good" if dd > 0 else "neutral", res_w["Diversion_rate"], C["teal"])
with k5:
    tone = "bad" if life < 10 else ("neutral" if life < 20 else "good")
    kpi_card("Landfill life", life_text(life), f"exhausted ≈ {exhaust_year:.0f}" if exhaust_year and exhaust_year < 2200 else "no exhaustion", tone, 100 - res["Cum_landfilled_t"] / capacity * 100, C["red"])

st.write("")
sc = SCENARIO_OPTIONS[selected_scenario]
st.caption(
    f"Scenario **{sc['label']}** · target levers: source reduction {pct(levers['source_reduction'])}% · collection {pct(levers['collection'])}% · "
    f"recycling {pct(levers['recycling'])}% · composting {pct(levers['composting'])}% · education {pct(levers['education'])}% · formalization {pct(levers['formalization'])}%."
)
if show_method_note:
    st.info("Baseline population and waste are read from the workbook and treated as the no-policy trajectory. Policy levers ramp from the current system to the "
            "target values (logistic or linear); waste is then routed through a year-by-year mass balance with collection, recycling, composting, process rejects and landfill filling.")

top_type = None
mix = df_types[(df_types["Ciudad"] == selected_city) & (df_types["Año"] == y1)]
if not mix.empty:
    tr = mix.sort_values("Toneladas_anio", ascending=False).iloc[0]
    top_type = (tr["Tipo"], 100 * tr["Toneladas_anio"] / mix["Toneladas_anio"].sum())

bullets = [
    f"In <b>{y1}</b>, <b>{selected_city}</b> generates <b>{fmt_t(row['Generated_t'])} t/yr</b> ({row['kg_person_day']:.2f} kg/person/day), "
    f"<b>{avoided_pct:.1f}%</b> below the no-policy baseline; generation grows <b>{gen_cagr:.2f}%/yr</b> across the window.",
    f"The system diverts <b>{row['Diversion_rate']:.1%}</b> of generated waste and collects <b>{row['Collection_rate']:.0%}</b>; "
    f"<b>{fmt_t(row['Uncollected_t'])} t/yr</b> remain unmanaged.",
    (f"Landfill capacity lasts <b>{life_text(life)}</b> (≈ {exhaust_year:.0f}) under this trajectory." if exhaust_year and exhaust_year < 2200
     else "Landfill capacity is not exhausted under this trajectory."),
]
if top_type:
    bullets.append(f"The dominant fraction is <b>{top_type[0]}</b>, about <b>{top_type[1]:.1f}%</b> of the {y1} waste mix.")

left, right = st.columns([1.15, 1])
with left:
    st.markdown("#### Executive insights")
    st.markdown("<div class='insight-box'><ul>" + "".join(f"<li>{b}</li>" for b in bullets) + "</ul></div>", unsafe_allow_html=True)
with right:
    st.markdown("#### Analytical reading guide")
    st.markdown(
        f"<div class='guide-box'><ul><li><b>Main question:</b> how does waste evolve and where does it end up under the selected scenario?</li>"
        f"<li><b>Focus city:</b> {selected_city} · <b>Window:</b> {y0}–{y1}</li>"
        f"<li><b>Levers</b> live in the sidebar and drive every tab consistently.</li>"
        f"<li><b>Recommended use:</b> compare scenarios, test sensitivity and benchmark peers.</li></ul></div>",
        unsafe_allow_html=True,
    )

st.write("")
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(
    ["📈 Population & Waste", "♻️ Composition", "🗺️ Geographic View", "🎞️ Dynamic Simulation", "🧭 Policy Simulator",
     "🚨 Alerts & Priorities", "🏙️ Benchmarking", "📐 Methodology & Equations", "ℹ️ About & Data"]
)

# ---------------------------------------------------------
# TAB 1 — POPULATION & WASTE
# ---------------------------------------------------------
with tab1:
    st.subheader(f"Population and Waste Trends — {selected_city}")
    add_section_intro("What this tab answers", "How population, total waste and per-capita pressure evolve, and how much waste the scenario avoids against the baseline.")
    x = res_w.index

    # Tab-specific axis styling: generous margins + readable ticks in two-column layouts.
    x_num = np.asarray(x, dtype=float)
    x_span = max(float(x_num[-1] - x_num[0]), 1.0)
    x_dtick = max(1, int(round(x_span / 5)))

    def style_t1_axes(fig, y_values, y_title, y_tickformat=None, zero_floor=False):
        vals = np.asarray(y_values, dtype=float)
        vals = vals[np.isfinite(vals)]
        if vals.size:
            ymin, ymax = float(vals.min()), float(vals.max())
            span = ymax - ymin
            pad = max(span * 0.10, abs(ymax) * 0.02, 1e-9)
            lower = 0.0 if zero_floor else max(0.0, ymin - pad)
            upper = ymax + pad
            fig.update_yaxes(range=[lower, upper])

        fig.update_xaxes(
            range=[float(x_num.min()) - 0.55, float(x_num.max()) + 0.55],
            tickmode="linear", tick0=int(x_num.min()), dtick=x_dtick,
            tickformat="d", automargin=True, title_standoff=10,
            showline=True, mirror=False,
        )
        fig.update_yaxes(
            title_text=y_title, tickformat=y_tickformat, automargin=True,
            title_standoff=14, ticklabelposition="outside",
            showline=True, mirror=False, nticks=6,
        )
        fig.update_layout(
            height=390, hovermode="x unified",
            margin=dict(l=82, r=24, t=78, b=58),
            title=dict(font=dict(size=15), y=0.96),
            legend=dict(y=1.01, x=0, orientation="h"),
        )
        return fig

    c1, c2 = st.columns(2)
    with c1:
        f = go.Figure()
        f.add_trace(go.Scatter(x=x, y=res_w["Baseline_t"], name="Baseline (no policy)", line=dict(color=C["grey"], dash="dash", width=2)))
        f.add_trace(go.Scatter(x=x, y=res_w["Generated_t"], name=f"Scenario: {selected_scenario}", line=dict(color=C["green"], width=3),
                               fill="tonexty", fillcolor="rgba(47,125,107,0.16)"))
        f.update_layout(title="Waste generation — baseline vs scenario")
        style_t1_axes(
            f,
            np.r_[res_w["Baseline_t"].to_numpy(), res_w["Generated_t"].to_numpy()],
            "Waste (t/year)", y_tickformat="~s", zero_floor=True,
        )
        show(f, "t1_waste")

    with c2:
        f = go.Figure(go.Scatter(x=x, y=res_w["Population"], name="Population", line=dict(color=C["blue"], width=3),
                                 fill="tozeroy", fillcolor="rgba(13,92,145,0.10)"))
        f.update_layout(title="Population projection", showlegend=False)
        style_t1_axes(f, res_w["Population"].to_numpy(), "Population (inhabitants)", y_tickformat="~s", zero_floor=False)
        show(f, "t1_pop")

    c3, c4 = st.columns(2)
    with c3:
        f = go.Figure()
        f.add_trace(go.Scatter(x=x, y=res_w["kg_person_day_baseline"], name="Baseline", line=dict(color=C["grey"], dash="dash", width=2)))
        f.add_trace(go.Scatter(x=x, y=res_w["kg_person_day"], name="Scenario", line=dict(color=C["gold"], width=3)))
        f.add_hline(y=1.1, line=dict(color=C["red"], dash="dot"), annotation_text="High threshold (1.1)", annotation_position="top left")
        f.update_layout(title="Per-capita waste generation")
        pc_vals = np.r_[res_w["kg_person_day_baseline"].to_numpy(), res_w["kg_person_day"].to_numpy(), [1.1]]
        style_t1_axes(f, pc_vals, "kg/person/day", y_tickformat=".2f", zero_floor=False)
        show(f, "t1_pc")

    with c4:
        pop_idx = 100 * res_w["Population"] / res_w["Population"].iloc[0]
        gen_idx = 100 * res_w["Generated_t"] / res_w["Generated_t"].iloc[0]
        base_idx = 100 * res_w["Baseline_t"] / res_w["Baseline_t"].iloc[0]
        f = go.Figure()
        f.add_trace(go.Scatter(x=x, y=pop_idx, name="Population", line=dict(color=C["blue"], width=3)))
        f.add_trace(go.Scatter(x=x, y=gen_idx, name="Waste (scenario)", line=dict(color=C["green"], width=3)))
        f.add_trace(go.Scatter(x=x, y=base_idx, name="Waste (baseline)", line=dict(color=C["grey"], dash="dash", width=2)))
        f.update_layout(title=f"Decoupling check — index ({x[0]} = 100)")
        style_t1_axes(f, np.r_[pop_idx.to_numpy(), gen_idx.to_numpy(), base_idx.to_numpy()], "Index", y_tickformat=".0f", zero_floor=False)
        show(f, "t1_idx")

# ---------------------------------------------------------
# TAB 2 — COMPOSITION
# ---------------------------------------------------------
with tab2:
    st.subheader(f"Waste Composition by Type — {selected_city}")
    add_section_intro("What this tab answers", "Which fractions dominate the waste mix and how their shares change across time.")
    df_city = df_types[(df_types["Ciudad"] == selected_city) & (df_types["Año"].between(y0, y1))].copy()

    if df_city.empty:
        st.info("No composition data is available for the selected city and year range.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric(f"Organics ({y1})", f"{latest_shares['org']:.1%}")
        m2.metric(f"Recoverables ({y1})", f"{latest_shares['rec']:.1%}")
        m3.metric(f"Other ({y1})", f"{latest_shares['oth']:.1%}")

        pal = px.colors.qualitative.Safe + px.colors.qualitative.Pastel
        tipos = sorted(df_city["Tipo"].unique())
        cmap = {t: pal[i % len(pal)] for i, t in enumerate(tipos)}

        left_c, right_c = st.columns(2)
        with left_c:
            view_mode = st.radio("Visualization mode", ["Time series", "Stacked share (%)", "Single year", "Share by type"], horizontal=True)
        with right_c:
            sort_mode = st.selectbox("Sort types", ["Alphabetical", "By value (desc)"])
        years_c = sorted(df_city["Año"].unique())

        if view_mode == "Time series":
            f = px.area(df_city, x="Año", y="Toneladas_anio", color="Tipo", color_discrete_map=cmap, title="Composition of waste by type over time", labels={"Toneladas_anio": "Tons/year", "Año": "Year", "Tipo": "Type"})
            f.update_layout(hovermode="x unified", height=440, yaxis_tickformat=",.2s")
        elif view_mode == "Stacked share (%)":
            f = px.area(df_city, x="Año", y="Toneladas_anio", color="Tipo", groupnorm="percent", color_discrete_map=cmap, title="Share of each waste type over time (%)", labels={"Toneladas_anio": "Share (%)", "Año": "Year", "Tipo": "Type"})
            f.update_layout(hovermode="x unified", height=440)
        elif view_mode == "Single year":
            ys = st.select_slider("Select year", options=years_c, value=years_c[0])
            d = df_city[df_city["Año"] == ys]
            d = d.sort_values("Toneladas_anio", ascending=False) if sort_mode == "By value (desc)" else d.sort_values("Tipo")
            f = px.bar(d, x="Tipo", y="Toneladas_anio", color="Tipo", color_discrete_map=cmap, text_auto=".2s", title=f"Composition by type — {ys}", labels={"Toneladas_anio": "Tons/year", "Tipo": "Type"})
            f.update_layout(showlegend=False, height=440)
        else:
            ys = st.select_slider("Select year for share", options=years_c, value=years_c[-1])
            d = df_city[df_city["Año"] == ys]
            d = d.sort_values("Toneladas_anio", ascending=False) if sort_mode == "By value (desc)" else d.sort_values("Tipo")
            f = px.pie(d, names="Tipo", values="Toneladas_anio", hole=0.5, color="Tipo", color_discrete_map=cmap, title=f"Waste share by type — {ys}")
            f.update_traces(textposition="inside", textinfo="percent+label")
            f.update_layout(height=440)
        show(f, "t2_main")

# ---------------------------------------------------------
# TAB 3 — GEOGRAPHY
# ---------------------------------------------------------
with tab3:
    st.subheader("Geographic Distribution of Waste and Population")
    add_section_intro("What this tab answers", "Where waste generation is concentrated and how territorial pressure differs among cities (scenario-adjusted).")
    col_a, col_b = st.columns(2)
    with col_a:
        view_year = st.slider("Select year", min_year, max_year, min_year, key="geo_year")
    with col_b:
        unit = st.radio("Units", ["tons/day", "tons/year"], horizontal=True)

    geo_df = pd.DataFrame(
        {
            "City": cities_available,
            "lat": [city_coords[c][0] for c in cities_available], "lon": [city_coords[c][1] for c in cities_available],
            "Landfill": [landfills.get(c, "N/A") for c in cities_available],
            "Population": [float(results[c].loc[view_year, "Population"]) for c in cities_available],
            "Waste_tons_year": [float(results[c].loc[view_year, "Generated_t"]) for c in cities_available],
            "Per_capita_kg_day": [float(results[c].loc[view_year, "kg_person_day"]) for c in cities_available],
        }
    )
    geo_df["Waste_tons_day"] = geo_df["Waste_tons_year"] / 365
    geo_df["Value"] = geo_df["Waste_tons_day"] if unit == "tons/day" else geo_df["Waste_tons_year"]

    gm, gb = st.columns([1.6, 1])
    with gm:
        fm = px.scatter_map(
            geo_df, lat="lat", lon="lon", color="Value", size="Value", size_max=38, hover_name="City",
            hover_data={"Landfill": True, "Population": ":,.0f", "Waste_tons_year": ":,.0f", "Waste_tons_day": ":,.1f", "Per_capita_kg_day": ":.2f", "lat": False, "lon": False, "Value": False},
            color_continuous_scale="Viridis", map_style="carto-positron", zoom=4.8, center={"lat": 6.5, "lon": -74.5}, title=f"Geographic distribution — {view_year}",
        )
        fm.update_layout(margin=dict(l=0, r=0, t=60, b=0), height=520, coloraxis_colorbar=dict(title=unit))
        show(fm, "t3_map")
    with gb:
        gs = geo_df.sort_values("Value")
        fb = px.bar(gs, x="Value", y="City", orientation="h", color="Value", color_continuous_scale="Viridis", title=f"Ranking ({unit})", labels={"Value": unit})
        fb.update_layout(height=520, coloraxis_showscale=False, xaxis_tickformat=",.2s")
        show(fb, "t3_bar")

# ---------------------------------------------------------
# TAB 4 — ANIMATION
# ---------------------------------------------------------
with tab4:
    st.subheader("Animated Waste Simulation (Cities + Aggregate Trend)")
    add_section_intro("What this tab answers", "How the spatial footprint and aggregate waste trajectory evolve together year by year. Bubble size and colour share one global scale, so growth is visible.")

    gen_wide = pd.DataFrame({c: results[c]["Generated_t"] for c in cities_available})
    base_wide = pd.DataFrame({c: results[c]["Baseline_t"] for c in cities_available})
    years = list(gen_wide.index)
    national, national_base = gen_wide.sum(axis=1), base_wide.sum(axis=1)
    vmin_g, vmax_g = float(gen_wide.to_numpy().min()), float(gen_wide.to_numpy().max())
    lats = [city_coords[c][0] for c in cities_available]
    lons = [city_coords[c][1] for c in cities_available]

    def map_trace(year, with_bar=True):
        vals = gen_wide.loc[year].to_numpy(float)
        sizes = (10 + 34 * np.sqrt(np.clip(vals / max(vmax_g, 1.0), 0, 1))).tolist()
        marker = dict(size=sizes, color=vals, colorscale="Viridis", cmin=vmin_g, cmax=vmax_g, opacity=0.88)
        if with_bar:
            marker.update(showscale=True, colorbar=dict(title="t/year", len=0.8))
        return go.Scattermap(lat=lats, lon=lons, mode="markers", marker=marker, text=cities_available,
                             hovertemplate="<b>%{text}</b><br>Waste: %{marker.color:,.0f} t/year<extra></extra>", showlegend=False)

    def line_trace(year):
        s = national.loc[:year]
        return go.Scatter(x=s.index, y=s.values, mode="lines+markers", line=dict(width=3, color=C["green"]), marker=dict(size=7, color=C["blue"]),
                          hovertemplate="Year %{x}<br>Total: %{y:,.0f} t/year<extra></extra>", showlegend=False)

    fa = make_subplots(rows=1, cols=2, specs=[[{"type": "map"}, {"type": "xy"}]], column_widths=[0.58, 0.42], horizontal_spacing=0.05,
                       subplot_titles=("Geographic projection", "Total waste trend (green = scenario, dashed = baseline)"))
    fa.add_trace(map_trace(years[0]), row=1, col=1)
    fa.add_trace(line_trace(years[0]), row=1, col=2)
    fa.add_trace(go.Scatter(x=years, y=national_base.values, mode="lines", line=dict(color=C["grey"], dash="dash", width=2), hoverinfo="skip", showlegend=False), row=1, col=2)
    fa.frames = [go.Frame(name=str(y), data=[map_trace(y), line_trace(y)], traces=[0, 1]) for y in years]
    fa.update_layout(
        map=dict(style="carto-positron", zoom=4.6, center=dict(lat=6.5, lon=-74.5)), height=560, margin=dict(l=10, r=10, t=70, b=70),
        xaxis_title="Year", yaxis_title="tons/year", yaxis_tickformat=",.2s",
        updatemenus=[dict(type="buttons", direction="left", x=0.02, y=-0.02, showactive=False, buttons=[
            dict(label="▶ Play", method="animate", args=[None, dict(frame=dict(duration=650, redraw=True), fromcurrent=True, transition=dict(duration=200))]),
            dict(label="⏸ Pause", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])])],
        sliders=[dict(active=0, x=0.18, y=-0.02, len=0.78, currentvalue=dict(prefix="Year: ", font=dict(size=15)),
                      steps=[dict(label=str(y), method="animate", args=[[str(y)], dict(mode="immediate", frame=dict(duration=0, redraw=True))]) for y in years])],
    )
    fa.update_xaxes(row=1, col=2, range=[years[0], years[-1]], tickformat="d")
    fa.update_yaxes(row=1, col=2, range=[0, float(max(national_base.max(), national.max())) * 1.05])
    show(fa, "t4_anim")

# ---------------------------------------------------------
# TAB 5 — POLICY SIMULATOR
# ---------------------------------------------------------
with tab5:
    st.subheader("Policy Simulator for Municipal Decision-Making")
    add_section_intro("What this tab answers", "What happens to flows, landfill life and diversion if the city changes collection, source reduction, recycling or composting — "
                      "including how robust the answer is. Edit the levers in the sidebar (🎛️ Policy levers).")
    sub1, sub2, sub3 = st.tabs(["Flows & KPIs", "Scenario comparison", "Sensitivity & uncertainty"])

    with sub1:
        r1, r2, r3, r4, r5, r6 = st.columns(6)
        r1.metric("Generated", f"{fmt_t(row['Generated_t'])} t/y", f"{-avoided_pct:.1f}% vs baseline", delta_color="inverse")
        r2.metric("Collected", f"{fmt_t(row['Collected_t'])} t/y")
        r3.metric("Unmanaged", f"{fmt_t(row['Uncollected_t'])} t/y")
        r4.metric("Diverted (net)", f"{fmt_t(row['Diverted_t'])} t/y")
        r5.metric("Landfilled", f"{fmt_t(row['Landfilled_t'])} t/y")
        r6.metric("Process rejects", f"{fmt_t(row['Rejects_t'])} t/y")

        g1, g2, g3 = st.columns(3)
        with g1:
            show(gauge(row["Diversion_rate"] * 100, "Diversion rate", 0, 100, [(0, 20, SOFT["red"]), (20, 35, SOFT["amber"]), (35, 100, SOFT["green"])], suffix="%"), "t5_g1")
        with g2:
            show(gauge(row["Collection_rate"] * 100, "Collection coverage", 50, 100, [(50, 85, SOFT["red"]), (85, 95, SOFT["amber"]), (95, 100, SOFT["green"])], suffix="%", fmt=".0f"), "t5_g2")
        with g3:
            show(gauge(life if np.isfinite(life) else 40, "Landfill life (years)", 0, 40, [(0, 5, SOFT["red"]), (5, 10, SOFT["amber"]), (10, 40, SOFT["green"])]), "t5_g3")

        show(sankey_fig(row), "t5_sankey")
        show(landfill_fill_fig(res, capacity, life), "t5_fill")

        eff_t = effective_levers(levers, assum)
        eff_df = pd.DataFrame(
            {
                "Lever": ["Source reduction", "Collection coverage", "Recycling capture", "Composting capture"],
                "Slider (target)": [levers["source_reduction"], levers["collection"], levers["recycling"], levers["composting"]],
                "Effective target (after soft bonuses)": [eff_t["source"], eff_t["collection"], eff_t["recycling"], eff_t["composting"]],
                f"Value reached in {y1}": [row["Eff_source"], row["Eff_collection"], row["Eff_recycling"], row["Eff_composting"]],
            }
        )
        st.markdown("#### Effective parameters")
        cfg = {c: st.column_config.NumberColumn(format="%.1f%%") for c in eff_df.columns[1:]}
        show_df(eff_df.assign(**{c: eff_df[c] * 100 for c in eff_df.columns[1:]}), hide_index=True, column_config=cfg)

    with sub2:
        scen_rows, scen_series = [], []
        runs = {name: {**{k: v for k, v in p.items() if k != "label"}} for name, p in SCENARIO_OPTIONS.items()}
        runs["Custom (current levers)"] = dict(levers)
        for name, tgt in runs.items():
            rr = run_city(inputs, tgt, assum)
            lf = landfill_life(rr.index.to_numpy(), rr["Landfilled_t"].to_numpy(), capacity)
            rw = rr.loc[y1]
            scen_rows.append({"Scenario": name, f"Generated {y1} (t/yr)": rw["Generated_t"], f"Diversion {y1}": rw["Diversion_rate"] * 100,
                              f"Landfilled {y1} (t/yr)": rw["Landfilled_t"], "Cumulative landfilled (t)": rr["Cum_landfilled_t"].iloc[-1],
                              "Landfill life (yr)": min(lf, 100.0), "Exhaustion year": (rr.index[0] + lf) if lf < 200 else np.nan})
            scen_series.append(rr.assign(Scenario=name))
        sdf = pd.concat(scen_series).reset_index()
        sc_colors = {"BAU": C["grey"], "Moderate Circularity": C["blue"], "Accelerated Circularity": C["green"], "Custom (current levers)": C["gold"]}

        c1, c2 = st.columns(2)
        with c1:
            f = px.line(sdf, x="Year", y="Landfilled_t", color="Scenario", color_discrete_map=sc_colors, title="Annual landfilled tons", labels={"Landfilled_t": "t/year"})
            f.update_traces(line=dict(width=3)); f.update_layout(hovermode="x unified", height=380, yaxis_tickformat=",.2s")
            show(f, "t5_s1")
        with c2:
            sdf["Diversion_pct"] = sdf["Diversion_rate"] * 100
            f = px.line(sdf, x="Year", y="Diversion_pct", color="Scenario", color_discrete_map=sc_colors, title="Diversion rate (%)", labels={"Diversion_pct": "%"})
            f.update_traces(line=dict(width=3)); f.update_layout(hovermode="x unified", height=380)
            show(f, "t5_s2")
        f = px.line(sdf, x="Year", y="Cum_landfilled_t", color="Scenario", color_discrete_map=sc_colors, title="Cumulative landfill filling vs remaining capacity", labels={"Cum_landfilled_t": "tons"})
        f.update_traces(line=dict(width=3))
        f.add_hline(y=capacity, line=dict(color=C["red"], dash="dash"), annotation_text=f"Capacity {fmt_t(capacity)} t", annotation_position="top left")
        f.update_layout(hovermode="x unified", height=400, yaxis_tickformat=",.2s")
        show(f, "t5_s3")

        st.markdown("#### Scenario summary")
        show_df(pd.DataFrame(scen_rows), hide_index=True, column_config={
            f"Generated {y1} (t/yr)": st.column_config.NumberColumn(format="%,.0f"), f"Diversion {y1}": st.column_config.NumberColumn(format="%.1f%%"),
            f"Landfilled {y1} (t/yr)": st.column_config.NumberColumn(format="%,.0f"), "Cumulative landfilled (t)": st.column_config.NumberColumn(format="%,.0f"),
            "Landfill life (yr)": st.column_config.NumberColumn(format="%.1f"), "Exhaustion year": st.column_config.NumberColumn(format="%.0f"),
        })
        st.caption("Landfill life is capped at 100 years in this table.")

    with sub3:
        st.markdown("##### One-at-a-time sensitivity (tornado)")
        t1c, t2c = st.columns(2)
        with t1c:
            metric = st.radio("Output metric", ["Cumulative landfilled (Mt)", "Landfill life (years)"], horizontal=True)
        with t2c:
            pp = st.slider("Perturbation (± percentage points)", 1, 15, 5)
        base_v, tor = tornado_table(inputs, levers, assum, capacity, metric, pp)
        unit_lbl = "Mt" if metric.startswith("Cumulative") else "years"
        ft = go.Figure()
        ft.add_trace(go.Bar(y=tor["Parameter"], x=tor["Low"], orientation="h", name=f"Decrease (−{pp} pp / −10%)", marker_color=C["blue"]))
        ft.add_trace(go.Bar(y=tor["Parameter"], x=tor["High"], orientation="h", name=f"Increase (+{pp} pp / +10%)", marker_color=C["gold"]))
        ft.update_layout(barmode="overlay", title=f"Δ {metric} vs base ({base_v:,.2f} {unit_lbl})", xaxis_title=f"Δ {unit_lbl}", height=440)
        show(ft, "t5_tor")
        st.caption("The levers with the widest bars are where uncertainty or policy effort matters most for the selected output.")

        st.markdown("##### Monte Carlo uncertainty")
        mc1, mc2 = st.columns(2)
        with mc1:
            n_runs = st.slider("Simulations", 100, 2000, 500, 100)
        with mc2:
            sigma = st.slider("Relative uncertainty (σ, %)", 5, 40, 15, 5) / 100
        mc = mc_run(inputs[0], inputs[1], inputs[3], inputs[4], levers, assum, float(capacity), int(n_runs), float(sigma))
        yrs = inputs[0]
        fm = go.Figure()
        fm.add_trace(go.Scatter(x=yrs, y=mc["p90"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fm.add_trace(go.Scatter(x=yrs, y=mc["p10"], fill="tonexty", fillcolor="rgba(13,92,145,0.18)", line=dict(width=0), name="P10–P90 band"))
        fm.add_trace(go.Scatter(x=yrs, y=mc["p50"], name="Median", line=dict(color=C["blue"], width=3)))
        fm.add_trace(go.Scatter(x=res.index, y=res["Cum_landfilled_t"], name="Deterministic", line=dict(color=C["slate"], dash="dash", width=2)))
        fm.add_hline(y=capacity, line=dict(color=C["red"], dash="dash"), annotation_text="Remaining capacity", annotation_position="top left")
        fm.update_layout(title="Cumulative landfilled tons — uncertainty band", yaxis_tickformat=",.2s", hovermode="x unified", height=400)
        show(fm, "t5_mc1")

        horizon_len = yrs[-1] - yrs[0] + 1
        p_exh = float(np.mean(mc["life"] <= horizon_len))
        q10, q50, q90 = np.percentile(mc["life"], [10, 50, 90])
        mm1, mm2, mm3 = st.columns(3)
        mm1.metric("P(capacity exhausted within horizon)", f"{p_exh:.0%}")
        mm2.metric("Landfill life — median", life_text(q50))
        mm3.metric("Landfill life — P10 / P90", f"{q10:,.1f} / {q90:,.1f} yr")
        fh = px.histogram(x=mc["life"], nbins=30, title="Distribution of landfill life (years, capped at 100)", labels={"x": "years"}, color_discrete_sequence=[C["blue"]])
        fh.add_vline(x=q50, line=dict(color=C["slate"], dash="dash"), annotation_text="median")
        fh.update_layout(height=320, showlegend=False, yaxis_title="runs")
        show(fh, "t5_mc2")

# ---------------------------------------------------------
# TAB 6 — ALERTS & PRIORITIES
# ---------------------------------------------------------
with tab6:
    st.subheader("Alerts, Risk Flags and Priority Ranking")
    add_section_intro("What this tab answers", "Which cities are under greater operational stress and what warnings a mayor should see immediately. "
                      "The index uses absolute reference thresholds, so a city is only 'High' priority if it is objectively stressed.")

    st.markdown("#### Alert console")
    for severity, message in alert_messages(row, life, gen_cagr, row["kg_person_day"]):
        {"High": st.error, "Medium": st.warning}.get(severity, st.success)(f"{severity} · {message}")

    with st.expander("Adjust priority-index weights"):
        wcols = st.columns(5)
        weights = {k: wcols[i].slider(RISK_LABELS[k], 0, 100, DEFAULT_WEIGHTS[k], 5, key=f"w_{k}") for i, k in enumerate(RISK_LABELS)}
        if sum(weights.values()) == 0:
            weights = dict(DEFAULT_WEIGHTS)
            st.warning("All weights are zero; defaults restored.")

    rank = priority_table(results, caps, year_range, weights)
    lvl_colors = {"Low": C["green"], "Medium": "#d99a00", "High": C["red"]}
    cl, cr = st.columns([1.5, 1])
    with cl:
        f = px.bar(rank, x="City", y="Priority_score", color="Priority_level", color_discrete_map=lvl_colors, category_orders={"Priority_level": ["Low", "Medium", "High"]},
                   title=f"Priority index by city ({y1})", labels={"Priority_score": "Priority score (0-100)"}, text_auto=".0f")
        f.update_layout(xaxis_tickangle=-25, height=420)
        show(f, "t6_bar")
    with cr:
        theta = [RISK_LABELS[k] for k in RISK_LABELS]
        sel = rank[rank["City"] == selected_city]
        fr = go.Figure()
        if not sel.empty:
            mean_v = [float(rank[f"s_{k}"].mean()) for k in RISK_LABELS]
            sel_v = [float(sel.iloc[0][f"s_{k}"]) for k in RISK_LABELS]
            fr.add_trace(go.Scatterpolar(r=mean_v + mean_v[:1], theta=theta + theta[:1], name="Peer average", line=dict(color=C["grey"], dash="dash")))
            fr.add_trace(go.Scatterpolar(r=sel_v + sel_v[:1], theta=theta + theta[:1], name=selected_city, fill="toself", fillcolor="rgba(196,69,54,0.18)", line=dict(color=C["red"], width=3)))
        fr.update_layout(title="Risk profile (0 = good, 1 = critical)", polar=dict(radialaxis=dict(range=[0, 1], tickfont=dict(size=10))), height=420, margin=dict(l=50, r=50, t=80, b=30))
        show(fr, "t6_radar")

    st.markdown("#### City priority ranking")
    show_df(
        rank[["City", "Priority_score", "Priority_level", "Waste_tons_year", "kg_person_day", "Growth_cagr_pct", "Diversion_rate", "Landfill_life_years"]].assign(Diversion_rate=lambda d: d["Diversion_rate"] * 100),
        hide_index=True,
        column_config={
            "Priority_score": st.column_config.ProgressColumn("Priority score", min_value=0, max_value=100, format="%.1f"),
            "Waste_tons_year": st.column_config.NumberColumn("Waste (t/yr)", format="%,.0f"),
            "kg_person_day": st.column_config.NumberColumn("kg/person/day", format="%.2f"),
            "Growth_cagr_pct": st.column_config.NumberColumn("Growth CAGR (%)", format="%.2f"),
            "Diversion_rate": st.column_config.NumberColumn("Diversion (%)", format="%.1f"),
            "Landfill_life_years": st.column_config.NumberColumn("Landfill life (yr, cap 100)", format="%.1f"),
        },
    )

# ---------------------------------------------------------
# TAB 7 — BENCHMARKING
# ---------------------------------------------------------
with tab7:
    st.subheader("Benchmarking Against Peer Cities")
    add_section_intro("What this tab answers", "How the selected city compares with similar cities by population size and operational pressure.")
    peers = peer_group(df_pop, selected_city, y1)
    bench_cities = sorted(set(peers + comparison_cities + [selected_city]))
    bench = pd.DataFrame(
        {
            "City": bench_cities,
            "Population": [float(results[c].loc[y1, "Population"]) for c in bench_cities],
            "Waste_tons_year": [float(results[c].loc[y1, "Generated_t"]) for c in bench_cities],
            "kg_person_day": [float(results[c].loc[y1, "kg_person_day"]) for c in bench_cities],
            "Diversion_pct": [float(results[c].loc[y1, "Diversion_rate"]) * 100 for c in bench_cities],
        }
    )
    bench["Group"] = np.where(bench["City"] == selected_city, "Selected city", "Peer")
    gcol = {"Selected city": C["red"], "Peer": C["blue"]}

    c1, c2 = st.columns(2)
    with c1:
        f = px.scatter(bench, x="Population", y="Waste_tons_year", color="Group", color_discrete_map=gcol, text="City", size="kg_person_day", size_max=32,
                       title=f"Population vs waste ({y1}) — bubble = kg/person/day", labels={"Waste_tons_year": "tons/year"})
        f.update_traces(textposition="top center"); f.update_layout(height=420, xaxis_tickformat=",.2s", yaxis_tickformat=",.2s")
        show(f, "t7_sc")
    with c2:
        bs = bench.sort_values("kg_person_day", ascending=False)
        f = px.bar(bs, x="City", y="kg_person_day", color="Group", color_discrete_map=gcol, title=f"Per-capita waste comparison ({y1})", labels={"kg_person_day": "kg/person/day"})
        f.add_hline(y=float(bench["kg_person_day"].median()), line=dict(color=C["grey"], dash="dot"), annotation_text="peer median", annotation_position="top right")
        f.update_layout(xaxis_tickangle=-25, height=420)
        show(f, "t7_bar")

    heat = pd.DataFrame({c: results[c]["kg_person_day"] for c in bench_cities}).loc[y0:y1].T
    fh = px.imshow(heat, aspect="auto", color_continuous_scale="YlGnBu", labels=dict(x="Year", y="City", color="kg/p/d"), title="Per-capita generation heatmap (kg/person/day)")
    fh.update_layout(height=max(280, 40 * len(bench_cities) + 120))
    show(fh, "t7_heat")

    show_df(bench.drop(columns="Group"), hide_index=True, column_config={
        "Population": st.column_config.NumberColumn(format="%,.0f"), "Waste_tons_year": st.column_config.NumberColumn("Waste (t/yr)", format="%,.0f"),
        "kg_person_day": st.column_config.NumberColumn("kg/person/day", format="%.2f"), "Diversion_pct": st.column_config.NumberColumn("Diversion (%)", format="%.1f"),
    })

# ---------------------------------------------------------
# TAB 8 — METHODOLOGY
# ---------------------------------------------------------
with tab8:
    st.subheader("Methodology, Data Structure and Equations")
    add_section_intro("What this tab answers", "Which mathematical relations, assumptions and workbook structures are used to compute every indicator.")

    st.markdown("##### 1 · Baseline and policy adoption")
    st.markdown("Workbook series are the **no-policy baseline** $W(t)$. Each lever $\\theta$ moves from the current system $\\theta_0$ to its target $\\theta^*$ following an adoption curve $r(t)$:")
    st.latex(r"\theta(t)=\theta_0+(\theta^*-\theta_0)\,r(t),\qquad r_{\text{lin}}=x,\quad r_{\text{log}}=\frac{\sigma(k(x-\tfrac12))-\sigma(-\tfrac k2)}{\sigma(\tfrac k2)-\sigma(-\tfrac k2)},\quad x=\frac{t-t_0}{T-t_0}")
    st.markdown("**Soft levers** (education $e$, formalization $f$) close a fraction of the remaining gap to a physical ceiling — diminishing returns, never above the cap:")
    st.latex(r"\theta_{\text{eff}}=\theta+(\theta_{\max}-\theta)\cdot\min\!\big(1,\;\varepsilon_e\,e+\varepsilon_f\,f\big)")

    st.markdown("##### 2 · Annual mass balance")
    st.latex(r"G=W(1-\sigma),\quad C=G\,\kappa,\quad U=G-C")
    st.latex(r"R_{in}=C\,s_{rec}\,\rho,\quad K_{in}=C\,s_{org}\,\gamma,\quad R=R_{in}(1-\varphi_r),\quad K=K_{in}(1-\varphi_k)")
    st.latex(r"D=R+K,\qquad L=C-D\;(\text{rejects included}),\qquad d=\frac{D}{G}")
    st.markdown("$G$ generated, $C$ collected, $U$ unmanaged, $s$ composition shares of the **collected** stream, $\\rho,\\gamma$ capture rates, $\\varphi$ process-reject rates, $D$ net diversion, $L$ landfilled.")

    st.markdown("##### 3 · Landfill life (dynamic)")
    st.latex(r"\text{Cum}(t)=\sum_{\tau\le t}L(\tau),\qquad T_{life}=\min\{t:\ \text{Cum}(t)\ge Q_{rem}\}-t_0")
    st.markdown("If capacity is not exhausted within the horizon, the final-year disposal rate is extrapolated.")

    st.markdown("##### 4 · Priority index")
    st.latex(r"\text{Score}=100\cdot\frac{\sum_i w_i\,\rho_i}{\sum_i w_i},\qquad \rho_i=\operatorname{clip}\!\Big(\frac{x_i-x_i^{good}}{x_i^{bad}-x_i^{good}},0,1\Big)")
    ref_df = pd.DataFrame([{"Indicator": RISK_LABELS[k], "Good": RISK_REFS[k][0], "Critical": RISK_REFS[k][1], "Default weight": DEFAULT_WEIGHTS[k]} for k in RISK_LABELS])
    show_df(ref_df, hide_index=True)

    st.markdown("##### 5 · Parameters")
    par = pd.DataFrame(
        [
            ["Ceilings", f"source {CAPS['source']:.0%}, collection {CAPS['collection']:.0%}, recycling {CAPS['recycling']:.0%}, composting {CAPS['composting']:.0%}"],
            ["Elasticities ε", f"source←edu {ELASTICITIES['el_src_edu']}, recycling←edu {ELASTICITIES['el_rec_edu']}, recycling←formal. {ELASTICITIES['el_rec_form']}, composting←edu {ELASTICITIES['el_com_edu']}"],
            ["Reject rates (current)", f"recycling {rec_reject:.0%}, composting {com_reject:.0%}"],
            ["Adoption", f"{ramp_kind}, targets reached in {assum['target_year']}"],
            ["Current-system levers θ₀", ", ".join(f"{k} {v:.0%}" for k, v in BASE_LEVERS.items())],
        ],
        columns=["Parameter", "Value"],
    )
    show_df(par, hide_index=True)

    with st.expander("What changed vs. v1 (model corrections)"):
        st.markdown(
            """
- **No more double-counted source reduction.** v1 reduced waste in the series *and* again in the simulator; v2 applies each lever exactly once.
- **Dynamic instead of single-year.** Levers ramp in over time; flows and landfill filling are computed every year.
- **Composition applies to the collected stream.** v1 sized recycling/composting pools on *generated* waste, so uncollected waste could be "recycled".
- **Process rejects.** Recycling and composting residues return to the landfill (v1 assumed 100% efficiency).
- **Landfill life is cumulative.** v1 divided capacity by a single year's disposal, ignoring growth and policy timing.
- **Bonuses close a gap** to a ceiling instead of being arbitrary additive terms; the unsupported "education → collection" term was removed.
- **Absolute priority index.** v1 min–max normalised across 10 cities (always producing a 'High'); constant inputs such as collection gap collapsed to zero. v2 uses good/critical thresholds and adjustable weights.
- **Growth alerts use CAGR,** so thresholds no longer depend on the window length.
- **Animation uses one global size/colour scale** (v1 rescaled every frame, hiding growth).
- **Slider defaults** use rounding (v1's `int(0.29*100)` gave 28).
            """
        )

# ---------------------------------------------------------
# TAB 9 — ABOUT & DATA
# ---------------------------------------------------------
with tab9:
    st.subheader("About the Platform")
    add_section_intro("What this tab answers", "What the dashboard does, what data it expects and how to export results.")
    st.markdown(
        """
**Purpose.** Explore urban waste dynamics and circularity potential for Colombian cities with structured simulation outputs.

**Expected workbook.** Sheets `Poblacion_2050` (years × cities), `ResiduosTotales_t_anio` (years × cities, tons/year) and `Residuos_5Tipos_largo` (columns `Ciudad`, `Año`, `Tipo`, `Toneladas_anio`).

**Modules.** Trends · composition · geography · animation · dynamic policy simulator (flows, scenarios, sensitivity, Monte Carlo) · alerts & priority index · benchmarking · methodology.
        """
    )

    out_pop = df_pop.loc[y0:y1, [selected_city]]
    out_waste = df_waste.loc[y0:y1, [selected_city]]
    out_sim = res_w.drop(columns=["Ramp"])
    d1, d2, d3 = st.columns(3)
    d1.download_button("Download population CSV", out_pop.to_csv().encode("utf-8"), f"population_{selected_city}_{y0}_{y1}.csv", "text/csv")
    d2.download_button("Download baseline waste CSV", out_waste.to_csv().encode("utf-8"), f"baseline_waste_{selected_city}_{y0}_{y1}.csv", "text/csv")
    d3.download_button("Download scenario simulation CSV", out_sim.to_csv().encode("utf-8"), f"simulation_{selected_city}_{selected_scenario.replace(' ', '_')}_{y0}_{y1}.csv", "text/csv")

    st.markdown("##### Data-quality check: waste-type classification")
    cls = df_types.groupby(["Tipo", "Cat"]).size().reset_index(name="Rows")
    cls["Category"] = cls["Cat"].map({"org": "Organics", "rec": "Recoverables", "oth": "Other"})
    show_df(cls[["Tipo", "Category", "Rows"]], hide_index=True)
    if (shares_df["rec"].sum() == 0) or (shares_df["org"].sum() == 0):
        st.warning("No waste type was classified as organics or recoverables; recycling/composting will have no effect. Check type names in the workbook.")
    st.caption("Types are classified by keyword (organic / plastic, paper, cardboard, glass, metal, textile). Adjust ORG_KEYS / REC_KEYS in the code if your labels differ.")

    if show_raw_data:
        st.write("Baseline population")
        show_df(out_pop)
        st.write("Baseline waste")
        show_df(out_waste)
        st.write("Scenario simulation")
        show_df(out_sim)

st.markdown("<div class='footer-note'>Designed as an institutional-academic observatory interface: robust, interpretable and communication-ready.</div>", unsafe_allow_html=True)
