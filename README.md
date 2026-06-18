# Del log del WMS a la decisión de mantenimiento

> Dashboard de KPIs de mantenimiento para almacenes automáticos (AS/RS).
> Convierte los registros crudos de un WMS/WCS en MTTR, MTBF, disponibilidad
> y patrones de fallo accionables a nivel de equipo, zona y celda.

[![Demo en vivo](https://img.shields.io/badge/demo-en%20vivo-2ea44f?style=for-the-badge)](https://dashboard-kpis-mantenimiento-asrs-ep8nttdf9imwcwvdnhhzpx.streamlit.app)

![CI](https://github.com/raulalba14-svg/dashboard-kpis-mantenimiento-asrs/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.40+-FF4B4B.svg)
![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)
![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC.svg)

## Aplicación en vivo

**[Abrir la demo en vivo →](https://dashboard-kpis-mantenimiento-asrs-ep8nttdf9imwcwvdnhhzpx.streamlit.app)**

No requiere instalación. La app está desplegada en Streamlit Cloud y opera sobre
un dataset sintético de ~1 año de operación.

---

## El problema que resuelve

Un almacén automático genera miles de registros al día en su WMS/WCS: misiones,
tiempos, códigos de error, paradas. Esos datos existen, pero rara vez se traducen
en **decisiones de mantenimiento**: ¿qué transelevador para más?, ¿qué código de
error concentra las averías?, ¿la carga de trabajo predice los fallos?, ¿voy mejor
o peor que el semestre pasado?

Este dashboard cierra ese hueco. Toma el log crudo y lo convierte en los KPIs que
un equipo de mantenimiento usa para **priorizar**: MTTR, MTBF, disponibilidad y
patrones de fallo, desglosados por equipo, por zona y por celda — con una síntesis
en cada pantalla que indica, en una frase, qué mirar primero.

> Diseñado a partir de experiencia previa en mantenimiento electromecánico
> industrial: los KPIs seleccionados (MTTR, MTBF, disponibilidad y patrones de
> fallo) son los que se utilizan en planta para priorizar ventanas de
> mantenimiento, no métricas elegidas desde fuera.

---

## Capturas

| | |
|---|---|
| ![Resumen general](assets/screenshots/00_resumen.png) | ![Plano de fallos](assets/screenshots/01_fallos.png) |
| **Resumen general** — gauge de disponibilidad vs. objetivo, KPIs en rejilla, evolución mensual y los 5 equipos que peor van, con síntesis ejecutiva en semáforo. | **Mapa de fallos** — sinóptico de la instalación coloreado por tasa de fallos/día: detecta al instante qué equipo está en rojo. |
| ![Rendimiento SRM](assets/screenshots/02_srm.png) | ![Comparativa de periodos](assets/screenshots/04_comparativa.png) |
| **Rendimiento por equipo** — MTTR/MTBF/disponibilidad por transelevador, heatmap del alzado y la relación carga ↔ averías con correlación. | **Comparativa de periodos** — tarjetas A vs B con mini-barras y variación de cada KPI: ¿voy mejor o peor que antes? |

---

## Qué KPIs calcula

Todos los indicadores se calculan a partir del log, por equipo y agregados, y son
descargables en CSV desde la propia app:

- **MTTR** (Mean Time To Repair) — tiempo medio de reparación, por equipo y global.
- **MTBF** (Mean Time Between Failures) — tiempo medio entre fallos.
- **Disponibilidad** — % de tiempo operativo frente al objetivo de servicio.
- **Disponibilidad mensual** — serie temporal para ver tendencia y estacionalidad.
- **Ciclos / tiempo de ciclo** — carga real de trabajo de cada equipo.
- **Patrón de fallos** — concentración por zona, por código de error y posición
  en el alzado (heatmap de celda).
- **Tasa de rechazo** — pallets rechazados por la inspección, por inspector y motivo.
- **Expedición** — tiempo de completado de cada pedido, throughput y cuellos de botella.
- **Variación entre periodos** — delta de cada KPI entre dos rangos de fechas.

---

## Funciones que van más allá de los números

Calcular los KPIs es solo la mitad: el dashboard también los **interpreta y los deja
llevarse a Excel**. Tres capas de funcionalidad lo separan de un gráfico estático:

### 🟢 Síntesis ejecutiva con semáforo

Cada módulo abre con una **lectura ejecutiva**: una o dos frases que traducen los
datos del periodo a una conclusión accionable — qué equipo es el más crítico, si la
carga explica los fallos (con su coeficiente de correlación), qué zona concentra las
averías. La síntesis se **recalcula con los filtros activos** y se tiñe como
**semáforo** (verde / ámbar / rojo) según la disponibilidad media frente al objetivo
del 95 %, de modo que el estado de la instalación se capta antes de leer una sola cifra.

### 📊 Visualizaciones operacionales

No son gráficos por defecto: cada visual responde a una pregunta de mantenimiento.

- **Gauge de disponibilidad vs. objetivo** — medidor con la línea del 95 % para ver de
  un vistazo si la instalación está dentro o fuera de objetivo.
- **Plano sinóptico con semáforo de salud** — el layout de la instalación coloreado por
  **tasa de fallos/día** (no por número absoluto), con cortes calibrados por tipo de
  equipo. El mismo color significa lo mismo sea cual sea el rango de fechas.
- **Heatmap del alzado del pasillo** — posición física (altura × columna) donde se
  concentran los fallos dentro de cada transelevador.
- **Dispersión carga ↔ fallos** — ¿los SRM más solicitados averían más? Scatter con
  correlación para decidir si conviene mantenimiento preventivo basado en ciclos.
- **Tarjetas comparativas A vs B** — mini-barras proporcionales y chip de variación
  por KPI, con aviso automático si los dos periodos tienen distinta duración.

### 📥 Exportación a CSV (formato Excel ES)

Cada módulo incluye un panel **«Descargar datos del módulo»** con un botón por dataset
derivado (KPIs, series mensuales, top 5, comparativas…). La descarga aplica **los
filtros activos** y usa separador `;`, decimal `,` y BOM UTF-8 para que Excel en
español abra el archivo con las tildes y los números correctos sin retoques.

---

## Las pantallas y qué pregunta responde cada una

| Módulo | Responde a… |
|---|---|
| **Resumen general** | ¿Cómo va la instalación en conjunto y qué equipos arrastran el dato? |
| **Fallos por zona y equipo** | ¿Dónde se concentran las averías? ¿Qué código de error domina? |
| **Rendimiento SRM** | ¿Cómo está cada transelevador? ¿La carga explica sus fallos? |
| **Rendimiento STV** | ¿Cómo está el anillo de vehículos? ¿Hay uno que frene al resto? |
| **Rechazos** | ¿Cuántos pallets rechaza la inspección y por qué motivo? |
| **Expedición** | ¿Cuánto tarda cada pedido en completarse y dónde están los cuellos de botella? |
| **Comparativa de periodos** | ¿Voy mejor o peor que antes? ¿Qué equipos han regresado? |
| **Acerca del proyecto** | Contexto, alcance del dataset y roadmap. |

---

## Stack y arquitectura

**Streamlit · pandas · Plotly**, sobre una arquitectura limpia pensada para que el
día de mañana se enchufe a datos reales sin reescribir la lógica:

```
I/O (carga/filtrado)  ↔  cálculo (funciones puras)  ↔  presentación (charts/UI)
```

- **Capa de cálculo pura** ([src/kpis.py](src/kpis.py)) — sin Streamlit, sin estado,
  sin efectos colaterales. Recibe DataFrames, devuelve DataFrames. Es lo que está
  cubierto por tests y lo que sobreviviría a un cambio de origen de datos.
- **Capa de I/O** ([src/data_loader.py](src/data_loader.py)) — carga y filtrado
  aislados del resto.
- **Capa de presentación** ([src/charts.py](src/charts.py), [pages/](pages/)) — los
  helpers de Plotly devuelven figuras, no pintan; cada módulo es un archivo.
- **Capa de interpretación** ([src/insights.py](src/insights.py)) — funciones puras que
  generan la síntesis ejecutiva de cada módulo a partir de los DataFrames filtrados.
- **Exportación** ([src/export.py](src/export.py)) — panel de descarga CSV (formato
  Excel ES) reutilizado por todos los módulos, sin duplicar lógica.
- **Tests con pytest** ([tests/](tests/)) — cubren los KPIs y la coherencia del dataset.
- **CI con GitHub Actions** ([.github/workflows/tests.yml](.github/workflows/tests.yml)) —
  los tests corren en cada push.
- **Docker** — imagen reproducible que genera el dataset en el build.
- **Desplegado** en Streamlit Cloud.

---

## Sobre los datos (importante)

El dataset es **100% sintético** y se genera por código ([scripts/generar_datos.py](scripts/generar_datos.py)).
La topología está **despersonalizada a propósito** — una configuración genérica de
**8 pasillos con un transelevador (SRM) cada uno** servidos por un **anillo único de
vehículos de transferencia (STV)** — que reproduce el *esquema* de un WMS/WCS real
sin contener ningún dato, instalación, marca ni cliente reales. El generador
correlaciona los fallos con la carga de misiones para que los KPIs sean realistas.

---

## Ejecutar en local

<details>
<summary>Instrucciones de instalación y ejecución</summary>

Requiere **Python 3.11+**.

```bash
# 1. Dependencias
pip install -r requirements.txt

# 2. Generar el dataset sintético (semilla fija → reproducible)
python scripts/generar_datos.py --semilla 42 --salida data/

# 3. Arrancar la app
streamlit run app.py        # http://localhost:8501

# 4. Tests
pytest tests/ -v
```

**Con Docker** (genera el dataset en el build, no necesitas Python local):

```bash
docker build -t analisis-asrs .
docker run -p 8501:8501 analisis-asrs   # http://localhost:8501
```

</details>

---

## Roadmap

- Conexión a datos reales del WMS/WCS reutilizando la misma capa de cálculo.
- Despliegue como webapp persistente sobre base de datos gestionada.

---

## Sobre mí

**Raúl Alba Cabello** — electromecánico de mantenimiento industrial reconvertido a
datos y desarrollo. Mi nicho es la intersección de **mantenimiento + KPIs en
almacenes automáticos (AS/RS)**: conozco la planta y los datos, y este proyecto es
mi forma de demostrar que ambos lados se hablan.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Raúl%20Alba%20Cabello-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/ra%C3%BAl-alba-cabello-17784575)
