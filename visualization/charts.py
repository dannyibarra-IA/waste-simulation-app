"""Figuras Plotly del observatorio. Estilo sobrio y editorial; observado vs simulado siempre distinguibles."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

C = dict(ink="#1c2b36", muted="#5d6b76", grid="rgba(28,43,54,0.08)", blue="#1f5f8b", green="#2e7d5b", gold="#b8860b",
         red="#b23a2e", sky="#5b9bc8", teal="#3a9e8f", grey="#8c99a3", purple="#6b5b95", sand="#d9cbb0")
SCEN_COLORS = ["#8c99a3", "#1f5f8b", "#2e7d5b", "#b8860b", "#6b5b95", "#b23a2e", "#3a9e8f", "#5b9bc8", "#a0522d", "#2f4f4f", "#c71585", "#556b2f"]
OBS_STYLE = dict(mode="markers+lines", line=dict(width=2), marker=dict(size=8, symbol="circle"))
SIM_DASH = "dash"

pio.templates["obs3"] = go.layout.Template(layout=dict(
    font=dict(family="Source Sans 3, Inter, Segoe UI, sans-serif", color=C["ink"], size=13),
    colorway=SCEN_COLORS, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(gridcolor=C["grid"], zeroline=False, linecolor="rgba(28,43,54,.3)", ticks="outside", tickcolor="rgba(28,43,54,.3)", automargin=True),
    yaxis=dict(gridcolor=C["grid"], zeroline=False, linecolor="rgba(28,43,54,.3)", automargin=True),
    hoverlabel=dict(bgcolor="white", font_size=12), legend=dict(orientation="h", yanchor="top", y=-0.12, x=0, bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    title=dict(font=dict(size=15), x=0, xanchor="left", y=0.97, yanchor="top"), margin=dict(l=20, r=20, t=60, b=20)))
pio.templates.default = "obs3"

PLOT_CONFIG = dict(displaylogo=False, toImageButtonOptions=dict(format="png", scale=3, filename="observatorio_residuos"))


def scen_color_map(keys):
    return {k: SCEN_COLORS[i % len(SCEN_COLORS)] for i, k in enumerate(keys)}


def line_obs_sim(sim: pd.DataFrame | None, obs: pd.Series | None, title, ytitle, sim_label="Simulado", obs_label="Observado",
                 color=C["blue"], fmt=",.3s", extra=None):
    f = go.Figure()
    if sim is not None and len(sim):
        f.add_trace(go.Scatter(x=sim.index, y=sim.values, name=sim_label, mode="lines", line=dict(color=color, width=3, dash=SIM_DASH)))
    if obs is not None and len(obs):
        f.add_trace(go.Scatter(x=obs.index, y=obs.values, name=obs_label, line=dict(color=C["ink"]), **{k: v for k, v in OBS_STYLE.items() if k != "line"}))
    for tr in extra or []:
        f.add_trace(tr)
    f.update_layout(title=title, yaxis_title=ytitle, yaxis_tickformat=fmt, hovermode="x unified", height=430)
    f.update_xaxes(tickformat="d")
    return f


def population_fig(pop: pd.DataFrame, title, labels):
    f = go.Figure()
    styles = {"base_censal_conciliada": dict(color=C["ink"], dash="solid"), "proyeccion_oficial": dict(color=C["blue"], dash="solid"),
              "estimado": dict(color=C["gold"], dash="dot")}
    for kind, st in styles.items():
        d = pop[pop["tipo_dato"] == kind]
        if kind == "estimado" and len(d):
            prev = pop[pop.index < d.index.min()].tail(1)
            d = pd.concat([prev, d])
        if len(d):
            f.add_trace(go.Scatter(x=d.index, y=d["poblacion_total"], name=labels.get(kind, kind), mode="lines+markers" if kind == "base_censal_conciliada" else "lines",
                                   line=dict(width=3, **st)))
    f.update_layout(title=title, yaxis_tickformat=",.3s", hovermode="x unified", height=360)
    f.update_xaxes(tickformat="d")
    return f


def scenario_lines(df, y, title, ytitle, scen_labels, cmap, fmt=",.3s", hline=None, hline_text=""):
    f = go.Figure()
    for s, d in df.groupby("escenario", sort=False):
        f.add_trace(go.Scatter(x=d["anio"], y=d[y], name=scen_labels.get(s, s), mode="lines", line=dict(width=3 if s != "BAU" else 2, color=cmap.get(s),
                                                                                                        dash="dash" if s == "BAU" else "solid")))
    if hline is not None:
        f.add_hline(y=hline, line=dict(color=C["red"], dash="dot"), annotation_text=hline_text, annotation_position="top left")
    f.update_layout(title=title, yaxis_title=ytitle, yaxis_tickformat=fmt, hovermode="x unified", height=430)
    f.update_xaxes(tickformat="d")
    return f


def band_fig(years, q, title, ytitle, det=None, det_label="Determinista", band_label="P5–P95", iqr_label="P25–P75", med_label="Mediana", fmt=",.3s", hline=None):
    f = go.Figure()
    f.add_trace(go.Scatter(x=years, y=q["p95"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
    f.add_trace(go.Scatter(x=years, y=q["p05"], fill="tonexty", fillcolor="rgba(31,95,139,0.12)", line=dict(width=0), name=band_label))
    f.add_trace(go.Scatter(x=years, y=q["p75"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
    f.add_trace(go.Scatter(x=years, y=q["p25"], fill="tonexty", fillcolor="rgba(31,95,139,0.25)", line=dict(width=0), name=iqr_label))
    f.add_trace(go.Scatter(x=years, y=q["p50"], name=med_label, line=dict(color=C["blue"], width=3)))
    if det is not None:
        f.add_trace(go.Scatter(x=years, y=det, name=det_label, line=dict(color=C["ink"], width=2, dash="dash")))
    if hline is not None:
        f.add_hline(y=hline, line=dict(color=C["red"], dash="dot"))
    f.update_layout(title=title, yaxis_title=ytitle, yaxis_tickformat=fmt, hovermode="x unified", height=430)
    f.update_xaxes(tickformat="d")
    return f


def sankey(row: pd.Series, L: dict, title):
    """L: etiquetas de nodos por clave."""
    keys = ["G", "U", "C", "Mixed", "Sr", "So", "Rrec", "Kout", "Rej", "Excess", "Landfill", "Deficit", "Prevented", "W"]
    idx = {k: i for i, k in enumerate(keys)}
    colors = {"W": C["grey"], "Prevented": C["teal"], "G": C["ink"], "U": C["red"], "C": C["blue"], "Mixed": C["grey"], "Sr": C["gold"], "So": C["green"],
              "Rrec": C["green"], "Kout": C["green"], "Rej": C["purple"], "Excess": C["red"], "Landfill": C["muted"], "Deficit": C["red"]}
    flows = [("W", "Prevented", row["Prevented"]), ("W", "G", row["G"]), ("G", "U", row["U"]), ("G", "C", row["C"]),
             ("C", "Mixed", row["Mixed"]), ("C", "Sr", row["Sr"]), ("C", "So", row["So"]),
             ("Sr", "Rrec", row["Rrec"]), ("Sr", "Rej", row["Rej_r"]), ("Sr", "Excess", row["Excess_r"]),
             ("So", "Kout", row["Kout"]), ("So", "Rej", row["Rej_o"]), ("So", "Excess", row["Excess_o"]),
             ("Mixed", "Landfill", row["Mixed"] * (row["Lf"] / max(row["Ld"], 1e-9))), ("Mixed", "Deficit", row["Mixed"] * (row["Overflow"] / max(row["Ld"], 1e-9))),
             ("Rej", "Landfill", (row["Rej_r"] + row["Rej_o"]) * row["Lf"] / max(row["Ld"], 1e-9)),
             ("Rej", "Deficit", (row["Rej_r"] + row["Rej_o"]) * row["Overflow"] / max(row["Ld"], 1e-9)),
             ("Excess", "Landfill", (row["Excess_r"] + row["Excess_o"]) * row["Lf"] / max(row["Ld"], 1e-9)),
             ("Excess", "Deficit", (row["Excess_r"] + row["Excess_o"]) * row["Overflow"] / max(row["Ld"], 1e-9))]
    flows = [(a, b, float(v)) for a, b, v in flows if v > 1e-6]

    def rgba(h, a=0.35):
        h = h.lstrip("#")
        return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"

    f = go.Figure(go.Sankey(arrangement="snap",
                            node=dict(label=[L.get(k, k) for k in keys], color=[colors[k] for k in keys], pad=18, thickness=16,
                                      hovertemplate="%{label}: %{value:,.0f} t/año<extra></extra>"),
                            link=dict(source=[idx[a] for a, _, _ in flows], target=[idx[b] for _, b, _ in flows], value=[v for *_, v in flows],
                                      color=[rgba(colors[b]) for _, b, _ in flows], hovertemplate="%{source.label} → %{target.label}<br>%{value:,.0f} t/año<extra></extra>")))
    f.update_layout(title=title, height=460)
    return f


def city_map(df, value_col, title, colorbar, hover_cols, exploratory_col="exploratorio", size=True):
    d = df.copy()
    vals = d[value_col].astype(float)
    vmin, vmax = float(np.nanmin(vals)), float(np.nanmax(vals))
    sizes = 8 + 30 * np.sqrt(np.clip((vals - min(vmin, 0)) / max(vmax - min(vmin, 0), 1e-9), 0, 1)) if size else np.full(len(d), 14)
    f = go.Figure()
    for flag, sym_op in ((False, 0.9), (True, 0.45)):
        m = d[exploratory_col] == flag
        if not m.any():
            continue
        dd = d[m]
        f.add_trace(go.Scattermap(lat=dd["lat"], lon=dd["lon"], mode="markers", text=dd["ciudad"],
                                  marker=dict(size=np.asarray(sizes)[m.to_numpy()], color=dd[value_col], colorscale="Viridis", cmin=vmin, cmax=vmax, opacity=sym_op,
                                              showscale=not flag or not (~d[exploratory_col]).any(), colorbar=dict(title=colorbar, len=0.75)),
                                  customdata=dd[hover_cols].to_numpy(), name=hover_cols and ("Exploratorio" if flag else "Con datos"),
                                  hovertemplate="<b>%{text}</b><br>" + "<br>".join(f"{c}: %{{customdata[{i}]}}" for i, c in enumerate(hover_cols)) + "<extra></extra>"))
    f.update_layout(map=dict(style="carto-positron", zoom=4.1, center=dict(lat=5.5, lon=-73.5)), height=600, margin=dict(l=0, r=0, t=50, b=0), title=title,
                    legend=dict(y=0.02, x=0.01, bgcolor="rgba(255,255,255,.8)"))
    return f


def tornado_fig(df, base, unit, title, low_label, high_label):
    f = go.Figure()
    f.add_trace(go.Bar(y=df["descripcion"], x=df["bajo"], orientation="h", name=low_label, marker_color=C["blue"]))
    f.add_trace(go.Bar(y=df["descripcion"], x=df["alto"], orientation="h", name=high_label, marker_color=C["gold"]))
    f.update_layout(barmode="overlay", title=title, xaxis_title=f"Δ {unit}", height=max(420, 22 * len(df) + 120))
    return f


def morris_fig(df, title):
    f = px.scatter(df, x="mu_star", y="sigma", text="parametro", color="clase", title=title,
                   labels=dict(mu_star="μ* (influencia media)", sigma="σ (no linealidad / interacciones)"))
    f.update_traces(textposition="top center", marker=dict(size=10))
    f.update_layout(height=480)
    return f


def gauge(value, title, vmin, vmax, steps, suffix=""):
    f = go.Figure(go.Indicator(mode="gauge+number", value=float(np.clip(value, vmin, vmax)), number=dict(suffix=suffix, valueformat=".1f"),
                               title=dict(text=title, font=dict(size=13)),
                               gauge=dict(axis=dict(range=[vmin, vmax]), bar=dict(color=C["ink"], thickness=0.3), bgcolor="white",
                                          steps=[dict(range=[a, b], color=c) for a, b, c in steps])))
    f.update_layout(height=210, margin=dict(l=20, r=20, t=50, b=5))
    return f
