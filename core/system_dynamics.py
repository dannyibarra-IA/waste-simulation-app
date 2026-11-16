"""
Motor de Dinámica de Sistemas del observatorio (v3).

Integración de Euler con paso interno `dt` (por defecto 0,25 años) y salida anual. El motor está
vectorizado sobre una dimensión de lote `n` (ciudades o muestras de Monte Carlo): cada parámetro es
un arreglo de forma (n,) y cada serie exógena de forma (n, T).

NIVELES (stocks)
  Q     capacidad remanente de disposición final                     [t]
  CumL  residuos acumulados en disposición final                     [t]
  Krec  capacidad instalada de clasificación y aprovechamiento       [t/año]
  Korg  capacidad instalada de tratamiento de orgánicos              [t/año]
  I     inventario de materiales recuperados                         [t]
  E     capacidad operativa de organizaciones de recicladores        [índice 0-1]
  A     adopción de la separación en la fuente                       [fracción de generadores]
  X     experiencia acumulada de clasificación (aprendizaje)         [t]

BUCLES DE REALIMENTACIÓN (cada uno con su ecuación en `simulate`)
  R1 Adopción social (+):        A ↑ → imitación q·A ↑ → dA/dt ↑
  R2 Aprendizaje operativo (+):  procesado ↑ → X ↑ → rechazo ρ ↓ → recuperado ↑
  R3 Incremento del aprovechamiento (+): oferta separada ↑ → capacidad deseada ↑ → inversión ↑ → procesado ↑ → X ↑
  B1 Saturación de capacidad (−): oferta separada > Krec → excedente a disposición; corrección por inversión con demora τ_build
  B2 Saturación de mercado (−): recuperado ↑ → inventario ↑ → precio P ↓ → captura e inversión ↓
  B3 Disponibilidad de materiales (−): adopción ↑ → menos residuo mezclado; la captura nunca supera C·s
  B4 Agotamiento de disposición (−): Q ↓ → vida útil ↓ → presión institucional ↑ → campañas e inversión ↑ → disposición ↓
  B5 Saturación de la adopción (−): (A_max − A) ↓ → dA/dt ↓
"""
from __future__ import annotations

import numpy as np

STOCKS = ("Q", "CumL", "Krec", "Korg", "I", "E", "A", "X")
FLOWS = ("W", "G", "C", "U", "Sr", "So", "Mixed", "Prec", "Porg", "Excess_r", "Excess_o", "Rej_r", "Rej_o",
         "Rrec", "Kout", "Sales", "Spill", "Ld", "Lf", "Overflow", "Prevented", "CapAdd_Q")
AUX = ("P", "rho_r", "kappa", "prev", "pressure", "util_rec", "util_org", "org_route", "eta_eff", "ramp", "D")


def ramp(t, t_impl, T_adopt, k=8.0):
    """Curva logística normalizada: 0 antes de t_impl, 1 en t_impl + T_adopt."""
    T = np.maximum(T_adopt, 1e-6)
    x = np.clip((t - t_impl) / T, 0.0, 1.0)
    s = 1.0 / (1.0 + np.exp(-k * (x - 0.5)))
    s0, s1 = 1.0 / (1.0 + np.exp(k * 0.5)), 1.0 / (1.0 + np.exp(-k * 0.5))
    out = (s - s0) / (s1 - s0)
    return np.where(t < t_impl, 0.0, out)


def _a(v, n):
    v = np.asarray(v, dtype=float)
    return np.broadcast_to(v, (n,)).astype(float) if v.ndim == 0 else v.astype(float)


def simulate(years, pop, P: dict, L: dict, init: dict | None = None, dt: float = 0.25, track_balance: bool = True):
    """
    years : (T,) años enteros consecutivos; years[0] es el año base t0.
    pop   : (n, T) población a mitad de año.
    P     : parámetros (ver core/parameters.py), escalares o (n,).
    L     : palancas de política (ver core/parameters.LEVERS), escalares o (n,).
    init  : observaciones del año base, (n,) con NaN si no hay dato:
              W_obs   generación total observada [t/año] (si existe, define g_pc0)
              R_obs   reciclables aprovechados observados [t/año]
              O_obs   orgánicos aprovechados observados [t/año]
              Q_obs   capacidad remanente reportada [t]
              kappa_obs cobertura observada [fracción]
    """
    years = np.asarray(years, dtype=float)
    pop = np.atleast_2d(np.asarray(pop, dtype=float))
    n, T = pop.shape
    init = init or {}
    p = {k: _a(v, n) for k, v in P.items()}
    lv = {k: _a(v, n) for k, v in L.items()}
    nan = np.full(n, np.nan)
    W_obs, R_obs, O_obs = (_a(init.get(k, nan), n) for k in ("W_obs", "R_obs", "O_obs"))
    Q_obs, kappa_obs = _a(init.get("Q_obs", nan), n), _a(init.get("kappa_obs", nan), n)

    t0 = years[0]
    steps_per_year = int(round(1.0 / dt))
    dt = 1.0 / steps_per_year
    inten = np.clip(lv["intensity"], 0.0, 2.0)

    # ---------- condiciones iniciales (año base) ------------------------------------------------
    g_pc0 = np.where(np.isfinite(W_obs) & (pop[:, 0] > 0), W_obs / np.maximum(pop[:, 0], 1) / 0.365, p["g_pc0"])
    kappa0 = np.where(np.isfinite(kappa_obs), np.clip(kappa_obs, 0.0, 1.0), p["kappa0"])
    W0 = pop[:, 0] * g_pc0 * 0.365
    C0 = W0 * kappa0
    E0 = np.clip(p["E0"], 0.01, 0.99)
    eta0 = np.clip(p["eta_r"], 0.0, 0.95)
    A_from_obs = R_obs / np.maximum(C0 * p["s_rec"] * eta0 * (1 - p["rho_r0"]), 1e-9)
    A0 = np.where(np.isfinite(R_obs), np.clip(A_from_obs, 0.0, 0.95 * p["A_max"]), p["A0"])
    route_from_obs = O_obs / np.maximum(C0 * p["s_org"] * A0 * p["eta_o"] * (1 - p["rho_o"]), 1e-9)
    route0 = np.where(np.isfinite(O_obs), np.clip(route_from_obs, 0.0, 1.0), p["org_route0"])
    Sr0 = C0 * p["s_rec"] * A0 * eta0
    So0 = C0 * p["s_org"] * route0 * A0 * p["eta_o"]
    util0 = np.clip(p["util0"], 0.3, 1.0)
    Rrec0 = Sr0 * (1 - p["rho_r0"])
    Ld0 = np.maximum(C0 - Sr0 - So0 + Sr0 * p["rho_r0"] + So0 * p["rho_o"], 1e-9)
    D0 = np.maximum(Rrec0 * (1 + p["mkt_headroom"]), 1e-9)

    st = dict(
        Q=np.where(np.isfinite(Q_obs), Q_obs, p["Q0_years"] * Ld0),
        CumL=np.zeros(n), Krec=Sr0 / util0, Korg=So0 / util0,
        I=Rrec0 * p["tau_sell"], E=E0.copy(), A=A0.copy(),
        X=np.maximum(Sr0 * 5.0, 1.0),  # supuesto: 5 años de experiencia previa equivalente
    )
    X0 = st["X"].copy()
    Q_init = st["Q"].copy()
    kE_base = p["delta_E"] * E0 / (1 - E0)  # mantiene E estacionario sin política
    A_max_eff0 = p["A_max"]

    out = {k: np.zeros((n, T)) for k in FLOWS + STOCKS + AUX}
    bal_max = 0.0
    Ld_smooth = Ld0.copy()
    Rrec_smooth = np.maximum(Rrec0, 1e-9)
    lf_year = int(np.nanmax(lv["landfill_add_year"])) if np.any(lv["landfill_add"] > 0) else None

    for yi in range(T):
        acc = {k: np.zeros(n) for k in FLOWS}
        aux_acc = {k: np.zeros(n) for k in AUX}
        I_start = st["I"].copy()
        for s in range(steps_per_year):
            t = years[yi] + s * dt
            frac = s * dt
            popt = pop[:, yi] if yi == T - 1 else pop[:, yi] * (1 - frac) + pop[:, yi + 1] * frac
            r = ramp(t, lv["t_impl"], lv["T_adopt"])
            r_next = ramp(t + dt, lv["t_impl"], lv["T_adopt"])
            dr = (r_next - r) / dt

            # --- generación y prevención
            gpc = g_pc0 * np.exp(p["g_growth"] * (t - t0))
            W = popt * gpc * 0.365
            prev = np.clip(lv["prev"] * inten * r, 0, 1) * p["prev_max"]
            G = W * (1 - prev)
            # --- recolección
            kappa = kappa0 + np.clip(lv["collection"] * inten * r, 0, 1) * np.maximum(p["kappa_max"] - kappa0, 0)
            C = G * kappa
            U = G - C
            # --- presión institucional por agotamiento de la disposición (B4)
            years_left = st["Q"] / np.maximum(Ld_smooth, 1e-9)
            pressure = np.clip((p["T_crit"] - years_left) / np.maximum(p["T_crit"], 1e-9), 0, 1) * p["alpha_press"]
            # --- mercado (B2)
            g_m = p["g_mkt"] + lv["mkt_growth_delta"]
            D = D0 * np.exp(g_m * (t - t0))
            D = np.where(lv["mkt_cap"] > 0, np.minimum(D, D0 * lv["mkt_cap"]), D)
            sell_pot = st["I"] / np.maximum(p["tau_sell"], 1e-6)
            # índice de precio relativo: 1 en el año base; >1 si la demanda crece más rápido que la oferta recuperada
            Pidx = np.clip(D / np.maximum(Rrec_smooth * (1 + p["mkt_headroom"]), 1e-9), 0.3, 2.0)
            Sales = np.minimum(sell_pot, D)
            Spill = np.maximum(st["I"] - p["inv_max_years"] * D, 0) / 0.25
            # --- separación en la fuente (R1, B5)
            fE = (0.5 + 0.5 * st["E"]) / (0.5 + 0.5 * E0)
            cap_gain = np.clip(lv["capture"] * inten * r, 0, 1)
            eta_eff = np.clip((eta0 + cap_gain * (0.95 - eta0)) * fE * Pidx ** p["eps_price"], 0, 0.95)
            Sr = C * p["s_rec"] * st["A"] * eta_eff
            route = route0 + np.clip(lv["org_route"] * inten * r, 0, 1) * (1 - route0)
            So = C * p["s_org"] * route * st["A"] * p["eta_o"]
            over = np.maximum(Sr + So - C, 0)   # restricción física (B3): nunca más que lo recolectado
            Sr, So = Sr - over * Sr / np.maximum(Sr + So, 1e-12), So - over * So / np.maximum(Sr + So, 1e-12)
            Mixed = C - Sr - So
            # --- interrupciones operativas (S9)
            in_disr = (lv["disrupt_dur"] > 0) & (t >= lv["disrupt_year"]) & (t < lv["disrupt_year"] + lv["disrupt_dur"])
            avail = np.where(in_disr, 1 - np.clip(lv["disrupt_loss"], 0, 1), 1.0)
            # --- clasificación y reciclaje (B1, R2)
            Prec = np.minimum(Sr, st["Krec"] * avail)
            Excess_r = Sr - Prec
            rho_learn = p["rho_r_min"] + (p["rho_r0"] - p["rho_r_min"]) * (st["X"] / X0) ** (-p["b_learn"])
            rho_r = rho_learn - np.clip(lv["reject_gain"] * inten * r, 0, 1) * (rho_learn - p["rho_r_min"])
            Rej_r = Prec * rho_r
            Rrec = Prec - Rej_r
            # --- orgánicos
            Porg = np.minimum(So, st["Korg"] * avail)
            Excess_o = So - Porg
            Rej_o = Porg * p["rho_o"]
            Kout = Porg - Rej_o
            # --- disposición final (B4)
            Ld = Mixed + Excess_r + Excess_o + Rej_r + Rej_o + Spill
            add_Q = np.zeros(n)
            if lf_year is not None and s == 0:
                add_Q = np.where((lv["landfill_add"] > 0) & (years[yi] == lv["landfill_add_year"]), lv["landfill_add"] * Ld0, 0.0) / dt
            Q_avail = st["Q"] + add_Q * dt
            Lf = np.minimum(Ld, Q_avail / dt)
            Overflow = Ld - Lf

            # --- inversión en capacidad (R3, B1)
            press_mult = 1 + pressure
            inv_rec = st["Krec"] / p["life_rec"] + np.maximum((1 + p["cap_margin"]) * Sr - st["Krec"], 0) / p["tau_build"] \
                * lv["invest_mult"] * press_mult * np.clip(Pidx, 0, 1.5)
            inv_org = st["Korg"] / p["life_org"] + np.maximum((1 + p["cap_margin"]) * So - st["Korg"], 0) / p["tau_build"] \
                * lv["invest_mult"] * press_mult
            plan_rec = lv["rec_cap_add"] * inten * W0 * dr
            plan_org = lv["org_cap_add"] * inten * W0 * dr
            # --- adopción (R1, B5)
            A_max_eff = A_max_eff0 + np.clip(lv["participation"] * inten * r, 0, 1) * (0.95 - A_max_eff0)
            p_ext = p["p_base"] + p["p_campaign_max"] * (np.clip(lv["campaign"] * inten * r, 0, 1) + pressure)
            dA = (p_ext + p["q_imit"] * st["A"]) * np.maximum(A_max_eff - st["A"], 0) - p["delta_A"] * st["A"]
            # --- capacidad organizativa
            dE = (kE_base + p["k_E"] * np.clip(lv["formalization"] * inten * r, 0, 1)) * (1 - st["E"]) - p["delta_E"] * st["E"]

            # --- integración (Euler)
            st["Q"] = np.maximum(Q_avail - Lf * dt, 0.0)
            st["CumL"] = st["CumL"] + Lf * dt
            st["Krec"] = np.maximum(st["Krec"] + (inv_rec + plan_rec - st["Krec"] / p["life_rec"]) * dt, 0.0)
            st["Korg"] = np.maximum(st["Korg"] + (inv_org + plan_org - st["Korg"] / p["life_org"]) * dt, 0.0)
            st["I"] = np.maximum(st["I"] + (Rrec - Sales - Spill) * dt, 0.0)
            st["A"] = np.clip(st["A"] + dA * dt, 0.0, 1.0)
            st["E"] = np.clip(st["E"] + dE * dt, 0.0, 1.0)
            st["X"] = st["X"] + Prec * dt
            Ld_smooth = Ld_smooth + (Ld - Ld_smooth) * dt / 1.0
            Rrec_smooth = Rrec_smooth + (Rrec - Rrec_smooth) * dt / 1.0

            loc = dict(W=W, G=G, C=C, U=U, Sr=Sr, So=So, Mixed=Mixed, Prec=Prec, Porg=Porg, Excess_r=Excess_r, Excess_o=Excess_o,
                       Rej_r=Rej_r, Rej_o=Rej_o, Rrec=Rrec, Kout=Kout, Sales=Sales, Spill=Spill, Ld=Ld, Lf=Lf, Overflow=Overflow,
                       Prevented=W - G, CapAdd_Q=add_Q)
            for k in FLOWS:
                acc[k] += loc[k] * dt
            for k, v in dict(P=Pidx, rho_r=rho_r, kappa=kappa, prev=prev, pressure=pressure, org_route=route, eta_eff=eta_eff, ramp=r, D=D,
                             util_rec=Prec / np.maximum(st["Krec"] * avail, 1e-9), util_org=Porg / np.maximum(st["Korg"] * avail, 1e-9)).items():
                aux_acc[k] += v * dt
            if track_balance:
                res = G + Spill - (U + Ld + Rrec + Kout)
                bal_max = max(bal_max, float(np.max(np.abs(res) / np.maximum(G, 1e-9))))

        for k in FLOWS:
            out[k][:, yi] = acc[k]
        for k in AUX:
            out[k][:, yi] = aux_acc[k]
        for k in STOCKS:
            out[k][:, yi] = st[k]
        if track_balance:
            # balance anual con inventario: G = U + Lf + Overflow + Sales + Kout + ΔI
            dI = st["I"] - I_start
            res = acc["G"] - (acc["U"] + acc["Lf"] + acc["Overflow"] + acc["Sales"] + acc["Kout"] + dI)
            bal_max = max(bal_max, float(np.max(np.abs(res) / np.maximum(acc["G"], 1e-9))))

    # vida útil: año (fraccional) en que Q llega a cero; si no ocurre en el horizonte, extrapolación al ritmo final
    life = np.full(n, np.inf)
    for i in range(n):
        hit = np.nonzero(out["Q"][i] <= 1e-6)[0]
        if hit.size:
            j = hit[0]
            q_prev = out["Q"][i, j - 1] if j > 0 else Q_init[i]
            life[i] = j + min(q_prev / max(out["Ld"][i, j], 1e-9), 1.0)
        elif out["Lf"][i, -1] > 0:
            life[i] = T + out["Q"][i, -1] / out["Lf"][i, -1]

    out["years"] = years.astype(int)
    out["life"] = life
    out["balance_max_rel_error"] = bal_max
    out["init"] = dict(A0_clipped=np.isfinite(R_obs) & (A_from_obs > 0.95 * p["A_max"]), g_pc0=g_pc0, kappa0=kappa0, A0=A0, route0=route0, W0=W0, Ld0=Ld0, Q0=np.where(np.isfinite(Q_obs), Q_obs, p["Q0_years"] * Ld0),
                       Q_assumed=~np.isfinite(Q_obs), Krec0=Sr0 / util0, D0=D0)
    return out
