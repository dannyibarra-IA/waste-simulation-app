# Registro de cambios

## 3.0.0 — 2026-11 (rama `v3`)

Autor original: Danny Ibarra Vega. Contribución técnica de la versión 3.0, con asistencia de Claude (Anthropic) bajo la dirección del autor.

### Auditoría de la v2 (hallazgos corregidos)
- El libro `simulacion_residuos_2025_2050.xlsx` era sintético: 0,80 kg/hab/día y una composición idéntica (68,2 % orgánicos) en las 10 ciudades y en todos los años. Por eso la desviación, el benchmarking y 3 de los 5 componentes del índice de prioridad eran iguales en todas las ciudades.
- Rellenos desactualizados: Navarro (Cali, cerrado en 2008), Henequén (Cartagena, cerrado hacia 2004) y Doña Juana (Soacha, que dispone en Nuevo Mondoñedo).
- Capacidades de relleno sin fuente, y rellenos compartidos tratados como si fueran de cada ciudad.
- El Monte Carlo dejaba fuera la capacidad, la composición y las elasticidades; con reducción en la fuente igual a 0, no variaba.
- El modelo era un balance de masa con rampas exógenas, sin realimentación.
- Además: archivo duplicado `app (3).py`, dependencias sin versión y `plotly>=5.20`, insuficiente para `scatter_map`.

### Nuevo
- Motor de Dinámica de Sistemas con 8 niveles, 3 bucles de refuerzo y 5 de balance, restricciones físicas y balance de materia verificado en cada paso.
- 32 capitales con DIVIPOLA y población oficial del DANE (2018–2042), más una extensión estimada a 2050.
- Sistema de datos con tipo, fuente, calidad, completitud y versión (hash) de cada archivo.
- Escenarios S1–S9, además de los tres de la v2, expresados como cierre de brecha por ciudad.
- Calibración con separación temporal, métricas MAE, RMSE, sMAPE, sesgo y R², y niveles de confiabilidad A–D.
- Monte Carlo reproducible por semilla, tornado y Morris.
- 12 módulos de interfaz en español e inglés.
- Exportación a CSV, Excel, JSON, ZIP reproducible y PDF, con identificador de ejecución.
- 72 pruebas automáticas.

### Datos SSPD integrados (2026-11-16)
- Disposición final 2018–2024 de las 32 capitales: bases 2019–2024 y Anexo 1 del informe 2018 (PDF).
- Aprovechamiento 2020–2024 por familia de material y ECA con su capacidad operativa. Los archivos AA2018, AA2019 y los anexos de 2020, 2021 y 2024 recibidos corresponden al sector de **acueducto y alcantarillado** y no se usan.
- Control de calidad: aprovechamiento por encima del potencial (Bogotá, Villavicencio), discontinuidades, sitios no autorizados, vida útil vencida o inestable.
- Correcciones al motor detectadas al usar datos reales:
  - Condición inicial coherente con totales anuales (iteración de punto fijo).
  - El aprovechamiento se compara solo con materiales inorgánicos.
  - La generación observada se deriva del tonelaje recolectado y la cobertura.
  - La tasa per cápita calibrada converge a una tendencia de largo plazo.
- Calibración de las 32 capitales: 22 en nivel A, 5 en B y 5 en C.
- Caracterización física por familias ingresada por el usuario.

### Conservado
- La v2 completa en `legacy/app_v2.py`, junto con su libro de datos.
