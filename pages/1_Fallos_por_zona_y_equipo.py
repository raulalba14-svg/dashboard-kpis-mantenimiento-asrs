"""Módulo 1 — Fallos por zona y equipo."""

import streamlit as st
import pandas as pd

from src.data_loader import aplicar_filtros_globales
from src.data_ui import cargar_tablas_con_feedback
from src.kpis import posicion_en_fallo
from src.charts import (
    plano_almacen, barras_ranking_umbrales,
    heatmap_alzado_pasillo, serie_anual_area, kpi_card_html,
)
from src.theme import (
    aplicar_tema, PRIMARIO, PRIMARIO_CLARO, EXITO, ADVERTENCIA, CRITICO,
    GRIS_500, GRIS_700,
)
from src.styles import inyectar_css, hero, lectura_ejecutiva
from src.config import init_session_state, rango_valido
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina
from src.insights import fallos_por_zona
from src.export import panel_exportacion

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
    st.markdown(kpi_card_html("Total fallos", f"{n_fallos_total:,}",
                              icono="⚠️"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card_html("Equipos afectados", f"{n_equipos_afectados}",
                              icono="🤖"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card_html("Equipo con más fallos", top_equipo,
                              icono="🔴"), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card_html("Fallos del top", f"{top_equipo_n:,}",
                              icono="📊"), unsafe_allow_html=True)

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

# Mapeo STV → tramo del anillo (vía posición en el momento del fallo, Txx)
fallos_tramos = {}
ev_stv = ev_enriq[ev_enriq["tipo"] == "STV"].copy()
if not ev_stv.empty:
    ev_stv_pos = posicion_en_fallo(ev_stv, misiones).dropna(subset=["posicion_inicial"])
    if not ev_stv_pos.empty:
        tramo_num = ev_stv_pos["posicion_inicial"].str.extract(r"T(\d+)")[0].dropna().astype(int)
        fallos_tramos = tramo_num.groupby(tramo_num).size().to_dict()

fig_plano = plano_almacen(
    fallos_pasillos=fallos_pasillos,
    fallos_tramos=fallos_tramos,
    titulo="",
)
st.plotly_chart(fig_plano, use_container_width=True,
                config={"displayModeBar": False})

st.caption(
    "**Lectura:** en el centro, cada pasillo representa un transelevador (SRM); "
    "alrededor, el anillo único de STV dividido en tramos. Cuanto más oscuro el "
    "color, mayor concentración de fallos en el periodo — las zonas en rojo son "
    "las que deben recibir atención prioritaria."
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
# Fila 3 — Alzado de un pasillo concreto (SRM): celda exacta Pxx-Ayy-Czz
# ---------------------------------------------------------------------------

st.subheader("Mapa de calor · alzado del pasillo (SRM)")

ev_pos = posicion_en_fallo(ev_enriq, misiones)
ev_pos_validos = ev_pos.dropna(subset=["posicion_inicial"])
srm_pos = ev_pos_validos[ev_pos_validos["posicion_inicial"].str.startswith("P", na=False)].copy()

if not srm_pos.empty:
    srm_pos["pasillo"] = (srm_pos["posicion_inicial"]
                          .str.extract(r"P(\d+)")[0]
                          .astype(str).str.zfill(2).apply(lambda x: f"P{x}"))
    srm_pos["altura"]  = (srm_pos["posicion_inicial"]
                          .str.extract(r"A(\d+)")[0]
                          .astype(str).str.zfill(2).apply(lambda x: f"A{x}"))
    srm_pos["columna"] = (srm_pos["posicion_inicial"]
                          .str.extract(r"C(\d+)")[0]
                          .astype(str).str.zfill(2).apply(lambda x: f"C{x}"))

    # Ranking de pasillos por nº de fallos para sugerir el más conflictivo por defecto
    fallos_por_pasillo = (srm_pos.groupby("pasillo").size()
                          .sort_values(ascending=False))
    pasillos_disponibles = [f"P{i:02d}" for i in range(1, 9)]
    pasillo_top = (fallos_por_pasillo.index[0]
                   if len(fallos_por_pasillo) else "P01")

    c_sel, c_info = st.columns([1, 3])
    with c_sel:
        st.markdown(
            """
            <style>
            div[data-testid="stSelectbox"] input { caret-color: transparent; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        pasillo_sel = st.selectbox(
            "Pasillo",
            options=pasillos_disponibles,
            index=pasillos_disponibles.index(pasillo_top),
            key="pasillo_alzado_sel",
        )
    with c_info:
        n_pasillo = int(fallos_por_pasillo.get(pasillo_sel, 0))
        st.markdown(
            f"<div style='padding-top:1.8rem;color:{GRIS_700};font-size:0.92rem;'>"
            f"Vista de alzado (columna × altura). Cada celda es una ubicación "
            f"física exacta. Pasillo seleccionado: <b>{pasillo_sel}</b> · "
            f"<b>{n_pasillo:,}</b> fallos en el periodo."
            f"</div>",
            unsafe_allow_html=True,
        )

    fig_alzado = heatmap_alzado_pasillo(srm_pos, pasillo=pasillo_sel)
    st.plotly_chart(fig_alzado, use_container_width=True,
                    config={"displayModeBar": False})

    # Top celdas del pasillo seleccionado
    sub = srm_pos[srm_pos["pasillo"] == pasillo_sel]
    if not sub.empty:
        top_celdas = (
            sub.groupby("posicion_inicial").size()
               .rename("n_fallos")
               .sort_values(ascending=False)
               .head(10)
               .reset_index()
               .rename(columns={"posicion_inicial": "Celda"})
        )
        ct, cv = st.columns([2, 3])
        with ct:
            st.markdown(f"**Top 10 celdas en {pasillo_sel}**")
            st.dataframe(
                top_celdas,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Celda": st.column_config.TextColumn("Celda"),
                    "n_fallos": st.column_config.ProgressColumn(
                        "Nº fallos",
                        format="%d",
                        min_value=0,
                        max_value=int(top_celdas["n_fallos"].max()),
                    ),
                },
            )

    st.caption(
        f"{len(ev_pos_validos):,} de {len(ev_pos):,} eventos con misión activa "
        f"identificada ({100 * len(ev_pos_validos) / max(len(ev_pos), 1):.0f}%)."
    )
else:
    st.info("Sin fallos SRM con posición identificada en el periodo.")

st.divider()

# ---------------------------------------------------------------------------
# Fila 4 — Evolución mensual
# ---------------------------------------------------------------------------

st.subheader("Evolución mensual del nº de fallos")
ev_enriq["ts_inicio_fallo"] = pd.to_datetime(ev_enriq["ts_inicio_fallo"])
ev_enriq["_mes"] = ev_enriq["ts_inicio_fallo"].dt.month
serie_fallos_mes = ev_enriq.groupby("_mes").size().rename("n_fallos")

fig_evol = serie_anual_area(
    serie_fallos_mes,
    titulo="",
    label_y="Nº fallos",
    referencia=float(serie_fallos_mes.mean()),
    color=CRITICO,
)
st.plotly_chart(fig_evol, use_container_width=True,
                config={"displayModeBar": False})

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
if not srm_pos.empty:
    _datasets_export["Fallos SRM por celda"] = (
        srm_pos.groupby("posicion_inicial").size()
               .rename("n_fallos").reset_index()
               .rename(columns={"posicion_inicial": "celda"})
    )

panel_exportacion(_datasets_export, prefijo="fallos")

pie_pagina()
