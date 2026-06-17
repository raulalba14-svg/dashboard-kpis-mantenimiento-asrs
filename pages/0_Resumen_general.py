"""Módulo 0 — Resumen general."""

import streamlit as st
import pandas as pd

from src.data_loader import aplicar_filtros_globales
from src.data_ui import cargar_tablas_con_feedback
from src.kpis import (
    kpis_globales, disponibilidad_por_equipo, disponibilidad_mensual,
    delta_vs_periodo_anterior, serie_mensual,
)
from src.charts import (
    serie_anual_area, gauge_disponibilidad, kpi_card_html, kpi_grid,
)
from src.theme import aplicar_tema, PRIMARIO, ADVERTENCIA, CRITICO, ACENTO
from src.styles import inyectar_css, hero, lectura_ejecutiva
from src.icons import chip
from src.config import (
    UNIDAD_TIEMPO, init_session_state, rango_valido, rango_calendario,
    RANGO_ANUAL,
)
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina
from src.insights import resumen_general
from src.export import panel_exportacion
from src.format import fmt_es

st.set_page_config(
    page_title="Resumen general",
    page_icon=str(FAVICON) if FAVICON.exists() else None,
    layout="wide",
)
aplicar_tema()
inyectar_css()
init_session_state()
render_sidebar_filtros()

rango        = st.session_state.get("rango_fechas")
tipos_equipo = st.session_state.get("tipos_equipo")
zonas        = st.session_state.get("zonas")

if not rango_valido(rango):
    st.info("Ajusta el rango de fechas en la barra lateral (selecciona inicio y fin).")
    st.stop()

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

hero(
    kicker="Módulo 0",
    titulo="Resumen general de la instalación",
    subtitulo=(
        f"Vista de 30 segundos del estado operacional. "
        f"Periodo: <b>{rango[0]:%d/%m/%Y}</b> → <b>{rango[1]:%d/%m/%Y}</b>."
    ),
)

# ---------------------------------------------------------------------------
# Carga y filtrado
# ---------------------------------------------------------------------------

_cargar = st.cache_data(cargar_tablas_con_feedback)
tablas = _cargar()

# Tablas globales (sin filtrar por rango) para el delta vs. periodo anterior:
# eventos para disponibilidad/MTTR/fallos y misiones para los ciclos.
f_global = aplicar_filtros_globales(
    tablas, rango_fechas=None,
    tipos_equipo=tipos_equipo, zonas=zonas,
)

f = aplicar_filtros_globales(
    tablas,
    rango_fechas=(str(rango[0]), str(rango[1])),
    tipos_equipo=tipos_equipo, zonas=zonas,
)
eventos  = f["eventos"]
misiones = f["misiones"]
equipos  = f["equipos"]

if eventos.empty and misiones.empty:
    st.warning("No hay datos para el periodo y los filtros seleccionados.")
    st.stop()

# Calendario de los KPIs: [inicio, fin + 1 día), coherente con el filtro de
# fechas (que incluye el día final completo).
rango_tuple = rango_calendario(rango)
unidad_label = "min" if UNIDAD_TIEMPO == "minutos" else "h"

# ---------------------------------------------------------------------------
# Cálculos: KPIs + delta + serie mensual de fallos (para exportación)
# ---------------------------------------------------------------------------

kpis = kpis_globales(eventos, misiones, equipos, rango_tuple, UNIDAD_TIEMPO)
delta = delta_vs_periodo_anterior(
    eventos, misiones, rango_tuple,
    eventos_global=f_global["eventos"],
    misiones_global=f_global["misiones"],
)

# Estado global de la instalación según la disponibilidad media frente al
# objetivo del 95 %: tiñe la síntesis como semáforo (verde/ámbar/rojo).
_disp = kpis["disponibilidad_media"]
_estado = "ok" if _disp >= 95 else ("vigilar" if _disp >= 90 else "critico")
lectura_ejecutiva(resumen_general(eventos, misiones, equipos, rango_tuple),
                  estado=_estado)

# Serie mensual de fallos (se exporta más abajo).
serie_fallos_mensual = serie_mensual(
    eventos, "ts_inicio_fallo", "id_evento", agg="count"
)


def _fmt_delta_int(v, sufijo=""):
    if v is None:
        return None, None
    sign = "+" if v >= 0 else ""
    return f"{sign}{fmt_es(v, 0)}{sufijo}", v <= 0   # menos fallos = mejor (delta positivo)


def _fmt_delta_mttr(v):
    if v is None:
        return None, None
    sign = "+" if v >= 0 else ""
    # MTTR menor = mejor
    return f"{sign}{fmt_es(v, 1)} min", v <= 0


# ---------------------------------------------------------------------------
# Fila 1 — Gauge de disponibilidad + KPIs en rejilla 2×2 (patrón del módulo 2)
# ---------------------------------------------------------------------------

st.subheader("Disponibilidad media de la instalación vs. objetivo")

delta_mttr_txt, delta_mttr_pos = _fmt_delta_mttr(delta["delta_mttr_min"])
delta_ciclos_txt, delta_ciclos_pos = _fmt_delta_int(delta["delta_ciclos"])
# Para ciclos, más es mejor → invertir el signo lógico
if delta["delta_ciclos"] is not None:
    delta_ciclos_pos = delta["delta_ciclos"] >= 0

# Gauge a la izquierda (más ancho) y las 4 tarjetas KPI en rejilla 2×2 a la derecha.
c_gauge, c_kpis = st.columns([2, 3])

with c_gauge:
    fig_gauge = gauge_disponibilidad(
        kpis["disponibilidad_media"],
        referencia=95.0,
        titulo="Disponibilidad vs. objetivo (95%)",
    )
    st.plotly_chart(fig_gauge, use_container_width=True,
                    config={"displayModeBar": False})

with c_kpis:
    st.markdown(
        kpi_grid([
            kpi_card_html("Fallos en el periodo", fmt_es(kpis['n_fallos'], 0),
                          icono=chip("alert-triangle", CRITICO), acento=CRITICO),
            kpi_card_html(f"MTTR medio ({unidad_label})", fmt_es(kpis['mttr_medio'], 1),
                          delta_mttr_txt, delta_mttr_pos, icono=chip("wrench", PRIMARIO),
                          acento=PRIMARIO),
            kpi_card_html(f"MTBF medio ({unidad_label})", fmt_es(kpis['mtbf_medio'], 0),
                          icono=chip("clock", ADVERTENCIA), acento=ADVERTENCIA),
            kpi_card_html("Ciclos totales", fmt_es(kpis['ciclos_totales'], 0),
                          delta_ciclos_txt, delta_ciclos_pos, icono=chip("rotate", ACENTO),
                          acento=ACENTO),
        ]),
        unsafe_allow_html=True,
    )

st.caption(
    "**Lectura:** disponibilidad media de la instalación frente al objetivo del "
    "**95%** (línea negra del medidor). El detalle equipo a equipo está en el "
    "Top 5 inferior y en los módulos 2 (SRM) y 3 (STV)."
)

st.divider()

# ---------------------------------------------------------------------------
# Fila 2 — Evolución anual de la disponibilidad (ancho completo)
# ---------------------------------------------------------------------------

# Año completo: el rango de fechas del sidebar no aplica a esta gráfica —
# con un rango corto la curva mensual quedaría sin puntos suficientes. Respeta
# los filtros de tipo/zona (f_global ya los aplica).
serie_disp_anual = disponibilidad_mensual(f_global["eventos"], RANGO_ANUAL)
# Eje Y ajustado a los datos (con 1 pp de margen, acotado a [0, 100]) para
# que las variaciones mensuales se aprecien en lugar de quedar aplastadas.
_vals = serie_disp_anual.dropna()
_rango_y = (
    (max(0.0, float(_vals.min()) - 1.0), min(100.0, float(_vals.max()) + 1.0))
    if not _vals.empty else None
)
fig_evol = serie_anual_area(
    serie_disp_anual,
    titulo="Evolución mensual de la disponibilidad",
    label_y="Disponibilidad (%)",
    referencia=float(
        disponibilidad_por_equipo(f_global["eventos"], RANGO_ANUAL).mean()
    ),
    rango_y=_rango_y,
)
st.plotly_chart(fig_evol, use_container_width=True,
                config={"displayModeBar": False})
st.caption(
    "**Nota:** esta gráfica muestra siempre el año completo para conservar "
    "la tendencia mensual; el rango de fechas del sidebar no la recorta."
)

st.divider()

# ---------------------------------------------------------------------------
# Fila 3 — Top 5 con peor disponibilidad
# ---------------------------------------------------------------------------

st.subheader("Top 5 · equipos con peor disponibilidad")
if not eventos.empty:
    disp_eq = disponibilidad_por_equipo(eventos, rango_tuple)
    n_fallos_eq = (
        eventos
        .groupby("id_equipo").size()
        .rename("n_fallos")
    )
    top5 = (
        disp_eq
        .rename("disponibilidad")
        .to_frame()
        .join(n_fallos_eq, how="left")
        .join(equipos.set_index("id")[["tipo", "zona"]], how="left")
        .sort_values("disponibilidad")
        .head(5)
        .reset_index()
        .rename(columns={"index": "id_equipo"})
    )
    top5["n_fallos"] = top5["n_fallos"].fillna(0).astype(int)

    st.dataframe(
        top5[["id_equipo", "tipo", "zona", "disponibilidad", "n_fallos"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "id_equipo":     st.column_config.TextColumn("Equipo"),
            "tipo":          st.column_config.TextColumn("Tipo"),
            "zona":          st.column_config.TextColumn("Zona"),
            "disponibilidad": st.column_config.ProgressColumn(
                "Disponibilidad",
                format="%.2f %%",
                min_value=80.0,
                max_value=100.0,
            ),
            "n_fallos":      st.column_config.NumberColumn(
                "Fallos", format="%d"
            ),
        },
    )
    st.caption(
        "Para ver el detalle individual, navega a **Módulo 2** (Rendimiento SRM) "
        "o **Módulo 3** (Rendimiento STV)."
    )
else:
    st.info("Sin eventos en el periodo seleccionado.")

st.divider()

# ---------------------------------------------------------------------------
# Exportación de datos
# ---------------------------------------------------------------------------

_datasets_export = {
    "KPIs globales": pd.DataFrame([{
        "disponibilidad_media_pct": kpis["disponibilidad_media"],
        "n_fallos": kpis["n_fallos"],
        f"mttr_medio_{unidad_label}": kpis["mttr_medio"],
        f"mtbf_medio_{unidad_label}": kpis["mtbf_medio"],
        "ciclos_totales": kpis["ciclos_totales"],
        "rango_inicio": rango[0].isoformat(),
        "rango_fin": rango[1].isoformat(),
    }]),
    "Disponibilidad mensual": serie_disp_anual.rename("disponibilidad_pct")
                              .reset_index().rename(columns={"index": "mes"}),
    "Fallos mensuales": serie_fallos_mensual.rename("n_fallos")
                        .reset_index().rename(columns={"index": "mes"}),
}
if not eventos.empty:
    _datasets_export["Top 5 peor disponibilidad"] = top5

panel_exportacion(_datasets_export, prefijo="resumen")

pie_pagina()
