"""
Capa de cálculo de KPIs — funciones puras de pandas.

No importa streamlit. Reciben DataFrames, devuelven Series/DataFrames/escalares.
Las fórmulas corresponden a la sección 3 de Documentacionfuncional.md.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd


# ---------------------------------------------------------------------------
# MTTR  (sección 3.1)
# ---------------------------------------------------------------------------

def mttr_por_equipo(
    eventos: pd.DataFrame,
    unidad: str = "minutos",
) -> pd.Series:
    """
    MTTR(equipo) = Σ duracion_fallo_i / nº fallos resueltos

    Solo sobre eventos con estado='resuelto'.
    unidad: 'minutos' | 'horas'
    Devuelve Series indexada por id_equipo.
    """
    resueltos = eventos[eventos["estado"] == "resuelto"].copy()
    resueltos["duracion"] = (
        pd.to_datetime(resueltos["ts_recuperacion"])
        - pd.to_datetime(resueltos["ts_inicio_fallo"])
    ).dt.total_seconds() / 60.0

    if unidad == "horas":
        resueltos["duracion"] /= 60.0

    return resueltos.groupby("id_equipo")["duracion"].mean().rename("mttr")


# ---------------------------------------------------------------------------
# MTBF  (sección 3.2)
# ---------------------------------------------------------------------------

def mtbf_por_equipo(
    eventos: pd.DataFrame,
    rango: tuple[datetime, datetime],
    unidad: str = "horas",
) -> pd.Series:
    """
    tiempo_operativo = tiempo_calendario - Σ duracion_fallo_i
    MTBF(equipo) = tiempo_operativo / nº fallos

    rango: (ts_inicio, ts_fin) del periodo analizado.
    unidad: 'minutos' | 'horas'
    Devuelve Series indexada por id_equipo.
    """
    ts_ini, ts_fin = pd.Timestamp(rango[0]), pd.Timestamp(rango[1])
    t_cal_h = (ts_fin - ts_ini).total_seconds() / 3600.0

    ev = eventos.copy()
    ev["ts_inicio_fallo"]  = pd.to_datetime(ev["ts_inicio_fallo"])
    ev["ts_recuperacion"]  = pd.to_datetime(ev["ts_recuperacion"])

    # Solo resueltos contribuyen al tiempo caído
    resueltos = ev[ev["estado"] == "resuelto"].copy()
    resueltos["dur_h"] = (
        resueltos["ts_recuperacion"] - resueltos["ts_inicio_fallo"]
    ).dt.total_seconds() / 3600.0

    tiempo_caido = resueltos.groupby("id_equipo")["dur_h"].sum()
    n_fallos     = ev.groupby("id_equipo")["id_evento"].count()

    tiempo_operativo_h = t_cal_h - tiempo_caido.reindex(n_fallos.index, fill_value=0)
    mtbf_h = tiempo_operativo_h / n_fallos

    if unidad == "minutos":
        mtbf_h *= 60.0

    return mtbf_h.rename("mtbf")


# ---------------------------------------------------------------------------
# Disponibilidad  (sección 3.3)
# ---------------------------------------------------------------------------

def disponibilidad_por_equipo(
    eventos: pd.DataFrame,
    rango: tuple[datetime, datetime],
) -> pd.Series:
    """
    Disponibilidad(equipo) = tiempo_operativo / tiempo_total_del_periodo  (en %)

    Equivalente a MTBF / (MTBF + MTTR).
    Devuelve Series indexada por id_equipo (valores 0–100).
    """
    ts_ini, ts_fin = pd.Timestamp(rango[0]), pd.Timestamp(rango[1])
    t_cal_s = (ts_fin - ts_ini).total_seconds()

    ev = eventos.copy()
    ev["ts_inicio_fallo"] = pd.to_datetime(ev["ts_inicio_fallo"])
    ev["ts_recuperacion"] = pd.to_datetime(ev["ts_recuperacion"])

    resueltos = ev[ev["estado"] == "resuelto"].copy()
    resueltos["dur_s"] = (
        resueltos["ts_recuperacion"] - resueltos["ts_inicio_fallo"]
    ).dt.total_seconds()

    tiempo_caido_s = resueltos.groupby("id_equipo")["dur_s"].sum()

    # Todos los equipos que aparecen en eventos
    todos = ev["id_equipo"].unique()
    tiempo_caido_s = tiempo_caido_s.reindex(todos, fill_value=0)

    disp = (1 - tiempo_caido_s / t_cal_s) * 100
    return disp.rename("disponibilidad")


# ---------------------------------------------------------------------------
# Ciclos  (sección 3.4)
# ---------------------------------------------------------------------------

def ciclos_por_equipo(
    misiones: pd.DataFrame,
    equipos: pd.DataFrame | None = None,
) -> pd.Series:
    """
    Número de misiones completadas por equipo (cada misión = un ciclo).

    El parámetro `equipos` se acepta por compatibilidad de firma con los
    llamadores; no influye en el conteo.
    """
    completadas = misiones[misiones["estado"] == "completada"]
    return completadas.groupby("id_equipo").size().rename("ciclos")


# ---------------------------------------------------------------------------
# Tiempo de ciclo  (sección 3.5)
# ---------------------------------------------------------------------------

def tiempo_ciclo(
    misiones: pd.DataFrame,
    unidad: str = "segundos",
) -> pd.Series:
    """
    tiempo_ciclo_i = ts_fin_i - ts_inicio_i  (sobre misiones completadas)

    Devuelve Series con la duración de cada misión completada.
    unidad: 'segundos' | 'minutos'
    """
    comp = misiones[misiones["estado"] == "completada"].copy()
    comp["ts_inicio"] = pd.to_datetime(comp["ts_inicio"])
    comp["ts_fin"]    = pd.to_datetime(comp["ts_fin"])
    dur_s = (comp["ts_fin"] - comp["ts_inicio"]).dt.total_seconds()
    if unidad == "minutos":
        dur_s /= 60.0
    return dur_s.rename("tiempo_ciclo")


# ---------------------------------------------------------------------------
# Posición en el momento del fallo  (sección 6)
# ---------------------------------------------------------------------------

def posicion_en_fallo(
    eventos: pd.DataFrame,
    misiones: pd.DataFrame,
) -> pd.DataFrame:
    """
    Para cada evento, devuelve la misión activa en ts_inicio_fallo
    (la misión del mismo equipo cuyo intervalo [ts_inicio, ts_fin] contiene
    ts_inicio_fallo).

    Retorna DataFrame con columnas del evento + posicion_inicial, posicion_final,
    id_mision de la misión activa. Eventos sin misión activa tienen NaN.

    Usa pd.merge_asof (backward) por equipo: O(n+m) en lugar del cartesiano
    O(n·m) que produce un join por id_equipo cuando hay millones de misiones.
    """
    ev = eventos.copy()
    ev["ts_inicio_fallo"] = pd.to_datetime(ev["ts_inicio_fallo"])

    # Solo procesar las misiones de los equipos que tienen eventos
    ids_con_eventos = set(ev["id_equipo"].unique())
    mis = misiones[misiones["id_equipo"].isin(ids_con_eventos)].copy()
    if mis.empty:
        ev["id_mision"] = pd.NA
        ev["posicion_inicial"] = pd.NA
        ev["posicion_final"] = pd.NA
        return ev

    mis["ts_inicio"] = pd.to_datetime(mis["ts_inicio"])
    mis["ts_fin"]    = pd.to_datetime(mis["ts_fin"])

    # merge_asof requiere ambos DataFrames ordenados por la clave de tiempo
    ev_ord  = ev.sort_values("ts_inicio_fallo").reset_index()  # preserva orden original en 'index'
    mis_ord = mis.sort_values("ts_inicio")[
        ["id_mision", "id_equipo", "ts_inicio", "ts_fin",
         "posicion_inicial", "posicion_final"]
    ]

    # Para cada evento, la última misión del mismo equipo iniciada <= ts_inicio_fallo
    merged = pd.merge_asof(
        ev_ord,
        mis_ord,
        left_on="ts_inicio_fallo",
        right_on="ts_inicio",
        by="id_equipo",
        direction="backward",
    )

    # La misión solo está "activa" si su ts_fin >= ts_inicio_fallo
    activa = merged["ts_fin"] >= merged["ts_inicio_fallo"]
    for col in ["id_mision", "posicion_inicial", "posicion_final"]:
        merged[col] = merged[col].where(activa)

    # Restaurar el orden original de eventos
    resultado = merged.sort_values("index").drop(
        columns=["index", "ts_inicio", "ts_fin"]
    ).reset_index(drop=True)
    return resultado


# ---------------------------------------------------------------------------
# Serie mensual  (sección 4.2)
# ---------------------------------------------------------------------------

def serie_mensual(
    df: pd.DataFrame,
    columna_fecha: str,
    columna_valor: str,
    agg: str = "mean",
) -> pd.Series:
    """
    Agrega columna_valor por mes del año.

    agg: 'mean' | 'sum' | 'count'
    Devuelve Series indexada por mes (1..12).
    """
    tmp = df.copy()
    tmp["_mes"] = pd.to_datetime(tmp[columna_fecha]).dt.month
    return tmp.groupby("_mes")[columna_valor].agg(agg).rename(columna_valor)


# ---------------------------------------------------------------------------
# Disponibilidad mensual media  (para Módulo 0 — evolución anual)
# ---------------------------------------------------------------------------

def disponibilidad_mensual(
    eventos: pd.DataFrame,
    rango: tuple[datetime, datetime],
) -> pd.Series:
    """
    Para cada mes contenido en `rango`, calcula la disponibilidad media
    de la instalación (media sobre id_equipo).

    Los eventos que cruzan el límite de mes se recortan (clip) al sub-rango
    de cada mes. Meses sin solape con `rango` quedan como NaN.
    Devuelve Series indexada por mes (1..12) con valores 0–100.
    """
    ts_ini_global = pd.Timestamp(rango[0])
    ts_fin_global = pd.Timestamp(rango[1])

    ev = eventos[eventos["estado"] == "resuelto"].copy()
    ev["ts_inicio_fallo"] = pd.to_datetime(ev["ts_inicio_fallo"])
    ev["ts_recuperacion"] = pd.to_datetime(ev["ts_recuperacion"])

    # Determinar meses con solape en el rango
    primer_mes = ts_ini_global.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    meses = pd.date_range(primer_mes, ts_fin_global, freq="MS")

    resultado = {}
    todos_equipos = eventos["id_equipo"].unique()

    for mes_inicio in meses:
        # Último instante del mes: primer día del mes siguiente − 1 segundo
        mes_fin = (mes_inicio + pd.offsets.MonthBegin(1)) - pd.Timedelta(seconds=1)
        # Acotar al rango global
        sub_ini = max(mes_inicio, ts_ini_global)
        sub_fin = min(mes_fin, ts_fin_global)
        t_cal_s = (sub_fin - sub_ini).total_seconds()
        if t_cal_s <= 0:
            continue

        # Filtrar eventos con ts_inicio_fallo dentro del sub-rango
        mask = (
            (ev["ts_inicio_fallo"] <= sub_fin) &
            (ev["ts_recuperacion"] >= sub_ini)
        )
        ev_mes = ev[mask].copy()

        if ev_mes.empty:
            resultado[mes_inicio.month] = 100.0
            continue

        # Clip de inicio/fin al sub-rango del mes
        ev_mes["ts_ini_clip"] = ev_mes["ts_inicio_fallo"].clip(lower=sub_ini, upper=sub_fin)
        ev_mes["ts_fin_clip"] = ev_mes["ts_recuperacion"].clip(lower=sub_ini, upper=sub_fin)
        ev_mes["dur_s"] = (ev_mes["ts_fin_clip"] - ev_mes["ts_ini_clip"]).dt.total_seconds()

        tiempo_caido = ev_mes.groupby("id_equipo")["dur_s"].sum()
        tiempo_caido = tiempo_caido.reindex(todos_equipos, fill_value=0)

        disp_eq = (1 - tiempo_caido / t_cal_s) * 100
        resultado[mes_inicio.month] = float(disp_eq.mean())

    return pd.Series(resultado, name="disponibilidad_mensual")


# ---------------------------------------------------------------------------
# KPIs agregados globales  (para Módulo 0)
# ---------------------------------------------------------------------------

def delta_vs_periodo_anterior(
    eventos: pd.DataFrame,
    misiones: pd.DataFrame,
    rango: tuple[datetime, datetime],
    eventos_global: pd.DataFrame | None = None,
    misiones_global: pd.DataFrame | None = None,
) -> dict:
    """
    Calcula las diferencias absolutas vs. el periodo inmediatamente anterior
    de la misma duración.

    Para que tenga sentido, `eventos_global`/`misiones_global` deben venir SIN
    filtrar por rango (pero pueden estar filtrados por tipo/zona). Si no se
    pasan, se usan `eventos`/`misiones` y el resultado puede ser nulo.

    Devuelve un dict con:
        delta_disponibilidad (pp)
        delta_n_fallos       (entero)
        delta_mttr_min       (float)
        delta_ciclos         (entero)
    """
    ts_ini = pd.Timestamp(rango[0])
    ts_fin = pd.Timestamp(rango[1])
    duracion = ts_fin - ts_ini
    if duracion.total_seconds() <= 0:
        return {"delta_disponibilidad": None, "delta_n_fallos": None,
                "delta_mttr_min": None, "delta_ciclos": None}

    ts_ini_prev = ts_ini - duracion
    ts_fin_prev = ts_ini

    ev_src = eventos_global if eventos_global is not None else eventos
    mis_src = misiones_global if misiones_global is not None else misiones

    ev_prev = ev_src[
        (pd.to_datetime(ev_src["ts_inicio_fallo"]) >= ts_ini_prev) &
        (pd.to_datetime(ev_src["ts_inicio_fallo"]) <  ts_fin_prev)
    ]
    mis_prev = mis_src[
        (pd.to_datetime(mis_src["ts_inicio"]) >= ts_ini_prev) &
        (pd.to_datetime(mis_src["ts_inicio"]) <  ts_fin_prev)
    ]

    if ev_prev.empty and mis_prev.empty:
        return {"delta_disponibilidad": None, "delta_n_fallos": None,
                "delta_mttr_min": None, "delta_ciclos": None}

    # Disponibilidad
    rango_prev = (str(ts_ini_prev.date()), str(ts_fin_prev.date()))
    rango_act  = (str(ts_ini.date()), str(ts_fin.date()))
    disp_prev = disponibilidad_por_equipo(ev_prev, rango_prev).mean() if not ev_prev.empty else 100.0
    disp_act  = disponibilidad_por_equipo(eventos, rango_act).mean() if not eventos.empty else 100.0

    mttr_prev = mttr_por_equipo(ev_prev).mean() if not ev_prev.empty else 0.0
    mttr_act  = mttr_por_equipo(eventos).mean() if not eventos.empty else 0.0

    ciclos_prev = int((mis_prev["estado"] == "completada").sum())
    ciclos_act  = int((misiones["estado"] == "completada").sum())

    return {
        "delta_disponibilidad": float(disp_act - disp_prev),
        "delta_n_fallos":       int(len(eventos) - len(ev_prev)),
        "delta_mttr_min":       float(mttr_act - mttr_prev),
        "delta_ciclos":         int(ciclos_act - ciclos_prev),
    }


def kpis_globales(
    eventos: pd.DataFrame,
    misiones: pd.DataFrame,
    equipos: pd.DataFrame,
    rango: tuple[datetime, datetime],
    unidad: str = "minutos",
) -> dict:
    """
    Devuelve dict con los KPIs resumen de toda la instalación:
        disponibilidad_media, n_fallos, mttr_medio, mtbf_medio, ciclos_totales
    """
    disp   = disponibilidad_por_equipo(eventos, rango)
    mttr   = mttr_por_equipo(eventos, unidad)
    mtbf   = mtbf_por_equipo(eventos, rango, unidad)
    ciclos = ciclos_por_equipo(misiones, equipos)

    return {
        "disponibilidad_media": float(disp.mean()) if len(disp) else 100.0,
        "n_fallos":             int(len(eventos)),
        "mttr_medio":           float(mttr.mean()) if len(mttr) else 0.0,
        "mtbf_medio":           float(mtbf.mean()) if len(mtbf) else 0.0,
        "ciclos_totales":       int(ciclos.sum()) if len(ciclos) else 0,
    }
