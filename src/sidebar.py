"""Sidebar de filtros globales compartido por todas las páginas."""

import streamlit as st
import pandas as pd

from src.config import FECHA_INICIO, FECHA_FIN, TIPOS_EQUIPO, ZONAS, init_session_state
from src.theme import PRIMARIO

_ZONAS_LABELS = {
    "pasillo":         "Pasillo (SRM)",
    "anillo_entrada":  "Anillo entrada",
    "anillo_salida":   "Anillo salida",
}


def render_sidebar_filtros() -> None:
    """Dibuja el sidebar de filtros globales y persiste sus valores en session_state."""
    init_session_state()

    with st.sidebar:
        st.markdown(
            f"<h2 style='color:{PRIMARIO};margin-bottom:0.4rem;'>Filtros globales</h2>",
            unsafe_allow_html=True,
        )
        st.caption("Aplican a todos los módulos.")

        fecha_ini_def = pd.Timestamp(FECHA_INICIO).date()
        fecha_fin_def = pd.Timestamp(FECHA_FIN).date()

        st.date_input(
            "Rango de fechas",
            min_value=fecha_ini_def,
            max_value=fecha_fin_def,
            key="rango_fechas",
        )

        st.multiselect(
            "Tipo de equipo",
            options=TIPOS_EQUIPO,
            key="tipos_equipo",
        )

        st.multiselect(
            "Zona",
            options=ZONAS,
            format_func=lambda z: _ZONAS_LABELS.get(z, z),
            key="zonas",
        )

        st.divider()
        st.caption("Selecciona un módulo en el menú superior.")
