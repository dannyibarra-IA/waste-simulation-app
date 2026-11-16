# Manual de usuario

## Barra lateral (afecta a todos los módulos)

- **Idioma:** ES o EN.
- **Región, Departamento y Ciudad de análisis:** los filtros acotan la lista de ciudades; la ciudad elegida alimenta los módulos 2 a 7, 9 y 10.
- **Escenarios a comparar:** elija cuatro o más. El BAU se incluye siempre como referencia. El **escenario principal** es el que se muestra en mapas y tarjetas.
- **Año de referencia:** año que usan las tarjetas, los mapas y los rankings.
- **Modo:** el educativo simplifica; el científico muestra todos los niveles, parámetros y diagnósticos.
- **Ajustes de política:** activan cambios sobre las palancas de todos los escenarios comparados. Puede ajustar el año de implementación, la velocidad de adopción, la intensidad, la participación, la eficiencia de recuperación, los rechazos, la capacidad instalada, las interrupciones y la ampliación de la disposición.
- **Parámetros de la ciudad:** modifican solo la ciudad de análisis y quedan registrados como «ajustado por el usuario» en el manifiesto.

## Cómo leer los resultados

- Las etiquetas *observado*, *proyección oficial*, *estimado*, *supuesto* y *simulado* acompañan cada cifra.
- En los gráficos, la línea continua con marcadores es un dato observado u oficial; la línea discontinua es simulada.
- Los avisos amarillos indican que la cifra depende de supuestos, por ejemplo una capacidad de relleno no reportada.
- En mapas y rankings, el asterisco (*) o el color arena marcan una ciudad exploratoria.

## Módulos

| # | Módulo | Para qué sirve |
|---|---|---|
| 1 | Observatorio nacional | Mapa de las 32 capitales, ranking, animación nacional y completitud de datos |
| 2 | Perfil de ciudad | DIVIPOLA, inventario de variables con fuente, parámetros usados, confiabilidad y limitaciones |
| 3 | Tendencias históricas | Población DANE (oficial y estimada), series SSPD frente a simulación y desacoplamiento |
| 4 | Composición | Fracciones usadas y potencial material frente a lo recuperado |
| 5 | Simulación dinámica | Niveles por escenario, bucles con sus ecuaciones y diagnóstico de balance |
| 6 | Escenarios | Comparación de disposición, aprovechamiento, capacidad remanente y desviación frente al BAU |
| 7 | Flujos | Sankey del balance de materia y curvas de utilización de capacidad |
| 8 | Comparación | Dispersión, barras per cápita, mapa de calor y tabla con cobertura de datos |
| 9 | Riesgos y alertas | Consola de alertas e índice de prioridad con umbrales absolutos y pesos ajustables |
| 10 | Sensibilidad e incertidumbre | Monte Carlo con semilla, tornado y Morris |
| 11 | Metodología y fuentes | Ecuaciones, registro de parámetros, fuentes, diccionario y estado de calibración |
| 12 | Descargas | CSV, Excel, manifiesto JSON, paquete ZIP reproducible e informe PDF |

## Reproducir una ejecución

1. En **Descargas**, baje el paquete ZIP.
2. En una copia del repositorio con la versión de código indicada, copie `rerun.py`, `manifest.json` y `resultados.csv` a la raíz.
3. Ejecute `python rerun.py manifest.json`. La diferencia reportada debe ser 0.
