# Colombia Circular Waste Observatory — Waste Simulation App 3.0

Plataforma de simulación y apoyo a decisiones sobre generación, recolección, aprovechamiento y disposición final de residuos sólidos en las **32 capitales departamentales de Colombia**, con un motor de Dinámica de Sistemas y escenarios hasta 2050.

**Autor original:** Danny Ibarra Vega, Ph.D. — Universidad de Antioquia.
Contribuciones de la versión 3.0: ver [`CHANGELOG.md`](CHANGELOG.md).

## Qué responde

¿Cómo evolucionarán la generación, el aprovechamiento y la disposición final de residuos en las 32 capitales hasta 2050, y qué escenarios de gestión mejorarían su desempeño bajo restricciones reales de capacidad, recuperación y tratamiento?

## Estado de los datos (léase antes de interpretar resultados)

| Información | Estado |
|---|---|
| Población 2018–2042, 32 capitales | **Oficial** (DANE, actualización del 30-jul-2025) |
| Población 2043–2050 | **Estimada** (extensión documentada de la serie DANE) |
| Disposición final 2018–2024, 32 capitales | **Observada** (SSPD: bases 2019–2024; Anexo 1 del informe 2018) |
| Aprovechamiento 2020–2024 | **Observado** en 27 capitales (SSPD; por familia de material). Bogotá y Villavicencio reportan más del 20 % del flujo y se acotan |
| Capacidad de rellenos | Derivada de la **fecha final de vida útil licenciada** reportada a la SSPD (31 capitales) |
| Capacidad de clasificación inicial | Capacidad operativa de las ECA reportada a la SSPD |
| Cobertura de recolección | **Supuesta** (95 %): no está en las bases cargadas |
| Composición física | Referencia nacional y supuesto, salvo que el usuario ingrese la caracterización de la ciudad (página Composición) |

**Calibración y validación fuera de muestra** (ajuste 2018–2022, validación 2023–2024, sMAPE de la disposición):
- **Nivel A (22):** Armenia, Barranquilla, Bogotá D. C., Bucaramanga, Ibagué, Manizales, Mocoa, Montería, Neiva, Pasto, Pereira, Popayán, Riohacha, San Andrés, San José de Cúcuta, San José del Guaviare, Santa Marta, Sincelejo, Tunja, Valledupar, Villavicencio, Yopal.
- **Nivel B (5):** Cartagena de Indias, Florencia, Medellín, Mitú, Puerto Carreño.
- **Nivel C (5):** Arauca, Cali, Inírida, Leticia, Quibdó. Son series con discontinuidades fuertes.

La aplicación nunca inventa datos para completar registros: cada valor lleva fuente, año, unidad, tipo (observado, proyección oficial, estimado, supuesto o simulado) y calidad.

## Módulos

1. Observatorio nacional · 2. Perfil de ciudad · 3. Tendencias históricas · 4. Composición · 5. Simulación dinámica · 6. Escenarios de políticas · 7. Flujos de materiales · 8. Comparación de ciudades · 9. Riesgos y alertas · 10. Sensibilidad e incertidumbre · 11. Metodología y fuentes · 12. Descarga de resultados.

Interfaz en español, con opción en inglés. Tiene un modo educativo y otro científico.

## Estructura

```
app.py                       navegación y barra lateral
core/                        motor científico (sin Streamlit)
  system_dynamics.py         niveles, flujos y bucles; integración de Euler con Δt = 0,25 años
  parameters.py              registro de parámetros (unidad, rango, clase y fuente)
  scenarios.py               BAU, moderado, acelerado y S1–S9
  data.py                    repositorio de datos y completitud por ciudad
  sspd_import.py             importador flexible de bases SSPD
  simulation_engine.py       orquestación por lotes (32 ciudades × escenarios)
validation/                  calibración, validación histórica, Monte Carlo, tornado, Morris y confiabilidad
visualization/charts.py      figuras Plotly
reports/report_generator.py  manifiesto, Excel, ZIP reproducible y PDF
ui/                          páginas de la interfaz
data/raw | processed         fuentes y tablas procesadas (data/build_data.py)
tests/                       72 pruebas automáticas
docs/                        metodología, ecuaciones, diccionario de datos, manual y despliegue
legacy/app_v2.py             versión 2 conservada sin cambios
```

## Uso local

```bash
pip install -r requirements.txt
python data/build_data.py        # regenera data/processed/ desde data/raw/
python -m pytest                 # verificación estructural, validación, interfaz y exportaciones
streamlit run app.py
```

Para actualizar los datos de la SSPD, copie las bases nuevas como `data/raw/sspd/sspd_DF_<año>.xlsx` (disposición final) o `data/raw/sspd/sspd_AA_<año>.xlsx` (aprovechamiento) y ejecute `python data/build_data.py`. El script importa los datos, aplica los controles de calidad, recalibra las 32 capitales y guarda la versión de los datos.

Versión HTML autónoma (sin servidor ni internet), con los 12 escenarios precalculados para las 32 capitales:

```bash
python reports/build_static_html.py        # genera dist/observatorio_residuos_v3.html
```

Despliegue en Streamlit Community Cloud: ver [`docs/deployment.md`](docs/deployment.md).
