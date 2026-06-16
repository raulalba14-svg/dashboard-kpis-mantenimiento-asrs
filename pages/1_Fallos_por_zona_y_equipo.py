"""Módulo 1 — Fallos por zona y equipo."""

import streamlit as st
import pandas as pd

from src.data_loader import aplicar_filtros_globales
from src.data_ui import cargar_tablas_con_feedback
from src.charts import (
    plano_almacen, barras_ranking_umbrales,
    serie_anual_area, kpi_card_html,
)
from src.theme import (
    aplicar_tema, PRIMARIO, PRIMARIO_CLARO, EXITO, ADVERTENCIA, CRITICO,
    GRIS_500, GRIS_700,
)
from src.styles import inyectar_css, hero, lectura_ejecutiva
from src.icons import chip
from src.config import init_session_state, rango_valido
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina
from src.insights import fallos_por_zona
from src.export import panel_exportacion
from src.format import fmt_es

st.set_page_config(
    page_title="Fallos por zona y equipo",
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

hero(
    kicker="Módulo 1",
    titulo="Fallos por pasillo y equipo",
    subtitulo=(
        "Localización geográfica de los fallos sobre el plano de la instalación. "
        "Identifica concentraciones por transelevador, pasillo y código de error."
    ),
)

# ---------------------------------------------------------------------------
# Carga y filtrado
# ---------------------------------------------------------------------------

_cargar = st.cache_data(cargar_tablas_con_feedback)
tablas = _cargar()
f = aplicar_filtros_globales(
    tablas,
    rango_fechas=(str(rango[0]), str(rango[1])),
    tipos_equipo=tipos_equipo, zonas=zonas,
)
eventos     = f["eventos"]
misiones    = f["misiones"]
equipos     = f["equipos"]
tipos_error = f["tipos_error"]

if eventos.empty:
    st.warning("No hay eventos para el periodo y los filtros seleccionados.")
    st.stop()

# Enriquecer eventos
ev_enriq = (
    eventos
    .merge(equipos[["id", "tipo", "zona"]], left_on="id_equipo",
           right_on="id", how="left")
    .merge(tipos_error[["codigo", "descripcion"]],
           left_on="codigo_error", right_on="codigo", how="left")
)

if ev_enriq.empty:
    st.warning("Sin eventos para los filtros seleccionados.")
    st.stop()

# ---------------------------------------------------------------------------
# Tarjetas KPI
# ---------------------------------------------------------------------------

n_fallos_total = len(ev_enriq)
n_equipos_afectados = ev_enriq["id_equipo"].nunique()
top_equipo = ev_enriq["id_equipo"].value_counts().idxmax()
top_equipo_n = ev_enriq["id_equipo"].value_counts().iloc[0]

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(kpi_card_html("Total fallos", fmt_es(n_fallos_total, 0),
                              icono=chip("alert-triangle", CRITICO), acento=CRITICO), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card_html("Equipos afectados", fmt_es(n_equipos_afectados, 0),
                              icono=chip("cpu", PRIMARIO_CLARO), acento=PRIMARIO_CLARO), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card_html("Equipo con más fallos", top_equipo,
                              icono=chip("alert-circle", ADVERTENCIA), acento=ADVERTENCIA), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card_html("Fallos del top", fmt_es(top_equipo_n, 0),
                              icono=chip("bar-chart", PRIMARIO), acento=PRIMARIO), unsafe_allow_html=True)

lectura_ejecutiva(fallos_por_zona(eventos, equipos))

st.divider()

# ---------------------------------------------------------------------------
# Fila 1 — Plano de la instalación (visual estrella)
# ---------------------------------------------------------------------------

st.subheader("Plano de la instalación · concentración de fallos")

# Mapeo equipo → pasillo (SRM-XX → pasillo XX)
ev_srm = ev_enriq[ev_enriq["tipo"] == "SRM"].copy()
ev_srm["pasillo_num"] = ev_srm["id_equipo"].str.extract(r"SRM-(\d+)")[0].astype(int)
fallos_pasillos = ev_srm.groupby("pasillo_num").size().to_dict()

# Mapeo STV → vehículo (fallos reales por id_equipo: STV-XX → nº fallos)
ev_stv = ev_enriq[ev_enriq["tipo"] == "STV"].copy()
ev_stv["stv_num"] = ev_stv["id_equipo"].str.extract(r"STV-(\d+)")[0]
ev_stv = ev_stv.dropna(subset=["stv_num"])
ev_stv["stv_num"] = ev_stv["stv_num"].astype(int)
fallos_stv = ev_stv.groupby("stv_num").size().to_dict()

# Días del periodo analizado (inclusivo) → el color es una tasa fallos/día, así
# el semáforo significa lo mismo sea cual sea el rango de fechas seleccionado.
dias_periodo = max((rango[1] - rango[0]).days + 1, 1)

fig_plano = plano_almacen(
    fallos_pasillos=fallos_pasillos,
    fallos_stv=fallos_stv,
    dias_periodo=dias_periodo,
    titulo="",
)
st.plotly_chart(fig_plano, use_container_width=True,
                config={"displayModeBar": False})

st.caption(
    "**Lectura:** en el centro, cada pasillo representa un transelevador (SRM); "
    "alrededor, el anillo único con los 15 vehículos de transferencia (STV), cada "
    "uno con su nº de fallos en el periodo. El color es un **semáforo de salud** "
    "según la **tasa de fallos por día** (no el total): verde = dentro de lo "
    "normal, ámbar = vigilar, rojo = por encima del umbral. Al acortar el rango "
    "de fechas, un equipo con fallos concentrados se vuelve ámbar o rojo."
)

st.divider()

# ---------------------------------------------------------------------------
# Fila 2 — Rankings de fallos
# ---------------------------------------------------------------------------

st.subheader("Rankings de fallos")
col_eq, col_cod = st.columns(2)

import plotly.graph_objects as go

with col_eq:
    n_por_equipo = ev_enriq.groupby("id_equipo").size().sort_values(ascending=False)
    st.markdown("**Por transelevador**")
    df = n_por_equipo.reset_index()
    df.columns = ["equipo", "valor"]
    df = df.sort_values("valor", ascending=True)
    p66 = df["valor"].quantile(0.66)
    p33 = df["valor"].quantile(0.33)
    df["color"] = df["valor"].apply(
        lambda v: CRITICO if v >= p66 else (ADVERTENCIA if v >= p33 else PRIMARIO)
    )
    fig_eq = go.Figure(go.Bar(
        x=df["valor"], y=df["equipo"], orientation="h",
        marker=dict(color=df["color"].tolist(),
                    line=dict(color="white", width=0.5)),
        text=df["valor"], textposition="outside",
        textfont=dict(color=GRIS_700, size=11),
        hovertemplate="<b>%{y}</b><br>%{x} fallos<extra></extra>",
    ))
    fig_eq.update_layout(
        title="", xaxis_title="Nº fallos", yaxis_title="",
        height=max(280, 26 * len(df) + 80), bargap=0.25,
    )
    st.plotly_chart(fig_eq, use_container_width=True,
                    config={"displayModeBar": False})

with col_cod:
    st.markdown("**Por código de error** (top 10)")
    n_por_codigo = (
        ev_enriq.assign(
            etiqueta=lambda d: d["codigo_error"] + " · " + d["descripcion"].fillna("")
        )
        .groupby("etiqueta").size()
        .sort_values(ascending=False)
        .head(10)
    )
    df_cod = n_por_codigo.reset_index()
    df_cod.columns = ["codigo", "valor"]
    df_cod = df_cod.sort_values("valor", ascending=True)
    fig_cod = go.Figure(go.Bar(
        x=df_cod["valor"], y=df_cod["codigo"], orientation="h",
        marker=dict(color=PRIMARIO, line=dict(color="white", width=0.5)),
        text=df_cod["valor"], textposition="outside",
        textfont=dict(color=GRIS_700, size=11),
        hovertemplate="<b>%{y}</b><br>%{x} fallos<extra></extra>",
    ))
    fig_cod.update_layout(
        title="", xaxis_title="Nº fallos", yaxis_title="",
        height=max(280, 26 * len(df_cod) + 80), bargap=0.3,
    )
    st.plotly_chart(fig_cod, use_container_width=True,
                    config={"displayModeBar": False})

st.divider()

# ---------------------------------------------------------------------------
# Fila 3 — Evolución mensual
# ---------------------------------------------------------------------------

st.subheader("Evolución mensual del nº de fallos")

# Serie de año completo: el rango de fechas del sidebar no aplica aquí —
# con un rango corto la curva mensual quedaría sin puntos suficientes. Los
# filtros de tipo y zona sí aplican (se reusan los del sidebar).
eventos_anual = aplicar_filtros_globales(
    tablas, tipos_equipo=tipos_equipo, zonas=zonas,
)["eventos"].copy()
eventos_anual["_mes"] = pd.to_datetime(eventos_anual["ts_inicio_fallo"]).dt.month
serie_fallos_mes = eventos_anual.groupby("_mes").size().rename("n_fallos")

fig_evol = serie_anual_area(
    serie_fallos_mes,
    titulo="",
    label_y="Nº fallos",
    referencia=float(serie_fallos_mes.mean()),
    color=CRITICO,
)
st.plotly_chart(fig_evol, use_container_width=True,
                config={"displayModeBar": False})
st.caption(
    "**Nota:** esta gráfica muestra siempre el año completo para conservar la "
    "tendencia mensual; el rango de fechas del sidebar no la recorta (los "
    "filtros de tipo y zona sí aplican)."
)

st.divider()

# ---------------------------------------------------------------------------
# Exportación de datos
# ---------------------------------------------------------------------------

_datasets_export = {
    "Fallos por equipo": n_por_equipo.rename("n_fallos")
                         .reset_index().rename(columns={"index": "id_equipo"}),
    "Fallos por codigo": ev_enriq.groupby("codigo_error").size()
                         .rename("n_fallos").reset_index(),
    "Fallos mensuales": serie_fallos_mes.reset_index().rename(
        columns={"_mes": "mes"}
    ),
    "Eventos enriquecidos": ev_enriq[[
        "id_evento", "id_equipo", "tipo", "zona", "codigo_error",
        "descripcion", "ts_inicio_fallo", "ts_recuperacion", "estado",
    ]],
}

panel_exportacion(_datasets_export, prefijo="fallos")

pie_pagina()
