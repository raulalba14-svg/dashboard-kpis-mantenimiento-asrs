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
        return "Los <b>8 SRM</b> no han registrado incidencias en el periodo filtrado."

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
# Módulo 3 — Rendimiento STV (anillo único)
# ---------------------------------------------------------------------------

def rendimiento_stv(
    eventos: pd.DataFrame,
    misiones: pd.DataFrame,
    equipos: pd.DataFrame,
    rango: tuple[str, str],
) -> str:
    stv_ids = set(equipos.loc[equipos["tipo"] == "STV", "id"])
    if not stv_ids:
        return _vacio("No hay STV en los filtros activos.")

    ev_stv = eventos[eventos["id_equipo"].isin(stv_ids)]
    if ev_stv.empty:
        return f"Los <b>{len(stv_ids)} STV</b> del anillo no han registrado incidencias en el periodo filtrado."

    disp = disponibilidad_por_equipo(ev_stv, rango)
    disp_media = float(disp.mean()) if len(disp) else 100.0
    peor = disp.idxmin() if len(disp) else None
    peor_valor = float(disp.min()) if len(disp) else 100.0

    n_fallos = int(len(ev_stv))
    juicio = (
        "El anillo opera dentro de objetivo."
        if disp_media >= _OBJETIVO_DISP
        else "El anillo opera por debajo de objetivo; un STV degradado puede frenar el flujo del resto."
    )

    return (
        f"Disponibilidad media del anillo de STV: <b>{disp_media:.2f}%</b> "
        f"sobre <b>{len(stv_ids)}</b> vehículos y <b>{n_fallos:,}</b> fallos. "
        + (f"El STV más crítico es <b>{peor}</b> (<b>{peor_valor:.2f}%</b>). " if peor else "")
        + juicio
    )
