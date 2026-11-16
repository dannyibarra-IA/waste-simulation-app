"""
Registro de parámetros del motor.

Cada parámetro declara unidad, valor por defecto, rango plausible (usado por Monte Carlo y Morris),
clase epistémica y fuente. Clases:

  medido      se toma de datos observados de la ciudad (sobrescribe el defecto)
  calibrado   se ajusta contra series históricas (validation/calibration.py)
  supuesto    valor exploratorio sin respaldo documental específico: SIEMPRE se muestra como supuesto
  referencia  valor documentado de fuente secundaria (nacional o internacional)
  politica    palanca de escenario definida por el usuario
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Param:
    key: str
    label_es: str
    label_en: str
    unit: str
    default: float
    low: float
    high: float
    kind: str
    source: str = ""
    group: str = "general"
    note: str = ""


_P = [
    # --- Generación y composición -------------------------------------------------------------
    Param("g_pc0", "Generación per cápita inicial", "Initial per-capita generation", "kg/hab/día", 0.75, 0.45, 1.20, "referencia",
          "DNP, CEMPRE y CEPAL (2021). Encuesta a municipios sobre gestión de residuos sólidos domiciliarios 2019 – Colombia (promedio nacional 0,75 kg/hab/día).",
          "generacion", "Se sustituye por el valor medido de la ciudad cuando hay datos SSPD."),
    Param("g_growth", "Crecimiento anual de la generación per cápita", "Annual per-capita growth", "1/año", 0.005, -0.01, 0.02, "supuesto",
          "", "generacion", "Calibrable con la serie 2018-2024 de cada ciudad."),
    Param("s_org", "Fracción orgánica", "Organic fraction", "fracción", 0.70, 0.50, 0.80, "referencia",
          "CATF (2024). Colombia waste sector fact sheet (los orgánicos representan cerca del 70 % del flujo).", "generacion"),
    Param("s_rec", "Fracción reciclable (papel, cartón, plástico, vidrio, metal)", "Recyclable fraction", "fracción", 0.20, 0.12, 0.30, "supuesto",
          "", "generacion", "Sustituir por la caracterización del PGIRS de cada ciudad."),
    # --- Recolección -------------------------------------------------------------------------
    Param("kappa0", "Cobertura de recolección inicial", "Initial collection coverage", "fracción", 0.95, 0.80, 1.00, "supuesto",
          "", "recoleccion", "Sustituir por la cobertura reportada (SUI) de la ciudad."),
    Param("kappa_max", "Techo de cobertura", "Coverage ceiling", "fracción", 0.995, 0.98, 1.00, "supuesto", "", "recoleccion"),
    # --- Separación en la fuente (difusión tipo Bass) ----------------------------------------
    Param("A0", "Adopción inicial de separación en la fuente", "Initial source-separation adoption", "fracción de generadores", 0.10, 0.02, 0.30, "calibrado",
          "", "separacion", "Se deriva del aprovechamiento observado del año base cuando existe."),
    Param("A_max", "Adopción máxima alcanzable", "Maximum adoption", "fracción", 0.70, 0.40, 0.90, "supuesto", "", "separacion"),
    Param("p_base", "Adopción espontánea (coeficiente de innovación)", "Innovation coefficient", "1/año", 0.010, 0.0, 0.03, "supuesto",
          "Estructura de Bass (1969). Sultan, Farley y Lehmann (1990) reportan p≈0,03 en promedio para bienes durables; aquí se adapta a una práctica doméstica.", "separacion"),
    Param("q_imit", "Imitación social (coeficiente de imitación)", "Imitation coefficient", "1/año", 0.15, 0.05, 0.40, "supuesto",
          "Estructura de Bass (1969). Sultan, Farley y Lehmann (1990) reportan q≈0,38 en promedio para bienes durables; se usa un valor menor por tratarse de una práctica doméstica.", "separacion"),
    Param("p_campaign_max", "Efecto máximo de campañas de separación", "Max campaign effect", "1/año", 0.08, 0.02, 0.15, "supuesto", "", "separacion"),
    Param("delta_A", "Abandono de la separación", "Adoption decay", "1/año", 0.03, 0.0, 0.08, "supuesto", "", "separacion"),
    Param("eta_r", "Eficiencia de captura de reciclables separados", "Capture efficiency of separated recyclables", "fracción", 0.60, 0.40, 0.85, "supuesto",
          "", "separacion"),
    Param("eta_o", "Eficiencia de captura de orgánicos separados", "Capture efficiency of separated organics", "fracción", 0.55, 0.30, 0.80, "supuesto", "", "separacion"),
    Param("org_route0", "Cobertura inicial de ruta selectiva de orgánicos", "Initial organics route coverage", "fracción", 0.02, 0.0, 0.10, "supuesto", "", "separacion"),
    # --- Clasificación y reciclaje ----------------------------------------------------------
    Param("rho_r0", "Rechazo inicial en clasificación", "Initial sorting reject rate", "fracción", 0.20, 0.08, 0.35, "supuesto", "", "reciclaje"),
    Param("rho_r_min", "Rechazo mínimo alcanzable", "Minimum reject rate", "fracción", 0.08, 0.03, 0.12, "supuesto", "", "reciclaje"),
    Param("b_learn", "Exponente de aprendizaje operativo", "Learning exponent", "adim.", 0.15, 0.05, 0.32, "referencia",
          "Curvas de experiencia: tasas de progreso de 80-95 % equivalen a b entre 0,07 y 0,32 (Argote y Epple, 1990).", "reciclaje"),
    Param("cap_margin", "Margen de capacidad deseada sobre la oferta", "Desired capacity margin", "fracción", 0.15, 0.0, 0.40, "supuesto", "", "reciclaje"),
    Param("tau_build", "Tiempo de construcción de capacidad", "Capacity build time", "años", 2.0, 1.0, 5.0, "supuesto", "", "reciclaje"),
    Param("life_rec", "Vida útil de instalaciones de clasificación", "Sorting facility lifetime", "años", 15.0, 10.0, 25.0, "supuesto", "", "reciclaje"),
    Param("util0", "Utilización inicial de la capacidad de clasificación", "Initial utilization", "fracción", 0.85, 0.6, 0.98, "supuesto", "", "reciclaje"),
    # --- Organización de recicladores ----------------------------------------------------------
    Param("E0", "Capacidad operativa inicial de organizaciones de recicladores", "Initial organisational capacity", "índice 0-1", 0.40, 0.2, 0.7, "supuesto", "", "recicladores"),
    Param("k_E", "Velocidad de fortalecimiento organizativo", "Organisational strengthening rate", "1/año", 0.05, 0.0, 0.15, "supuesto", "", "recicladores"),
    Param("delta_E", "Pérdida de capacidad organizativa", "Organisational decay", "1/año", 0.03, 0.0, 0.08, "supuesto", "", "recicladores"),
    # --- Mercado de materiales ------------------------------------------------------------------
    Param("mkt_headroom", "Holgura inicial de la demanda de materiales", "Initial market headroom", "fracción", 0.25, 0.0, 0.8, "supuesto", "", "mercado"),
    Param("g_mkt", "Crecimiento anual de la demanda de materiales", "Annual market growth", "1/año", 0.03, 0.0, 0.07, "supuesto", "", "mercado"),
    Param("tau_sell", "Tiempo medio de venta del inventario", "Mean inventory sale time", "años", 0.15, 0.05, 0.5, "supuesto", "", "mercado"),
    Param("inv_max_years", "Inventario máximo (años de demanda)", "Max inventory (years of demand)", "años", 0.25, 0.1, 0.6, "supuesto", "", "mercado"),
    Param("eps_price", "Elasticidad de la captura al precio", "Capture elasticity to price", "adim.", 0.3, 0.0, 0.8, "supuesto", "", "mercado"),
    # --- Orgánicos ----------------------------------------------------------------------------
    Param("rho_o", "Rechazo en tratamiento de orgánicos", "Organics treatment reject rate", "fracción", 0.15, 0.05, 0.35, "supuesto", "", "organicos"),
    Param("life_org", "Vida útil de plantas de orgánicos", "Organics plant lifetime", "años", 15.0, 10.0, 25.0, "supuesto", "", "organicos"),
    # --- Disposición final ------------------------------------------------------------------------
    Param("Q0_years", "Capacidad remanente inicial (años de disposición del año base)", "Initial remaining capacity (years of base disposal)", "años", 15.0, 3.0, 30.0, "supuesto",
          "", "disposicion", "Solo se usa si no hay capacidad reportada; el resultado se marca como exploratorio."),
    Param("T_crit", "Umbral de vida útil que activa presión institucional", "Life threshold triggering pressure", "años", 10.0, 5.0, 15.0, "supuesto", "", "disposicion"),
    Param("alpha_press", "Intensidad de la respuesta institucional a la presión", "Institutional response to pressure", "adim.", 0.5, 0.0, 1.0, "supuesto", "", "disposicion"),
    # --- Prevención -------------------------------------------------------------------------------
    Param("prev_max", "Techo de prevención en la fuente", "Prevention ceiling", "fracción", 0.30, 0.15, 0.40, "supuesto", "", "prevencion"),
]

PARAMS: dict[str, Param] = {p.key: p for p in _P}
DEFAULTS: dict[str, float] = {p.key: p.default for p in _P}

# Palancas de política (definidas por escenario; no tienen incertidumbre de parámetro)
LEVERS = {
    "t_impl": ("Año de implementación", "Implementation year", "año", 2026),
    "T_adopt": ("Tiempo de adopción (velocidad)", "Adoption time", "años", 8.0),
    "intensity": ("Intensidad global de la intervención", "Global intensity", "0-1", 1.0),
    "prev": ("Prevención en la fuente (fracción del techo)", "Source prevention (share of ceiling)", "0-1", 0.0),
    "collection": ("Cierre de brecha de cobertura", "Coverage gap closure", "0-1", 0.0),
    "campaign": ("Campañas de separación en la fuente", "Source-separation campaigns", "0-1", 0.0),
    "participation": ("Participación ciudadana (eleva la adopción máxima)", "Citizen participation", "0-1", 0.0),
    "org_route": ("Ruta selectiva de orgánicos (cobertura objetivo)", "Organics route coverage", "0-1", 0.0),
    "capture": ("Mejora de eficiencia de captura", "Capture efficiency gain", "0-1", 0.0),
    "formalization": ("Fortalecimiento de recicladores y ECA", "Waste-picker strengthening", "0-1", 0.0),
    "rec_cap_add": ("Capacidad adicional de clasificación (% de generación base)", "Added sorting capacity (% of base generation)", "fracción", 0.0),
    "org_cap_add": ("Capacidad adicional de orgánicos (% de generación base)", "Added organics capacity (% of base generation)", "fracción", 0.0),
    "invest_mult": ("Multiplicador de inversión endógena", "Endogenous investment multiplier", "x", 1.0),
    "reject_gain": ("Reducción de rechazos (fracción de la brecha al mínimo)", "Reject reduction", "0-1", 0.0),
    "mkt_growth_delta": ("Cambio en el crecimiento de la demanda de materiales", "Market growth change", "1/año", 0.0),
    "mkt_cap": ("Techo de mercado (fracción de la demanda base)", "Market ceiling multiplier", "x", 0.0),
    "disrupt_year": ("Año de interrupción operativa", "Disruption year", "año", 0),
    "disrupt_dur": ("Duración de la interrupción", "Disruption duration", "años", 0.0),
    "disrupt_loss": ("Pérdida de capacidad durante la interrupción", "Capacity loss during disruption", "fracción", 0.0),
    "landfill_add": ("Ampliación de capacidad de disposición (años de disposición base)", "Landfill expansion (years of base disposal)", "años", 0.0),
    "landfill_add_year": ("Año de la ampliación de disposición", "Landfill expansion year", "año", 0),
}
LEVER_DEFAULTS = {k: v[3] for k, v in LEVERS.items()}


def param_table(lang: str = "es"):
    import pandas as pd
    rows = []
    for p in _P:
        rows.append({
            "Parámetro" if lang == "es" else "Parameter": p.key,
            "Descripción" if lang == "es" else "Description": p.label_es if lang == "es" else p.label_en,
            "Unidad" if lang == "es" else "Unit": p.unit,
            "Defecto" if lang == "es" else "Default": p.default,
            "Rango" if lang == "es" else "Range": f"{p.low} – {p.high}",
            "Clase" if lang == "es" else "Class": p.kind,
            "Fuente" if lang == "es" else "Source": p.source or ("Supuesto del observatorio" if lang == "es" else "Observatory assumption"),
        })
    return pd.DataFrame(rows)
