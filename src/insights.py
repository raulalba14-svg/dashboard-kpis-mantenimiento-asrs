"""
Generadores de "Lectura ejecutiva" por módulo.

Cada función recibe los DataFrames ya filtrados (resultado de
`aplicar_filtros_globales`) y devuelve un string HTML corto con la
interpretación accionable de los datos. Sin efectos colaterales, sin
imports de Streamlit.

Diseño: una frase compacta con cifras concretas marcadas con <b> y, cuando
proceda, una segunda frase con la implicación operativa. Robusto ante
DataFrames vacíos: si no hay datos suficientes, devuelve un mensaje neutro.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.kpis import (
    disponibilidad_por_equipo,
    mttr_por_equipo,
    ciclos_por_equipo,
    tasa_rechazo,
    tiempo_ciclo,
)


_OBJETIVO_DISP = 95.0  # %


def _vacio(mensaje: str = "Sin datos suficientes para generar una lectura ejecutiva.") -> str:
    return mensaje


# ---------------------------------------------------------------------------
# Módulo 0 — Resumen general
# ---------------------------------------------------------------------------

def resumen_general(
    eventos: pd.DataFrame,
    misiones: pd.DataFrame,
    equipos: pd.DataFrame,
    rango: tuple[str, str],
) -> str:
    if eventos.empty:
        return _vacio()

    disp = disponibilidad_por_equipo(eventos, rango)
    disp_media = float(disp.mean()) if len(disp) else 100.0
    sobre_objetivo = disp_media >= _OBJETIVO_DISP
    comparativo = "por encima" if sobre_objetivo else "por debajo"
    juicio = (
        "El parque opera dentro de objetivo."
        if sobre_objetivo
        else "El parque opera por debajo de objetivo; revisar los equipos críticos."
    )

    peor_equipo = disp.idxmin() if len(disp) else None
    peor_valor = float(disp.min()) if len(disp) else 100.0

    return (
        f"Disponibilidad media de la instalación: <b>{disp_media:.2f}%</b> — "
        f"{comparativo} del objetivo del <b>{_OBJETIVO_DISP:.0f}%</b>. "
        f"{juicio} "
        + (
            f"El equipo más crítico es <b>{peor_equipo}</b> con "
            f"<b>{peor_valor:.2f}%</b> de disponibilidad."
            if peor_equipo is not None
            else ""
        )
    )


# ---------------------------------------------------------------------------
# Módulo 1 — Fallos por zona y equipo
# ---------------------------------------------------------------------------

def fallos_por_zona(
    eventos: pd.DataFrame,
    equipos: pd.DataFrame,
) -> str:
    if eventos.empty:
        return _vacio()

    # Concentración por zona
    ev_con_zona = eventos.merge(
        equipos[["id", "zona"]], left_on="id_equipo", right_on="id", how="left"
    )
    por_zona = ev_con_zona.groupby("zona").size().sort_values(ascending=False)
    if por_zona.empty:
        return _vacio()

    zona_top = por_zona.index[0]
    pct_zona = 100.0 * por_zona.iloc[0] / por_zona.sum()

    # Código de error dominante
    por_codigo = eventos.groupby("codigo_error").size().sort_values(ascending=False)
    codigo_top = por_codigo.index[0] if len(por_codigo) else "—"

    # Equipo con más fallos
    por_equipo = eventos.groupby("id_equipo").size().sort_values(ascending=False)
    equipo_top = por_equipo.index[0]
    n_fallos_top = int(por_equipo.iloc[0])

    return (
        f"El <b>{pct_zona:.0f}%</b> de los fallos se concentra en "
        f"<b>{zona_top.replace('_', ' ')}</b>, con <b>{codigo_top}</b> como código de error dominante. "
        f"El equipo con más incidencias es <b>{equipo_top}</b> "
        f"(<b>{n_fallos_top}</b> fallos) — priorizarlo en la próxima ventana de mantenimiento."
    )


# ---------------------------------------------------------------------------
# Módulo 2 — Rendimiento SRM
# ---------------------------------------------------------------------------

def rendimiento_srm(
    eventos: pd.DataFrame,
    misiones: pd.DataFrame,
    equipos: pd.DataFrame,
    rango: tuple[str, str],
) -> str:
    srm_ids = set(equipos.loc[equipos["tipo"] == "SRM", "id"])
    if not srm_ids:
        return _vacio("No hay transelevadores SRM en los filtros activos.")

    ev_srm = eventos[eventos["id_equipo"].isin(srm_ids)]
    mis_srm = misiones[misiones["id_equipo"].isin(srm_ids)]

    if ev_srm.empty:
        return "Los <b>20 SRM</b> no han registrado incidencias en el periodo filtrado."

    disp = disponibilidad_por_equipo(ev_srm, rango)
    disp_media = float(disp.mean()) if len(disp) else 100.0

    ciclos = ciclos_por_equipo(mis_srm)
    if len(ciclos) > 3 and len(disp) > 3:
        # ¿Los SRM con más ciclos tienen más fallos?
        n_fallos = ev_srm.groupby("id_equipo").size().rename("n_fallos")
        df = pd.concat([ciclos, n_fallos], axis=1).dropna()
        if len(df) >= 4:
            corr = df["ciclos"].corr(df["n_fallos"])
        else:
            corr = None
    else:
        corr = None

    if corr is None:
        correlacion_msg = ""
    elif corr > 0.4:
        correlacion_msg = (
            " La carga y la tasa de fallo correlacionan positivamente "
            f"(<b>r={corr:.2f}</b>) — los SRM más solicitados sufren más averías: "
            "valorar mantenimiento preventivo basado en ciclos."
        )
    elif corr < -0.2:
        correlacion_msg = (
            f" La carga y la tasa de fallo no correlacionan (<b>r={corr:.2f}</b>); "
            "los fallos parecen aleatorios o vinculados a otros factores."
        )
    else:
        correlacion_msg = (
            f" La carga no explica los fallos (<b>r={corr:.2f}</b>); "
            "buscar causa raíz por código de error en lugar de por uso."
        )

    peor = disp.idxmin() if len(disp) else None
    return (
        f"Disponibilidad media de los SRM: <b>{disp_media:.2f}%</b>. "
        + (f"El SRM más crítico es <b>{peor}</b>." if peor else "")
        + correlacion_msg
    )


# ---------------------------------------------------------------------------
# Módulo 3 — Rendimiento STV
# ---------------------------------------------------------------------------

def rendimiento_stv(
    eventos: pd.DataFrame,
    misiones: pd.DataFrame,
    equipos: pd.DataFrame,
    rango: tuple[str, str],
) -> str:
    stv = equipos[equipos["tipo"] == "STV"]
    if stv.empty:
        return _vacio("No hay STV en los filtros activos.")

    entrada_ids = set(stv.loc[stv["zona"] == "anillo_entrada", "id"])
    salida_ids = set(stv.loc[stv["zona"] == "anillo_salida", "id"])

    def _disp(ids: set) -> float | None:
        ev = eventos[eventos["id_equipo"].isin(ids)]
        if ev.empty:
            return None
        s = disponibilidad_por_equipo(ev, rango)
        return float(s.mean()) if len(s) else None

    disp_e = _disp(entrada_ids)
    disp_s = _disp(salida_ids)

    partes = []
    if disp_e is not None:
        partes.append(f"anillo de entrada <b>{disp_e:.2f}%</b>")
    if disp_s is not None:
        partes.append(f"anillo de salida <b>{disp_s:.2f}%</b>")

    if not partes:
        return "Los <b>30 STV</b> no han registrado incidencias en el periodo filtrado."

    cabecera = "Disponibilidad por anillo — " + " · ".join(partes) + "."

    # Cuello de botella
    cierre = ""
    if disp_e is not None and disp_s is not None:
        if disp_s < disp_e - 1.0:
            cierre = (
                " El anillo de salida arrastra al conjunto — sus 10 STV de doble cuna "
                "limitan el throughput de expedición."
            )
        elif disp_e < disp_s - 1.0:
            cierre = (
                " El anillo de entrada es el más crítico — los 20 STV de cuna simple "
                "saturan el flujo de recepción."
            )

    return cabecera + cierre


# ---------------------------------------------------------------------------
# Módulo 4 — Obstrucciones y rechazos
# ---------------------------------------------------------------------------

def obstrucciones_rechazos(
    misiones: pd.DataFrame,
    eventos: pd.DataFrame,
) -> str:
    if misiones.empty:
        return _vacio()

    tasa = tasa_rechazo(misiones)
    tasa_pct = tasa * 100 if tasa else 0.0
    n_rechazos = int((misiones["estado"] == "rechazada").sum())
    n_total = int(len(misiones))

    if n_rechazos == 0:
        return f"Cero rechazos sobre <b>{n_total:,}</b> misiones — el flujo del anillo es limpio."

    return (
        f"Tasa de rechazo global: <b>{tasa_pct:.2f}%</b> "
        f"(<b>{n_rechazos:,}</b> rechazos sobre <b>{n_total:,}</b> misiones). "
        "Una parte se debe a sensores descalibrados del inspector de pallets "
        "(corregible con mantenimiento) y otra a saturación del anillo (dimensión operativa). "
        "Reducir la primera libera operarios y desatura el flujo."
    )


# ---------------------------------------------------------------------------
# Módulo 5 — Expedición / anillo de salida
# ---------------------------------------------------------------------------

def expedicion(
    misiones: pd.DataFrame,
    equipos: pd.DataFrame,
    rango: tuple[str, str],
) -> str:
    salida_ids = set(equipos.loc[equipos["zona"] == "anillo_salida", "id"])
    if not salida_ids:
        return _vacio("No hay STV de salida en los filtros activos.")

    mis_salida = misiones[
        (misiones["id_equipo"].isin(salida_ids)) &
        (misiones["estado"] == "completada")
    ]
    if mis_salida.empty:
        return _vacio("No hay misiones completadas en el anillo de salida.")

    t_ciclo_s = tiempo_ciclo(mis_salida, unidad="segundos")
    t_medio = float(t_ciclo_s.mean())
    t_mediana = float(t_ciclo_s.median())

    # Throughput: doble cuna multiplica por 2 los pallets por misión completada
    pallets = 2 * len(mis_salida)
    ts_ini = pd.Timestamp(rango[0])
    ts_fin = pd.Timestamp(rango[1]) + pd.Timedelta(days=1)
    horas = (ts_fin - ts_ini).total_seconds() / 3600.0
    throughput = pallets / horas if horas > 0 else 0

    # Cuello de botella: STV con tiempo de ciclo medio más alto
    t_por_stv = (
        mis_salida.assign(
            _t=(pd.to_datetime(mis_salida["ts_fin"])
                - pd.to_datetime(mis_salida["ts_inicio"])).dt.total_seconds()
        )
        .groupby("id_equipo")["_t"].mean()
    )
    cuello = t_por_stv.idxmax() if len(t_por_stv) else None
    cuello_t = float(t_por_stv.max()) if len(t_por_stv) else 0.0

    cierre = (
        f" El cuello de botella es <b>{cuello}</b> "
        f"(<b>{cuello_t:.1f}s</b> de tiempo de ciclo medio)."
        if cuello else ""
    )

    return (
        f"Tiempo de ciclo medio en el anillo de salida: <b>{t_medio:.1f}s</b> "
        f"(mediana <b>{t_mediana:.1f}s</b>). "
        f"Throughput estimado: <b>{throughput:,.0f} pallets/h</b> aprovechando la doble cuna."
        + cierre
    )
