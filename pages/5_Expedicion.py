"""Módulo 5 — Expedición y rendimiento del anillo."""

import streamlit as st
import pandas as pd

from src.data_loader import aplicar_filtros_globales
from src.data_ui import cargar_tablas_con_feedback
from src.kpis import tiempo_ciclo
from src.charts import histograma_distribucion, kpi_card_html, kpi_grid, gauge_objetivo, GAUGE_ALTURA
from src.theme import aplicar_tema, PRIMARIO, PRIMARIO_CLARO, EXITO, ADVERTENCIA, CRITICO, ACENTO
from src.format import fmt_es
from src.styles import inyectar_css, hero, lectura_ejecutiva
from src.icons import chip
from src.config import init_session_state, rango_valido
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina
from src.insights import expedicion
from src.export import panel_exportacion
from src.intervalos import union_solape_segundos

st.set_page_config(
    page_title="Expedición / anillo",
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
    titulo="Expedición y rendimiento del anillo",
    subtitulo=(
        "Tiempo de completado de cada <b>pedido</b> en el transporte de "
        "salida. Cada pedido es un <b>trailer completo: 28 pallets</b> "
        "(28 misiones de cuna simple) que los <b>15 STV</b> del anillo "
        "llevan hasta los muelles de expedición."
    ),
)
st.caption(
    "Ámbito fijo del módulo: **STV · anillo único**. Los filtros de tipo y zona "
    "del sidebar no aplican aquí; el rango de fechas sí."
)

# ---------------------------------------------------------------------------
# Carga: solo STV del anillo
# ---------------------------------------------------------------------------

_cargar = st.cache_data(cargar_tablas_con_feedback)
tablas = _cargar()

f = aplicar_filtros_globales(
    tablas,
    rango_fechas=(str(rango[0]), str(rango[1])),
    tipos_equipo=["STV"], zonas=["anillo"],
)
misiones = f["misiones"]
equipos  = f["equipos"]

# Eventos del recorrido completo (SRM de origen + STV del anillo) acotados al
# rango, para el diagnóstico de retrasos por parada. Se toman sin filtrar por
# zona porque el filtro global del anillo excluiría las averías de SRM.
_eventos_diag = aplicar_filtros_globales(
    tablas, rango_fechas=(str(rango[0]), str(rango[1])),
)["eventos"]
_equipos_todos = tablas["equipos"]

if misiones.empty:
    st.warning("No hay datos del anillo para el periodo seleccionado.")
    st.stop()

completadas = misiones[misiones["estado"] == "completada"].copy()
if completadas.empty:
    st.warning("No hay misiones completadas en el periodo seleccionado.")
    st.stop()

tc_s = tiempo_ciclo(completadas, unidad="segundos")

ts_ini_global = pd.Timestamp(str(rango[0]))
ts_fin_global = pd.Timestamp(str(rango[1])) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
horas_periodo = (ts_fin_global - ts_ini_global).total_seconds() / 3600.0
n_misiones_comp = len(completadas)
# Cuna simple: un pallet por misión completada.
pallets_totales = n_misiones_comp
throughput_global = pallets_totales / horas_periodo if horas_periodo > 0 else 0.0

# ---------------------------------------------------------------------------
# Diagnóstico: minutos de parada (SRM origen / anillo STV) por pedido y pallet
# ---------------------------------------------------------------------------

def _minutos_union(intervalos, p_ini, p_fin) -> float:
    """Minutos de parada dentro de [p_ini, p_fin] como unión de intervalos
    (paradas simultáneas no cuentan dos veces)."""
    return union_solape_segundos(intervalos, p_ini, p_fin) / 60.0


def construir_diagnostico_pedidos(con_pedido, pedidos, eventos, equipos_todos, franja_fn):
    """
    Devuelve un DataFrame por pallet con la causa de retraso de su pedido:
    minutos de parada del SRM de origen y del anillo solapados con la ventana
    de carga, y el retraso total (unión de ambas familias de paradas).
    """
    ids_anillo = set(equipos_todos.loc[equipos_todos["zona"] == "anillo", "id"])

    ev = eventos[eventos["ts_recuperacion"].notna()].copy()
    ev_stv = ev[ev["id_equipo"].isin(ids_anillo)]
    iv_stv = sorted(zip(ev_stv["ts_inicio_fallo"], ev_stv["ts_recuperacion"]))

    ev_srm = ev[ev["id_equipo"].astype(str).str.startswith("SRM-")].copy()
    ev_srm["pasillo"] = "P" + ev_srm["id_equipo"].str.extract(r"SRM-(\d+)")[0]
    iv_srm = {
        pas: sorted(zip(g["ts_inicio_fallo"], g["ts_recuperacion"]))
        for pas, g in ev_srm.groupby("pasillo")
    }

    pasillos_ped = con_pedido.groupby("id_pedido")["origen_pasillo"].agg(set)

    filas = []
    for pid, prow in pedidos.iterrows():
        p_ini, p_fin = prow["ts_ini"], prow["ts_fin"]
        min_anillo = _minutos_union(
            [iv for iv in iv_stv if iv[0] < p_fin and iv[1] > p_ini], p_ini, p_fin
        )
        pasillos = {p for p in pasillos_ped.get(pid, set()) if isinstance(p, str) and p.startswith("P")}
        iv_srm_ped = []
        for pas in pasillos:
            iv_srm_ped += [iv for iv in iv_srm.get(pas, ()) if iv[0] < p_fin and iv[1] > p_ini]
        min_srm = _minutos_union(iv_srm_ped, p_ini, p_fin)
        # Retraso total del pedido = unión de TODAS las paradas (SRM origen + anillo).
        retraso = _minutos_union(
            [iv for iv in iv_stv if iv[0] < p_fin and iv[1] > p_ini] + iv_srm_ped,
            p_ini, p_fin,
        )
        filas.append({
            "id_pedido": pid,
            "muelle": prow.get("muelle", ""),
            "franja": franja_fn(p_ini.hour),
            "t_min": prow["t_min"],
            "origen_srm": ", ".join(sorted("SRM-" + p[1:] for p in pasillos)) or "—",
            "min_srm": min_srm,
            "min_anillo": min_anillo,
            "retraso_min": retraso,
        })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Pedidos de expedición: agrupación de misiones por id_pedido
# ---------------------------------------------------------------------------

tiene_pedidos = (
    "id_pedido" in completadas.columns
    and completadas["id_pedido"].astype(str).str.startswith("PED-").any()
)

tiene_muelle = (
    "muelle" in completadas.columns
    and completadas["muelle"].astype(str).str.startswith("M-").any()
)

tiene_origen = (
    "origen_pasillo" in completadas.columns
    and completadas["origen_pasillo"].astype(str).str.startswith("P").any()
)

if tiene_pedidos:
    con_pedido = completadas[completadas["id_pedido"].astype(str).str.startswith("PED-")]
    _agg = dict(
        ts_ini=("ts_inicio", "min"),
        ts_fin=("ts_fin", "max"),
        n_misiones=("id_mision", "count"),
    )
    if tiene_muelle:
        _agg["muelle"] = ("muelle", "first")
    pedidos = con_pedido.groupby("id_pedido").agg(**_agg)
    pedidos["pallets"] = pedidos["n_misiones"]   # cuna simple: 1 pallet/misión
    pedidos["t_min"] = (
        (pedidos["ts_fin"] - pedidos["ts_ini"]).dt.total_seconds() / 60
    )

# ---------------------------------------------------------------------------
# Fila 1 — Gauge de tiempo de completado + tarjetas KPI (centradas en el pedido)
# ---------------------------------------------------------------------------

if tiene_pedidos:
    st.subheader("Tiempo de completado de pedidos vs. objetivo")

    completado_medio = float(pedidos["t_min"].mean())

    # Gauge a la izquierda (más ancho) y las 4 tarjetas KPI en rejilla 2×2 a la
    # derecha (mismo patrón que el módulo 0).
    c_gauge, c_kpis = st.columns([2, 3])
    with c_gauge:
        fig_gauge = gauge_objetivo(
            completado_medio,
            rango=(0.0, 360.0),
            umbral_verde=210.0,
            umbral_ambar=300.0,
            objetivo=210.0,
            titulo="Trailer · 28 pallets",
            sufijo=" min",
            menor_es_mejor=True,
            decimales=1,
        )
        st.plotly_chart(fig_gauge, use_container_width=True,
                        config={"displayModeBar": False})
    with c_kpis:
        st.markdown(kpi_grid([
            kpi_card_html("Pedidos (trailers)", fmt_es(len(pedidos), 0),
                          icono=chip("truck", PRIMARIO), acento=PRIMARIO),
            kpi_card_html("Completado P95 (min)", fmt_es(pedidos['t_min'].quantile(0.95), 0),
                          icono=chip("bar-chart", ADVERTENCIA), acento=ADVERTENCIA),
            kpi_card_html("Pallets expedidos", fmt_es(pallets_totales, 0),
                          icono=chip("package", PRIMARIO_CLARO), acento=PRIMARIO_CLARO),
            kpi_card_html("Throughput (pallets/h)", fmt_es(throughput_global, 1),
                          icono=chip("gauge", ACENTO), acento=ACENTO),
        ], altura=GAUGE_ALTURA), unsafe_allow_html=True)

    st.caption(
        "**Lectura:** tiempo medio de completado de un pedido (trailer de 28 "
        "pallets) frente al objetivo de **210 min** (línea negra del medidor). "
        "por debajo del objetivo · hasta 300 min · por encima."
    )
else:
    st.markdown(kpi_grid([
        kpi_card_html("Misiones completadas", fmt_es(n_misiones_comp, 0),
                      icono=chip("check-circle", EXITO), acento=EXITO),
        kpi_card_html("Pallets expedidos", fmt_es(pallets_totales, 0),
                      icono=chip("package", PRIMARIO_CLARO), acento=PRIMARIO_CLARO),
        kpi_card_html("Throughput (pallets/h)", fmt_es(throughput_global, 1),
                      icono=chip("gauge", ACENTO), acento=ACENTO),
        kpi_card_html("TC medio (s)", fmt_es(tc_s.mean(), 1),
                      icono=chip("clock", ADVERTENCIA), acento=ADVERTENCIA),
        kpi_card_html("TC mediana (s)", fmt_es(tc_s.median(), 1),
                      icono=chip("bar-chart", PRIMARIO), acento=PRIMARIO),
    ], columnas=5), unsafe_allow_html=True)
    st.info(
        "El dataset no incluye pedidos de expedición (columna `id_pedido`) — "
        "regenera los datos con scripts/generar_datos.py para ver el análisis "
        "por pedido."
    )

lectura_ejecutiva(expedicion(misiones, equipos, (str(rango[0]), str(rango[1]))))

st.divider()

# ---------------------------------------------------------------------------
# Fila 2 — Tiempo de carga por muelle y franja + diagnóstico de retrasos
# ---------------------------------------------------------------------------

if tiene_pedidos and tiene_muelle:
    st.subheader("Tiempo medio de carga por muelle y franja horaria")

    # Franja horaria según la hora de inicio de carga del pedido.
    _FRANJAS = ["Mañana (06–14)", "Tarde (14–22)", "Noche (22–06)"]

    def _franja(h: int) -> str:
        if 6 <= h < 14:
            return _FRANJAS[0]
        if 14 <= h < 22:
            return _FRANJAS[1]
        return _FRANJAS[2]

    ped_m = pedidos.copy()
    ped_m["franja"] = ped_m["ts_ini"].dt.hour.apply(_franja)

    # Tabla cruzada: filas = muelle, columnas = franja, valor = tiempo medio (min).
    tabla_mf = ped_m.pivot_table(
        index="muelle", columns="franja", values="t_min", aggfunc="mean",
    ).reindex(columns=_FRANJAS)
    tabla_mf["Todas"] = ped_m.groupby("muelle")["t_min"].mean()
    fila_total = ped_m.groupby("franja")["t_min"].mean().reindex(_FRANJAS)
    fila_total["Todas"] = ped_m["t_min"].mean()
    tabla_mf.loc["Todos"] = fila_total
    tabla_mf = tabla_mf.rename_axis("Muelle").reset_index()

    # Semáforo relativo a la media global: rojo = más lento (peor) que la media.
    media_global = float(ped_m["t_min"].mean())

    def _color_tiempo(v: float) -> str:
        if pd.isna(v):
            return ""
        if v <= media_global * 0.98:
            fondo, texto = "#E6F4EA", EXITO          # claramente más rápido
        elif v <= media_global * 1.02:
            fondo, texto = "#FDF1E1", ADVERTENCIA     # en torno a la media
        else:
            fondo, texto = "#FBE7E2", CRITICO         # más lento que la media
        return f"background-color: {fondo}; color: {texto}; font-weight: 600;"

    _cols_valor = _FRANJAS + ["Todas"]
    _styler = (
        tabla_mf.style
        .map(_color_tiempo, subset=_cols_valor)
        .format({c: (lambda v: f"{fmt_es(v, 1)} min") for c in _cols_valor}, na_rep="—")
    )
    st.dataframe(_styler, use_container_width=True, hide_index=True)

    st.caption(
        f"**Lectura:** cada celda es el tiempo medio de carga (min) de los pedidos "
        f"de ese muelle en esa franja horaria. Cada pedido es un trailer completo "
        f"de 28 pallets. El color compara con la media global ({fmt_es(media_global, 1)} "
        f"min): más rápido · en la media · más lento. La fila/columna "
        f"**Todas/Todos** son los promedios marginales."
    )

    st.divider()

    # -----------------------------------------------------------------------
    # Diagnóstico de retrasos por pedido/pallet (origen SRM + anillo STV)
    # -----------------------------------------------------------------------

    st.subheader("Diagnóstico de retrasos · origen y anillo")

    diag = construir_diagnostico_pedidos(
        con_pedido, pedidos, _eventos_diag, _equipos_todos, _franja,
    )

    cdg1, cdg2 = st.columns(2)
    with cdg1:
        muelle_sel = st.selectbox(
            "Muelle", options=["Todos"] + sorted(diag["muelle"].dropna().unique().tolist()),
            key="m5_diag_muelle",
        )
    with cdg2:
        franja_sel = st.selectbox(
            "Franja horaria", options=["Todas"] + _FRANJAS, key="m5_diag_franja",
        )

    sel = diag.copy()
    if muelle_sel != "Todos":
        sel = sel[sel["muelle"] == muelle_sel]
    if franja_sel != "Todas":
        sel = sel[sel["franja"] == franja_sel]

    # Texto diagnóstico de la selección.
    if sel.empty:
        st.info("Sin pedidos para esa combinación de muelle y franja.")
    else:
        n_ped = sel["id_pedido"].nunique()
        t_medio_sel = sel.groupby("id_pedido")["t_min"].first().mean()
        retr_medio = sel.groupby("id_pedido")["retraso_min"].first().mean()
        ped_stv = sel[sel["min_anillo"] > 0]["id_pedido"].nunique()
        ped_srm = sel[sel["min_srm"] > 0]["id_pedido"].nunique()
        min_stv = sel.groupby("id_pedido")["min_anillo"].first().sum()
        min_srm = sel.groupby("id_pedido")["min_srm"].first().sum()

        donde = []
        if muelle_sel != "Todos":
            donde.append(f"muelle **{muelle_sel}**")
        if franja_sel != "Todas":
            donde.append(f"franja **{franja_sel}**")
        ctx = (" en " + " · ".join(donde)) if donde else " (toda la expedición)"

        if retr_medio < 0.5:
            veredicto = "**Sin retrasos relevantes**"
        elif retr_medio < 5:
            veredicto = "**Retraso moderado**"
        else:
            veredicto = "**Retraso significativo**"

        st.markdown(
            f"{veredicto}{ctx}: **{fmt_es(n_ped, 0)}** pedidos, tiempo medio de carga "
            f"**{fmt_es(t_medio_sel, 1)} min** (retraso medio sobre la base: "
            f"**+{fmt_es(retr_medio, 1)} min**).\n\n"
            f"- **Anillo (STV):** {fmt_es(ped_stv, 0)} pedidos afectados por paradas "
            f"del circuito · {fmt_es(min_stv, 0)} min de parada acumulada.\n"
            f"- **Traslos de origen (SRM):** {fmt_es(ped_srm, 0)} pedidos afectados por paradas "
            f"del SRM que extraía sus pallets · {fmt_es(min_srm, 0)} min acumulados."
        )

    # Tabla por pallet de la selección.
    st.markdown("**Detalle por pallet**")

    def _color_retraso(v: float) -> str:
        if pd.isna(v) or v <= 0.1:
            return ""
        if v < 5:
            return f"background-color: #FDF1E1; color: {ADVERTENCIA}; font-weight: 600;"
        return f"background-color: #FBE7E2; color: {CRITICO}; font-weight: 600;"

    cols_show = ["id_pedido", "muelle", "franja", "origen_srm",
                 "min_srm", "min_anillo", "retraso_min"]
    _sty = (
        sel.sort_values("retraso_min", ascending=False)[cols_show]
        .head(300)
        .style
        .map(_color_retraso, subset=["retraso_min"])
        .format({"min_srm": lambda v: f"{fmt_es(v, 0)} min",
                 "min_anillo": lambda v: f"{fmt_es(v, 0)} min",
                 "retraso_min": lambda v: f"{fmt_es(v, 1)} min"}, na_rep="—")
    )
    st.dataframe(
        _sty, use_container_width=True, hide_index=True,
        column_config={
            "id_pedido":  st.column_config.TextColumn("Pedido"),
            "muelle":     st.column_config.TextColumn("Muelle"),
            "franja":     st.column_config.TextColumn("Franja"),
            "origen_srm": st.column_config.TextColumn("Origen (SRM)"),
            "min_srm":    st.column_config.TextColumn("Parada SRM"),
            "min_anillo": st.column_config.TextColumn("Parada anillo"),
            "retraso_min": st.column_config.TextColumn("Retraso total"),
        },
    )
    st.caption(
        "Cada fila es un pedido: su muelle, franja y los **SRM de origen** de los "
        "que se extrajeron sus pallets. **Parada SRM** = minutos que esos SRM "
        "estuvieron averiados durante la carga del pedido; **Parada anillo** = "
        "minutos de parada del anillo (afecta a todos los pedidos en carga). El "
        "**retraso total** del pedido es la unión de ambas (paradas simultáneas no "
        "se suman dos veces). Máx. 300 filas, ordenadas por retraso."
    )

    st.divider()

elif tiene_pedidos:
    # Dataset con pedidos pero sin muelle (versión antigua de los datos).
    st.subheader("Distribución del tiempo de completado por pedido")

    fig_hist = histograma_distribucion(
        pedidos["t_min"],
        titulo="",
        label_x="Tiempo de completado (minutos)",
        nbins=50,
    )
    st.plotly_chart(fig_hist, use_container_width=True,
                    config={"displayModeBar": False})

    pp25, pp50, pp75, pp95 = pedidos["t_min"].quantile([0.25, 0.50, 0.75, 0.95])
    st.caption(
        f"P25: {fmt_es(pp25, 1)} min · P50: {fmt_es(pp50, 1)} min · P75: {fmt_es(pp75, 1)} min · "
        f"P95: {fmt_es(pp95, 1)} min. El desglose por muelle requiere regenerar los "
        f"datos con scripts/generar_datos.py."
    )

    st.divider()

# ---------------------------------------------------------------------------
# Exportación de datos
# ---------------------------------------------------------------------------

_resumen = {
    "n_misiones_completadas": n_misiones_comp,
    "pallets_totales": pallets_totales,
    "throughput_ph_global": round(throughput_global, 2),
    "tc_medio_s": round(float(tc_s.mean()), 2),
    "tc_mediana_s": round(float(tc_s.median()), 2),
}
if tiene_pedidos:
    _resumen.update({
        "n_pedidos": len(pedidos),
        "t_completado_medio_min": round(float(pedidos["t_min"].mean()), 2),
        "t_completado_p95_min": round(float(pedidos["t_min"].quantile(0.95)), 2),
    })

_datasets_export = {
    "Resumen del periodo": pd.DataFrame([_resumen]),
}
if tiene_pedidos:
    _cols_ped = ["id_pedido", "pallets", "n_misiones", "t_min", "ts_ini", "ts_fin"]
    if tiene_muelle:
        _cols_ped.insert(1, "muelle")
    _datasets_export["Pedidos de expedición"] = pedidos.reset_index()[_cols_ped]
    if tiene_muelle:
        _datasets_export["Tiempo carga por muelle y franja"] = tabla_mf
        _datasets_export["Diagnóstico de retrasos por pedido"] = diag

panel_exportacion(_datasets_export, prefijo="expedicion")

pie_pagina()
