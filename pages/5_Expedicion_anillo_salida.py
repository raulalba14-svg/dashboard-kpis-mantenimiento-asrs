"""Módulo 5 — Expedición y rendimiento del anillo de salida."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.data_loader import cargar_tablas, aplicar_filtros_globales
from src.kpis import tiempo_ciclo, ciclos_por_equipo
from src.charts import (
    histograma_distribucion, barras_ranking_umbrales, dual_axis,
    kpi_card_html,
)
from src.theme import (
    aplicar_tema, PRIMARIO, PRIMARIO_CLARO, EXITO, ADVERTENCIA, CRITICO,
    GRIS_500, GRIS_700,
)
from src.styles import inyectar_css, hero, lectura_ejecutiva
from src.config import init_session_state, rango_valido
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina
from src.insights import expedicion
from src.export import panel_exportacion

st.set_page_config(
    page_title="Expedición / anillo de salida",
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
    kicker="Módulo 5",
    titulo="Expedición y rendimiento del anillo de salida",
    subtitulo=(
        "Tiempos de ciclo y throughput de los <b>10 STV de salida</b> con "
        "doble cuna (dos pallets por misión)."
    ),
)

# ---------------------------------------------------------------------------
# Carga: solo anillo salida
# ---------------------------------------------------------------------------

_cargar = st.cache_data(cargar_tablas)
tablas = _cargar()

f = aplicar_filtros_globales(
    tablas,
    rango_fechas=(str(rango[0]), str(rango[1])),
    tipos_equipo=["STV"], zonas=["anillo_salida"],
)
misiones = f["misiones"]
equipos  = f["equipos"]

if misiones.empty:
    st.warning("No hay datos del anillo de salida para el periodo seleccionado.")
    st.stop()

completadas = misiones[misiones["estado"] == "completada"].copy()
if completadas.empty:
    st.warning("No hay misiones completadas en el periodo seleccionado.")
    st.stop()

tc_s = tiempo_ciclo(completadas, unidad="segundos")
tc_min = tiempo_ciclo(completadas, unidad="minutos")

ts_ini_global = pd.Timestamp(str(rango[0]))
ts_fin_global = pd.Timestamp(str(rango[1])) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
horas_periodo = (ts_fin_global - ts_ini_global).total_seconds() / 3600.0
n_misiones_comp = len(completadas)
pallets_totales = n_misiones_comp * 2
throughput_global = pallets_totales / horas_periodo if horas_periodo > 0 else 0.0

# ---------------------------------------------------------------------------
# Fila 1 — Tarjetas KPI
# ---------------------------------------------------------------------------

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(kpi_card_html("Misiones completadas",
                              f"{n_misiones_comp:,}",
                              icono="✅"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card_html("Pallets expedidos",
                              f"{pallets_totales:,}",
                              icono="📦"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card_html("Throughput (pallets/h)",
                              f"{throughput_global:.1f}",
                              icono="🚀"), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card_html("TC medio (s)",
                              f"{tc_s.mean():.1f}",
                              icono="⏱️"), unsafe_allow_html=True)
with c5:
    st.markdown(kpi_card_html("TC mediana (s)",
                              f"{tc_s.median():.1f}",
                              icono="📊"), unsafe_allow_html=True)

lectura_ejecutiva(expedicion(misiones, equipos, (str(rango[0]), str(rango[1]))))

st.divider()

# ---------------------------------------------------------------------------
# Fila 2 — Distribución del tiempo de ciclo
# ---------------------------------------------------------------------------

st.subheader("Distribución del tiempo de ciclo")

fig_hist = histograma_distribucion(
    tc_s,
    titulo="",
    label_x="Tiempo de ciclo (segundos)",
    nbins=50,
)
st.plotly_chart(fig_hist, use_container_width=True,
                config={"displayModeBar": False})

p25, p50, p75, p95 = tc_s.quantile([0.25, 0.50, 0.75, 0.95])
st.caption(f"P25: {p25:.1f} s · P50: {p50:.1f} s · P75: {p75:.1f} s · P95: {p95:.1f} s")

st.divider()

# ---------------------------------------------------------------------------
# Fila 3 — Rendimiento por STV de salida
# ---------------------------------------------------------------------------

st.subheader("Rendimiento por STV de salida")

completadas["ts_inicio"] = pd.to_datetime(completadas["ts_inicio"])
completadas["ts_fin"]    = pd.to_datetime(completadas["ts_fin"])
completadas["tc_s"] = (completadas["ts_fin"] - completadas["ts_inicio"]).dt.total_seconds()

tc_por_stv = completadas.groupby("id_equipo")["tc_s"].agg(
    tc_medio="mean", tc_mediana="median", n_misiones="count"
).reset_index()
tc_por_stv["pallets"] = tc_por_stv["n_misiones"] * 2
tc_por_stv["throughput_ph"] = tc_por_stv["pallets"] / horas_periodo
p75_global = float(tc_s.quantile(0.75))
tc_por_stv["cuello_botella"] = tc_por_stv["tc_medio"] > p75_global

st.dataframe(
    tc_por_stv[["id_equipo", "tc_medio", "tc_mediana", "n_misiones",
                "pallets", "throughput_ph", "cuello_botella"]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "id_equipo":       st.column_config.TextColumn("STV"),
        "tc_medio":        st.column_config.NumberColumn("TC medio (s)", format="%.1f"),
        "tc_mediana":      st.column_config.NumberColumn("TC mediana (s)", format="%.1f"),
        "n_misiones":      st.column_config.NumberColumn("Misiones", format="%d"),
        "pallets":         st.column_config.NumberColumn("Pallets", format="%d"),
        "throughput_ph":   st.column_config.NumberColumn("Throughput (p/h)", format="%.1f"),
        "cuello_botella":  st.column_config.CheckboxColumn(
            "⚠️ Cuello", help=f"TC medio > P75 global ({p75_global:.0f} s)"
        ),
    },
)

# Barras (menor TC = mejor; aquí invertimos: cuanto más alto, peor)
serie_tc = tc_por_stv.set_index("id_equipo")["tc_medio"]
df_bar = serie_tc.sort_values(ascending=False).reset_index()
df_bar.columns = ["equipo", "tc"]

fig_tc = go.Figure(go.Bar(
    x=df_bar["tc"], y=df_bar["equipo"], orientation="h",
    marker=dict(color=df_bar["tc"].apply(
        lambda v: CRITICO if v > p75_global * 1.1
                  else (ADVERTENCIA if v > p75_global else EXITO)
    ).tolist(), line=dict(color="white", width=0.5)),
    text=df_bar["tc"].map("{:.1f} s".format),
    textposition="outside",
    textfont=dict(color=GRIS_700, size=11),
    hovertemplate="<b>%{y}</b><br>TC medio: %{x:.1f} s<extra></extra>",
))
fig_tc.add_vline(x=p75_global, line_dash="dash", line_color=GRIS_500,
                 annotation_text=f"P75 global: {p75_global:.0f} s",
                 annotation_position="top", annotation_font_color=GRIS_700)
fig_tc.update_layout(
    title="Tiempo de ciclo medio por STV (s)",
    xaxis_title="TC medio (s)",
    yaxis_title="",
    height=max(280, 28 * len(df_bar) + 80),
    bargap=0.3,
)
st.plotly_chart(fig_tc, use_container_width=True,
                config={"displayModeBar": False})

cuellos = tc_por_stv[tc_por_stv["cuello_botella"]]["id_equipo"].tolist()
if cuellos:
    st.caption(f"⚠️ Cuellos de botella: {', '.join(cuellos)}")

st.divider()

# ---------------------------------------------------------------------------
# Fila 4 — Detalle individual
# ---------------------------------------------------------------------------

with st.expander("🔍 Detalle individual de un STV de salida", expanded=False):
    stv_ids = sorted(completadas["id_equipo"].unique().tolist())
    stv_sel = st.selectbox("Selecciona un STV",
                           options=["Todos"] + stv_ids,
                           key="m5_stv_sel")

    if stv_sel != "Todos":
        mis_sel = completadas[completadas["id_equipo"] == stv_sel]
        tc_sel  = mis_sel["tc_s"]
        st.markdown(f"**{stv_sel}** · {len(mis_sel):,} misiones completadas")

        ca, cb, cc, cd = st.columns(4)
        with ca:
            st.markdown(kpi_card_html("TC medio (s)",
                                      f"{tc_sel.mean():.1f}"),
                        unsafe_allow_html=True)
        with cb:
            st.markdown(kpi_card_html("TC mediana (s)",
                                      f"{tc_sel.median():.1f}"),
                        unsafe_allow_html=True)
        with cc:
            st.markdown(kpi_card_html("Pallets",
                                      f"{len(mis_sel) * 2:,}"),
                        unsafe_allow_html=True)
        with cd:
            st.markdown(kpi_card_html("Throughput (p/h)",
                                      f"{len(mis_sel) * 2 / horas_periodo:.1f}"),
                        unsafe_allow_html=True)

        fig_ind = histograma_distribucion(
            tc_sel,
            titulo=f"Distribución TC · {stv_sel}",
            label_x="Tiempo de ciclo (s)",
        )
        st.plotly_chart(fig_ind, use_container_width=True,
                        config={"displayModeBar": False})

st.divider()

# ---------------------------------------------------------------------------
# Fila 5 — Evolución mensual: TC + throughput (dual axis)
# ---------------------------------------------------------------------------

st.subheader("Evolución mensual · tiempo de ciclo + throughput")

completadas["_mes"] = completadas["ts_inicio"].dt.month
tc_mensual = completadas.groupby("_mes")["tc_s"].mean()

# Throughput mensual con horas reales de cada mes acotadas al rango
horas_por_mes = {}
mes_actual = ts_ini_global.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
while mes_actual <= ts_fin_global:
    mes_fin = (mes_actual + pd.offsets.MonthBegin(1)) - pd.Timedelta(seconds=1)
    sub_ini = max(mes_actual, ts_ini_global)
    sub_fin = min(mes_fin, ts_fin_global)
    horas = (sub_fin - sub_ini).total_seconds() / 3600.0
    if horas > 0:
        horas_por_mes[mes_actual.month] = horas
    mes_actual = mes_actual + pd.offsets.MonthBegin(1)

pallets_mes = completadas.groupby("_mes").size() * 2
throughput_mensual = pallets_mes.div(pd.Series(horas_por_mes))

# Alinear índices
meses_validos = sorted(set(tc_mensual.index) & set(throughput_mensual.index))
tc_align = tc_mensual.reindex(meses_validos)
th_align = throughput_mensual.reindex(meses_validos)

fig_dual = dual_axis(
    th_align, "Throughput (p/h)", PRIMARIO_CLARO,
    tc_align, "TC medio (s)",     ADVERTENCIA,
    titulo="",
)
st.plotly_chart(fig_dual, use_container_width=True,
                config={"displayModeBar": False})
st.caption(
    "**Lectura:** las barras representan throughput mensual (pallets/h); "
    "la línea, TC medio mensual (s). Una **subida del TC con bajada del throughput** "
    "indica saturación o degradación del rendimiento."
)

st.divider()

# ---------------------------------------------------------------------------
# Exportación de datos
# ---------------------------------------------------------------------------

panel_exportacion(
    {
        "Rendimiento por STV": tc_por_stv,
        "Evolución mensual": pd.DataFrame({
            "mes": meses_validos,
            "tc_medio_s": tc_align.values,
            "throughput_ph": th_align.values,
        }),
        "Resumen del periodo": pd.DataFrame([{
            "n_misiones_completadas": n_misiones_comp,
            "pallets_totales": pallets_totales,
            "throughput_ph_global": round(throughput_global, 2),
            "tc_medio_s": round(float(tc_s.mean()), 2),
            "tc_mediana_s": round(float(tc_s.median()), 2),
            "tc_p25_s": round(float(p25), 2),
            "tc_p75_s": round(float(p75), 2),
            "tc_p95_s": round(float(p95), 2),
        }]),
    },
    prefijo="expedicion",
)

pie_pagina()
