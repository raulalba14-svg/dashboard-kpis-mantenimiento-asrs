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
    barras_ranking_umbrales, serie_anual_area, scatter_ciclos_fallos,
    kpi_card_html,
)
from src.theme import aplicar_tema, PRIMARIO, GRIS_700, EXITO, ADVERTENCIA, CRITICO
from src.styles import inyectar_css, hero, lectura_ejecutiva
from src.config import UNIDAD_TIEMPO, init_session_state, rango_valido, rango_calendario
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina
from src.insights import rendimiento_stv
from src.export import panel_exportacion
from src.format import fmt_es
from src.estilos_tabla import estilo_disponibilidad

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
# Fila 1 — KPI globales del anillo de STV
# ---------------------------------------------------------------------------

c1, c2, c3, c4 = st.columns(4)
disp_media = float(tabla["disponibilidad"].mean())
mttr_medio = float(tabla["mttr"].dropna().mean()) if tabla["mttr"].notna().any() else 0.0
ciclos_total = int(tabla["ciclos"].sum())
n_fallos_total = int(tabla["n_fallos"].sum())

with c1:
    st.markdown(kpi_card_html("Disponibilidad media anillo",
                              f"{fmt_es(disp_media, 2)} %", icono="📈"),
                unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card_html(f"MTTR medio ({unidad_label})",
                              fmt_es(mttr_medio, 1), icono="🛠️"),
                unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card_html("Ciclos totales",
                              fmt_es(ciclos_total, 0), icono="🔄"),
                unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card_html("Fallos en el periodo",
                              fmt_es(n_fallos_total, 0), icono="⚠️"),
                unsafe_allow_html=True)

lectura_ejecutiva(rendimiento_stv(eventos, misiones, equipos, rango_tuple))

st.divider()

# ---------------------------------------------------------------------------
# Fila 2 — Tabla comparativa con barra de disponibilidad
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
# Fila 3 — Ranking por umbrales + Scatter ciclos vs fallos
# ---------------------------------------------------------------------------

cr, cs = st.columns([3, 2])

with cr:
    st.subheader("Disponibilidad por STV")
    fig_disp = barras_ranking_umbrales(
        tabla.set_index("id_equipo")["disponibilidad"],
        titulo="",
        label_x="Disponibilidad (%)",
        umbral_alto=95.0,
        umbral_bajo=90.0,
        invertir=False,
        media=disp_media,
    )
    st.plotly_chart(fig_disp, use_container_width=True,
                    config={"displayModeBar": False})
    st.caption(
        f"🟢 ≥ 95 %  ·  🟠 90 – 95 %  ·  🔴 < 90 %  ·  Media del anillo: {fmt_es(disp_media, 2)} %"
    )

with cs:
    st.subheader("Ciclos vs. fallos")
    scatter_df = tabla[["id_equipo", "ciclos", "n_fallos"]].fillna(0)
    scatter_df["ciclos"] = scatter_df["ciclos"].astype(int)
    scatter_df["n_fallos"] = scatter_df["n_fallos"].astype(int)
    fig_scatter = scatter_ciclos_fallos(
        scatter_df,
        col_ciclos="ciclos",
        col_fallos="n_fallos",
        col_label="id_equipo",
        titulo="",
    )
    st.plotly_chart(fig_scatter, use_container_width=True,
                    config={"displayModeBar": False})
    st.caption(
        "**Lectura:** cada punto es un STV. Eje X = ciclos, eje Y = fallos. "
        "Las líneas punteadas marcan la mediana y forman cuadrantes: "
        "**arriba-derecha** = mucho uso y mucho fallo (priorizar preventivo); "
        "**arriba-izquierda** = poco uso pero falla (revisar causa raíz)."
    )

st.divider()

# ---------------------------------------------------------------------------
# Fila 4 — Detalle individual
# ---------------------------------------------------------------------------

with st.expander("🔍 Detalle individual de un STV", expanded=False):
    stv_ids = sorted(tabla["id_equipo"].tolist())
    stv_sel = st.selectbox("Selecciona un STV", options=stv_ids, key="m3_stv_sel")

    ev_stv  = eventos[eventos["id_equipo"] == stv_sel]
    row = tabla[tabla["id_equipo"] == stv_sel].iloc[0]

    cc1, cc2, cc3, cc4, cc5 = st.columns(5)
    with cc1:
        st.markdown(kpi_card_html("Disponibilidad", f"{fmt_es(row['disponibilidad'], 2)} %"),
                    unsafe_allow_html=True)
    with cc2:
        mttr_str = fmt_es(row['mttr'], 1) if pd.notna(row['mttr']) else "—"
        st.markdown(kpi_card_html(f"MTTR ({unidad_label})", mttr_str),
                    unsafe_allow_html=True)
    with cc3:
        mtbf_str = fmt_es(row['mtbf'], 0) if pd.notna(row['mtbf']) else "—"
        st.markdown(kpi_card_html(f"MTBF ({unidad_label})", mtbf_str),
                    unsafe_allow_html=True)
    with cc4:
        st.markdown(kpi_card_html("Ciclos",
                                  fmt_es(int(row['ciclos']) if pd.notna(row['ciclos']) else 0, 0)),
                    unsafe_allow_html=True)
    with cc5:
        st.markdown(kpi_card_html("Fallos", fmt_es(int(row['n_fallos']), 0)),
                    unsafe_allow_html=True)

    st.markdown("")

    if not ev_stv.empty:
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
        st.markdown("**Histórico de fallos**")
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

        serie_disp_stv = disponibilidad_mensual(ev_stv, rango_tuple)
        fig_evol = serie_anual_area(
            serie_disp_stv,
            titulo=f"Disponibilidad mensual · {stv_sel}",
            label_y="Disponibilidad (%)",
            referencia=float(row["disponibilidad"]),
        )
        st.plotly_chart(fig_evol, use_container_width=True,
                        config={"displayModeBar": False})
    else:
        st.info(f"{stv_sel} no registra fallos en el periodo seleccionado.")

st.divider()

# ---------------------------------------------------------------------------
# Exportación de datos
# ---------------------------------------------------------------------------

panel_exportacion(
    {
        "KPIs por STV": tabla,
        "Ciclos vs fallos": scatter_df,
    },
    prefijo="stv",
)

pie_pagina()
