"""Tests de src/intervalos.py — unión de solapes dentro de una ventana."""

import pandas as pd

from src.intervalos import union_solape_segundos


def _ts(s):
    return pd.Timestamp(s)


VENTANA = (_ts("2025-01-01 00:00"), _ts("2025-01-01 10:00"))  # 10 h


def test_sin_intervalos_es_cero():
    assert union_solape_segundos([], *VENTANA) == 0.0


def test_un_intervalo_dentro():
    iv = [(_ts("2025-01-01 01:00"), _ts("2025-01-01 02:00"))]  # 1 h
    assert union_solape_segundos(iv, *VENTANA) == 3600.0


def test_solapes_no_se_cuentan_dos_veces():
    """Dos averías que se solapan cuentan como el tiempo de su unión, no la suma."""
    iv = [
        (_ts("2025-01-01 01:00"), _ts("2025-01-01 03:00")),  # 2 h
        (_ts("2025-01-01 02:00"), _ts("2025-01-01 04:00")),  # solapa 1 h con la anterior
    ]
    # Unión = [01:00, 04:00] = 3 h, no 4 h.
    assert union_solape_segundos(iv, *VENTANA) == 3 * 3600.0


def test_intervalos_disjuntos_se_suman():
    iv = [
        (_ts("2025-01-01 01:00"), _ts("2025-01-01 02:00")),  # 1 h
        (_ts("2025-01-01 05:00"), _ts("2025-01-01 06:00")),  # 1 h
    ]
    assert union_solape_segundos(iv, *VENTANA) == 2 * 3600.0


def test_recorte_a_la_ventana():
    """Las averías que sobresalen de la ventana se recortan a ella."""
    iv = [
        (_ts("2024-12-31 22:00"), _ts("2025-01-01 01:00")),  # solo 1 h dentro
        (_ts("2025-01-01 09:00"), _ts("2025-01-01 12:00")),  # solo 1 h dentro
    ]
    assert union_solape_segundos(iv, *VENTANA) == 2 * 3600.0


def test_intervalo_fuera_de_la_ventana_no_cuenta():
    iv = [(_ts("2025-01-02 00:00"), _ts("2025-01-02 01:00"))]
    assert union_solape_segundos(iv, *VENTANA) == 0.0
