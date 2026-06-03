"""Módulo 3 — Rendimiento de STV."""

import streamlit as st
import pandas as pd

from src.data_loader import cargar_tablas, aplicar_filtros_globales
from src.kpis import (
    mttr_por_equipo, mtbf_por_equipo, disponibilidad_por_equipo,
    disponibilidad_mensual, ciclos_por_equipo,
)
from src.charts import (
    barras_ranking_umbrales, evolucion_dos_lineas,
    serie_anual_area, kpi_card_html,
)
from src.theme import (
    aplicar_tema, PRIMARIO, PRIMARIO_CLARO, GRIS_500, GRIS_700,
)
from src.styles import inyectar_css, hero, lectura_ejecutiva
from src.config import UNIDAD_TIEMPO, init_session_state, rango_valido
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina
from src.insights import rendimiento_stv
from src.export import panel_exportacion

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
    titulo="Rendimiento de STV",
    subtitulo=(
        "Análisis segmentado por anillo: <b>20 STV de entrada</b> (cuna simple) "
        "y <b>10 STV de salida</b> (doble cuna)."
    ),
)

# ---------------------------------------------------------------------------
# Carga: ambos anillos
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
unidad_label = "min" if UNIDAD_TIEMPO == "minutos" else "h"

if eventos.empty and misiones.empty:
    st.warning("No hay datos STV para el periodo seleccionado.")
    st.stop()

# ---------------------------------------------------------------------------
# Selector de anillo (sidebar local)
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        f"<h3 style='color:{PRIMARIO};'>Filtros de módulo 3</h3>",
        unsafe_allow_html=True,
    )
    anillo_sel = st.radio(
        "Anillo",
        options=["Ambos", "Entrada (cuna simple)", "Salida (doble cuna)"],
        key="m3_anillo",
    )

zona_map = {
    "Ambos": ["anillo_entrada", "anillo_salida"],
    "Entrada (cuna simple)": ["anillo_entrada"],
    "Salida (doble cuna)": ["anillo_salida"],
}
zonas_activas = zona_map[anillo_sel]

equipos_f = equipos[equipos["zona"].isin(zonas_activas)]
ids_f     = set(equipos_f["id"])
eventos_f = eventos[eventos["id_equipo"].isin(ids_f)]
misiones_f = misiones[misiones["id_equipo"].isin(ids_f)]

# ---------------------------------------------------------------------------
# Helper para construir tabla por anillo
# ---------------------------------------------------------------------------

def _tabla_kpis_stv(ev, mis, eq):
    disp     = disponibilidad_por_equipo(ev, rango_tuple) if not ev.empty else pd.Series(dtype=float)
    mttr     = mttr_por_equipo(ev, UNIDAD_TIEMPO) if not ev.empty else pd.Series(dtype=float)
    mtbf     = mtbf_por_equipo(ev, rango_tuple, UNIDAD_TIEMPO) if not ev.empty else pd.Series(dtype=float)
    ciclos   = ciclos_por_equipo(mis, eq) if not mis.empty else pd.Series(dtype=float)
    n_fallos = (
        ev.groupby("id_equipo").size().rename("n_fallos")
        if not ev.empty else pd.Series(dtype=int)
    )
    return (
        pd.DataFrame({"id_equipo": eq["id"].tolist()})
        .set_index("id_equipo")
        .join(disp.rename("disponibilidad"))
        .join(mttr.rename("mttr"))
        .join(mtbf.rename("mtbf"))
        .join(ciclos.rename("ciclos"))
        .join(n_fallos)
        .join(eq.set_index("id")[["zona"]])
        .fillna({"disponibilidad": 100.0, "n_fallos": 0, "ciclos": 0})
        .sort_index()
        .reset_index()
    )


tabla = _tabla_kpis_stv(eventos_f, misiones_f, equipos_f)

# ---------------------------------------------------------------------------
# Fila 1 — Tarjetas resumen por anillo (cada anillo en una card)
# ---------------------------------------------------------------------------

anillos_presentes = tabla["zona"].dropna().unique().tolist()
zona_labels = {
    "anillo_entrada": ("Anillo entrada", "cuna simple · 20 STV", PRIMARIO),
    "anillo_salida":  ("Anillo salida",  "doble cuna · 10 STV",  PRIMARIO_CLARO),
}

cols_anillo = st.columns(max(len(anillos_presentes), 1))
for col, zona in zip(cols_anillo, sorted(anillos_presentes)):
    sub = tabla[tabla["zona"] == zona]
    label, subtitle, color = zona_labels.get(zona, (zona, "", PRIMARIO))
    disp_med = float(sub["disponibilidad"].mean())
    mttr_med = float(sub["mttr"].dropna().mean()) if sub["mttr"].notna().any() else 0.0
    ciclos_total = int(sub["ciclos"].sum())

    with col:
        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid #E4E7EC;border-radius:12px;
                        padding:16px 20px;box-shadow:0 1px 2px rgba(16,24,40,0.05);
                        border-top:4px solid {color};">
                <div style="display:flex;align-items:baseline;justify-content:space-between;">
                    <div>
                        <div style="color:#101828;font-size:1.05rem;font-weight:700;">{label}</div>
                        <div style="color:{GRIS_500};font-size:0.82rem;">{subtitle}</div>
                    </div>
                    <div style="color:{color};font-size:1.6rem;font-weight:700;">{disp_med:.2f}%</div>
                </div>
                <div style="margin-top:14px;display:flex;gap:20px;">
                    <div>
                        <div style="color:{GRIS_500};font-size:0.7rem;text-transform:uppercase;">MTTR</div>
                        <div style="color:#101828;font-weight:600;font-size:1rem;">
                            {mttr_med:.1f} {unidad_label}
                        </div>
                    </div>
                    <div>
                        <div style="color:{GRIS_500};font-size:0.7rem;text-transform:uppercase;">Ciclos</div>
                        <div style="color:#101828;font-weight:600;font-size:1rem;">{ciclos_total:,}</div>
                    </div>
                    <div>
                        <div style="color:{GRIS_500};font-size:0.7rem;text-transform:uppercase;">Fallos</div>
                        <div style="color:#101828;font-weight:600;font-size:1rem;">{int(sub['n_fallos'].sum()):,}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

lectura_ejecutiva(rendimiento_stv(eventos, misiones, equipos, rango_tuple))

st.divider()

# ---------------------------------------------------------------------------
# Fila 2 — Tabla comparativa intra-anillo
# ---------------------------------------------------------------------------

st.subheader("Tabla comparativa")

tabla_display = tabla.copy()
tabla_display["anillo"] = tabla_display["zona"].map({
    "anillo_entrada": "Entrada", "anillo_salida": "Salida"
})

st.dataframe(
    tabla_display[["id_equipo", "anillo", "disponibilidad", "mttr",
                   "mtbf", "ciclos", "n_fallos"]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "id_equipo":      st.column_config.TextColumn("Equipo"),
        "anillo":         st.column_config.TextColumn("Anillo"),
        "disponibilidad": st.column_config.ProgressColumn(
            "Disponibilidad",
            format="%.2f %%",
            min_value=80.0, max_value=100.0,
        ),
        "mttr": st.column_config.NumberColumn(f"MTTR ({unidad_label})", format="%.1f"),
        "mtbf": st.column_config.NumberColumn(f"MTBF ({unidad_label})", format="%.0f"),
        "ciclos":   st.column_config.NumberColumn("Ciclos", format="%d"),
        "n_fallos": st.column_config.NumberColumn("Fallos", format="%d"),
    },
)

st.divider()

# ---------------------------------------------------------------------------
# Fila 3 — Disponibilidad por STV (rankings dentro de cada anillo)
# ---------------------------------------------------------------------------

st.subheader("Disponibilidad por STV")

tab_ent, tab_sal = st.tabs(["🟦 Anillo entrada", "🟩 Anillo salida"])
for tab, zona in [(tab_ent, "anillo_entrada"), (tab_sal, "anillo_salida")]:
    with tab:
        sub = tabla[tabla["zona"] == zona]
        if sub.empty:
            st.info("Sin datos para este anillo.")
            continue
        media = float(sub["disponibilidad"].mean())
        fig = barras_ranking_umbrales(
            sub.set_index("id_equipo")["disponibilidad"],
            titulo="",
            label_x="Disponibilidad (%)",
            umbral_alto=95.0, umbral_bajo=90.0,
            invertir=False, media=media,
        )
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})

st.divider()

# ---------------------------------------------------------------------------
# Fila 4 — Evolución anual: dos líneas (entrada vs salida)
# ---------------------------------------------------------------------------

st.subheader("Evolución mensual de la disponibilidad")

ids_ent = set(equipos[equipos["zona"] == "anillo_entrada"]["id"])
ids_sal = set(equipos[equipos["zona"] == "anillo_salida"]["id"])
ev_ent = eventos[eventos["id_equipo"].isin(ids_ent)]
ev_sal = eventos[eventos["id_equipo"].isin(ids_sal)]

if not ev_ent.empty and not ev_sal.empty:
    serie_ent = disponibilidad_mensual(ev_ent, rango_tuple)
    serie_sal = disponibilidad_mensual(ev_sal, rango_tuple)
    fig_dos = evolucion_dos_lineas(
        serie_ent, "Entrada", PRIMARIO,
        serie_sal, "Salida", PRIMARIO_CLARO,
        titulo="",
        label_y="Disponibilidad (%)",
    )
    st.plotly_chart(fig_dos, use_container_width=True,
                    config={"displayModeBar": False})
elif not ev_ent.empty:
    st.plotly_chart(
        serie_anual_area(disponibilidad_mensual(ev_ent, rango_tuple),
                         "Entrada", "Disponibilidad (%)"),
        use_container_width=True, config={"displayModeBar": False},
    )

st.divider()

# ---------------------------------------------------------------------------
# Fila 5 — Detalle individual
# ---------------------------------------------------------------------------

with st.expander("🔍 Detalle individual de un STV", expanded=False):
    stv_ids = sorted(tabla["id_equipo"].tolist())
    stv_sel = st.selectbox("Selecciona un STV", options=stv_ids, key="m3_stv_sel")

    ev_stv  = eventos[eventos["id_equipo"] == stv_sel]
    row     = tabla[tabla["id_equipo"] == stv_sel].iloc[0]
    es_salida = row.get("zona") == "anillo_salida"

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(kpi_card_html("Disponibilidad", f"{row['disponibilidad']:.2f} %"),
                    unsafe_allow_html=True)
    with c2:
        mttr_str = f"{row['mttr']:.1f}" if pd.notna(row['mttr']) else "—"
        st.markdown(kpi_card_html(f"MTTR ({unidad_label})", mttr_str),
                    unsafe_allow_html=True)
    with c3:
        mtbf_str = f"{row['mtbf']:,.0f}" if pd.notna(row['mtbf']) else "—"
        st.markdown(kpi_card_html(f"MTBF ({unidad_label})", mtbf_str),
                    unsafe_allow_html=True)
    with c4:
        ciclos_label = "Ciclos (×2)" if es_salida else "Ciclos"
        st.markdown(kpi_card_html(ciclos_label,
                                  f"{int(row['ciclos']) if pd.notna(row['ciclos']) else 0:,}"),
                    unsafe_allow_html=True)
    with c5:
        st.markdown(kpi_card_html("Fallos", f"{int(row['n_fallos']):,}"),
                    unsafe_allow_html=True)

    if es_salida:
        st.caption("Doble cuna: cada misión transporta 2 pallets. El conteo ya incluye ese factor.")

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
        "KPIs por STV": tabla_display[[
            "id_equipo", "anillo", "disponibilidad", "mttr",
            "mtbf", "ciclos", "n_fallos",
        ]],
    },
    prefijo="stv",
)

pie_pagina()
