"""
Escenarios de política. Cada escenario es un conjunto de palancas (core.parameters.LEVERS).

Las palancas se expresan como fracción de la BRECHA entre la condición inicial de cada ciudad y un techo
físico (p. ej. collection=0.5 cierra la mitad de la brecha de cobertura de esa ciudad), de modo que un
mismo escenario produce trayectorias distintas según el punto de partida de cada ciudad y no impone
valores homogéneos.
"""
from __future__ import annotations

from copy import deepcopy

from core.parameters import LEVER_DEFAULTS

_BASE = dict(LEVER_DEFAULTS)

SCENARIOS = {
    "BAU": dict(label_es="Continuidad (BAU)", label_en="Business as usual",
                desc_es="Sin intervenciones nuevas. La capacidad, la adopción y el mercado evolucionan solo por sus dinámicas endógenas.",
                desc_en="No new interventions; capacity, adoption and markets evolve only through endogenous dynamics.",
                levers={}),
    "MOD": dict(label_es="Circularidad moderada", label_en="Moderate circularity",
                desc_es="Paquete moderado conservado de la v2: prevención, cobertura, campañas y rutas de orgánicos de intensidad media.",
                desc_en="Moderate package kept from v2.",
                levers=dict(prev=0.15, collection=0.5, campaign=0.4, participation=0.2, org_route=0.15, capture=0.2, formalization=0.3,
                            rec_cap_add=0.02, org_cap_add=0.02)),
    "ACC": dict(label_es="Circularidad acelerada", label_en="Accelerated circularity",
                desc_es="Paquete de alta intensidad conservado de la v2.",
                desc_en="High-intensity package kept from v2.",
                levers=dict(prev=0.40, collection=0.9, campaign=0.8, participation=0.5, org_route=0.40, capture=0.5, formalization=0.6,
                            rec_cap_add=0.05, org_cap_add=0.06, reject_gain=0.3, T_adopt=6.0)),
    "S1": dict(label_es="S1 · Prevención y reducción en la fuente", label_en="S1 · Source prevention",
               desc_es="Reduce la generación hasta el 50 % del techo de prevención.", desc_en="Prevention up to 50 % of its ceiling.",
               levers=dict(prev=0.5)),
    "S2": dict(label_es="S2 · Incremento del reciclaje", label_en="S2 · More recycling",
               desc_es="Campañas, mejor captura y menos rechazos en la corriente de reciclables.", desc_en="Campaigns, capture and lower rejects.",
               levers=dict(campaign=0.7, capture=0.5, reject_gain=0.4)),
    "S3": dict(label_es="S3 · Compostaje y digestión anaerobia", label_en="S3 · Composting and AD",
               desc_es="Ruta selectiva de orgánicos y capacidad de tratamiento nueva.", desc_en="Organics route and new treatment capacity.",
               levers=dict(org_route=0.6, org_cap_add=0.10, campaign=0.3)),
    "S4": dict(label_es="S4 · Recicladores y ECA", label_en="S4 · Waste pickers and sorting stations",
               desc_es="Fortalecimiento organizativo de recicladores de oficio y estaciones de clasificación.", desc_en="Waste-picker strengthening and sorting stations.",
               levers=dict(formalization=0.9, rec_cap_add=0.03, capture=0.3)),
    "S5": dict(label_es="S5 · Ampliación de capacidad de procesamiento", label_en="S5 · Processing capacity expansion",
               desc_es="Capacidad planificada de clasificación y de orgánicos más inversión endógena reforzada.", desc_en="Planned capacity plus stronger investment.",
               levers=dict(rec_cap_add=0.06, org_cap_add=0.06, invest_mult=1.5)),
    "S6": dict(label_es="S6 · Mejora de separación en la fuente", label_en="S6 · Better source separation",
               desc_es="Campañas intensas y mayor participación ciudadana.", desc_en="Strong campaigns and participation.",
               levers=dict(campaign=1.0, participation=0.7)),
    "S7": dict(label_es="S7 · Estrategia circular integrada", label_en="S7 · Integrated circular strategy",
               desc_es="Combinación de S1 a S6.", desc_en="Combination of S1–S6.",
               levers=dict(prev=0.5, collection=0.9, campaign=1.0, participation=0.7, org_route=0.6, capture=0.5, formalization=0.9,
                           rec_cap_add=0.06, org_cap_add=0.10, invest_mult=1.5, reject_gain=0.4)),
    "S8": dict(label_es="S8 · Restricciones de capacidad y mercado", label_en="S8 · Capacity and market constraints",
               desc_es="Estrategia integrada con demanda de materiales estancada y menor inversión.", desc_en="Integrated strategy under stagnant markets.",
               levers=dict(campaign=1.0, participation=0.7, org_route=0.6, capture=0.5, formalization=0.9, mkt_growth_delta=-0.03, mkt_cap=1.3,
                           invest_mult=0.5)),
    "S9": dict(label_es="S9 · Interrupción operativa", label_en="S9 · Operational disruption",
               desc_es="Pérdida temporal del 60 % de la capacidad de procesamiento durante 2 años desde 2030.", desc_en="60 % processing loss for 2 years from 2030.",
               levers=dict(campaign=0.4, disrupt_year=2030, disrupt_dur=2.0, disrupt_loss=0.6)),
}


def levers_for(key: str, overrides: dict | None = None) -> dict:
    lv = deepcopy(_BASE)
    lv.update(SCENARIOS[key]["levers"])
    if overrides:
        lv.update({k: v for k, v in overrides.items() if v is not None})
    return lv


def label(key: str, lang: str = "es") -> str:
    return SCENARIOS[key][f"label_{lang}"]
