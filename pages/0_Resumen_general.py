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
    serie_anual_area, gauge_disponibilidad,
    sparkline, kpi_card_html,
)
from src.theme import (
    aplicar_tema, PRIMARIO, PRIMARIO_CLARO, EXITO, ADVERTENCIA, CRITICO,
    GRIS_500, GRIS_700,
)
from src.styles import inyectar_css, hero, lectura_ejecutiva
from src.config import UNIDAD_TIEMPO, init_session_state, rango_valido
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina
from src.insights import resumen_general
from src.export import panel_exportacion

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

# Eventos globales (sin rango) para calcular el delta vs. periodo anterior.
# No usamos las misiones globales (4,8 M filas) por rendimiento: el delta de
# ciclos se calcula directamente con counts del periodo y un derivado.
f_global_eventos = aplicar_filtros_globales(
    tablas, rango_fechas=None,
    tipos_equipo=tipos_equipo, zonas=zonas,
)["eventos"]

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

rango_tuple = (str(rango[0]), str(rango[1]))
unidad_label = "min" if UNIDAD_TIEMPO == "minutos" else "h"

# ---------------------------------------------------------------------------
# Cálculos: KPIs + delta + series mensuales para sparklines
# ---------------------------------------------------------------------------

kpis = kpis_globales(eventos, misiones, equipos, rango_tuple, UNIDAD_TIEMPO)
delta = delta_vs_periodo_anterior(
    eventos, misiones, rango_tuple,
    eventos_global=f_global_eventos,
    misiones_global=None,  # omitimos misiones globales por rendimiento (4,8M filas)
)

lectura_ejecutiva(resumen_general(eventos, misiones, equipos, rango_tuple))

# Series mensuales para sparkline
serie_disp_mensual = disponibilidad_mensual(eventos, rango_tuple)
serie_fallos_mensual = serie_mensual(
    eventos, "ts_inicio_fallo", "id_evento", agg="count"
)


def _fmt_delta_disp(v):
    if v is None:
        return None, None
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f} pp", v >= 0


def _fmt_delta_int(v, sufijo=""):
    if v is None:
        return None, None
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:,}{sufijo}", v <= 0   # menos fallos = mejor (delta positivo)


def _fmt_delta_mttr(v):
    if v is None:
        return None, None
    sign = "+" if v >= 0 else ""
    # MTTR menor = mejor
    return f"{sign}{v:.1f} min", v <= 0


# ---------------------------------------------------------------------------
# Fila 1 — KPIs principales con sparkline (2 cards grandes)
# ---------------------------------------------------------------------------

c1, c2 = st.columns(2)

with c1:
    st.markdown(
        f"""
        <div style="background:#F9FAFB;border:1px solid #E4E7EC;border-radius:12px;
                    padding:18px 22px;box-shadow:0 1px 2px rgba(16,24,40,0.05);">
            <div style="color:{GRIS_500};font-size:0.78rem;font-weight:500;
                        text-transform:uppercase;letter-spacing:0.04em;">
                Disponibilidad media
            </div>
            <div style="color:#101828;font-size:2.2rem;font-weight:700;
                        line-height:1.1;margin-top:4px;">
                {kpis['disponibilidad_media']:.2f} %
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        sparkline(serie_disp_mensual, color=EXITO, altura=70),
        use_container_width=True,
        config={"displayModeBar": False},
    )

with c2:
    st.markdown(
        f"""
        <div style="background:#F9FAFB;border:1px solid #E4E7EC;border-radius:12px;
                    padding:18px 22px;box-shadow:0 1px 2px rgba(16,24,40,0.05);">
            <div style="color:{GRIS_500};font-size:0.78rem;font-weight:500;
                        text-transform:uppercase;letter-spacing:0.04em;">
                Fallos en el periodo
            </div>
            <div style="color:#101828;font-size:2.2rem;font-weight:700;
                        line-height:1.1;margin-top:4px;">
                {kpis['n_fallos']:,}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        sparkline(serie_fallos_mensual, color=CRITICO, altura=70),
        use_container_width=True,
        config={"displayModeBar": False},
    )

st.markdown("")

# ---------------------------------------------------------------------------
# Fila 2 — KPIs secundarios con delta
# ---------------------------------------------------------------------------

c3, c4, c5 = st.columns(3)

delta_mttr_txt, delta_mttr_pos = _fmt_delta_mttr(delta["delta_mttr_min"])
delta_ciclos_txt, delta_ciclos_pos = _fmt_delta_int(delta["delta_ciclos"])
# Para ciclos, más es mejor → invertir el signo lógico
if delta["delta_ciclos"] is not None:
    delta_ciclos_pos = delta["delta_ciclos"] >= 0

with c3:
    st.markdown(
        kpi_card_html(
            f"MTTR medio ({unidad_label})",
            f"{kpis['mttr_medio']:.1f}",
            delta_mttr_txt,
            delta_mttr_pos,
            icono="🛠️",
        ),
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        kpi_card_html(
            f"MTBF medio ({unidad_label})",
            f"{kpis['mtbf_medio']:,.0f}",
            None, None,
            icono="⏱️",
        ),
        unsafe_allow_html=True,
    )

with c5:
    st.markdown(
        kpi_card_html(
            "Ciclos totales",
            f"{kpis['ciclos_totales']:,}",
            delta_ciclos_txt,
            delta_ciclos_pos,
            icono="🔄",
        ),
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Fila 3 — Gauge + evolución anual de disponibilidad
# ---------------------------------------------------------------------------

cg, ce = st.columns([1, 2])

with cg:
    fig_gauge = gauge_disponibilidad(
        kpis["disponibilidad_media"],
        referencia=95.0,
        titulo="Disponibilidad vs. objetivo (95%)",
    )
    st.plotly_chart(fig_gauge, use_container_width=True,
                    config={"displayModeBar": False})

with ce:
    fig_evol = serie_anual_area(
        serie_disp_mensual,
        titulo="Evolución mensual de la disponibilidad",
        label_y="Disponibilidad (%)",
        referencia=float(kpis["disponibilidad_media"]),
    )
    st.plotly_chart(fig_evol, use_container_width=True,
                    config={"displayModeBar": False})

st.divider()

# ---------------------------------------------------------------------------
# Fila 4 — Top 5 con peor disponibilidad
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
    "Disponibilidad mensual": serie_disp_mensual.rename("disponibilidad_pct")
                              .reset_index().rename(columns={"index": "mes"}),
    "Fallos mensuales": serie_fallos_mensual.rename("n_fallos")
                        .reset_index().rename(columns={"index": "mes"}),
}
if not eventos.empty:
    _datasets_export["Top 5 peor disponibilidad"] = top5

panel_exportacion(_datasets_export, prefijo="resumen")

pie_pagina()
