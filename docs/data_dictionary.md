# Diccionario de datos

Generado desde el código con `python docs/build_dictionary.py`.

## Tablas procesadas

| Archivo | Clave | Columnas |
|---|---|---|
| `capitales.csv` | divipola | ciudad, departamento, region, lat, lon, coord_fuente, coord_calidad |
| `poblacion.csv` | divipola, anio | poblacion_total, poblacion_cabecera (hab), tipo_dato, fuente |
| `residuos_observados.csv` | divipola, anio, variable | valor, unidad, tipo_dato, calidad, fuente, nota |

**tipo_dato:** `base_censal_conciliada`, `proyeccion_oficial`, `observado`, `estimado`, `supuesto` o `simulado`. **calidad:** `reportado_SSPD`, `documental`, `oficial` o `aproximada`.

## Variables del perfil de ciudad

| Clave | Descripción | Unidad |
|---|---|---|
| poblacion | Población histórica y proyectada | hab |
| generacion_pc | Generación per cápita | kg/hab/día |
| generacion_t | Generación total | t/año |
| composicion | Composición física | fracción |
| aprovechado_t | Cantidad aprovechada | t/año |
| dispuesto_t | Cantidad dispuesta | t/año |
| cobertura_recoleccion | Cobertura de recolección | fracción |
| eca_numero | Instalaciones de aprovechamiento (ECA) | número |
| relleno_nombre | Sistema de disposición final | texto |
| tipo_sitio | Tipo de sitio de disposición | texto |
| eca_capacidad_t | Capacidad operativa de ECA | t/año |
| capacidad_remanente_t | Capacidad remanente de disposición | t |
| vida_util_reportada_anios | Vida útil reportada | años |

## Salidas de simulación

| Variable | Descripción | Unidad |
|---|---|---|
| pop | Población | hab |
| W | Generación sin prevención | t/año |
| G | Generación | t/año |
| C | Recolectado | t/año |
| U | No recolectado | t/año |
| Sr | Reciclables separados | t/año |
| So | Orgánicos separados | t/año |
| Mixed | Residuo mezclado | t/año |
| Prec | Procesado en clasificación | t/año |
| Porg | Procesado orgánicos | t/año |
| Excess_r | Reciclables sin capacidad | t/año |
| Excess_o | Orgánicos sin capacidad | t/año |
| Rej_r | Rechazo de clasificación | t/año |
| Rej_o | Rechazo de orgánicos | t/año |
| Rrec | Materiales recuperados | t/año |
| Kout | Orgánicos tratados | t/año |
| Sales | Materiales comercializados | t/año |
| Spill | Inventario no comercializado a disposición | t/año |
| Ld | Demanda de disposición | t/año |
| Lf | Dispuesto en relleno | t/año |
| Overflow | Disposición sin capacidad licenciada (déficit) | t/año |
| Prevented | Prevenido en la fuente | t/año |
| CapAdd_Q | Ampliación de capacidad de disposición | t/año |
| Q | Capacidad remanente de disposición | t |
| CumL | Disposición acumulada | t |
| Krec | Capacidad de clasificación | t/año |
| Korg | Capacidad de orgánicos | t/año |
| I | Inventario de materiales | t |
| E | Capacidad organizativa recicladores | 0-1 |
| A | Adopción de separación | fracción |
| P | Índice de precio de materiales | base=1 |
| rho_r | Tasa de rechazo en clasificación | fracción |
| kappa | Cobertura de recolección | fracción |
| pressure | Presión institucional | 0-1 |
| util_rec | Utilización de capacidad de clasificación | fracción |
| util_org | Utilización de capacidad de orgánicos | fracción |
| tasa_aprovechamiento | (Materiales recuperados + orgánicos tratados) / generación | fracción |
| gpc_kg_dia | Generación per cápita | kg/hab/día |
| disp_pc_kg_dia | Disposición per cápita (incluye déficit) | kg/hab/día |
| desviacion_acum_vs_bau_t | Disposición evitada acumulada respecto al BAU | t |
| vida_util_instantanea | Q / demanda de disposición | años |

## Parámetros

| Parámetro      | Descripción                                                    | Unidad                  |   Defecto | Rango        | Clase      | Fuente                                                                                                                                                                     |
|:---------------|:---------------------------------------------------------------|:------------------------|----------:|:-------------|:-----------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| g_pc0          | Generación per cápita inicial                                  | kg/hab/día              |     0.75  | 0.45 – 1.2   | referencia | DNP, CEMPRE y CEPAL (2021). Encuesta a municipios sobre gestión de residuos sólidos domiciliarios 2019 – Colombia (promedio nacional 0,75 kg/hab/día).                     |
| g_growth       | Crecimiento per cápita de corto plazo (año base)               | 1/año                   |     0.005 | -0.03 – 0.03 | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| g_lr           | Crecimiento per cápita de largo plazo                          | 1/año                   |     0.005 | 0.0 – 0.015  | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| tau_g          | Tiempo de convergencia de la tasa per cápita                   | años                    |     5     | 2.0 – 10.0   | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| s_org          | Fracción orgánica                                              | fracción                |     0.7   | 0.5 – 0.8    | referencia | CATF (2024). Colombia waste sector fact sheet (los orgánicos representan cerca del 70 % del flujo).                                                                        |
| s_rec          | Fracción reciclable (papel, cartón, plástico, vidrio, metal)   | fracción                |     0.2   | 0.12 – 0.3   | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| kappa0         | Cobertura de recolección inicial                               | fracción                |     0.95  | 0.8 – 1.0    | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| kappa_max      | Techo de cobertura                                             | fracción                |     0.995 | 0.98 – 1.0   | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| A0             | Adopción inicial de separación en la fuente                    | fracción de generadores |     0.1   | 0.02 – 0.3   | calibrado  | Supuesto del observatorio                                                                                                                                                  |
| A_max          | Adopción máxima alcanzable                                     | fracción                |     0.7   | 0.4 – 0.9    | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| p_base         | Adopción espontánea (coeficiente de innovación)                | 1/año                   |     0.01  | 0.0 – 0.03   | supuesto   | Estructura de Bass (1969). Sultan, Farley y Lehmann (1990) reportan p≈0,03 en promedio para bienes durables; aquí se adapta a una práctica doméstica.                      |
| q_imit         | Imitación social (coeficiente de imitación)                    | 1/año                   |     0.15  | 0.05 – 0.4   | supuesto   | Estructura de Bass (1969). Sultan, Farley y Lehmann (1990) reportan q≈0,38 en promedio para bienes durables; se usa un valor menor por tratarse de una práctica doméstica. |
| p_campaign_max | Efecto máximo de campañas de separación                        | 1/año                   |     0.08  | 0.02 – 0.15  | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| delta_A        | Abandono de la separación                                      | 1/año                   |     0.03  | 0.0 – 0.08   | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| eta_r          | Eficiencia de captura de reciclables separados                 | fracción                |     0.6   | 0.4 – 0.85   | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| eta_o          | Eficiencia de captura de orgánicos separados                   | fracción                |     0.55  | 0.3 – 0.8    | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| org_route0     | Cobertura inicial de ruta selectiva de orgánicos               | fracción                |     0.02  | 0.0 – 0.1    | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| rho_r0         | Rechazo inicial en clasificación                               | fracción                |     0.2   | 0.08 – 0.35  | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| rho_r_min      | Rechazo mínimo alcanzable                                      | fracción                |     0.08  | 0.03 – 0.12  | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| b_learn        | Exponente de aprendizaje operativo                             | adim.                   |     0.15  | 0.05 – 0.32  | referencia | Curvas de experiencia: tasas de progreso de 80-95 % equivalen a b entre 0,07 y 0,32 (Argote y Epple, 1990).                                                                |
| cap_margin     | Margen de capacidad deseada sobre la oferta                    | fracción                |     0.15  | 0.0 – 0.4    | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| tau_build      | Tiempo de construcción de capacidad                            | años                    |     2     | 1.0 – 5.0    | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| life_rec       | Vida útil de instalaciones de clasificación                    | años                    |    15     | 10.0 – 25.0  | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| util0          | Utilización inicial de la capacidad de clasificación           | fracción                |     0.85  | 0.6 – 0.98   | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| E0             | Capacidad operativa inicial de organizaciones de recicladores  | índice 0-1              |     0.4   | 0.2 – 0.7    | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| k_E            | Velocidad de fortalecimiento organizativo                      | 1/año                   |     0.05  | 0.0 – 0.15   | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| delta_E        | Pérdida de capacidad organizativa                              | 1/año                   |     0.03  | 0.0 – 0.08   | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| mkt_headroom   | Holgura inicial de la demanda de materiales                    | fracción                |     0.25  | 0.0 – 0.8    | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| g_mkt          | Crecimiento anual de la demanda de materiales                  | 1/año                   |     0.03  | 0.0 – 0.07   | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| tau_sell       | Tiempo medio de venta del inventario                           | años                    |     0.15  | 0.05 – 0.5   | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| inv_max_years  | Inventario máximo (años de demanda)                            | años                    |     0.25  | 0.1 – 0.6    | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| eps_price      | Elasticidad de la captura al precio                            | adim.                   |     0.3   | 0.0 – 0.8    | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| rho_o          | Rechazo en tratamiento de orgánicos                            | fracción                |     0.15  | 0.05 – 0.35  | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| life_org       | Vida útil de plantas de orgánicos                              | años                    |    15     | 10.0 – 25.0  | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| Q0_years       | Capacidad remanente inicial (años de disposición del año base) | años                    |    15     | 3.0 – 30.0   | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| T_crit         | Umbral de vida útil que activa presión institucional           | años                    |    10     | 5.0 – 15.0   | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| alpha_press    | Intensidad de la respuesta institucional a la presión          | adim.                   |     0.5   | 0.0 – 1.0    | supuesto   | Supuesto del observatorio                                                                                                                                                  |
| prev_max       | Techo de prevención en la fuente                               | fracción                |     0.3   | 0.15 – 0.4   | supuesto   | Supuesto del observatorio                                                                                                                                                  |

## Palancas de política

| Palanca | Descripción | Unidad | Defecto |
|---|---|---|---|
| t_impl | Año de implementación | año | 2026 |
| T_adopt | Tiempo de adopción (velocidad) | años | 8.0 |
| intensity | Intensidad global de la intervención | 0-1 | 1.0 |
| prev | Prevención en la fuente (fracción del techo) | 0-1 | 0.0 |
| collection | Cierre de brecha de cobertura | 0-1 | 0.0 |
| campaign | Campañas de separación en la fuente | 0-1 | 0.0 |
| participation | Participación ciudadana (eleva la adopción máxima) | 0-1 | 0.0 |
| org_route | Ruta selectiva de orgánicos (cobertura objetivo) | 0-1 | 0.0 |
| capture | Mejora de eficiencia de captura | 0-1 | 0.0 |
| formalization | Fortalecimiento de recicladores y ECA | 0-1 | 0.0 |
| rec_cap_add | Capacidad adicional de clasificación (% de generación base) | fracción | 0.0 |
| org_cap_add | Capacidad adicional de orgánicos (% de generación base) | fracción | 0.0 |
| invest_mult | Multiplicador de inversión endógena | x | 1.0 |
| reject_gain | Reducción de rechazos (fracción de la brecha al mínimo) | 0-1 | 0.0 |
| mkt_growth_delta | Cambio en el crecimiento de la demanda de materiales | 1/año | 0.0 |
| mkt_cap | Techo de mercado (fracción de la demanda base) | x | 0.0 |
| disrupt_year | Año de interrupción operativa | año | 0 |
| disrupt_dur | Duración de la interrupción | años | 0.0 |
| disrupt_loss | Pérdida de capacidad durante la interrupción | fracción | 0.0 |
| landfill_add | Ampliación de capacidad de disposición (años de disposición base) | años | 0.0 |
| landfill_add_year | Año de la ampliación de disposición | año | 0 |
