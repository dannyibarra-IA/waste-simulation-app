"""
Colombia Circular Waste Observatory — Waste Simulation App 3.0

Autor original: Danny Ibarra Vega, Ph.D. · Universidad de Antioquia.
Versión 3.0: motor de Dinámica de Sistemas modular (core/), 32 capitales con población DANE, datos trazables,
calibración, validación e incertidumbre (validation/), exportación reproducible (reports/).
La versión 2 se conserva sin cambios en legacy/app_v2.py.
"""
import streamlit as st

st.set_page_config(page_title="Colombia Circular Waste Observatory", page_icon="♻️", layout="wide", initial_sidebar_state="expanded")

from ui.common import CSS, sidebar, tr  # noqa: E402
from ui.pages_a import page_composition, page_national, page_profile, page_trends  # noqa: E402
from ui.pages_b import page_compare, page_dynamics, page_flows, page_scenarios  # noqa: E402
from ui.pages_c import page_downloads, page_methods, page_risks, page_uncertainty  # noqa: E402

st.markdown(CSS, unsafe_allow_html=True)
sidebar()

PAGES = [
    (page_national, tr("Observatorio nacional", "National observatory"), "🗺️", "observatorio"),
    (page_profile, tr("Perfil de ciudad", "City profile"), "🏙️", "perfil"),
    (page_trends, tr("Tendencias históricas", "Historical trends"), "📈", "tendencias"),
    (page_composition, tr("Composición de residuos", "Waste composition"), "♻️", "composicion"),
    (page_dynamics, tr("Simulación dinámica", "Dynamic simulation"), "🔁", "dinamica"),
    (page_scenarios, tr("Escenarios de políticas", "Policy scenarios"), "🧭", "escenarios"),
    (page_flows, tr("Flujos de materiales", "Material flows"), "🔀", "flujos"),
    (page_compare, tr("Comparación de ciudades", "City comparison"), "🏘️", "comparacion"),
    (page_risks, tr("Riesgos y alertas", "Risks and alerts"), "🚨", "riesgos"),
    (page_uncertainty, tr("Sensibilidad e incertidumbre", "Sensitivity and uncertainty"), "🎲", "incertidumbre"),
    (page_methods, tr("Metodología y fuentes", "Methodology and sources"), "📐", "metodologia"),
    (page_downloads, tr("Descarga de resultados", "Downloads"), "⬇️", "descargas"),
]
nav = st.navigation([st.Page(fn, title=title, icon=icon, url_path=slug, default=(i == 0)) for i, (fn, title, icon, slug) in enumerate(PAGES)])
nav.run()
st.markdown("<div style='color:#5d6b76;font-size:.82rem;text-align:center;padding:1.2rem 0'>Colombia Circular Waste Observatory · Waste Simulation App 3.0 · "
            "Danny Ibarra Vega, Ph.D. · Universidad de Antioquia</div>", unsafe_allow_html=True)
