"""
Carga de datos y filtros globales.

I/O puro: lee CSV, parsea fechas, aplica filtros de sidebar.
Sin lógica de KPIs.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import EQUIPOS_CSV, EVENTOS_CSV, MISIONES_CSV, TIPOS_ERROR_CSV


def cargar_tablas() -> dict[str, pd.DataFrame]:
    """
    Lee los 4 CSV y devuelve un dict con DataFrames tipados.

    Pensado para decorarse con @st.cache_data en la app:
        cargar_tablas = st.cache_data(cargar_tablas)
    """
    equipos = pd.read_csv(EQUIPOS_CSV)
    tipos_error = pd.read_csv(TIPOS_ERROR_CSV)
    misiones = pd.read_csv(
        MISIONES_CSV,
        parse_dates=["ts_inicio", "ts_fin"],
    )
    eventos = pd.read_csv(
        EVENTOS_CSV,
        parse_dates=["ts_inicio_fallo", "ts_recuperacion"],
    )
    return {
        "equipos":     equipos,
        "tipos_error": tipos_error,
        "misiones":    misiones,
        "eventos":     eventos,
    }


def aplicar_filtros_globales(
    tablas: dict[str, pd.DataFrame],
    rango_fechas: tuple[str, str] | None = None,
    tipos_equipo: list[str] | None = None,
    zonas: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Filtra las cuatro tablas según los filtros globales del sidebar.

    - rango_fechas: (fecha_inicio, fecha_fin) como strings 'YYYY-MM-DD'.
    - tipos_equipo: lista de tipos a incluir ('SRM', 'STV'). None = todos.
    - zonas: lista de zonas a incluir. None = todas.

    Devuelve un nuevo dict con las tablas filtradas (no modifica el original).
    """
    equipos     = tablas["equipos"].copy()
    tipos_error = tablas["tipos_error"].copy()
    misiones    = tablas["misiones"].copy()
    eventos     = tablas["eventos"].copy()

    # Filtrar equipos por tipo y zona
    if tipos_equipo:
        equipos = equipos[equipos["tipo"].isin(tipos_equipo)]
    if zonas:
        equipos = equipos[equipos["zona"].isin(zonas)]

    ids_validos = set(equipos["id"])

    # Propagar filtro de equipos a misiones y eventos
    misiones = misiones[misiones["id_equipo"].isin(ids_validos)]
    eventos  = eventos[eventos["id_equipo"].isin(ids_validos)]

    # Filtrar por rango de fechas
    if rango_fechas:
        ts_ini = pd.Timestamp(rango_fechas[0])
        ts_fin = pd.Timestamp(rango_fechas[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

        misiones = misiones[
            (misiones["ts_inicio"] >= ts_ini) & (misiones["ts_inicio"] <= ts_fin)
        ]
        eventos = eventos[
            (eventos["ts_inicio_fallo"] >= ts_ini) & (eventos["ts_inicio_fallo"] <= ts_fin)
        ]

    return {
        "equipos":     equipos,
        "tipos_error": tipos_error,
        "misiones":    misiones,
        "eventos":     eventos,
    }
