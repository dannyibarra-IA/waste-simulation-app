# Metodología

## 1. Propósito y alcance

El observatorio simula, para cada una de las 32 capitales departamentales, la trayectoria anual 2024–2050 de la generación, la recolección, la separación en la fuente, la clasificación y el reciclaje, el tratamiento de orgánicos, los rechazos, la comercialización de materiales y la disposición final, bajo distintos escenarios de política pública. Se trata de un modelo de apoyo a decisiones, no de un pronóstico puntual.

## 2. Datos

- **Población:** DANE, proyecciones municipales por área 2018–2042 (actualización del 30-jul-2025). El año 2018 es la base censal conciliada. Para 2043–2050 se aplica, de forma constante, la tasa media logarítmica de 2037–2042 de cada municipio. Esa extensión se marca como *estimado*.
- **Disposición final (SSPD):** para 2019–2024 se toman las bases de los informes nacionales; las toneladas se suman por municipio atendido entre sitios. Para 2018 se usa el Anexo 1 del informe en PDF (promedio ton/día × 365, que difiere entre 1 y 2 % del total anual del resumen del informe).
- **Vida útil de los rellenos:** se usa la fecha final de vida útil licenciada del sitio principal. La capacidad remanente de la ciudad se asigna en proporción a su disposición: los años de vida útil del sitio se multiplican por la disposición de la ciudad. Esa vida útil corresponde a la licencia y cambia entre informes cuando la licencia se modifica.
- **Aprovechamiento (SSPD):** toneladas por familia de material (papel y cartón, plásticos, vidrio, metales, madera y textil). Solo incluye la actividad de aprovechamiento del servicio público y no incluye orgánicos. Por eso se compara solo con los materiales recuperados del modelo.
- **ECA:** se suma la capacidad operativa (t/mes × 12) y se excluyen los valores de relleno (9999).
- **Recolectado observado:** dispuesto + aprovechado. La generación se obtiene dividiendo por la cobertura, que no viene en estas bases y se mantiene como supuesto (95 %).
- **Totales anuales y flujos instantáneos:** las observaciones son totales anuales. Una iteración de punto fijo reajusta la condición inicial hasta que el total simulado del primer año reproduce el observado.
- **Controles de calidad** (`core/quality.py`):
  - Si el aprovechamiento supera el 20 % del flujo, se excluye de la calibración y se acota en la condición inicial (Bogotá, Villavicencio).
  - Se señalan los saltos interanuales del dispuesto mayores a 40 %.
  - Se señala la disposición en botaderos o celdas.
  - Se señala la vida útil vencida o inestable.
- **Registros documentales:** valores puntuales con URL en `data/raw/registros_documentales.csv`.
- **Respaldo nacional**, usado solo cuando falta el dato de la ciudad: 0,75 kg/hab/día (DNP, CEMPRE y CEPAL, 2021) y 70 % de orgánicos (CATF, 2024).
- **Calidad:** cada fila declara tipo, fuente y calidad. Cada ciudad tiene un indicador de completitud sobre 11 variables del perfil y un conteo de años con serie histórica.

## 3. Modelo

Es un modelo de Dinámica de Sistemas con 8 niveles y 8 bucles de realimentación explícitos (ver `equations.md`). Decisiones de diseño:

- **Palancas relativas a la brecha.** Un escenario cierra una fracción de la distancia entre la condición inicial de cada ciudad y su techo físico. Así no se imponen valores homogéneos.
- **Restricciones físicas duras.** Lo separado nunca supera lo recolectado, y lo procesado nunca supera la capacidad instalada. Si se agota la capacidad de disposición, el exceso se contabiliza como **déficit**, en lugar de desaparecer del balance.
- **Paso temporal.** Δt = 0,25 años; la prueba de convergencia con Δt = 1/16 da un error menor a 1 %.
- **Dos modos.** El educativo muestra un subconjunto de niveles y parámetros. El científico muestra todos, junto con el diagnóstico de balance.

## 4. Verificación, calibración y validación

1. **Verificación estructural** (`tests/test_mass_balance.py`): cierre del balance, no negatividad, restricciones físicas, condiciones extremas, convergencia temporal y reproducción de la condición inicial.
2. **Calibración** (`validation/calibration.py`): mínimos cuadrados acotados sobre la disposición y, cuando es utilizable, el aprovechamiento.
   - Por parsimonia, solo se calibran γ (tasa per cápita de corto plazo) y, con al menos 3 años de aprovechamiento en el ajuste, p (adopción espontánea).
   - γ converge hacia g_lr con τ = 5 años, para no extrapolar a 2050 una tendencia de 5 años.
   - En muchas capitales γ queda en el límite de ±3 %/año, porque la disposición reportada no acompaña el crecimiento poblacional proyectado por el DANE. Se informa en el perfil de la ciudad.
3. **Validación fuera de muestra:** los dos últimos años observados se reservan cuando la serie conserva al menos 3 años para el ajuste. Métricas: MAE, RMSE, sMAPE, sesgo medio y R².
4. **Experimento gemelo:** con datos sintéticos generados por el propio modelo, la calibración recupera γ con un error menor a 0,004 (`tests/test_validation.py`). Esto valida el *procedimiento*, no el modelo.
5. **Confiabilidad A–D** (`validation/reliability.py`). Un modelo que solo superó pruebas de programación nunca se califica como validado.

## 5. Incertidumbre

- **De parámetros:** Monte Carlo con distribución triangular en el rango del registro, con moda en el valor usado; los parámetros medidos no se muestrean. La semilla es reproducible y las muestras se pueden exportar.
- **Local:** tornado con los extremos del rango de cada parámetro.
- **Global:** cribado de Morris (μ*, σ). Sobol no se ejecuta en línea por su costo, mayor a 10⁴ simulaciones.
- **De escenario:** se explora comparando escenarios.
- **Estructural:** forma funcional de difusión, aprendizaje, mercado e inversión. Se documenta, pero no se representa en las bandas.

## 6. Limitaciones conocidas

- La cobertura de recolección no está en las bases cargadas y se supone en 95 %.
- La composición física por ciudad no está cargada. En Medellín, Barranquilla, Montería, Bogotá y Villavicencio, el aprovechamiento reportado supera el que el modelo puede reproducir con 20 % de reciclables: se recomienda ingresar la caracterización del PGIRS.
- Las series de Leticia, Arauca, Quibdó, Inírida y Cali tienen discontinuidades fuertes (cambios de reporte o de sitio), y su validación es pobre (nivel C).
- La capacidad remanente de los rellenos rara vez se publica de forma comparable. Los rellenos regionales compartidos, como Colomba–El Guabal o La Pradera, requieren asignar a cada municipio una fracción de su capacidad. Esa asignación aún no está implementada: cuando existe un registro, la vida útil reportada es la del relleno completo.
- El aprovechamiento reportado a la SSPD por la actividad de aprovechamiento puede incluir material de fuera del municipio y discontinuidades de reporte. Estas inconsistencias deben revisarse antes de calibrar.
- Las coordenadas son aproximadas y solo tienen uso cartográfico. Los mapas coropléticos municipales requieren geometrías oficiales (MGN del DANE), que no están incluidas.
