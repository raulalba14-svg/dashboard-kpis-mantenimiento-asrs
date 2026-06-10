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

# Equipos — 8 pasillos en paralelo (un transelevador por pasillo) y un anillo
# único de vehículos de transferencia (STV) que alimenta y evacúa los pasillos.
N_SRM = 8
N_STV = 15

IDS_SRM = [f"SRM-{i:02d}" for i in range(1, N_SRM + 1)]
IDS_STV = [f"STV-{i:02d}" for i in range(1, N_STV + 1)]
IDS_TODOS = IDS_SRM + IDS_STV

TIPOS_EQUIPO = ["SRM", "STV"]
ZONAS = ["pasillo", "anillo"]

# Geometría del pasillo (para el alzado y la generación de posiciones)
N_ALTURAS = 16
N_COLUMNAS = 48

# Tramos del anillo único por los que circulan los STV
N_TRAMOS_ANILLO = 24

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


# Códigos de error que se contabilizan como causa de mantenimiento (vs. desgaste
# operativo esperable). E03: desviación de posición por descalibración del láser.
CODIGOS_MANTENIMIENTO = {"E03"}


# Umbrales de salud por TASA de fallos (fallos/día), no por nº absoluto. Así el
# color del plano significa lo mismo sea cual sea el rango de fechas: un equipo
# con 130 fallos en un año está sano; los mismos 130 en una semana, crítico.
# Cortes por tipo de equipo (SRM falla algo más que STV por su ciclo en altura).
# Calibrados sobre la operación normal del dataset (SRM ~0,3/día, STV ~0,23/día).
#   (corte_verde, corte_ambar):  < verde = sano · < ambar = vigilar · ≥ ambar = crítico
UMBRALES_TASA_FALLOS = {
    "SRM": (0.40, 0.55),
    "STV": (0.30, 0.42),
}


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


def rango_calendario(rango) -> tuple[pd.Timestamp, pd.Timestamp]:
    """
    Convierte el par (date_ini, date_fin) del filtro — ambos días inclusive —
    en los timestamps de calendario que esperan los KPIs: [inicio, fin + 1 día).

    Coherente con `aplicar_filtros_globales`, que incluye el día final completo.
    Sin el +1 día, el calendario quedaría un día corto respecto a los eventos
    filtrados y un rango de un solo día tendría duración cero (disponibilidad
    y MTBF divididos por cero).
    """
    return (pd.Timestamp(rango[0]), pd.Timestamp(rango[1]) + pd.Timedelta(days=1))


# Paletas de colores reexportadas desde src/theme.py para evitar duplicación.
# El tema corporativo es la única fuente de verdad cromática.
from src.theme import COLOR_CATEGORIA, COLOR_SEVERIDAD  # noqa: E402  (al final del módulo)
