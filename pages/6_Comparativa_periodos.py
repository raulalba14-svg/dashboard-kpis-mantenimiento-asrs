"""Módulo 4 — Comparativa de periodos."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.data_loader import aplicar_filtros_globales
from src.data_ui import cargar_tablas_con_feedback
from src.kpis import kpis_globales, disponibilidad_por_equipo
from src.charts import kpi_card_html
from src.theme import (
    aplicar_tema, PRIMARIO, PRIMARIO_CLARO, EXITO, CRITICO,
    GRIS_500, GRIS_700,
)
from src.styles import inyectar_css, hero
from src.config import (
    UNIDAD_TIEMPO, FECHA_INICIO, FECHA_FIN, init_session_state,
    rango_calendario,
)
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina
from src.export import panel_exportacion
from src.format import fmt_es

st.set_page_config(
    page_title="Comparativa de periodos",
    page_icon=str(FAVICON) if FAVICON.exists() else None,
    layout="wide",
)
aplicar_tema()
inyectar_css()
init_session_state()
render_sidebar_filtros()

hero(
    kicker="Módulo 6",
    titulo="Comparativa de periodos",
    subtitulo=(
        "Compara dos rangos de fechas y mide la variación de los KPIs principales "
        "para detectar mejoras, regresiones o estacionalidad."
    ),
)

# ---------------------------------------------------------------------------
# Selección de periodos
# ---------------------------------------------------------------------------

fecha_min = pd.Timestamp(FECHA_INICIO).date()
fecha_max = pd.Timestamp(FECHA_FIN).date()

# Defaults útiles: S1 vs S2 del año
s1_fin_default = pd.Timestamp(f"{fecha_min.year}-06-30").date()
s2_ini_default = pd.Timestamp(f"{fecha_min.year}-07-01").date()

col_a, col_b = st.columns(2)
with col_a:
    st.markdown(
        f"<div style='color:{GRIS_500};font-size:0.78rem;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:0.04em;'>"
        f"Periodo A · referencia</div>",
        unsafe_allow_html=True,
    )
    rango_a = st.date_input(
        "Rango A",
        value=(fecha_min, s1_fin_default),
        min_value=fecha_min,
        max_value=fecha_max,
        key="cmp_rango_a",
        label_visibility="collapsed",
    )

with col_b:
    st.markdown(
        f"<div style='color:{GRIS_500};font-size:0.78rem;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:0.04em;'>"
        f"Periodo B · comparado</div>",
        unsafe_allow_html=True,
    )
    rango_b = st.date_input(
        "Rango B",
        value=(s2_ini_default, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max,
        key="cmp_rango_b",
        label_visibility="collapsed",
    )


def _rango_ok(r) -> bool:
    return (
        isinstance(r, (tuple, list)) and len(r) == 2
        and r[0] is not None and r[1] is not None and r[0] <= r[1]
    )


if not (_rango_ok(rango_a) and _rango_ok(rango_b)):
    st.info("Selecciona inicio y fin para ambos periodos.")
    st.stop()

# ---------------------------------------------------------------------------
# Carga + filtrado por periodo (respetando filtros globales de tipo/zona)
# ---------------------------------------------------------------------------

tipos_equipo = st.session_state.get("tipos_equipo")
zonas        = st.session_state.get("zonas")

_cargar = st.cache_data(cargar_tablas_con_feedback)
tablas = _cargar()

fa = aplicar_filtros_globales(
    tablas,
    rango_fechas=(str(rango_a[0]), str(rango_a[1])),
    tipos_equipo=tipos_equipo, zonas=zonas,
)
fb = aplicar_filtros_globales(
    tablas,
    rango_fechas=(str(rango_b[0]), str(rango_b[1])),
    tipos_equipo=tipos_equipo, zonas=zonas,
)

# Calendario de los KPIs: [inicio, fin + 1 día), coherente con el filtro de
# fechas (que incluye el día final completo). Permite comparar rangos de 1 día.
rango_a_tuple = rango_calendario(rango_a)
rango_b_tuple = rango_calendario(rango_b)
unidad_label = "min" if UNIDAD_TIEMPO == "minutos" else "h"

kpis_a = kpis_globales(fa["eventos"], fa["misiones"], fa["equipos"],
                       rango_a_tuple, UNIDAD_TIEMPO)
kpis_b = kpis_globales(fb["eventos"], fb["misiones"], fb["equipos"],
                       rango_b_tuple, UNIDAD_TIEMPO)


def _dias(r):
    return (pd.Timestamp(r[1]) - pd.Timestamp(r[0])).days + 1


dias_a, dias_b = _dias(rango_a), _dias(rango_b)

st.caption(
    f"**A**: {rango_a[0]:%d/%m/%Y} → {rango_a[1]:%d/%m/%Y} · {dias_a} días  "
    f"&nbsp;&nbsp;|&nbsp;&nbsp;  "
    f"**B**: {rango_b[0]:%d/%m/%Y} → {rango_b[1]:%d/%m/%Y} · {dias_b} días"
)
if dias_a != dias_b:
    st.warning(
        f"Los periodos tienen duración distinta ({dias_a} vs {dias_b} días). "
        f"Los KPIs de tasa (disponibilidad, MTTR) son comparables; "
        f"los conteos absolutos (fallos, ciclos) NO lo son directamente."
    )

st.divider()

# ---------------------------------------------------------------------------
# KPIs comparados
# ---------------------------------------------------------------------------

def _delta_card(label, val_a, val_b, decimales=2, sufijo="", mejor="alto"):
    """Renderiza una tarjeta comparativa A vs B con mini-barras y chip de delta.

    Las dos barras se escalan contra el mayor de los dos valores de la propia
    tarjeta, de modo que su longitud relativa refleja la diferencia A↔B.
    Los números se muestran en formato español (punto de miles, coma decimal).
    """
    delta = val_b - val_a
    if mejor == "alto":
        signo_ok = delta >= 0
    else:
        signo_ok = delta <= 0
    color = EXITO if signo_ok else CRITICO
    flecha = "▲" if delta > 0 else ("▼" if delta < 0 else "■")
    signo = "+" if delta > 0 else ""

    # Barras proporcionales al mayor de los dos valores de la tarjeta.
    ref = max(abs(val_a), abs(val_b)) or 1.0
    pct_a = max(0.0, min(100.0, abs(val_a) / ref * 100))
    pct_b = max(0.0, min(100.0, abs(val_b) / ref * 100))

    # HTML compacto en una sola línea: si dejamos saltos de línea con sangría,
    # el parser de Markdown de st.markdown lo interpreta como bloque de código
    # y lo muestra como texto crudo en lugar de renderizarlo.
    def _fila(letra, valor, pct, color_barra):
        return (
            '<div style="display:flex;align-items:center;gap:10px;margin-top:7px;">'
            f'<div style="color:{GRIS_500};font-size:0.7rem;width:12px;flex:none;'
            f'font-weight:600;">{letra}</div>'
            '<div style="flex:1;background:#F2F4F7;border-radius:6px;height:9px;'
            'overflow:hidden;">'
            f'<div style="width:{pct:.1f}%;background:{color_barra};height:100%;'
            'border-radius:6px;"></div></div>'
            '<div style="color:#101828;font-size:1.05rem;font-weight:600;'
            'white-space:nowrap;text-align:right;min-width:84px;">'
            f'{fmt_es(valor, decimales)}{sufijo}</div>'
            '</div>'
        )

    return (
        '<div style="background:#FFFFFF;border:1px solid #E4E7EC;border-radius:12px;'
        'padding:16px 20px;box-shadow:0 1px 2px rgba(16,24,40,0.05);">'
        '<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<div style="color:{GRIS_500};font-size:0.72rem;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:0.04em;">{label}</div>'
        f'<div style="background:{color}1A;color:{color};font-size:0.82rem;'
        'font-weight:700;padding:3px 10px;border-radius:999px;white-space:nowrap;">'
        f'{flecha} {signo}{fmt_es(delta, decimales)}{sufijo}</div>'
        '</div>'
        f'{_fila("A", val_a, pct_a, PRIMARIO_CLARO)}'
        f'{_fila("B", val_b, pct_b, PRIMARIO)}'
        '</div>'
    )


c1, c2 = st.columns(2)
with c1:
    st.markdown(
        _delta_card("Disponibilidad media",
                    kpis_a["disponibilidad_media"], kpis_b["disponibilidad_media"],
                    decimales=2, sufijo=" %", mejor="alto"),
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        _delta_card(f"MTTR medio ({unidad_label})",
                    kpis_a["mttr_medio"], kpis_b["mttr_medio"],
                    decimales=1, mejor="bajo"),
        unsafe_allow_html=True,
    )

c3, c4 = st.columns(2)
with c3:
    st.markdown(
        _delta_card("Nº fallos",
                    kpis_a["n_fallos"], kpis_b["n_fallos"],
                    decimales=0, mejor="bajo"),
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        _delta_card("Ciclos totales",
                    kpis_a["ciclos_totales"], kpis_b["ciclos_totales"],
                    decimales=0, mejor="alto"),
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Comparativa por equipo (disponibilidad A vs B)
# ---------------------------------------------------------------------------

st.subheader("Disponibilidad por equipo · A vs B")

disp_a = disponibilidad_por_equipo(fa["eventos"], rango_a_tuple) if not fa["eventos"].empty else pd.Series(dtype=float)
disp_b = disponibilidad_por_equipo(fb["eventos"], rango_b_tuple) if not fb["eventos"].empty else pd.Series(dtype=float)

todos_ids = fa["equipos"]["id"].tolist()
disp_a = disp_a.reindex(todos_ids).fillna(100.0)
disp_b = disp_b.reindex(todos_ids).fillna(100.0)

df_disp = pd.DataFrame({
    "id_equipo": todos_ids,
    "disp_a": disp_a.values,
    "disp_b": disp_b.values,
})
df_disp["delta"] = df_disp["disp_b"] - df_disp["disp_a"]
df_disp = df_disp.sort_values("delta")

c_chart, c_tabla = st.columns([3, 2])

with c_chart:
    top_n = min(20, len(df_disp))
    top_caidas = df_disp.head(top_n // 2)
    top_subidas = df_disp.tail(top_n - len(top_caidas))
    df_focus = pd.concat([top_caidas, top_subidas])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_focus["disp_a"], y=df_focus["id_equipo"], orientation="h",
        name="Periodo A",
        marker=dict(color=PRIMARIO_CLARO),
        hovertemplate="<b>%{y}</b><br>A: %{x:.2f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=df_focus["disp_b"], y=df_focus["id_equipo"], orientation="h",
        name="Periodo B",
        marker=dict(color=PRIMARIO),
        hovertemplate="<b>%{y}</b><br>B: %{x:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        barmode="group",
        title=f"Top {len(df_focus)} equipos por cambio de disponibilidad",
        xaxis_title="Disponibilidad (%)",
        yaxis_title="",
        height=max(320, 22 * len(df_focus) + 100),
        bargap=0.25,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False})

with c_tabla:
    st.markdown("**Mayores caídas / subidas de disponibilidad**")
    mostrar = pd.concat([
        df_disp.head(5).assign(_grupo="Caída"),
        df_disp.tail(5).assign(_grupo="Mejora")[::-1],
    ])
    st.dataframe(
        mostrar[["id_equipo", "disp_a", "disp_b", "delta"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "id_equipo": st.column_config.TextColumn("Equipo"),
            "disp_a":    st.column_config.NumberColumn("A (%)", format="%.2f"),
            "disp_b":    st.column_config.NumberColumn("B (%)", format="%.2f"),
            "delta":     st.column_config.NumberColumn("Δ (pp)", format="%+.2f"),
        },
    )

st.caption(
    "**Lectura:** los equipos con **Δ negativo** han empeorado su disponibilidad "
    "en el periodo B; los de **Δ positivo** han mejorado. Una caída marcada "
    "señala un equipo cuya regresión hay que investigar."
)

st.divider()

# ---------------------------------------------------------------------------
# Exportación
# ---------------------------------------------------------------------------

panel_exportacion(
    {
        "KPIs comparados": pd.DataFrame([
            {"kpi": "disponibilidad_media_pct",
             "A": kpis_a["disponibilidad_media"],
             "B": kpis_b["disponibilidad_media"],
             "delta": kpis_b["disponibilidad_media"] - kpis_a["disponibilidad_media"]},
            {"kpi": f"mttr_medio_{unidad_label}",
             "A": kpis_a["mttr_medio"],
             "B": kpis_b["mttr_medio"],
             "delta": kpis_b["mttr_medio"] - kpis_a["mttr_medio"]},
            {"kpi": "n_fallos",
             "A": kpis_a["n_fallos"],
             "B": kpis_b["n_fallos"],
             "delta": kpis_b["n_fallos"] - kpis_a["n_fallos"]},
            {"kpi": "ciclos_totales",
             "A": kpis_a["ciclos_totales"],
             "B": kpis_b["ciclos_totales"],
             "delta": kpis_b["ciclos_totales"] - kpis_a["ciclos_totales"]},
        ]),
        "Disponibilidad por equipo": df_disp,
    },
    prefijo="comparativa",
)

pie_pagina()
