# Documentación funcional — Herramienta de análisis de datos operacionales AS/RS

**Proyecto:** Sistema de análisis de datos para la optimización del mantenimiento en un almacén logístico automatizado del sector logístico
**Stack:** Python + Streamlit + pandas (datos simulados representativos de la instalación real)
**Propósito del documento:** Especificación funcional previa al desarrollo. Define cada módulo, qué visualiza, qué calcula, qué filtra y cómo se navega.

---

## 1. Visión general

### 1.1. Problema que resuelve

El sistema WMS/WCS de la instalación registra automáticamente cada incidencia (hora de fallo, equipo, código de error, hora de recuperación) y cada misión de los equipos, pero esos datos quedan sin explotar. No existe ningún mecanismo que los transforme en indicadores de mantenimiento. En concreto, no se calcula:

- El **MTTR** (tiempo medio de reparación) por equipo ni por zona.
- El **MTBF** (tiempo medio entre fallos) por equipo.
- La **disponibilidad** individual de cada equipo.
- Patrones de fallo (recurrencia por código de error, concentración geográfica, evolución temporal).

La herramienta cubre ese vacío: ingiere los datos en el mismo esquema que produce el WMS/WCS y los convierte en información accionable para la toma de decisiones de mantenimiento.

### 1.2. Alcance y naturaleza de los datos

Por confidencialidad, la herramienta opera sobre **datos simulados** que reproducen fielmente el esquema, los rangos y los patrones de comportamiento de la instalación real. Esto permite demostrar toda la funcionalidad sin exponer información de la empresa. El esquema de los datos simulados es idéntico al del WMS/WCS, de modo que la migración a datos reales en el futuro no requeriría reescribir la lógica de análisis.

### 1.3. Contexto de la instalación (parámetros de simulación)

| Elemento | Cantidad | Características |
|---|---|---|
| Pasillos (single-depth) | 20 | 12 alturas, ~26.880 ubicaciones por cara de pasillo |
| Transelevadores SRM | 20 (uno por pasillo) | Monomástil, ~50 km/h, telemetría dual (encoder + láser) en ejes X e Y |
| STV anillo de entrada | 20 | Cuna simple |
| STV anillo de salida | 10 | Doble cuna (dos pallets simultáneos para capacidad de ciclo) |
| Control | — | PLCs Siemens S7-300/400 sobre Profibus |
| Régimen de operación | 24 h | 3 turnos, operativa *lights-out* |

---

## 2. Modelo de datos ✅

La herramienta se apoya en cuatro tablas que replican el esquema del WMS/WCS.

### 2.1. Tabla `eventos_incidencia`

Registro de cada avería detectada.

| Campo | Tipo | Descripción |
|---|---|---|
| `id_evento` | int | Identificador único del evento |
| `id_equipo` | str | FK a `equipos.id` |
| `codigo_error` | str | FK a `tipos_error.codigo` |
| `ts_inicio_fallo` | datetime | Instante en que el WMS/WCS registra el fallo |
| `ts_recuperacion` | datetime | Instante en que el equipo vuelve a estar operativo |
| `estado` | str | `resuelto` / `en_curso` |

### 2.2. Tabla `equipos`

Inventario de equipos.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | str | Identificador único (p. ej. `SRM-07`, `STV-E-12`, `STV-S-03`) |
| `tipo` | str | `SRM` / `STV` |
| `zona` | str | `anillo_entrada` / `anillo_salida` / `pasillo` |
| `estado_operativo` | str | `operativo` / `fuera_servicio` / `mantenimiento` |

> Nota de diseño: para los STV conviene un subcampo o convención de `id` que distinga anillo de entrada (cuna simple) y anillo de salida (doble cuna), porque el módulo 3 los analiza por separado.

### 2.3. Tabla `misiones`

Registro de cada movimiento ejecutado por un equipo.

| Campo | Tipo | Descripción |
|---|---|---|
| `id_mision` | int | Identificador único |
| `id_equipo` | str | FK a `equipos.id` |
| `posicion_inicial` | str | Coordenada/ubicación de origen |
| `posicion_final` | str | Coordenada/ubicación de destino |
| `ts_inicio` | datetime | Inicio de la misión |
| `ts_fin` | datetime | Fin de la misión |
| `estado` | str | `completada` / `abortada` / `rechazada` |

### 2.4. Tabla `tipos_error`

Catálogo de códigos de error.

| Campo | Tipo | Descripción |
|---|---|---|
| `codigo` | str | Código de error (FK desde `eventos_incidencia`) |
| `descripcion` | str | Descripción legible |
| `duracion_media_min` | int | Duración media de reparación (minutos), usada por el simulador como media de la lognormal que sortea la duración real de cada fallo |

> **Nota — atributos que dependen del equipo, no del código:**
> La *criticidad operativa* (impacto en el flujo del almacén) es un atributo del equipo, no del fallo: cualquier avería en una STV detiene un anillo entero (crítica), mientras que una avería en un SRM solo afecta a su pasillo (media). Se guarda en la columna `criticidad` de la tabla `equipos`.
>
> Anteriormente existían columnas `categoria` y `severidad` en `tipos_error` que se han eliminado: la primera porque no existe en los sistemas reales (el WCS solo da el código de error), y la segunda porque mezclaba "duración del fallo" con "impacto en el flujo", dos conceptos que ahora viven separados (`duracion_media_min` por código de error, `criticidad` por equipo).

---

## 3. Definición de los KPIs ✅

Los cálculos son comunes a varios módulos, por lo que se definen una sola vez aquí y se reutilizan.

### 3.1. MTTR (Mean Time To Recovery)

**Criterio adoptado:** se mide desde que el WMS/WCS registra el fallo hasta que el equipo vuelve a operar.

> Justificación del criterio: no se mide el tiempo de respuesta del técnico porque el uso de tablets para rearme remoto desacopla la intervención física del momento de recuperación. El indicador relevante para la disponibilidad de la instalación es el tiempo total que el equipo está caído, no el tiempo que tarda un técnico en llegar. Esto debe documentarse explícitamente porque condiciona la interpretación de todos los demás KPIs.

```
duracion_fallo_i = ts_recuperacion_i − ts_inicio_fallo_i

MTTR(equipo) = Σ duracion_fallo_i / nº de fallos resueltos del equipo
```

Se calcula solo sobre eventos con `estado = resuelto`. Unidad de salida: minutos u horas (configurable).

### 3.2. MTBF (Mean Time Between Failures)

```
tiempo_operativo_total = tiempo_calendario_del_periodo − Σ duracion_fallo_i

MTBF(equipo) = tiempo_operativo_total / nº de fallos del equipo
```

El tiempo de calendario se acota al rango de fechas del filtro activo.

### 3.3. Disponibilidad

```
Disponibilidad(equipo) = MTBF / (MTBF + MTTR)
```

Equivalente operacional:

```
Disponibilidad(equipo) = tiempo_operativo / tiempo_total_del_periodo
```

Se expresa en porcentaje. Es el indicador resumen que el tribunal y la dirección leen primero.

### 3.4. Ciclos

Número de misiones completadas por un equipo en el periodo. Para los SRM, un ciclo equivale a una misión de almacenamiento o extracción. Para los STV de doble cuna del anillo de salida, debe contemplarse que una misión puede transportar dos pallets, lo que afecta a la capacidad de ciclo.

### 3.5. Tiempo de ciclo

```
tiempo_ciclo_i = ts_fin_i − ts_inicio_i      (sobre misiones completadas)
```

Se analiza por su media, su distribución y su evolución temporal.

---

## 4. Arquitectura de navegación ✅

Aplicación Streamlit multipágina. Barra lateral (`st.sidebar`) persistente con los filtros comunes; el cuerpo cambia según el módulo seleccionado.

```
┌─ Barra lateral (filtros globales) ────────────┐
│  • Rango de fechas                            │
│  • Tipo de equipo (SRM / STV / todos)         │
│  • Zona (entrada / salida / pasillo / todas)  │
│  • Selector de módulo                         │
└───────────────────────────────────────────────┘

  0. Resumen general (home / dashboard)
  1. Fallos por zona y equipo
  2. Rendimiento de transelevadores SRM
  3. Rendimiento de STV
  4. Obstrucciones y rechazos
  5. Expedición y rendimiento del anillo de salida
```

### 4.1. Filtros comunes

Presentes en todos los módulos, en la barra lateral, y aplicados de forma transversal a los datos antes de cualquier cálculo:

- **Rango de fechas:** selector de fecha inicio/fin. Acota el periodo de todos los KPIs.
- **Tipo de equipo:** `SRM` / `STV` / todos.
- **Zona:** `anillo_entrada` / `anillo_salida` / `pasillo` / todas.

### 4.2. Vista de evolución anual

Todos los módulos incluyen una vista de evolución temporal (serie mensual a lo largo del año) del indicador principal del módulo, para detectar tendencias y estacionalidad.

---

## 5. Módulo 0 — Resumen general ✅

**Propósito:** pantalla de entrada. Vista de 30 segundos del estado de la instalación.

**Qué visualiza:**
- KPIs globales en tarjetas (`st.metric`): disponibilidad media de la instalación, nº total de fallos del periodo, MTTR medio, MTBF medio, ciclos totales.
- Gráfica de evolución anual de la disponibilidad media.
- Top 5 de equipos con peor disponibilidad (tabla resumen con acceso a su detalle).

**Cálculos:** agregados de los KPIs de la sección 3 sobre todo el parque, respetando filtros.

**Filtros:** los tres comunes.

---

## 6. Módulo 1 — Fallos por zona y equipo ✅

**Propósito:** localizar dónde y en qué equipos se concentran los fallos, e incorporar la posición del equipo en el momento del fallo.

**Qué visualiza:**
- **Ranking de equipos por nº de fallos** (barras horizontales ordenadas).
- **Ranking por zona** (entrada / salida / pasillos).
- **Posición del equipo en el momento del fallo:** para cada evento, se cruza con la misión activa en `ts_inicio_fallo` para situar geográficamente dónde se produjo el fallo (altura, ubicación, tramo del anillo). Mapa de calor o dispersión por ubicación.
- Evolución anual del nº de fallos.

**Cálculos:**
- Conteo de eventos agrupado por `id_equipo` y por `zona`.
- Cruce `eventos_incidencia` × `misiones` para asignar posición al fallo (la misión cuyo intervalo `[ts_inicio, ts_fin]` contiene `ts_inicio_fallo`).

**Filtros:** solo los tres comunes (fechas, tipo de equipo, zona).

---

## 7. Módulo 2 — Rendimiento de transelevadores SRM ✅

**Propósito:** evaluar individualmente los 20 SRM, el corazón de la instalación.

**Qué visualiza:**
- Tabla comparativa de los 20 SRM: MTTR, MTBF, disponibilidad y ciclos por equipo.
- **Gráfica de disponibilidad por SRM** (barras), con línea de referencia del objetivo/medio.
- Detalle individual al seleccionar un SRM: sus KPIs, su histórico de fallos (con duración real en minutos por evento) y su evolución anual de disponibilidad.
- Relación ciclos vs. fallos (¿los equipos más solicitados fallan más?).

**Cálculos:** MTTR, MTBF, disponibilidad y ciclos (sección 3) calculados por equipo para `tipo = SRM`.

**Filtros:** rango de fechas; zona implícita (pasillos); selector de SRM individual.

---

## 8. Módulo 3 — Rendimiento de STV ✅

**Propósito:** evaluar los STV diferenciando los dos anillos, porque tienen configuración distinta (cuna simple en entrada, doble cuna en salida) y su comportamiento no es comparable directamente.

**Qué visualiza:**
- KPIs (MTTR, MTBF, disponibilidad, ciclos) **segmentados por anillo**: 20 STV de entrada vs. 10 STV de salida.
- Tabla comparativa intra-anillo.
- Gráficas de disponibilidad por STV dentro de cada anillo.
- Detalle individual por STV.
- Evolución anual por anillo.

**Cálculos:** los mismos KPIs, agrupados primero por `zona` (entrada/salida) y luego por equipo. La doble cuna del anillo de salida se tiene en cuenta al interpretar ciclos y capacidad.

**Filtros:** rango de fechas; selector de anillo (entrada / salida / ambos); selector de STV individual.

---

## 9. Módulo 4 — Obstrucciones y rechazos ✅

**Propósito:** analizar los rechazos y obstrucciones, que tienen una doble dimensión.

- **Dimensión de mantenimiento:** rechazos por sensores del inspector de pallets descalibrados. Son fallos corregibles que generan falsos rechazos.
- **Dimensión operativa:** saturación del anillo. Reducir rechazos desatura el anillo y libera a los operarios de los puestos de rechazo.

**Qué visualiza:**
- **Distribución geográfica de rechazos** (en qué puntos del anillo / inspectores se concentran).
- Ranking de puntos de inspección por nº de rechazos.
- Separación entre rechazos de causa de mantenimiento (sensor) y de causa operativa (saturación), en la medida en que el código de error lo permita.
- Tasa de rechazo: rechazos / misiones totales.
- Evolución anual de la tasa de rechazo.

**Cálculos:**
- Filtrado de `misiones` con `estado = rechazada` y de eventos asociados a posicionamiento/inspección.
- Agrupación geográfica por `posicion` del rechazo.
- Tasa de rechazo = nº rechazos / nº misiones, por punto y global.

**Filtros:** rango de fechas; zona (anillos).

---

## 10. Módulo 5 — Expedición y rendimiento del anillo de salida ✅

**Propósito:** medir el rendimiento de la expedición, centrado en los tiempos de ciclo del anillo de salida (los 10 STV de doble cuna).

**Qué visualiza:**
- Tiempo de ciclo medio del anillo de salida y su distribución (histograma / boxplot).
- Tiempos de ciclo por STV de salida.
- Throughput de expedición (pallets/hora), teniendo en cuenta la doble cuna.
- Identificación de cuellos de botella (STV con tiempos de ciclo atípicos).
- Evolución anual del tiempo de ciclo medio.

**Cálculos:**
- Tiempo de ciclo (sección 3.5) sobre misiones completadas de STV de salida.
- Throughput = pallets expedidos / tiempo, considerando que una misión de doble cuna puede mover dos pallets.
- Estadísticos de distribución (media, mediana, percentiles).

**Filtros:** rango de fechas; selector de STV de salida individual.

---

## 11. Notas de implementación para el desarrollo

- **Generador de datos simulados:** ✅ `scripts/generar_datos.py` — 4,84 M misiones · 9.700 eventos · estacionalidad · correlación ciclos↔fallos · coherencia temporal verificada con 10 tests.
- **Capa de cálculo separada de la capa de visualización:** ✅ `src/kpis.py` — funciones puras de pandas, 23 tests unitarios verdes, cero `import streamlit`.
- **Cacheo:** `@st.cache_data` aplicado mediante `st.cache_data(cargar_tablas)` en cada página, manteniendo `src/data_loader.py` libre de dependencias de Streamlit.
- **Internacionalización de unidades:** parámetro global `UNIDAD_TIEMPO` en `src/config.py` para mostrar tiempos en minutos u horas.
- **Inicialización de filtros globales:** ✅ `src/config.py` expone `init_session_state()`, llamada al inicio de cada página. Garantiza que `rango_fechas`, `tipos_equipo` y `zonas` tienen valores por defecto (año completo, todos los equipos, todas las zonas) aunque el usuario navegue directamente a una subpágina sin pasar por `app.py`.
- **Evolución anual de disponibilidad:** ✅ `src/kpis.py` — función `disponibilidad_mensual()` que recorta (clip) los eventos que cruzan límite de mes al sub-rango de cada mes, para un cálculo correcto de disponibilidad mensual media.
- **Roadmap de producto:** migración a datos reales del WMS/WCS manteniendo el mismo esquema y la misma capa de cálculo; despliegue como webapp persistente conectada a base de datos (línea Next.js + base de datos gestionada) e integración con la herramienta Grafana de monitorización en tiempo real ya en marcha en la instalación.