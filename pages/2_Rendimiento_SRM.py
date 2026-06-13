"""Módulo 2 — Rendimiento de transelevadores SRM."""

import streamlit as st
import pandas as pd

from src.data_loader import aplicar_filtros_globales
from src.data_ui import cargar_tablas_con_feedback
from src.kpis import (
    mttr_por_equipo, mtbf_por_equipo, disponibilidad_por_equipo,
    disponibilidad_mensual, ciclos_por_equipo, posicion_en_fallo,
)
from src.charts import (
    barras_horizontales, serie_anual_area,
    kpi_card_html, evolucion_multilinea_con_media, heatmap_alzado_pasillo,
    gauge_disponibilidad,
)
from src.theme import aplicar_tema, PRIMARIO, GRIS_700
from src.styles import inyectar_css, hero, lectura_ejecutiva
from src.config import (
    UNIDAD_TIEMPO, init_session_state, rango_valido, rango_calendario,
    RANGO_ANUAL,
)
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina
from src.insights import rendimiento_srm
from src.export import panel_exportacion
from src.format import fmt_es
from src.estilos_tabla import estilo_disponibilidad, color_por_umbral

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
        "Análisis individual de los 8 SRM bimástiles que sirven los pasillos. "
        "MTTR, MTBF, disponibilidad y ciclos por equipo."
    ),
)
st.caption(
    "Ámbito fijo del módulo: **SRM · pasillo**. Los filtros de tipo y zona "
    "del sidebar no aplican aquí; el rango de fechas sí."
)

# ---------------------------------------------------------------------------
# Carga: forzar SRM / pasillo (no depende del filtro global de zona)
# ---------------------------------------------------------------------------

_cargar = st.cache_data(cargar_tablas_con_feedback)
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

# Calendario de los KPIs: [inicio, fin + 1 día), coherente con el filtro de
# fechas (que incluye el día final completo).
rango_tuple = rango_calendario(rango)
unidad_label = "min" if UNIDAD_TIEMPO == "minutos" else "h"

if eventos.empty and misiones.empty:
    st.warning("No hay datos SRM para el periodo seleccionado.")
    st.stop()

# Eventos de año completo (sin recorte de fechas) para las evoluciones mensuales.
eventos_anual = aplicar_filtros_globales(
    tablas, tipos_equipo=["SRM"], zonas=["pasillo"],
)["eventos"]

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
# Fila 1 — Disponibilidad de la flota (gauge) + KPI globales
# ---------------------------------------------------------------------------

st.subheader("Disponibilidad media de la flota vs. objetivo")

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
        titulo="8 SRM · pasillo",
    )
    st.plotly_chart(fig_gauge, use_container_width=True,
                    config={"displayModeBar": False})
with c1:
    st.markdown(kpi_card_html(f"MTTR medio ({unidad_label})",
                              fmt_es(mttr_medio, 1), icono="🛠️"),
                unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card_html("Ciclos totales",
                              fmt_es(ciclos_total, 0), icono="🔄"),
                unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card_html("Fallos en el periodo",
                              fmt_es(n_fallos_total, 0), icono="⚠️"),
                unsafe_allow_html=True)

st.caption(
    "**Lectura:** disponibilidad media de los 8 transelevadores frente al "
    "objetivo del **95%** (línea negra del medidor). El detalle equipo a equipo "
    "está en la tabla comparativa inferior."
)

lectura_ejecutiva(rendimiento_srm(eventos, misiones, equipos, rango_tuple))

st.divider()

# ---------------------------------------------------------------------------
# Fila 2 — Tabla comparativa con semáforo de disponibilidad
# ---------------------------------------------------------------------------

st.subheader("Tabla comparativa · 8 SRM")

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

# Eventos SRM con su duración y descripción de error, base para ambas gráficas.
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

_opciones_srm = ["Todos"] + sorted(tabla["id_equipo"].tolist())

# Selector único que controla ambas gráficas.
srm_sel = st.selectbox(
    "Transelevador", options=_opciones_srm, key="m2_fallos_srm",
)

# Umbrales semáforo escalados por periodo y nº de equipos: los cortes se fijan
# por SRM y por semana, y se multiplican por (días del rango / 7) y por el nº de
# SRM mostrados. Así el color es justo tanto si miras 1 equipo o los 8, como si
# el rango es una semana o el año entero.
_n_srm_sel = 1 if srm_sel != "Todos" else len(tabla)
_dias_rango = (pd.Timestamp(rango[1]) - pd.Timestamp(rango[0])).days + 1
_escala = max(_dias_rango / 7.0, 1e-9) * _n_srm_sel

# Base por SRM y por semana (validada contra los datos): frecuencia y horas.
_FREC_ROJO, _FREC_AMBAR = 0.30 * _escala, 0.18 * _escala
_HORA_ROJO, _HORA_AMBAR = 0.55 * _escala, 0.30 * _escala


def _color_frecuencia(v: float) -> str:
    return color_por_umbral(v, _FREC_ROJO, _FREC_AMBAR)


def _color_horas(v: float) -> str:
    return color_por_umbral(v, _HORA_ROJO, _HORA_AMBAR)


base = _ev_fallos if srm_sel == "Todos" else _ev_fallos[_ev_fallos["id_equipo"] == srm_sel]
g = (
    base.groupby("descripcion")
    .agg(n_fallos=("id_evento", "size"), horas_parada=("_dur_h", "sum"))
    .reset_index()
)

col_frec, col_tiempo = st.columns(2)

with col_frec:
    if g.empty:
        st.info("Sin fallos en el periodo para la selección.")
    else:
        fig_frec = barras_horizontales(
            g.set_index("descripcion")["n_fallos"],
            titulo="Nº de fallos por tipo",
            label_x="Nº de fallos",
            color_fn=_color_frecuencia,
            formato_valor="{:,.0f}",
        )
        st.plotly_chart(fig_frec, use_container_width=True,
                        config={"displayModeBar": False})

with col_tiempo:
    if g.empty:
        st.info("Sin fallos en el periodo para la selección.")
    else:
        fig_tiempo = barras_horizontales(
            g.set_index("descripcion")["horas_parada"],
            titulo="Tiempo de parada por tipo",
            label_x="Horas de parada",
            color_fn=_color_horas,
            formato_valor="{:,.1f} h",
        )
        st.plotly_chart(fig_tiempo, use_container_width=True,
                        config={"displayModeBar": False})

st.caption(
    "Ambas gráficas muestran los modos de fallo de los SRM: la izquierda por "
    "**frecuencia** (cuántas veces ocurre cada avería) y la derecha por **tiempo "
    "de parada acumulado** (su impacto en horas). El selector superior controla "
    "las dos a la vez (un transelevador o toda la flota). El color marca la "
    "gravedad — 🟢 normal · 🟠 elevado · 🔴 foco crítico — con umbrales que se "
    "ajustan al periodo y al nº de equipos mostrados."
)

st.divider()

# ---------------------------------------------------------------------------
# Fila 4 — Evolución mensual de la disponibilidad (una línea por SRM + media)
# ---------------------------------------------------------------------------

st.subheader("Evolución mensual de la disponibilidad")

# Año completo: el rango de fechas del sidebar no aplica a esta gráfica.
# Una serie mensual por cada SRM (disponibilidad_mensual con los eventos de ese
# equipo da su propia serie; un SRM sin fallos queda al 100% todos los meses).
_series_srm = {}
for _srm in sorted(equipos["id"].tolist()):
    _ev = eventos_anual[eventos_anual["id_equipo"] == _srm]
    if _ev.empty:
        _series_srm[_srm] = pd.Series(100.0, index=range(1, 13))
    else:
        _series_srm[_srm] = disponibilidad_mensual(_ev, RANGO_ANUAL)

_destacar = st.selectbox(
    "Destacar transelevador",
    options=["Ninguno"] + sorted(equipos["id"].tolist()),
    key="m2_evol_destacar",
)

fig_evol_flota = evolucion_multilinea_con_media(
    _series_srm,
    titulo="",
    label_y="Disponibilidad (%)",
    color_media=PRIMARIO,
    destacar=None if _destacar == "Ninguno" else _destacar,
)
st.plotly_chart(fig_evol_flota, use_container_width=True,
                config={"displayModeBar": False})
st.caption(
    "**Lectura:** cada línea gris es un transelevador; la línea azul es la "
    "**media de la flota**. Usa el selector para resaltar un SRM en color, o "
    "pasa el ratón sobre una línea para identificarla. Muestra siempre el año "
    "completo para conservar la tendencia mensual; el rango de fechas del "
    "sidebar no la recorta."
)

st.divider()

# ---------------------------------------------------------------------------
# Fila 5 — Mapa de calor del alzado de un pasillo (celda exacta Pxx-Ayy-Czz)
# ---------------------------------------------------------------------------

st.subheader("Mapa de calor · alzado del pasillo")

# Cruce de cada fallo con la misión activa para situar la celda física (P-A-C).
ev_pos = posicion_en_fallo(eventos, misiones)
ev_pos_validos = ev_pos.dropna(subset=["posicion_inicial"])
srm_pos = ev_pos_validos[
    ev_pos_validos["posicion_inicial"].str.startswith("P", na=False)
].copy()

if srm_pos.empty:
    st.info("Sin fallos SRM con posición identificada en el periodo.")
else:
    srm_pos["pasillo"] = (srm_pos["posicion_inicial"]
                          .str.extract(r"P(\d+)")[0]
                          .astype(str).str.zfill(2).apply(lambda x: f"P{x}"))
    srm_pos["altura"]  = (srm_pos["posicion_inicial"]
                          .str.extract(r"A(\d+)")[0]
                          .astype(str).str.zfill(2).apply(lambda x: f"A{x}"))
    srm_pos["columna"] = (srm_pos["posicion_inicial"]
                          .str.extract(r"C(\d+)")[0]
                          .astype(str).str.zfill(2).apply(lambda x: f"C{x}"))

    # Pasillo más conflictivo por defecto.
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
            key="m2_pasillo_alzado_sel",
        )
    with c_info:
        n_pasillo = int(fallos_por_pasillo.get(pasillo_sel, 0))
        st.markdown(
            f"<div style='padding-top:1.8rem;color:{GRIS_700};font-size:0.92rem;'>"
            f"Vista de alzado (columna × altura). Cada celda es una ubicación "
            f"física exacta. Pasillo seleccionado: <b>{pasillo_sel}</b> · "
            f"<b>{fmt_es(n_pasillo, 0)}</b> fallos en el periodo."
            f"</div>",
            unsafe_allow_html=True,
        )

    fig_alzado = heatmap_alzado_pasillo(srm_pos, pasillo=pasillo_sel)
    st.plotly_chart(fig_alzado, use_container_width=True,
                    config={"displayModeBar": False})

    # Top celdas de toda la instalación (los 8 pasillos)
    top_celdas = (
        srm_pos.groupby("posicion_inicial").size()
               .rename("n_fallos")
               .sort_values(ascending=False)
               .head(10)
               .reset_index()
               .rename(columns={"posicion_inicial": "Celda"})
    )
    ct, cv = st.columns([2, 3])
    with ct:
        st.markdown("**Top 10 celdas · todos los pasillos**")
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
        f"{fmt_es(len(ev_pos_validos), 0)} de {fmt_es(len(ev_pos), 0)} fallos con "
        f"misión activa identificada "
        f"({fmt_es(100 * len(ev_pos_validos) / max(len(ev_pos), 1), 0)}%)."
    )

st.divider()

# ---------------------------------------------------------------------------
# Fila 6 — Detalle individual
# ---------------------------------------------------------------------------

with st.expander("🔍 Detalle individual de un SRM", expanded=False):
    srm_ids = sorted(tabla["id_equipo"].tolist())
    srm_det = st.selectbox("Selecciona un SRM", options=srm_ids, key="m2_srm_sel")

    ev_srm  = eventos[eventos["id_equipo"] == srm_det]
    row = tabla[tabla["id_equipo"] == srm_det].iloc[0]

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
    else:
        st.info(f"{srm_det} no registra fallos en el periodo seleccionado.")

    # Evolución mensual a año completo (el rango de fechas no la recorta)
    ev_srm_anual = eventos_anual[eventos_anual["id_equipo"] == srm_det]
    if not ev_srm_anual.empty:
        serie_disp_srm = disponibilidad_mensual(ev_srm_anual, RANGO_ANUAL)
        # Eje Y ajustado a los datos (1 pp de margen, acotado a [0, 100]) para
        # que las variaciones mensuales se aprecien en lugar de quedar aplastadas.
        _vals_srm = serie_disp_srm.dropna()
        _rango_y_srm = (
            (max(0.0, float(_vals_srm.min()) - 1.0),
             min(100.0, float(_vals_srm.max()) + 1.0))
            if not _vals_srm.empty else None
        )
        fig_evol = serie_anual_area(
            serie_disp_srm,
            titulo=f"Disponibilidad mensual · {srm_det}",
            label_y="Disponibilidad (%)",
            referencia=float(
                disponibilidad_por_equipo(ev_srm_anual, RANGO_ANUAL).mean()
            ),
            rango_y=_rango_y_srm,
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

_datasets_srm = {
    "KPIs por SRM": tabla,
}
if not srm_pos.empty:
    _datasets_srm["Fallos SRM por celda"] = (
        srm_pos.groupby("posicion_inicial").size()
               .rename("n_fallos").reset_index()
               .rename(columns={"posicion_inicial": "celda"})
    )

panel_exportacion(_datasets_srm, prefijo="srm")

pie_pagina()
