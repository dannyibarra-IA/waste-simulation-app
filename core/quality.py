"""
Control de calidad de las series SSPD por ciudad. Señala, sin corregir silenciosamente:

  Q1 aprovechamiento_sobre_potencial  aprovechado/(aprovechado+dispuesto) > umbral: supera el potencial reciclable
                                      plausible del flujo municipal (posible material de otros municipios, grandes
                                      generadores o sobrerreporte). La serie de aprovechamiento se EXCLUYE de la calibración
                                      y no fija la condición inicial.
  Q2 discontinuidad                   cambio interanual del dispuesto > 40 %: probable cambio de reporte o de cobertura.
  Q3 sitio_no_autorizado              el sitio principal es botadero, celda de contingencia o transitoria.
  Q4 vida_util_vencida                la fecha final de vida útil del sitio principal ya pasó.
  Q5 vida_util_inestable              la vida útil reportada cambia más de 5 años entre informes consecutivos (licencias modificadas).
  Q6 serie_aprovechamiento_corta      menos de 3 años de aprovechamiento.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RECOVERY_SHARE_MAX = 0.20
JUMP_MAX = 0.40
UNAUTHORIZED = ("BOTADERO", "CONTINGENCIA", "TRANSITORIA", "CUERPO DE AGUA", "QUEMA", "ENTERRAMIENTO")

LABELS = {
    "aprovechamiento_sobre_potencial": ("Aprovechamiento reportado por encima del potencial reciclable", "Reported recovery above recyclable potential"),
    "discontinuidad": ("Discontinuidad en la serie de disposición", "Break in the disposal series"),
    "sitio_no_autorizado": ("Disposición en sitio no autorizado o transitorio", "Disposal in unauthorised or transitional site"),
    "vida_util_vencida": ("Vida útil licenciada vencida", "Licensed life expired"),
    "vida_util_inestable": ("Vida útil reportada inestable entre informes", "Unstable reported life across reports"),
    "serie_aprovechamiento_corta": ("Serie de aprovechamiento corta o ausente", "Short or missing recovery series"),
}


def city_flags(profile) -> list[dict]:
    flags = []
    disp, apr = profile.series("dispuesto_t"), profile.series("aprovechado_t")
    if len(apr):
        share = (apr / (apr + disp.reindex(apr.index))).dropna()
        bad = share[share > RECOVERY_SHARE_MAX]
        if len(bad):
            flags.append(dict(codigo="aprovechamiento_sobre_potencial", severidad="alta",
                              detalle=f"Aprovechado / (aprovechado + dispuesto) = {', '.join(f'{y}: {v:.0%}' for y, v in bad.items())} (umbral {RECOVERY_SHARE_MAX:.0%}). "
                                      "La serie se excluye de la calibración y de la condición inicial.", anios=list(map(int, bad.index))))
    if len(apr) < 3:
        flags.append(dict(codigo="serie_aprovechamiento_corta", severidad="media", detalle=f"{len(apr)} año(s) con aprovechamiento reportado.", anios=list(map(int, apr.index))))
    if len(disp) >= 2:
        ch = disp.pct_change().dropna()
        jumps = ch[ch.abs() > JUMP_MAX]
        if len(jumps):
            flags.append(dict(codigo="discontinuidad", severidad="media",
                              detalle="Cambio interanual del dispuesto: " + ", ".join(f"{y}: {v:+.0%}" for y, v in jumps.items()), anios=list(map(int, jumps.index))))
    t = profile.text("tipo_sitio")
    if t is not None and any(k in str(t["valor"]).upper() for k in UNAUTHORIZED):
        flags.append(dict(codigo="sitio_no_autorizado", severidad="alta", detalle=f"{t['valor']} ({int(t['anio'])}).", anios=[int(t["anio"])]))
    life = profile.series("vida_util_reportada_anios")
    life = life[~life.index.duplicated(keep="last")]
    if len(life):
        if life.iloc[-1] <= 0:
            flags.append(dict(codigo="vida_util_vencida", severidad="alta", detalle=f"Vida útil reportada {life.iloc[-1]:.1f} años en {life.index[-1]}.", anios=[int(life.index[-1])]))
        d = life.diff().abs().dropna()
        if (d > 5).any():
            flags.append(dict(codigo="vida_util_inestable", severidad="media",
                              detalle="Saltos de vida útil reportada: " + ", ".join(f"{y}: {life.loc[y]:.1f} años" for y in d[d > 5].index), anios=list(map(int, d[d > 5].index))))
    return flags


def recovery_usable(profile) -> bool:
    return not any(f["codigo"] == "aprovechamiento_sobre_potencial" for f in city_flags(profile))


def quality_table(repo, lang="es") -> pd.DataFrame:
    rows = []
    for c in repo.codes:
        p = repo.profile(c)
        for f in city_flags(p):
            rows.append(dict(ciudad=p.ciudad, divipola=c, alerta=LABELS[f["codigo"]][0 if lang == "es" else 1], severidad=f["severidad"], detalle=f["detalle"]))
    return pd.DataFrame(rows, columns=["ciudad", "divipola", "alerta", "severidad", "detalle"])
