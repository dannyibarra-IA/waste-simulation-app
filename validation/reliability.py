"""
Indicador de confiabilidad por ciudad. Combina disponibilidad de datos, completitud histórica, calidad de calibración,
desempeño de validación y nivel de incertidumbre. NUNCA califica como "validado" un modelo que solo superó pruebas de
programación: sin validación fuera de muestra el nivel máximo es "calibrado sin validar".
"""
from __future__ import annotations

import numpy as np


LEVELS = {
    "A": "Validado fuera de muestra (sMAPE de validación ≤ 10 % y de ajuste ≤ 15 %)",
    "B": "Validado con error moderado (sMAPE de validación entre 10 % y 25 %)",
    "C": "Calibrado sin validación fuera de muestra, o validación con error alto",
    "D": "Exploratorio: sin series históricas de residuos; resultados condicionados a supuestos",
}


def assess(profile, calib: dict | None, mc_life=None) -> dict:
    comp = profile.completeness
    hist_years = comp.get("_anios_historicos", 0)
    out = dict(disponibilidad=comp.get("_score", 0), completitud_historica=round(100 * min(hist_years, 7) / 7))
    level, notes = "D", []
    if calib and calib.get("status") == "calibrado":
        fit_s = calib["fit"]["dispuesto"]["sMAPE"]
        out["calibracion_sMAPE"] = round(fit_s, 1)
        level = "C"
        val = calib.get("validation", {}).get("dispuesto")
        if val and val.get("n", 0) > 0:
            out["validacion_sMAPE"] = round(val["sMAPE"], 1)
            level = "A" if val["sMAPE"] <= 10 else ("B" if val["sMAPE"] <= 25 else "C")
            if level == "A" and fit_s > 15:
                level = "B"
                notes.append(f"Ajuste histórico con error alto (sMAPE {fit_s:.1f} %); el nivel se limita a B.")
        else:
            notes.append("Sin años reservados para validación fuera de muestra.")
        if calib.get("at_bound"):
            notes.append(f"Parámetros en el límite del rango: {', '.join(calib['at_bound'])}. Con g_growth en el límite suele indicar que la disposición "
                         "reportada no acompaña el crecimiento poblacional proyectado por el DANE (migración, cobertura o cambios de reporte).")
        if not calib.get("uso_aprovechamiento", True):
            notes.append("La serie de aprovechamiento se excluyó de la calibración por superar el potencial reciclable plausible.")
    else:
        notes.append("Sin serie histórica de residuos suficiente: simulación exploratoria.")
    if mc_life is not None and np.size(mc_life):
        p5, p50, p95 = np.percentile(mc_life, [5, 50, 95])
        out["incertidumbre_vida_util_rel"] = round(float((p95 - p5) / max(p50, 1e-9)), 2)
    out["nivel"] = level
    out["descripcion"] = LEVELS[level]
    out["limitaciones"] = notes
    return out
