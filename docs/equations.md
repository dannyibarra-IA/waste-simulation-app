# Ecuaciones del motor (core/system_dynamics.py)

Unidades: toneladas (t), años; los flujos están en t/año. Integración: Euler explícito con Δt = 0,25 años, y salidas anuales como la suma de flujo·Δt. La población se interpola linealmente dentro del año.

## Condiciones iniciales (año base t₀ = 2024)

| Símbolo | Definición | Origen |
|---|---|---|
| g_pc,0 | W_obs / (Pob₀ · 0,365); si no hay observación, 0,75 kg/hab/día | SSPD o referencia DNP-CEMPRE-CEPAL |
| κ₀ | cobertura observada; si no, parámetro `kappa0` | SUI o supuesto |
| A₀ | R_obs / (C₀ · s_rec · η · (1 − ρ₀)), topado en 0,95·A_max | se deriva de lo observado |
| ω₀ | O_obs / (C₀ · s_org · A₀ · η_o · (1 − ρ_o)) | se deriva de lo observado |
| K_rec,0 | S_r,0 / u₀ | supuesto u₀ = 0,85 |
| Q₀ | capacidad reportada; si no, vida útil reportada · L_d,0; si tampoco, Q0_years · L_d,0 (supuesto) | registro documental o supuesto |
| I₀ | R₀ · τ_s | equilibrio |
| X₀ | 5 · S_r,0 | supuesto |
| E₀ | parámetro `E0`; k_E,base = δ_E E₀/(1 − E₀) mantiene E estacionario sin política | supuesto |

## Palancas

r(t) es una logística normalizada: vale 0 antes de t_impl y 1 en t_impl + T_adop. Una palanca λ ∈ [0, 1], con intensidad global ι, cierra una fracción de la brecha propia de cada ciudad:

θ(t) = θ₀ + λ ι r(t) (θ_max − θ₀)

## Flujos

```
W   = Pob · g_pc,0 · exp(γ (t − t₀)) · 0,365
G   = W (1 − π_prev),           π_prev = λ_prev ι r · prev_max
C   = κ G,                       U = G − C
S_r = C · s_rec · A · η_eff,     η_eff = min(0,95, (η + λ_cap ι r (0,95 − η)) · (0,5 + 0,5E)/(0,5 + 0,5E₀) · P^ε)
S_o = C · s_org · ω · A · η_o,   ω = ω₀ + λ_org ι r (1 − ω₀)
(si S_r + S_o > C se reescalan proporcionalmente)
M   = C − S_r − S_o
a   = 1 − pérdida durante la interrupción (S9); 1 en otro caso
P_rec = min(S_r, K_rec a),  E_r = S_r − P_rec,  ρ = ρ_min + (ρ₀ − ρ_min)(X/X₀)^(−b) − λ_rej ι r (·),  Rch_r = ρ P_rec,  R = P_rec − Rch_r
P_org = min(S_o, K_org a),  E_o = S_o − P_org,  Rch_o = ρ_o P_org,  K_out = P_org − Rch_o
D   = D₀ exp((g_mkt + Δg)(t − t₀)) [≤ D₀·techo],   D₀ = R₀ (1 + h)
P   = clip(D / (R̄ (1 + h)), 0,3, 2),   R̄ = media móvil de primer orden de R (1 año)
V   = min(I/τ_s, D),            Derrame = max(0, I − I_max_años · D) / 0,25
L_d = M + E_r + E_o + Rch_r + Rch_o + Derrame
L_f = min(L_d, Q/Δt),           Déficit = L_d − L_f
π   = α · clip((T_crit − Q/L̄_d)/T_crit, 0, 1)
```

## Niveles

```
dQ/dt     = Ampliación(t) − L_f
dCumL/dt  = L_f
dK_rec/dt = Inv_rec + Plan_rec − K_rec/vida_rec
            Inv_rec = K_rec/vida_rec + max(0, (1+m)S_r − K_rec)/τ_build · μ · (1+π) · min(P, 1,5)
            Plan_rec = λ_K ι W₀ dr/dt
dK_org/dt = análogo, sin término de precio
dI/dt     = R − V − Derrame
dA/dt     = (p + p_camp (λ_camp ι r + π) + q A)(A_max,eff − A) − δ_A A
            A_max,eff = A_max + λ_part ι r (0,95 − A_max)
dE/dt     = (k_E,base + k_E λ_form ι r)(1 − E) − δ_E E
dX/dt     = P_rec
```

## Identidades verificadas en las pruebas

- G + Derrame = U + L_d + R + K_out, en cada paso.
- G = U + L_f + Déficit + V + K_out + ΔI, en cada año.
- Q(t) = Q₀ + Σ ampliaciones − CumL(t).
- C ≤ G; S_r + S_o ≤ C; R ≤ C·s_rec; K_out ≤ C·s_org; P_rec ≤ K_rec; todos los niveles ≥ 0.

## Vida útil

Si Q llega a 0 en el año j: vida = j + Q_{j−1}/L_d,j. Si no se agota antes de 2050, se extrapola: vida = T + Q_T/L_f,T.
