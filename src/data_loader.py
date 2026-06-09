"""
Carga de datos y filtros globales.

I/O puro: lee CSV, parsea fechas, aplica filtros de sidebar.
Sin lógica de KPIs.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

from src.config import (
    DATA_DIR,
    EQUIPOS_CSV,
    EVENTOS_CSV,
    MISIONES_CSV,
    ROOT_DIR,
    TIPOS_ERROR_CSV,
)

# Semilla fija → dataset reproducible bit-a-bit (KPIs idénticos en cada arranque).
SEMILLA_DATASET = 42

_GENERADOR = ROOT_DIR / "scripts" / "generar_datos.py"


def datos_disponibles() -> bool:
    """True si los 4 CSV requeridos existen y son válidos (fechas parseables)."""
    if not all(
        p.exists()
        for p in (EQUIPOS_CSV, TIPOS_ERROR_CSV, MISIONES_CSV, EVENTOS_CSV)
    ):
        return False
    return _csv_eventos_valido()


def _csv_eventos_valido() -> bool:
    """
    True si eventos_incidencia.csv tiene fechas parseables en ts_recuperacion.

    Defensa ante un dataset corrupto persistido (p. ej. Streamlit Cloud, que
    conserva el `data/` generado entre reinicios): un generador antiguo escribía
    ts_recuperacion como enteros nanosegundo, que al parsear lanzan
    OutOfBoundsDatetime. Si detectamos eso, tratamos el dataset como no
    disponible para forzar su regeneración con el generador actual.
    """
    try:
        # Leer igual que cargar_tablas (parse_dates) y exigir que la columna
        # quede como datetime. Un CSV con enteros nanosegundo se lee como
        # numérico (no datetime) o revienta con OutOfBoundsDatetime: en ambos
        # casos lo tratamos como corrupto.
        muestra = pd.read_csv(
            EVENTOS_CSV, usecols=["ts_recuperacion"],
            nrows=2000, parse_dates=["ts_recuperacion"],
        )
        return pd.api.types.is_datetime64_any_dtype(muestra["ts_recuperacion"])
    except Exception:
        return False


def _generar() -> None:
    """Ejecuta el generador de datos por ruta de fichero (scripts/ no es paquete)."""
    spec = importlib.util.spec_from_file_location("generar_datos", _GENERADOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar el generador en {_GENERADOR}")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    gen.generar_dataset(DATA_DIR, semilla=SEMILLA_DATASET)


def asegurar_datos() -> bool:
    """
    Garantiza que los 4 CSV existen y son válidos, regenerándolos si faltan
    o si están corruptos.

    Devuelve True si tuvo que generarlos (primer arranque en un entorno limpio,
    p. ej. Streamlit Cloud, donde `data/` está en .gitignore; o un dataset
    previo corrupto), False si ya estaban y eran válidos. La generación usa la
    semilla fija → cifras idénticas siempre.

    No depende de Streamlit a propósito: este módulo es I/O puro. El feedback
    visual (spinner) se aplica desde la capa que sí conoce Streamlit.
    """
    if datos_disponibles():
        return False

    _generar()
    return True


def cargar_tablas() -> dict[str, pd.DataFrame]:
    """
    Lee los 4 CSV y devuelve un dict con DataFrames tipados.

    Si los CSV no existen (entorno limpio sin `data/`), los genera primero
    con `asegurar_datos()`. Pensado para decorarse con @st.cache_data:
        cargar_tablas = st.cache_data(cargar_tablas)
    """
    asegurar_datos()

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
    - tipos_equipo: lista de tipos a incluir ('SRM'). None = todos.
    - zonas: lista de zonas a incluir ('pasillo'). None = todas.

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
