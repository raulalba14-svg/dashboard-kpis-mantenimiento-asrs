from pathlib import Path
import pandas as pd

# Rutas
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"

EQUIPOS_CSV = DATA_DIR / "equipos.csv"
TIPOS_ERROR_CSV = DATA_DIR / "tipos_error.csv"
MISIONES_CSV = DATA_DIR / "misiones.csv"
EVENTOS_CSV = DATA_DIR / "eventos_incidencia.csv"

# Dataset
ANO_DATASET = 2025
FECHA_INICIO = f"{ANO_DATASET}-01-01"
FECHA_FIN = f"{ANO_DATASET}-12-31"

# Equipos
N_SRM = 20
N_STV_ENTRADA = 20
N_STV_SALIDA = 10

IDS_SRM = [f"SRM-{i:02d}" for i in range(1, N_SRM + 1)]
IDS_STV_ENTRADA = [f"STV-E-{i:02d}" for i in range(1, N_STV_ENTRADA + 1)]
IDS_STV_SALIDA = [f"STV-S-{i:02d}" for i in range(1, N_STV_SALIDA + 1)]
IDS_TODOS = IDS_SRM + IDS_STV_ENTRADA + IDS_STV_SALIDA

TIPOS_EQUIPO = ["SRM", "STV"]
ZONAS = ["pasillo", "anillo_entrada", "anillo_salida"]

# Unidad de tiempo para KPIs ("minutos" u "horas")
UNIDAD_TIEMPO = "minutos"

def init_session_state():
    """
    Inicializa los valores por defecto del session_state si no existen.
    Llamar al inicio de cada página para garantizar que los filtros tienen valor
    aunque el usuario haya navegado directamente sin pasar por app.py.
    """
    import streamlit as st
    if "rango_fechas" not in st.session_state:
        st.session_state["rango_fechas"] = (
            pd.Timestamp(FECHA_INICIO).date(),
            pd.Timestamp(FECHA_FIN).date(),
        )
    if "tipos_equipo" not in st.session_state:
        st.session_state["tipos_equipo"] = TIPOS_EQUIPO[:]
    if "zonas" not in st.session_state:
        st.session_state["zonas"] = ZONAS[:]


def rango_valido(rango) -> bool:
    """
    True si `rango` es un par (date_ini, date_fin) usable.

    st.date_input puede devolver un único `date` mientras el usuario está
    re-seleccionando, lo que rompe `len(rango)` con TypeError.
    """
    return (
        isinstance(rango, (tuple, list))
        and len(rango) == 2
        and rango[0] is not None
        and rango[1] is not None
    )


# Códigos de error que se contabilizan como causa de mantenimiento
# (vs. operativa) en el módulo 4 — Obstrucciones y rechazos.
# E12: rechazo del inspector de pallets por sensor descalibrado.
CODIGOS_MANTENIMIENTO = {"E12"}


# Paletas de colores reexportadas desde src/theme.py para evitar duplicación.
# El tema corporativo es la única fuente de verdad cromática.
from src.theme import COLOR_CATEGORIA, COLOR_SEVERIDAD  # noqa: E402  (al final del módulo)
