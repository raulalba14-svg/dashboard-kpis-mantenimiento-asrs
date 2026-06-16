"""Módulo 3 — Rendimiento de los STV del anillo único."""

import streamlit as st
import pandas as pd

from src.data_loader import aplicar_filtros_globales
from src.data_ui import cargar_tablas_con_feedback
from src.kpis import (
    mttr_por_equipo, mtbf_por_equipo, disponibilidad_por_equipo,
    disponibilidad_mensual, ciclos_por_equipo,
)
from src.charts import (
    barras_horizontales, serie_anual_area,
    kpi_card_html, evolucion_multilinea_con_media, gauge_disponibilidad,
)
from src.theme import aplicar_tema, PRIMARIO, GRIS_700, EXITO, ADVERTENCIA, CRITICO, ACENTO
from src.styles import inyectar_css, hero, lectura_ejecutiva
from src.icons import chip
from src.config import (
    UNIDAD_TIEMPO, init_session_state, rango_valido, rango_calendario,
    RANGO_ANUAL,
)
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina
from src.insights import rendimiento_stv
from src.export import panel_exportacion
from src.format import fmt_es
from src.estilos_tabla import estilo_disponibilidad, color_por_umbral

st.set_page_config(
    page_title="Rendimiento STV",
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
    kicker="Módulo 3",
    titulo="Rendimiento de los STV del anillo",
    subtitulo=(
        "Análisis individual de los 15 vehículos de transferencia (STV) que "
        "circulan por el anillo único, alimentando y evacuando los pasillos. "
        "MTTR, MTBF, disponibilidad y ciclos por equipo."
    ),
)
st.caption(
    "Ámbito fijo del módulo: **STV · anillo único**. Los filtros de tipo y zona "
    "del sidebar no aplican aquí; el rango de fechas sí."
)

# ---------------------------------------------------------------------------
# Carga: forzar STV / anillo (no depende del filtro global de zona)
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
equipos     = f["equipos"]
tipos_error = f["tipos_error"]

# Calendario de los KPIs: [inicio, fin + 1 día), coherente con el filtro de
# fechas (que incluye el día final completo).
rango_tuple = rango_calendario(rango)
unidad_label = "min" if UNIDAD_TIEMPO == "minutos" else "h"

if eventos.empty and misiones.empty:
    st.warning("No hay datos STV para el periodo seleccionado.")
    st.stop()

# Eventos de año completo (sin recorte de fechas) para las evoluciones mensuales.
eventos_anual = aplicar_filtros_globales(
    tablas, tipos_equipo=["STV"], zonas=["anillo"],
)["eventos"]

# ---------------------------------------------------------------------------
# KPIs por STV
# ---------------------------------------------------------------------------

disp   = disponibilidad_por_equipo(eventos, rango_tuple)
mttr   = mttr_por_equipo(eventos, UNIDAD_TIEMPO)
mtbf   = mtbf_por_equipo(eventos, rango_tuple, UNIDAD_TIEMPO)
ciclos = ciclos_por_equipo(misiones, equipos)
n_fallos = eventos.groupby("id_equipo").size().rename("n_fallos")

todos_stv = equipos["id"].tolist()
tabla = (
    pd.DataFrame({"id_equipo": todos_stv})
    .set_index("id_equipo")
    .join(disp.rename("disponibilidad"))
    .join(mttr.rename("mttr"))
    .join(mtbf.rename("mtbf"))
    .join(ciclos.rename("ciclos"))
    .join(n_fallos)
    .fillna({"disponibilidad": 100.0, "n_fallos": 0, "ciclos": 0})
    .sort_index()
    .reset_index()
)

# ---------------------------------------------------------------------------
# Fila 1 — Disponibilidad del anillo (gauge) + KPI globales
# ---------------------------------------------------------------------------

st.subheader("Disponibilidad media del anillo vs. objetivo")

disp_media = float(tabla["disponibilidad"].mean())
mttr_medio = float(tabla["mttr"].dropna().mean()) if tabla["mttr"].notna().any() else 0.0
ciclos_total = int(tabla["ciclos"].sum())
n_fallos_total = int(tabla["n_fallos"].sum())

# Gauge a la izquierda (más ancho) y las tres tarjetas KPI a la derecha.
c_gauge, c1, c2, c3 = st.columns([2, 1, 1, 1])

with c_gauge:
    fig_gauge = gauge_disponibilidad(
        disp_media,
        referencia=95.0,
        titulo="15 STV · anillo único",
    )
    st.plotly_chart(fig_gauge, use_container_width=True,
                    config={"displayModeBar": False})
with c1:
    st.markdown(kpi_card_html(f"MTTR medio ({unidad_label})",
                              fmt_es(mttr_medio, 1), icono=chip("wrench", PRIMARIO),
                              acento=PRIMARIO),
                unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card_html("Ciclos totales",
                              fmt_es(ciclos_total, 0), icono=chip("rotate", ACENTO),
                              acento=ACENTO),
                unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card_html("Fallos en el periodo",
                              fmt_es(n_fallos_total, 0), icono=chip("alert-triangle", CRITICO),
                              acento=CRITICO),
                unsafe_allow_html=True)

st.caption(
    "**Lectura:** los STV trabajan en serie en un mismo circuito — la avería de "
    "un solo vehículo frena el flujo del conjunto —, por lo que el anillo se "
    "valora en conjunto: disponibilidad media frente al objetivo del **95%** "
    "(línea negra del medidor). El detalle vehículo a vehículo está en la tabla "
    "comparativa inferior."
)

_estado = "ok" if disp_media >= 95 else ("vigilar" if disp_media >= 90 else "critico")
lectura_ejecutiva(rendimiento_stv(eventos, misiones, equipos, rango_tuple),
                  estado=_estado)

st.divider()

# ---------------------------------------------------------------------------
# Fila 2 — Tabla comparativa con semáforo de disponibilidad
# ---------------------------------------------------------------------------

st.subheader("Tabla comparativa · 15 STV")

# Tabla con Styler para mostrar los números en formato español (coma decimal,
# punto de miles). La disponibilidad lleva fondo-semáforo por umbral en lugar
# de barra de progreso, porque st.dataframe formatea las ProgressColumn en
# inglés y no admite fmt_es.
_nombres = {
    "id_equipo": "Equipo", "disponibilidad": "Disponibilidad",
    "mttr": f"MTTR ({unidad_label})", "mtbf": f"MTBF ({unidad_label})",
    "ciclos": "Ciclos", "n_fallos": "Fallos",
}
_styler = (
    tabla.rename(columns=_nombres)
    .style
    .map(estilo_disponibilidad, subset=["Disponibilidad"])
    .format({
        "Disponibilidad": lambda v: f"{fmt_es(v, 2)} %",
        f"MTTR ({unidad_label})": lambda v: fmt_es(v, 1),
        f"MTBF ({unidad_label})": lambda v: fmt_es(v, 0),
        "Ciclos": lambda v: fmt_es(v, 0),
        "Fallos": lambda v: fmt_es(v, 0),
    }, na_rep="—")
)

st.dataframe(_styler, use_container_width=True, hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Fila 3 — Fallos por tipo: frecuencia y tiempo de parada (en paralelo)
# ---------------------------------------------------------------------------

st.subheader("Fallos por tipo de avería")

# Eventos STV con su duración y descripción de error, base para ambas gráficas.
_ev_fallos = eventos.assign(
    _dur_h=(
        (pd.to_datetime(eventos["ts_recuperacion"])
         - pd.to_datetime(eventos["ts_inicio_fallo"]))
        .dt.total_seconds() / 3600.0
    )
).merge(
    tipos_error[["codigo", "descripcion"]],
    left_on="codigo_error", right_on="codigo", how="left",
)

_opciones_stv = ["Todos"] + sorted(tabla["id_equipo"].tolist())

# Selector único que controla ambas gráficas.
stv_fallos_sel = st.selectbox(
    "STV", options=_opciones_stv, key="m3_fallos_stv",
)

# Umbrales semáforo escalados por periodo y nº de equipos: cortes por STV y por
# semana, multiplicados por (días del rango / 7) y por el nº de STV mostrados.
# Mismos umbrales base que el módulo SRM para coherencia entre módulos.
_n_stv_sel = 1 if stv_fallos_sel != "Todos" else max(len(tabla), 1)
_dias_rango = (pd.Timestamp(rango[1]) - pd.Timestamp(rango[0])).days + 1
_escala = max(_dias_rango / 7.0, 1e-9) * _n_stv_sel

_FREC_ROJO, _FREC_AMBAR = 0.30 * _escala, 0.18 * _escala
_HORA_ROJO, _HORA_AMBAR = 0.55 * _escala, 0.30 * _escala


def _color_frecuencia(v: float) -> str:
    return color_por_umbral(v, _FREC_ROJO, _FREC_AMBAR)


def _color_horas(v: float) -> str:
    return color_por_umbral(v, _HORA_ROJO, _HORA_AMBAR)


_base_fallos = (
    _ev_fallos if stv_fallos_sel == "Todos"
    else _ev_fallos[_ev_fallos["id_equipo"] == stv_fallos_sel]
)
g_fallos = (
    _base_fallos.groupby("descripcion")
    .agg(n_fallos=("id_evento", "size"), horas_parada=("_dur_h", "sum"))
    .reset_index()
)

col_frec, col_tiempo = st.columns(2)

with col_frec:
    if g_fallos.empty:
        st.info("Sin fallos en el periodo para la selección.")
    else:
        fig_frec = barras_horizontales(
            g_fallos.set_index("descripcion")["n_fallos"],
            titulo="Nº de fallos por tipo",
            label_x="Nº de fallos",
            color_fn=_color_frecuencia,
            formato_valor="{:,.0f}",
        )
        st.plotly_chart(fig_frec, use_container_width=True,
                        config={"displayModeBar": False})

with col_tiempo:
    if g_fallos.empty:
        st.info("Sin fallos en el periodo para la selección.")
    else:
        fig_tiempo = barras_horizontales(
            g_fallos.set_index("descripcion")["horas_parada"],
            titulo="Tiempo de parada por tipo",
            label_x="Horas de parada",
            color_fn=_color_horas,
            formato_valor="{:,.1f} h",
        )
        st.plotly_chart(fig_tiempo, use_container_width=True,
                        config={"displayModeBar": False})

st.caption(
    "Ambas gráficas muestran los modos de fallo de los STV: la izquierda por "
    "**frecuencia** (cuántas veces ocurre cada avería) y la derecha por **tiempo "
    "de parada acumulado** (su impacto en horas). El selector superior controla "
    "las dos a la vez (un STV o toda la flota del anillo). El color marca la "
    "gravedad — normal · elevado · foco crítico — con umbrales que se "
    "ajustan al periodo y al nº de equipos mostrados."
)

st.divider()

# ---------------------------------------------------------------------------
# Fila 4 — Evolución mensual de la disponibilidad (una línea por STV + media)
# ---------------------------------------------------------------------------

st.subheader("Evolución mensual de la disponibilidad")

# Año completo: el rango de fechas del sidebar no aplica a esta gráfica.
# Una serie mensual por cada STV (un STV sin fallos queda al 100% todos los meses).
_series_stv = {}
for _stv in sorted(equipos["id"].tolist()):
    _ev = eventos_anual[eventos_anual["id_equipo"] == _stv]
    if _ev.empty:
        _series_stv[_stv] = pd.Series(100.0, index=range(1, 13))
    else:
        _series_stv[_stv] = disponibilidad_mensual(_ev, RANGO_ANUAL)

_destacar = st.selectbox(
    "Destacar STV",
    options=["Ninguno"] + sorted(equipos["id"].tolist()),
    key="m3_evol_destacar",
)

fig_evol_flota = evolucion_multilinea_con_media(
    _series_stv,
    titulo="",
    label_y="Disponibilidad (%)",
    color_media=PRIMARIO,
    destacar=None if _destacar == "Ninguno" else _destacar,
)
st.plotly_chart(fig_evol_flota, use_container_width=True,
                config={"displayModeBar": False})
st.caption(
    "**Lectura:** cada línea gris es un STV; la línea azul es la **media del "
    "anillo**. Usa el selector para resaltar un vehículo en color, o pasa el "
    "ratón sobre una línea para identificarla. Muestra siempre el año completo "
    "para conservar la tendencia mensual; el rango de fechas del sidebar no la "
    "recorta."
)

st.divider()

# ---------------------------------------------------------------------------
# Fila 5 — Detalle individual
# ---------------------------------------------------------------------------

with st.expander("Detalle individual de un STV", expanded=False):
    stv_ids = sorted(tabla["id_equipo"].tolist())
    stv_det = st.selectbox("Selecciona un STV", options=stv_ids, key="m3_stv_sel")

    ev_stv  = eventos[eventos["id_equipo"] == stv_det]
    row = tabla[tabla["id_equipo"] == stv_det].iloc[0]

    cc1, cc2, cc3, cc4, cc5 = st.columns(5)
    with cc1:
        st.markdown(kpi_card_html("Disponibilidad", f"{fmt_es(row['disponibilidad'], 2)} %",
                                  icono=chip("check-circle", EXITO), acento=EXITO),
                    unsafe_allow_html=True)
    with cc2:
        mttr_str = fmt_es(row['mttr'], 1) if pd.notna(row['mttr']) else "—"
        st.markdown(kpi_card_html(f"MTTR ({unidad_label})", mttr_str,
                                  icono=chip("wrench", PRIMARIO), acento=PRIMARIO),
                    unsafe_allow_html=True)
    with cc3:
        mtbf_str = fmt_es(row['mtbf'], 0) if pd.notna(row['mtbf']) else "—"
        st.markdown(kpi_card_html(f"MTBF ({unidad_label})", mtbf_str,
                                  icono=chip("clock", ADVERTENCIA), acento=ADVERTENCIA),
                    unsafe_allow_html=True)
    with cc4:
        st.markdown(kpi_card_html("Ciclos",
                                  fmt_es(int(row['ciclos']) if pd.notna(row['ciclos']) else 0, 0),
                                  icono=chip("rotate", ACENTO), acento=ACENTO),
                    unsafe_allow_html=True)
    with cc5:
        st.markdown(kpi_card_html("Fallos", fmt_es(int(row['n_fallos']), 0),
                                  icono=chip("alert-triangle", CRITICO), acento=CRITICO),
                    unsafe_allow_html=True)

    st.markdown("")

    if not ev_stv.empty:
        st.markdown("**Histórico de fallos**")
        ev_hist = (
            ev_stv
            .merge(tipos_error[["codigo", "descripcion"]],
                   left_on="codigo_error", right_on="codigo", how="left")
            .assign(duracion_min=lambda d: (
                (pd.to_datetime(d["ts_recuperacion"])
                 - pd.to_datetime(d["ts_inicio_fallo"]))
                .dt.total_seconds() / 60
            ).round(1))
            [["ts_inicio_fallo", "ts_recuperacion", "estado",
              "descripcion", "duracion_min"]]
            .sort_values("ts_inicio_fallo", ascending=False)
            .reset_index(drop=True)
        )
        st.dataframe(
            ev_hist,
            use_container_width=True,
            hide_index=True,
            column_config={
                "duracion_min": st.column_config.NumberColumn(
                    "Duración (min)", format="%.1f",
                ),
            },
        )
    else:
        st.info(f"{stv_det} no registra fallos en el periodo seleccionado.")

    # Evolución mensual a año completo (el rango de fechas no la recorta)
    ev_stv_anual = eventos_anual[eventos_anual["id_equipo"] == stv_det]
    if not ev_stv_anual.empty:
        serie_disp_stv = disponibilidad_mensual(ev_stv_anual, RANGO_ANUAL)
        # Eje Y ajustado a los datos (1 pp de margen, acotado a [0, 100]) para
        # que las variaciones mensuales se aprecien en lugar de quedar aplastadas.
        _vals_stv = serie_disp_stv.dropna()
        _rango_y_stv = (
            (max(0.0, float(_vals_stv.min()) - 1.0),
             min(100.0, float(_vals_stv.max()) + 1.0))
            if not _vals_stv.empty else None
        )
        fig_evol = serie_anual_area(
            serie_disp_stv,
            titulo=f"Disponibilidad mensual · {stv_det}",
            label_y="Disponibilidad (%)",
            referencia=float(
                disponibilidad_por_equipo(ev_stv_anual, RANGO_ANUAL).mean()
            ),
            rango_y=_rango_y_stv,
        )
        st.plotly_chart(fig_evol, use_container_width=True,
                        config={"displayModeBar": False})
        st.caption(
            "**Nota:** esta gráfica muestra siempre el año completo para "
            "conservar la tendencia mensual; el rango de fechas del sidebar "
            "no la recorta."
        )

st.divider()

# ---------------------------------------------------------------------------
# Exportación de datos
# ---------------------------------------------------------------------------

panel_exportacion(
    {
        "KPIs por STV": tabla,
    },
    prefijo="stv",
)

pie_pagina()
