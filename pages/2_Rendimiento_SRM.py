"""Módulo 2 — Rendimiento de transelevadores SRM."""

import streamlit as st
import pandas as pd

from src.data_loader import cargar_tablas, aplicar_filtros_globales
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
from src.config import UNIDAD_TIEMPO, init_session_state, rango_valido
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina
from src.insights import rendimiento_srm
from src.export import panel_exportacion

st.set_page_config(
    page_title="Rendimiento SRM",
    page_icon=str(FAVICON) if FAVICON.exists() else None,
    layout="wide",
)
aplicar_tema()
inyectar_css()
init_session_state()
render_sidebar_filtros()

rango        = st.session_state.get("rango_fechas")

if not rango_valido(rango):
    st.info("Ajusta el rango de fechas en la barra lateral (selecciona inicio y fin).")
    st.stop()

hero(
    kicker="Módulo 2",
    titulo="Rendimiento de transelevadores SRM",
    subtitulo=(
        "Análisis individual de los 20 SRM monomástiles que sirven los pasillos. "
        "MTTR, MTBF, disponibilidad y ciclos por equipo."
    ),
)

# ---------------------------------------------------------------------------
# Carga: forzar SRM / pasillo (no depende del filtro global de zona)
# ---------------------------------------------------------------------------

_cargar = st.cache_data(cargar_tablas)
tablas = _cargar()

f = aplicar_filtros_globales(
    tablas,
    rango_fechas=(str(rango[0]), str(rango[1])),
    tipos_equipo=["SRM"], zonas=["pasillo"],
)
eventos     = f["eventos"]
misiones    = f["misiones"]
equipos     = f["equipos"]
tipos_error = f["tipos_error"]

rango_tuple = (str(rango[0]), str(rango[1]))
unidad_label = "min" if UNIDAD_TIEMPO == "minutos" else "h"

if eventos.empty and misiones.empty:
    st.warning("No hay datos SRM para el periodo seleccionado.")
    st.stop()

# ---------------------------------------------------------------------------
# KPIs por SRM
# ---------------------------------------------------------------------------

disp   = disponibilidad_por_equipo(eventos, rango_tuple)
mttr   = mttr_por_equipo(eventos, UNIDAD_TIEMPO)
mtbf   = mtbf_por_equipo(eventos, rango_tuple, UNIDAD_TIEMPO)
ciclos = ciclos_por_equipo(misiones, equipos)
n_fallos = eventos.groupby("id_equipo").size().rename("n_fallos")

todos_srm = equipos["id"].tolist()
tabla = (
    pd.DataFrame({"id_equipo": todos_srm})
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
# Fila 1 — KPI globales de la flota SRM
# ---------------------------------------------------------------------------

c1, c2, c3, c4 = st.columns(4)
disp_media = float(tabla["disponibilidad"].mean())
mttr_medio = float(tabla["mttr"].dropna().mean()) if tabla["mttr"].notna().any() else 0.0
ciclos_total = int(tabla["ciclos"].sum())
n_fallos_total = int(tabla["n_fallos"].sum())

with c1:
    st.markdown(kpi_card_html("Disponibilidad media flota",
                              f"{disp_media:.2f} %", icono="📈"),
                unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card_html(f"MTTR medio ({unidad_label})",
                              f"{mttr_medio:.1f}", icono="🛠️"),
                unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card_html("Ciclos totales",
                              f"{ciclos_total:,}", icono="🔄"),
                unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card_html("Fallos en el periodo",
                              f"{n_fallos_total:,}", icono="⚠️"),
                unsafe_allow_html=True)

lectura_ejecutiva(rendimiento_srm(eventos, misiones, equipos, rango_tuple))

st.divider()

# ---------------------------------------------------------------------------
# Fila 2 — Tabla comparativa con barra de disponibilidad
# ---------------------------------------------------------------------------

st.subheader("Tabla comparativa · 20 SRM")

st.dataframe(
    tabla,
    use_container_width=True,
    hide_index=True,
    column_config={
        "id_equipo":      st.column_config.TextColumn("Equipo"),
        "disponibilidad": st.column_config.ProgressColumn(
            "Disponibilidad",
            format="%.2f %%",
            min_value=80.0,
            max_value=100.0,
        ),
        "mttr": st.column_config.NumberColumn(f"MTTR ({unidad_label})", format="%.1f"),
        "mtbf": st.column_config.NumberColumn(f"MTBF ({unidad_label})", format="%.0f"),
        "ciclos":   st.column_config.NumberColumn("Ciclos", format="%d"),
        "n_fallos": st.column_config.NumberColumn("Fallos", format="%d"),
    },
)

st.divider()

# ---------------------------------------------------------------------------
# Fila 3 — Ranking por umbrales + Scatter ciclos vs fallos
# ---------------------------------------------------------------------------

cr, cs = st.columns([3, 2])

with cr:
    st.subheader("Disponibilidad por SRM")
    fig_disp = barras_ranking_umbrales(
        tabla.set_index("id_equipo")["disponibilidad"],
        titulo="",
        label_x="Disponibilidad (%)",
        umbral_alto=95.0,
        umbral_bajo=90.0,
        invertir=False,  # menor primero (peor arriba en gráfica)
        media=disp_media,
    )
    st.plotly_chart(fig_disp, use_container_width=True,
                    config={"displayModeBar": False})
    st.caption(
        f"🟢 ≥ 95 %  ·  🟠 90 – 95 %  ·  🔴 < 90 %  ·  Media de la flota: {disp_media:.2f} %"
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
        "**Lectura:** cada punto es un SRM. Eje X = ciclos, eje Y = fallos. "
        "Las líneas punteadas marcan la mediana y forman cuadrantes: "
        "**arriba-derecha** = mucho uso y mucho fallo (priorizar preventivo); "
        "**arriba-izquierda** = poco uso pero falla (revisar causa raíz)."
    )

st.divider()

# ---------------------------------------------------------------------------
# Fila 4 — Detalle individual
# ---------------------------------------------------------------------------

with st.expander("🔍 Detalle individual de un SRM", expanded=False):
    srm_ids = sorted(tabla["id_equipo"].tolist())
    srm_sel = st.selectbox("Selecciona un SRM", options=srm_ids, key="m2_srm_sel")

    ev_srm  = eventos[eventos["id_equipo"] == srm_sel]
    mis_srm = misiones[misiones["id_equipo"] == srm_sel]
    row = tabla[tabla["id_equipo"] == srm_sel].iloc[0]

    cc1, cc2, cc3, cc4, cc5 = st.columns(5)
    with cc1:
        st.markdown(kpi_card_html("Disponibilidad", f"{row['disponibilidad']:.2f} %"),
                    unsafe_allow_html=True)
    with cc2:
        mttr_str = f"{row['mttr']:.1f}" if pd.notna(row['mttr']) else "—"
        st.markdown(kpi_card_html(f"MTTR ({unidad_label})", mttr_str),
                    unsafe_allow_html=True)
    with cc3:
        mtbf_str = f"{row['mtbf']:,.0f}" if pd.notna(row['mtbf']) else "—"
        st.markdown(kpi_card_html(f"MTBF ({unidad_label})", mtbf_str),
                    unsafe_allow_html=True)
    with cc4:
        st.markdown(kpi_card_html("Ciclos",
                                  f"{int(row['ciclos']) if pd.notna(row['ciclos']) else 0:,}"),
                    unsafe_allow_html=True)
    with cc5:
        st.markdown(kpi_card_html("Fallos", f"{int(row['n_fallos']):,}"),
                    unsafe_allow_html=True)

    st.markdown("")

    if not ev_srm.empty:
        ev_hist = (
            ev_srm
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

        serie_disp_srm = disponibilidad_mensual(ev_srm, rango_tuple)
        fig_evol = serie_anual_area(
            serie_disp_srm,
            titulo=f"Disponibilidad mensual · {srm_sel}",
            label_y="Disponibilidad (%)",
            referencia=float(row["disponibilidad"]),
        )
        st.plotly_chart(fig_evol, use_container_width=True,
                        config={"displayModeBar": False})
    else:
        st.info(f"{srm_sel} no registra fallos en el periodo seleccionado.")

st.divider()

# ---------------------------------------------------------------------------
# Exportación de datos
# ---------------------------------------------------------------------------

panel_exportacion(
    {
        "KPIs por SRM": tabla,
        "Ciclos vs fallos": scatter_df,
    },
    prefijo="srm",
)

pie_pagina()
