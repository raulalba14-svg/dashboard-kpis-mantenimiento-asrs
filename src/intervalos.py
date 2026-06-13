"""Utilidades de intervalos temporales compartidas.

Los STV circulan por un anillo único en serie: varias averías simultáneas
detienen el circuito una sola vez. Por eso, para acotar el tiempo de parada
dentro de la ventana de un pedido se calcula la UNIÓN de los intervalos de
avería (no la suma), evitando contar doble el tiempo solapado.

Esta lógica la comparten el generador de datos (`scripts/generar_datos.py`) y
la página de expedición (módulo 5). Mantenerla en un único sitio garantiza que
el cálculo del dataset y el que se muestra en la app no se desincronicen.
"""

from __future__ import annotations


def union_solape_segundos(intervalos, p_ini, p_fin) -> float:
    """Segundos de parada (unión de intervalos) dentro de la ventana [p_ini, p_fin].

    `intervalos` es un iterable de pares (inicio, fin) de averías, con valores
    comparables y restables que devuelvan un timedelta con `.total_seconds()`
    (p. ej. pandas.Timestamp). Los intervalos se recortan a la ventana, se
    ordenan y se fusionan los solapes; se devuelve el total en segundos.
    """
    recortados = []
    for ini, fin in intervalos:
        a = max(ini, p_ini)
        b = min(fin, p_fin)
        if b > a:
            recortados.append((a, b))
    if not recortados:
        return 0.0
    recortados.sort()
    total = 0.0
    cur_ini, cur_fin = recortados[0]
    for a, b in recortados[1:]:
        if a <= cur_fin:                 # se solapan: fusionar
            cur_fin = max(cur_fin, b)
        else:
            total += (cur_fin - cur_ini).total_seconds()
            cur_ini, cur_fin = a, b
    total += (cur_fin - cur_ini).total_seconds()
    return total
