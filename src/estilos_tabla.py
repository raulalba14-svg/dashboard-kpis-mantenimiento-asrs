"""Estilos de celda compartidos para las tablas con semáforo.

Centraliza el coloreado por umbral que comparten las tablas de los módulos de
rendimiento (SRM y STV): el fondo semáforo de disponibilidad y la elección de
color por umbral para frecuencia y horas de parada.
"""

from __future__ import annotations

from src.theme import EXITO, ADVERTENCIA, CRITICO


def estilo_disponibilidad(v: float) -> str:
    """Celda con fondo semáforo según umbral (≥95 verde, 90–95 ámbar, <90 rojo).

    Fondo claro + texto del color saturado para que se lea bien y el estado se
    capte de un vistazo. st.dataframe respeta background-color sólido (no los
    degradados), por eso se colorea el fondo de la celda completa.
    """
    if v >= 95:
        fondo, texto = "#E6F4EA", EXITO          # verde claro
    elif v >= 90:
        fondo, texto = "#FDF1E1", ADVERTENCIA     # ámbar claro
    else:
        fondo, texto = "#FBE7E2", CRITICO         # rojo claro
    return f"background-color: {fondo}; color: {texto}; font-weight: 700;"


def color_por_umbral(v: float, rojo: float, ambar: float) -> str:
    """Devuelve el color (crítico/advertencia/éxito) según dos umbrales.

    `v >= rojo` → crítico; `v >= ambar` → advertencia; en otro caso → éxito.
    Se usa para colorear texto de frecuencia y horas de parada en las tablas.
    """
    return CRITICO if v >= rojo else (ADVERTENCIA if v >= ambar else EXITO)
