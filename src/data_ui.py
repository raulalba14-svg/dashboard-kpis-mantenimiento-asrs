"""
Capa de UI sobre `src.data_loader`.

Mantiene `data_loader.py` libre de Streamlit (I/O puro) y concentra aquí el
único punto donde la carga necesita feedback visual: la primera generación
del dataset en un entorno limpio (p. ej. Streamlit Cloud, donde `data/` está
en .gitignore), que tarda unos segundos.
"""

from __future__ import annotations

import streamlit as st

from src.data_loader import cargar_tablas, datos_disponibles


def cargar_tablas_con_feedback():
    """
    Como `cargar_tablas()`, pero muestra un spinner si hay que generar el
    dataset por primera vez. En arranques posteriores los CSV ya existen y
    la llamada es directa (y, decorada con @st.cache_data, instantánea).
    """
    if datos_disponibles():
        return cargar_tablas()

    with st.spinner(
        "Generando dataset de demo por primera vez (≈ 939.994 misiones)… "
        "Solo ocurre en el primer arranque."
    ):
        return cargar_tablas()
