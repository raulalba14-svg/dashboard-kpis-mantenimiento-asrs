"""Módulo 4 — Rechazos."""

import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from src.data_loader import aplicar_filtros_globales
from src.data_ui import cargar_tablas_con_feedback
from src.kpis import tasa_rechazo
from src.charts import (
    serie_anual_area, donut_categoria, kpi_card_html, kpi_grid, GAUGE_ALTURA,
    evolucion_lineas_categoria, gauge_objetivo,
)
from src.theme import (
    aplicar_tema, PRIMARIO, PRIMARIO_CLARO, ADVERTENCIA, CRITICO, GRIS_700,
)
from src.styles import inyectar_css, hero, lectura_ejecutiva
from src.icons import chip
from src.config import init_session_state, rango_valido
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina
from src.insights import rechazos
from src.export import panel_exportacion
from src.format import fmt_es

st.set_page_config(
    page_title="Rechazos",
    page_icon=str(FAVICON) if FAVICON.exists() else None,
    layout="wide",
)
aplicar_tema()
inyectar_css()
init_session_state()
render_sidebar_filtros()

rango = st.session_state.get("rango_fechas")

if not rango_valido(rango):
    st.info("Ajusta el rango de fechas en la barra lateral (selecciona inicio y fin).")
    st.stop()

hero(
    kicker="Módulo 4",
    titulo="Rechazos",
    subtitulo=(
        "Análisis de la inspección de pallets en recepción: dónde y por qué se "
        "rechazan los pallets, y cómo evoluciona la tasa en el tiempo."
    ),
)
st.caption(
    "Ámbito fijo del módulo: **STV · anillo único**. Los filtros de tipo y zona "
    "del sidebar no aplican aquí; el rango de fechas sí."
)

# ---------------------------------------------------------------------------
# Carga: STV del anillo único
# ---------------------------------------------------------------------------

_cargar = st.cache_data(cargar_tablas_con_feedback)
tablas = _cargar()

f = aplicar_filtros_globales(
    tablas,
    rango_fechas=(str(rango[0]), str(rango[1])),
    tipos_equipo=["STV"], zonas=["anillo"],
)
eventos     = f["eventos"]
misiones    = f["misiones"]

if misiones.empty:
    st.warning("No hay datos de misiones para el periodo seleccionado.")
    st.stop()

# ---------------------------------------------------------------------------
# Cálculos
# ---------------------------------------------------------------------------

rechazadas = misiones[misiones["estado"] == "rechazada"].copy()

tasa_global = tasa_rechazo(misiones)
n_rechazos  = len(rechazadas)
n_misiones  = len(misiones)

# ---------------------------------------------------------------------------
# Fila 1 — Tasa de rechazo (gauge) + KPI globales
# ---------------------------------------------------------------------------

st.subheader("Tasa de rechazo vs. objetivo")

# Gauge a la izquierda (más ancho) y las dos tarjetas KPI a la derecha.
c_gauge, c_kpis = st.columns([2, 3])

with c_gauge:
    fig_gauge = gauge_objetivo(
        tasa_global * 100,
        rango=(0.0, 5.0),
        umbral_verde=2.0,
        umbral_ambar=3.5,
        objetivo=2.0,
        titulo="Inspección de recepción",
        sufijo=" %",
        menor_es_mejor=True,
    )
    st.plotly_chart(fig_gauge, use_container_width=True,
                    config={"displayModeBar": False})
with c_kpis:
    st.markdown(kpi_grid([
        kpi_card_html("Misiones totales", fmt_es(n_misiones, 0),
                      icono=chip("package", PRIMARIO_CLARO), acento=PRIMARIO_CLARO),
        kpi_card_html("Rechazadas", fmt_es(n_rechazos, 0),
                      icono=chip("x-circle", CRITICO), acento=CRITICO),
    ], columnas=2, altura=GAUGE_ALTURA), unsafe_allow_html=True)

st.caption(
    "**Lectura:** tasa de rechazo frente al objetivo del **2%** (línea negra del "
    "medidor). Verde por debajo del objetivo, ámbar hasta el 3,5%, rojo por "
    "encima."
)

# Estado según la tasa de rechazo frente al objetivo del 2 % (menor = mejor).
_tasa_pct = tasa_global * 100
_estado = "ok" if _tasa_pct <= 2 else ("vigilar" if _tasa_pct <= 4 else "critico")
lectura_ejecutiva(rechazos(misiones, eventos), estado=_estado)

st.divider()

# ---------------------------------------------------------------------------
# Fila 2 — Inspección de recepción: dónde y por qué se rechaza
# ---------------------------------------------------------------------------

st.subheader("Inspección de recepción · dónde y por qué se rechaza")
st.caption(
    "Un rechazo no es una avería del anillo: lo genera un **puesto de inspección "
    "de pallets** en recepción. El pallet parte del inspector (origen `INSP-xx`) "
    "y un STV del anillo lo transporta al puesto de rechazo."
)

MOTIVO_LABELS = {
    "fuera_de_dimensiones":    "Fuera de dimensiones",
    "exceso_de_peso":          "Exceso de peso",
    "hueco_pallet_incorrecto": "Hueco de pallet incorrecto",
}

if rechazadas.empty:
    st.info("Sin misiones rechazadas en el periodo seleccionado.")
else:
    por_inspector = (rechazadas.groupby("posicion_inicial").size()
                     .sort_index().rename("rechazos"))
    if "motivo_rechazo" in rechazadas.columns:
        serie_motivo = (rechazadas["motivo_rechazo"].map(MOTIVO_LABELS)
                        .dropna().value_counts())
    else:
        serie_motivo = pd.Series(dtype=int)

    col_insp, col_motivo = st.columns(2)

    with col_insp:
        st.markdown("**Rechazos por inspector**")
        fig_insp = go.Figure(go.Bar(
            x=por_inspector.index, y=por_inspector.values,
            marker=dict(color=PRIMARIO, line=dict(color="white", width=0.5)),
            text=[fmt_es(v, 0) for v in por_inspector.values],
            textposition="outside",
            textfont=dict(color=GRIS_700, size=11),
            hovertemplate="<b>%{x}</b><br>%{y:,} rechazos<extra></extra>",
        ))
        fig_insp.update_layout(
            title="", xaxis_title="", yaxis_title="Nº rechazos",
            height=320, bargap=0.35,
        )
        st.plotly_chart(fig_insp, use_container_width=True,
                        config={"displayModeBar": False})

    with col_motivo:
        st.markdown("**Motivo del rechazo**")
        if serie_motivo.sum() > 0:
            color_map_motivo = {
                "Fuera de dimensiones":       PRIMARIO,
                "Exceso de peso":             ADVERTENCIA,
                "Hueco de pallet incorrecto": PRIMARIO_CLARO,
            }
            st.plotly_chart(
                donut_categoria(serie_motivo, titulo="",
                                color_map=color_map_motivo),
                use_container_width=True, config={"displayModeBar": False},
            )
        else:
            st.info("El dataset no incluye motivo de rechazo — regenera los "
                    "datos con scripts/generar_datos.py.")

    st.caption(
        "Un inspector con una proporción anómala de rechazos apunta a un sensor "
        "descalibrado (causa de mantenimiento); un reparto uniforme apunta a la "
        "calidad del pallet de origen (causa operativa)."
    )

st.divider()

# ---------------------------------------------------------------------------
# Fila 3 — Evolución mensual de la tasa de rechazo
# ---------------------------------------------------------------------------

st.subheader("Evolución mensual de la tasa de rechazo")

# Serie de año completo: el rango de fechas del sidebar no aplica aquí —
# con un rango corto la curva mensual quedaría sin puntos suficientes.
misiones_anual = aplicar_filtros_globales(
    tablas, tipos_equipo=["STV"], zonas=["anillo"],
)["misiones"]

misiones_mes = misiones_anual.copy()
misiones_mes["ts_inicio"] = pd.to_datetime(misiones_mes["ts_inicio"])
misiones_mes["_mes"] = misiones_mes["ts_inicio"].dt.month

rechazos_mes = (
    misiones_mes[misiones_mes["estado"] == "rechazada"]
    .groupby("_mes").size().rename("rechazos")
)
total_mes = misiones_mes.groupby("_mes").size().rename("total")
tasa_mes = (rechazos_mes / total_mes * 100).rename("tasa_rechazo")

fig_evol = serie_anual_area(
    tasa_mes,
    titulo="",
    label_y="Tasa de rechazo (%)",
    referencia=float(tasa_rechazo(misiones_anual) * 100),
    color=PRIMARIO,   # serie temporal neutra en azul de marca (el semáforo se reserva para gauges/plano)
    rango_y=(1.8, 2.2),
)
st.plotly_chart(fig_evol, use_container_width=True,
                config={"displayModeBar": False})
st.caption(
    "**Nota:** esta gráfica muestra siempre el año completo para conservar la "
    "tendencia mensual; el rango de fechas del sidebar no la recorta. El eje "
    "está acotado en torno al 2% para que las variaciones mensuales se aprecien."
)

st.divider()

# ---------------------------------------------------------------------------
# Fila 4 — Evolución mensual del nº de rechazos por motivo
# ---------------------------------------------------------------------------

st.subheader("Evolución mensual de rechazos por motivo")

# Año completo (mismo criterio que la evolución de la tasa): nº de rechazos de
# cada motivo mes a mes. Permite ver qué motivo concreto sube o baja.
rech_mes = misiones_mes[misiones_mes["estado"] == "rechazada"]

series_motivo_mes: dict[str, pd.Series] = {}
if "motivo_rechazo" in rech_mes.columns and not rech_mes.empty:
    for _cod, _label in MOTIVO_LABELS.items():
        _serie = (
            rech_mes[rech_mes["motivo_rechazo"] == _cod]
            .groupby("_mes").size()
            .reindex(range(1, 13), fill_value=0)
        )
        if _serie.sum() > 0:
            series_motivo_mes[_label] = _serie

if series_motivo_mes:
    color_map_motivo_linea = {
        "Fuera de dimensiones":       PRIMARIO,
        "Exceso de peso":             ADVERTENCIA,
        "Hueco de pallet incorrecto": PRIMARIO_CLARO,
    }
    fig_motivo_mes = evolucion_lineas_categoria(
        series_motivo_mes,
        titulo="",
        label_y="Nº de rechazos",
        color_map=color_map_motivo_linea,
    )
    st.plotly_chart(fig_motivo_mes, use_container_width=True,
                    config={"displayModeBar": False})
    st.caption(
        "**Lectura:** cada línea es un motivo de rechazo a lo largo del año. "
        "Un motivo que crece de forma sostenida apunta a una causa estructural "
        "(p. ej. un sensor que se va descalibrando); picos puntuales suelen ser "
        "lotes concretos de pallets defectuosos. Muestra siempre el año completo; "
        "el rango de fechas del sidebar no la recorta."
    )
else:
    st.info("El dataset no incluye motivo de rechazo — regenera los datos con "
            "scripts/generar_datos.py.")

st.divider()

# ---------------------------------------------------------------------------
# Exportación de datos
# ---------------------------------------------------------------------------

_datasets_export = {
    "Tasa de rechazo mensual": tasa_mes.reset_index().rename(
        columns={"_mes": "mes"}
    ),
}
if not rechazadas.empty:
    _datasets_export["Rechazos por inspector"] = por_inspector.reset_index().rename(
        columns={"posicion_inicial": "inspector"}
    )
    if serie_motivo.sum() > 0:
        _datasets_export["Motivos de rechazo"] = (
            serie_motivo.rename("rechazos").reset_index()
            .rename(columns={"index": "motivo"})
        )
if series_motivo_mes:
    _datasets_export["Rechazos por motivo (mensual)"] = (
        pd.DataFrame(series_motivo_mes)
        .rename_axis("mes").reset_index()
    )

panel_exportacion(_datasets_export, prefijo="rechazos")

pie_pagina()
