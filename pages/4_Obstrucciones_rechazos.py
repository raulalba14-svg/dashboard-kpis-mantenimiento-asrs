"""Módulo 4 — Obstrucciones y rechazos."""

import streamlit as st
import pandas as pd

from src.data_loader import cargar_tablas, aplicar_filtros_globales
from src.kpis import tasa_rechazo
from src.charts import (
    banda_tramos, barras_ranking_umbrales, serie_anual_area,
    donut_categoria, kpi_card_html,
)
from src.theme import (
    aplicar_tema, PRIMARIO, PRIMARIO_CLARO, ADVERTENCIA, CRITICO,
    GRIS_500, GRIS_700,
)
from src.styles import inyectar_css, hero, lectura_ejecutiva
from src.config import init_session_state, rango_valido, CODIGOS_MANTENIMIENTO
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina
from src.insights import obstrucciones_rechazos
from src.export import panel_exportacion

st.set_page_config(
    page_title="Obstrucciones y rechazos",
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
    titulo="Obstrucciones y rechazos",
    subtitulo=(
        "Análisis del anillo: distribución geográfica de rechazos, "
        "separación entre causa de mantenimiento (sensor) y operativa (saturación)."
    ),
)

# ---------------------------------------------------------------------------
# Carga: STV de ambos anillos
# ---------------------------------------------------------------------------

_cargar = st.cache_data(cargar_tablas)
tablas = _cargar()

f = aplicar_filtros_globales(
    tablas,
    rango_fechas=(str(rango[0]), str(rango[1])),
    tipos_equipo=["STV"], zonas=["anillo_entrada", "anillo_salida"],
)
eventos     = f["eventos"]
misiones    = f["misiones"]
equipos     = f["equipos"]
tipos_error = f["tipos_error"]

rango_tuple = (str(rango[0]), str(rango[1]))

if misiones.empty:
    st.warning("No hay datos de misiones para el periodo seleccionado.")
    st.stop()

# ---------------------------------------------------------------------------
# Cálculos
# ---------------------------------------------------------------------------

rechazadas = misiones[misiones["estado"] == "rechazada"].copy()
abortadas  = misiones[misiones["estado"] == "abortada"].copy()

ev_cat = eventos.merge(
    tipos_error[["codigo", "descripcion"]],
    left_on="codigo_error", right_on="codigo", how="left",
)

ev_mant = ev_cat[ev_cat["codigo_error"].isin(CODIGOS_MANTENIMIENTO)]
ev_oper = ev_cat[~ev_cat["codigo_error"].isin(CODIGOS_MANTENIMIENTO)]

tasa_global = tasa_rechazo(misiones)
n_rechazos  = len(rechazadas)
n_misiones  = len(misiones)
n_abortadas = len(abortadas)

# ---------------------------------------------------------------------------
# Fila 1 — KPIs en tarjetas
# ---------------------------------------------------------------------------

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(kpi_card_html("Misiones totales", f"{n_misiones:,}",
                              icono="📦"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card_html("Rechazadas", f"{n_rechazos:,}",
                              icono="🚫"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card_html("Tasa de rechazo",
                              f"{tasa_global * 100:.2f} %",
                              icono="📊"), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card_html("Abortadas", f"{n_abortadas:,}",
                              icono="⚠️"), unsafe_allow_html=True)

lectura_ejecutiva(obstrucciones_rechazos(misiones, eventos))

st.divider()

# ---------------------------------------------------------------------------
# Fila 2 — Distribución geográfica como banda
# ---------------------------------------------------------------------------

st.subheader("Distribución geográfica de rechazos")

if rechazadas.empty:
    st.info("Sin misiones rechazadas en el periodo seleccionado.")
else:
    rechazadas["tramo"] = rechazadas["posicion_inicial"].str.extract(r"(ENT-T\d+|SAL-T\d+)")
    rechazadas["anillo"] = rechazadas["tramo"].str[:3]

    # Entrada
    rech_ent = rechazadas[rechazadas["anillo"] == "ENT"]
    rech_sal = rechazadas[rechazadas["anillo"] == "SAL"]

    if not rech_ent.empty:
        serie_ent = (rech_ent.groupby("tramo").size()
                              .sort_index().rename("rechazos"))
        st.markdown(
            f"<div style='color:{GRIS_700};font-weight:600;margin-top:8px;'>"
            f"Anillo de entrada</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            banda_tramos(serie_ent,
                         titulo="",
                         label_y="Nº rechazos",
                         color=PRIMARIO),
            use_container_width=True, config={"displayModeBar": False},
        )

    if not rech_sal.empty:
        serie_sal = (rech_sal.groupby("tramo").size()
                              .sort_index().rename("rechazos"))
        st.markdown(
            f"<div style='color:{GRIS_700};font-weight:600;margin-top:8px;'>"
            f"Anillo de salida</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            banda_tramos(serie_sal,
                         titulo="",
                         label_y="Nº rechazos",
                         color=PRIMARIO_CLARO),
            use_container_width=True, config={"displayModeBar": False},
        )

st.divider()

# ---------------------------------------------------------------------------
# Fila 3 — Causa mantenimiento vs operativa
# ---------------------------------------------------------------------------

st.subheader("Causa: mantenimiento vs. operativa")
st.caption(
    "**Mantenimiento** — código E12: rechazo por inspector de pallets (sensor descalibrado). "
    "**Operativa** — resto de causas: saturación del anillo, error de lectura, obstrucción."
)

ratio_mant = len(ev_mant) / max(len(ev_cat), 1) * 100

col_donut, col_tabla = st.columns([2, 3])

with col_donut:
    serie_causa = pd.Series({
        "Mantenimiento (E12)": len(ev_mant),
        "Operativa":            len(ev_oper),
    })
    color_map_causa = {
        "Mantenimiento (E12)": ADVERTENCIA,
        "Operativa":            PRIMARIO,
    }
    if serie_causa.sum() > 0:
        st.plotly_chart(
            donut_categoria(serie_causa, titulo="", color_map=color_map_causa),
            use_container_width=True, config={"displayModeBar": False},
        )
    else:
        st.info("Sin eventos en el periodo.")

with col_tabla:
    st.markdown(f"**Mantenimiento (E12)** · {len(ev_mant):,} eventos · {ratio_mant:.1f}% del total")
    if not ev_mant.empty:
        n_mant_eq = (ev_mant.groupby("id_equipo").size()
                            .sort_values(ascending=False)
                            .rename("eventos").head(10))
        st.dataframe(
            n_mant_eq.reset_index().rename(
                columns={"id_equipo": "Equipo", "eventos": "Eventos E12"}
            ),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("Sin eventos E12 en el periodo.")

st.divider()

# ---------------------------------------------------------------------------
# Fila 4 — Tasa de rechazo por equipo
# ---------------------------------------------------------------------------

st.subheader("Tasa de rechazo por STV")

if not rechazadas.empty:
    tasa_eq = tasa_rechazo(misiones, agrupar_por="id_equipo") * 100
    media_tasa = float(tasa_eq.mean())
    # Para tasa de rechazo: menor = mejor (umbrales invertidos)
    # Reutilizamos barras_ranking_umbrales con interpretación inversa.
    # Pero la función trata "mayor = mejor". Construimos a mano para invertir colores.
    df = tasa_eq.sort_values(ascending=False).reset_index()
    df.columns = ["equipo", "tasa"]

    import plotly.graph_objects as go
    fig = go.Figure(go.Bar(
        x=df["tasa"], y=df["equipo"], orientation="h",
        marker=dict(color=df["tasa"].apply(
            lambda v: CRITICO if v >= 3.0 else (ADVERTENCIA if v >= 2.0 else PRIMARIO)
        ).tolist(),
                    line=dict(color="white", width=0.5)),
        text=df["tasa"].map("{:.2f}%".format),
        textposition="outside",
        textfont=dict(color=GRIS_700, size=11),
        hovertemplate="<b>%{y}</b><br>%{x:.2f}%<extra></extra>",
    ))
    fig.add_vline(x=media_tasa, line_dash="dash", line_color=GRIS_500,
                  annotation_text=f"Media: {media_tasa:.2f}%",
                  annotation_position="top", annotation_font_color=GRIS_700)
    fig.update_layout(
        title="",
        xaxis_title="Tasa de rechazo (%)",
        yaxis_title="",
        height=max(280, 18 * len(df) + 80),
        bargap=0.25,
    )
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False})
    st.caption("🟦 < 2 %  ·  🟠 2 – 3 %  ·  🔴 ≥ 3 %")

st.divider()

# ---------------------------------------------------------------------------
# Fila 5 — Evolución mensual de la tasa de rechazo
# ---------------------------------------------------------------------------

st.subheader("Evolución mensual de la tasa de rechazo")

misiones_mes = misiones.copy()
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
    referencia=float(tasa_global * 100),
    color=ADVERTENCIA,
)
st.plotly_chart(fig_evol, use_container_width=True,
                config={"displayModeBar": False})

st.divider()

# ---------------------------------------------------------------------------
# Exportación de datos
# ---------------------------------------------------------------------------

_datasets_export = {
    "Tasa de rechazo mensual": tasa_mes.reset_index().rename(
        columns={"_mes": "mes"}
    ),
    "Causa mantenimiento vs operativa": pd.DataFrame({
        "categoria": ["Mantenimiento (E12)", "Operativa"],
        "eventos": [len(ev_mant), len(ev_oper)],
    }),
}
if not rechazadas.empty:
    _datasets_export["Rechazos por tramo"] = (
        rechazadas.groupby("tramo").size().rename("rechazos").reset_index()
    )
    _datasets_export["Tasa de rechazo por STV"] = (
        tasa_eq.rename("tasa_rechazo_pct").reset_index()
    )

panel_exportacion(_datasets_export, prefijo="rechazos")

pie_pagina()
