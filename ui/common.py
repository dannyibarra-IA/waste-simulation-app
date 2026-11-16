"""Estado compartido, caché, barra lateral y utilidades de presentación."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import streamlit as st

from core.data import Repository
from core.parameters import LEVER_DEFAULTS, LEVERS, PARAMS
from core.scenarios import SCENARIOS
from core.simulation_engine import BASE_YEAR, END_YEAR, run_scenarios
from visualization.charts import PLOT_CONFIG

APP_VERSION = "3.0.0"
APP_NAME = "Colombia Circular Waste Observatory"


def lang() -> str:
    return st.session_state.get("lang", "es")


def tr(es: str, en: str) -> str:
    return es if lang() == "es" else en


def scen_label(k):
    return SCENARIOS[k][f"label_{lang()}"]


@st.cache_resource(show_spinner=False)
def get_repo(version_key: str = "") -> Repository:
    return Repository()


def repo() -> Repository:
    return get_repo()


@st.cache_data(show_spinner=False, max_entries=48)
def cached_run(codes: tuple, scenarios: tuple, lever_json: str, param_json: str, base_year: int, end_year: int):
    df, meta = run_scenarios(get_repo(), list(codes), list(scenarios), json.loads(lever_json) or None, json.loads(param_json) or None,
                             base_year=base_year, end_year=end_year)
    return df, meta


def results(codes=None, scenarios=None):
    """Resultados de simulación para las ciudades y escenarios pedidos, con las palancas y parámetros del usuario."""
    s = st.session_state
    codes = tuple(codes or s.get("codes_all", repo().codes))
    scenarios = tuple(scenarios or s.get("scenarios", ["BAU"]))
    if "BAU" not in scenarios:
        scenarios = ("BAU",) + scenarios
    return cached_run(codes, scenarios, json.dumps(s.get("lever_overrides", {}), sort_keys=True),
                      json.dumps(s.get("param_overrides", {}), sort_keys=True), BASE_YEAR, END_YEAR)


def show(fig, key):
    st.plotly_chart(fig, key=key, config=PLOT_CONFIG, theme=None, **({"width": "stretch"}))


def table(df, **kw):
    st.dataframe(df, width="stretch", **kw)


def fmt_t(x):
    try:
        x = float(x)
    except Exception:
        return str(x)
    if not np.isfinite(x):
        return "—"
    for lim, suf in ((1e9, "G"), (1e6, "M"), (1e3, "k")):
        if abs(x) >= lim:
            return f"{x / lim:,.2f} {suf}"
    return f"{x:,.0f}"


def life_text(v):
    return "> 100" if not np.isfinite(v) or v > 100 else f"{v:,.1f}"


def intro(title, text):
    st.markdown(f"<div class='section-panel'><div class='section-title'>{title}</div><div class='section-text'>{text}</div></div>", unsafe_allow_html=True)


def kpi(label, value, note="", tone="neutral", tag=None):
    tag_html = f"<span class='tag {tag}'>{ {'obs': tr('observado', 'observed'), 'sim': tr('simulado', 'simulated'), 'sup': tr('supuesto', 'assumed'), 'est': tr('estimado', 'estimated'), 'proj': tr('proyección oficial', 'official projection')}[tag] }</span>" if tag else ""
    st.markdown(f"<div class='kpi'><div class='kpi-label'>{label}{tag_html}</div><div class='kpi-value'>{value}</div>"
                f"<div class='kpi-note {tone}'>{note}</div></div>", unsafe_allow_html=True)


def exploratory_notice(meta_row):
    msgs = []
    if meta_row.get("exploratory"):
        msgs.append(tr("La generación de residuos de esta ciudad no tiene serie observada cargada: se usa la referencia nacional de 0,75 kg/hab/día "
                       "(DNP-CEMPRE-CEPAL, 2021). **Simulación exploratoria.**",
                       "No observed waste series loaded for this city: the national reference of 0.75 kg/cap/day is used. **Exploratory run.**"))
    if meta_row.get("capacity_assumed"):
        msgs.append(tr("La capacidad remanente de disposición no está reportada: se supone igual a `Q0_years` años de la disposición del año base. "
                       "La vida útil resultante **no es un dato**.",
                       "Remaining disposal capacity is not reported; it is assumed as `Q0_years` years of base disposal. The resulting landfill life **is not data**."))
    prov = meta_row.get("provenance", {})
    if "LICENCIA VENCIDA" in str(prov.get("capacidad", "")):
        msgs.append(tr("La vida útil licenciada del sitio principal reportada a la SSPD ya venció: el modelo arranca con capacidad remanente cero y toda la disposición "
                       "se contabiliza como **disposición sin capacidad licenciada**. Si existe una ampliación aprobada, regístrela en «Ajustes de política → Ampliación».",
                       "The site's licensed life reported to SSPD has expired: all disposal counts as beyond licensed capacity. Register any approved expansion."))
    if "aprovechado_ajuste" in prov:
        msgs.append(tr("El aprovechamiento reportado supera el potencial reciclable plausible del flujo municipal; para la condición inicial se acota al 20 % "
                       "y la serie se excluye de la calibración (ver «Perfil de ciudad → Calidad de datos»).",
                       "Reported recovery exceeds plausible potential; capped at 20 % for the initial condition and excluded from calibration."))
    if meta_row.get("A0_clipped"):
        msgs.append(tr("El aprovechamiento reportado supera lo que el modelo puede recuperar con la fracción reciclable en uso (20 % por defecto): el primer año "
                       "subestima el aprovechamiento y sobrestima la disposición. Ingrese la caracterización de la ciudad en la página **Composición de residuos**.",
                       "Observed recovery exceeds the model's structural potential with the assumed composition; initial adoption was capped."))
    for m in msgs:
        st.warning(m, icon="⚠️")


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700;800&display=swap');
html, body, .stApp{font-family:"Source Sans 3","Inter","Segoe UI",sans-serif;color:#1c2b36;}
[data-testid="stAppViewContainer"]{background:#f6f7f5;}
[data-testid="stSidebar"]{background:#eef0ec;border-right:1px solid rgba(28,43,54,.08);}
.block-container{padding-top:1.4rem;max-width:1400px;}
h1,h2,h3{letter-spacing:-.01em;color:#1c2b36;}
.hero{border-bottom:1px solid rgba(28,43,54,.12);padding:.2rem 0 .9rem;margin-bottom:1rem;}
.hero-kicker{font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;color:#1f5f8b;}
.hero-title{font-size:1.9rem;font-weight:800;line-height:1.15;margin:.15rem 0 .25rem;}
.hero-sub{color:#5d6b76;font-size:.98rem;max-width:1000px;}
.section-panel{background:#fff;border:1px solid rgba(28,43,54,.08);border-left:4px solid #1f5f8b;border-radius:10px;padding:.6rem .9rem;margin-bottom:.9rem;}
.section-title{font-size:.78rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:#1f5f8b;}
.section-text{color:#5d6b76;font-size:.93rem;line-height:1.5;}
.kpi{background:#fff;border:1px solid rgba(28,43,54,.08);border-radius:10px;padding:.75rem .9rem;height:100%;}
.kpi-label{color:#5d6b76;font-size:.74rem;text-transform:uppercase;letter-spacing:.05em;font-weight:700;}
.kpi-value{font-size:1.45rem;font-weight:800;line-height:1.2;margin-top:.15rem;}
.kpi-note{font-size:.8rem;color:#5d6b76;margin-top:.1rem;} .kpi-note.bad{color:#b23a2e;} .kpi-note.good{color:#2e7d5b;}
.tag{font-size:.65rem;font-weight:700;border-radius:999px;padding:.05rem .4rem;margin-left:.4rem;text-transform:none;letter-spacing:0;}
.tag.obs{background:#e3ecf3;color:#1f5f8b;} .tag.sim{background:#e8f1ec;color:#2e7d5b;} .tag.sup{background:#f6ead3;color:#8a6200;} .tag.est{background:#efe9f5;color:#6b5b95;} .tag.proj{background:#e3ecf3;color:#1f5f8b;}
footer{visibility:hidden;}
</style>
"""


def hero(title, sub):
    st.markdown(f"<div class='hero'><div class='hero-kicker'>{APP_NAME} · v{APP_VERSION}</div><div class='hero-title'>{title}</div>"
                f"<div class='hero-sub'>{sub}</div></div>", unsafe_allow_html=True)


def sidebar():
    s = st.session_state
    r = repo()
    st.sidebar.markdown(f"**{APP_NAME}**  \nWaste Simulation App {APP_VERSION}")
    s.lang = "es" if st.sidebar.segmented_control("Idioma / Language", ["ES", "EN"], default="ES" if lang() == "es" else "EN", key="lang_sel") != "EN" else "en"
    caps = r.capitals
    regions = sorted(caps["region"].unique())
    reg = st.sidebar.multiselect(tr("Región", "Region"), regions, key="f_region")
    sub = caps[caps["region"].isin(reg)] if reg else caps
    deps = sorted(sub["departamento"].unique())
    dep = st.sidebar.multiselect(tr("Departamento", "Department"), deps, key="f_dep")
    sub = sub[sub["departamento"].isin(dep)] if dep else sub
    names = list(sub.sort_values("ciudad")["ciudad"])
    default_city = "Medellín" if "Medellín" in names else names[0]
    city = st.sidebar.selectbox(tr("Ciudad de análisis", "Focus city"), names, index=names.index(s.get("city_name", default_city)) if s.get("city_name") in names else names.index(default_city), key="city_sel")
    s.city_name = city
    s.city = r.code_of(city)
    s.codes_filtered = list(sub["divipola"])
    s.codes_all = r.codes
    keys = list(SCENARIOS)
    s.scenarios = st.sidebar.multiselect(tr("Escenarios a comparar", "Scenarios to compare"), keys, default=s.get("scenarios", ["BAU", "MOD", "ACC", "S7"]),
                                         format_func=scen_label, key="scen_sel") or ["BAU"]
    s.scenario_focus = st.sidebar.selectbox(tr("Escenario principal", "Main scenario"), s.scenarios, index=min(len(s.scenarios) - 1, 3) if len(s.scenarios) > 1 else 0,
                                            format_func=scen_label, key="scen_focus")
    s.year = st.sidebar.slider(tr("Año de referencia", "Reference year"), BASE_YEAR, END_YEAR, s.get("year", 2035), key="year_sel")
    s.mode = st.sidebar.segmented_control(tr("Modo", "Mode"), [tr("Educativo", "Educational"), tr("Científico", "Scientific")],
                                          default=tr("Científico", "Scientific"), key="mode_sel") or tr("Científico", "Scientific")
    with st.sidebar.expander(tr("🎛️ Ajustes de política (todas las ciudades)", "🎛️ Policy adjustments (all cities)")):
        st.caption(tr("Modifican las palancas de TODOS los escenarios comparados. Déjelas en 'escenario' para usar las definiciones originales.",
                      "They modify the levers of ALL compared scenarios."))
        lo = {}
        if st.checkbox(tr("Año de implementación", "Implementation year"), key="o_t"):
            lo["t_impl"] = st.slider(" ", 2025, 2040, 2026, key="o_t_v", label_visibility="collapsed")
        if st.checkbox(tr("Velocidad de adopción (años)", "Adoption time (years)"), key="o_T"):
            lo["T_adopt"] = float(st.slider("  ", 2, 20, 8, key="o_T_v", label_visibility="collapsed"))
        if st.checkbox(tr("Intensidad global", "Global intensity"), key="o_i"):
            lo["intensity"] = st.slider("   ", 0.0, 1.5, 1.0, 0.05, key="o_i_v", label_visibility="collapsed")
        if st.checkbox(tr("Participación ciudadana", "Citizen participation"), key="o_p"):
            lo["participation"] = st.slider("    ", 0.0, 1.0, 0.5, 0.05, key="o_p_v", label_visibility="collapsed")
        if st.checkbox(tr("Eficiencia de recuperación (captura)", "Recovery efficiency"), key="o_c"):
            lo["capture"] = st.slider("     ", 0.0, 1.0, 0.5, 0.05, key="o_c_v", label_visibility="collapsed")
        if st.checkbox(tr("Reducción de rechazos", "Reject reduction"), key="o_r"):
            lo["reject_gain"] = st.slider("      ", 0.0, 1.0, 0.4, 0.05, key="o_r_v", label_visibility="collapsed")
        if st.checkbox(tr("Capacidad instalada adicional (% generación)", "Added capacity (% generation)"), key="o_k"):
            v = st.slider("       ", 0, 20, 5, key="o_k_v", label_visibility="collapsed") / 100
            lo["rec_cap_add"], lo["org_cap_add"] = v, v
        if st.checkbox(tr("Interrupción operativa", "Operational disruption"), key="o_d"):
            lo["disrupt_year"] = st.slider(tr("Año", "Year"), 2025, 2048, 2030, key="o_d_y")
            lo["disrupt_dur"] = float(st.slider(tr("Duración (años)", "Duration (years)"), 0.25, 5.0, 2.0, 0.25, key="o_d_d"))
            lo["disrupt_loss"] = st.slider(tr("Pérdida de capacidad", "Capacity loss"), 0.0, 1.0, 0.6, 0.05, key="o_d_l")
        if st.checkbox(tr("Ampliación de disposición final", "Landfill expansion"), key="o_l"):
            lo["landfill_add"] = float(st.slider(tr("Años de disposición base", "Years of base disposal"), 1, 30, 10, key="o_l_v"))
            lo["landfill_add_year"] = st.slider(tr("Año", "Year"), 2025, 2050, 2032, key="o_l_y")
        s.lever_overrides = lo
    with st.sidebar.expander(tr("🧪 Parámetros de la ciudad", "🧪 City parameters")):
        st.caption(tr("Solo afectan a la ciudad de análisis. Cada cambio queda registrado como 'ajustado por el usuario'.",
                      "Only for the focus city; recorded as user-adjusted."))
        po = dict(s.get("param_overrides", {}).get(s.city, {}))
        for k in ("s_rec", "s_org", "kappa0", "Q0_years", "eta_r", "rho_r0", "g_growth"):
            p = PARAMS[k]
            on = st.checkbox(f"{p.label_es if lang() == 'es' else p.label_en} [{p.unit}]", value=k in po, key=f"po_{s.city}_{k}")
            if on:
                po[k] = st.slider(k, float(p.low), float(p.high), float(po.get(k, p.default)), key=f"pv_{s.city}_{k}", label_visibility="collapsed")
            else:
                po.pop(k, None)
        allp = dict(s.get("param_overrides", {}))
        if po:
            allp[s.city] = po
        else:
            allp.pop(s.city, None)
        s.param_overrides = allp
    st.sidebar.caption(tr("Fuentes: DANE (población 2018-2042), SSPD (residuos, cuando se cargan). Ver «Metodología y fuentes».",
                          "Sources: DANE (population), SSPD (waste, when loaded)."))
