"""
Formato numérico en convención española para los textos de la app.

Punto como separador de miles y coma como decimal (1.205 · 200,3). Se usa en
los números que se leen como frase — tarjetas KPI, lecturas ejecutivas y
captions —, donde el formato inglés (1,205 · 200.3) induce a error al lector
español. Las tablas mantienen el formato técnico con punto decimal para
conservar el ordenado numérico nativo de st.dataframe.
"""

from __future__ import annotations


def fmt_es(valor: float, decimales: int = 1) -> str:
    """
    Formatea un número en convención española: punto de miles, coma decimal.

    fmt_es(1205, 0)   -> "1.205"
    fmt_es(200.3, 1)  -> "200,3"
    fmt_es(33642, 0)  -> "33.642"
    fmt_es(-5.5, 1)   -> "-5,5"

    Se formatea primero en inglés (con `,` de miles y `.` decimal) y se
    intercambian los separadores usando un placeholder para no pisarse.
    """
    s = f"{valor:,.{decimales}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
