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
| Pasillos (doble fondo) | 8 | 16 alturas × 48 columnas por cara, ~98.300 ubicaciones en total |
| Transelevadores SRM | 8 (uno por pasillo) | Bimástil, ~160 m/min traslación · ~35 m/min elevación, telemetría dual (encoder + láser) en ejes X e Y |
| Transportadores de pasillo | 16 | Uno de entrada y uno de salida por pasillo (cinta/rodillos); contexto operativo, sin KPIs propios |
| Control | — | PLCs Beckhoff (TwinCAT) sobre EtherCAT |
| Régimen de operación | 24 h | 3 turnos, operativa *lights-out* |

> No hay anillo de transporte ni vehículos de transferencia: cada transelevador coge los pallets de su transportador de entrada para ubicarlos y los deposita en el de salida al extraerlos. Recepción y preparación quedan fuera del alcance de los KPIs.

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
| `id` | str | Identificador único (p. ej. `SRM-03`, `SRM-07`) |
| `tipo` | str | `SRM` |
| `zona` | str | `pasillo` |
| `estado_operativo` | str | `operativo` / `fuera_servicio` / `mantenimiento` |

> Nota de diseño: la instalación tiene un único tipo de equipo con KPIs (el transelevador). Los campos `tipo` y `zona` se conservan en el esquema para que la migración a una instalación con más tipos de equipo no requiera cambios estructurales.

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
| `estado` | str | `completada` / `abortada` |

### 2.4. Tabla `tipos_error`

Catálogo de códigos de error.

| Campo | Tipo | Descripción |
|---|---|---|
| `codigo` | str | Código de error (FK desde `eventos_incidencia`) |
| `descripcion` | str | Descripción legible |
| `duracion_media_min` | int | Duración media de reparación (minutos), usada por el simulador como media de la lognormal que sortea la duración real de cada fallo |

> **Nota — el catálogo solo guarda lo que produce el WCS:**
> El catálogo `tipos_error` mantiene únicamente `codigo`, `descripcion` y `duracion_media_min`. Anteriormente se barajaron columnas `categoria` y `severidad`, descartadas: la primera porque no existe en los sistemas reales (el WCS solo da el código de error) y la segunda porque mezclaba "duración del fallo" con "impacto operativo". La duración media de reparación por código (`duracion_media_min`) es el único atributo que el simulador necesita para sortear la duración real de cada fallo.

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

Número de misiones completadas por un transelevador en el periodo. Un ciclo equivale a una misión de almacenamiento o extracción.

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
│  • Tipo de equipo (SRM)                       │
│  • Zona (pasillo)                             │
│  • Selector de módulo                         │
└───────────────────────────────────────────────┘

  0. Resumen general (home / dashboard)
  1. Fallos por pasillo y equipo
  2. Rendimiento de transelevadores SRM
  6. Comparativa de periodos
```

### 4.1. Filtros comunes

Presentes en todos los módulos, en la barra lateral, y aplicados de forma transversal a los datos antes de cualquier cálculo:

- **Rango de fechas:** selector de fecha inicio/fin. Acota el periodo de todos los KPIs.
- **Tipo de equipo:** `SRM` (único tipo con KPIs).
- **Zona:** `pasillo` (única zona).

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

## 6. Módulo 1 — Fallos por pasillo y equipo ✅

**Propósito:** localizar en qué pasillos y transelevadores se concentran los fallos, e incorporar la posición del equipo en el momento del fallo.

**Qué visualiza:**
- **Plano de la instalación:** los 8 pasillos en paralelo coloreados por intensidad de fallos del SRM que los sirve.
- **Ranking de transelevadores por nº de fallos** (barras horizontales ordenadas).
- **Ranking por código de error** (top 10).
- **Posición del equipo en el momento del fallo:** para cada evento se cruza con la misión activa en `ts_inicio_fallo` para situar la ubicación exacta (pasillo, altura, columna). Mapa de calor de alzado del pasillo seleccionado.
- Evolución anual del nº de fallos.

**Cálculos:**
- Conteo de eventos agrupado por `id_equipo` y por `codigo_error`.
- Cruce `eventos_incidencia` × `misiones` para asignar posición al fallo (la misión cuyo intervalo `[ts_inicio, ts_fin]` contiene `ts_inicio_fallo`).

**Filtros:** los comunes (fechas, tipo de equipo, zona).

---

## 7. Módulo 2 — Rendimiento de transelevadores SRM ✅

**Propósito:** evaluar individualmente los 8 SRM, el corazón de la instalación.

**Qué visualiza:**
- Tabla comparativa de los 8 SRM: MTTR, MTBF, disponibilidad y ciclos por equipo.
- **Gráfica de disponibilidad por SRM** (barras), con línea de referencia del objetivo/medio.
- Detalle individual al seleccionar un SRM: sus KPIs, su histórico de fallos (con duración real en minutos por evento) y su evolución anual de disponibilidad.
- Relación ciclos vs. fallos (¿los equipos más solicitados fallan más?).

**Cálculos:** MTTR, MTBF, disponibilidad y ciclos (sección 3) calculados por equipo para `tipo = SRM`.

**Filtros:** rango de fechas; selector de SRM individual.

---

## 8. Módulo 6 — Comparativa de periodos ✅

**Propósito:** comparar dos rangos de fechas y medir la variación de los KPIs principales para detectar mejoras, regresiones o estacionalidad.

**Qué visualiza:**
- Tarjetas con valor en el periodo A, valor en el periodo B y delta coloreado (disponibilidad, MTTR, nº de fallos, ciclos).
- Comparativa de disponibilidad por transelevador (A vs. B) y tabla con las mayores caídas/subidas.

**Cálculos:** los KPIs de la sección 3 calculados de forma independiente para cada periodo, respetando los filtros globales de tipo/zona.

**Filtros:** dos selectores de rango de fechas (A y B); los filtros globales de tipo/zona.

---

## 9. Notas de implementación para el desarrollo

- **Generador de datos simulados:** ✅ `scripts/generar_datos.py` — ~0,41 M misiones · ~940 eventos · estacionalidad · correlación ciclos↔fallos · coherencia temporal verificada con tests.
- **Capa de cálculo separada de la capa de visualización:** ✅ `src/kpis.py` — funciones puras de pandas, tests unitarios verdes, cero `import streamlit`.
- **Cacheo:** `@st.cache_data` aplicado mediante `st.cache_data(cargar_tablas)` en cada página, manteniendo `src/data_loader.py` libre de dependencias de Streamlit.
- **Internacionalización de unidades:** parámetro global `UNIDAD_TIEMPO` en `src/config.py` para mostrar tiempos en minutos u horas.
- **Inicialización de filtros globales:** ✅ `src/config.py` expone `init_session_state()`, llamada al inicio de cada página. Garantiza que `rango_fechas`, `tipos_equipo` y `zonas` tienen valores por defecto (año completo, todos los equipos, todas las zonas) aunque el usuario navegue directamente a una subpágina sin pasar por `app.py`.
- **Evolución anual de disponibilidad:** ✅ `src/kpis.py` — función `disponibilidad_mensual()` que recorta (clip) los eventos que cruzan límite de mes al sub-rango de cada mes, para un cálculo correcto de disponibilidad mensual media.
- **Roadmap de producto:** migración a datos reales del WMS/WCS manteniendo el mismo esquema y la misma capa de cálculo; despliegue como webapp persistente conectada a base de datos (línea Next.js + base de datos gestionada) e integración con una herramienta de monitorización en tiempo real tipo Grafana.