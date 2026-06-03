"""Tests unitarios de src/kpis.py con DataFrames construidos a mano."""

import pandas as pd
import pytest

from src.kpis import (
    delta_vs_periodo_anterior,
    disponibilidad_mensual,
    disponibilidad_por_equipo,
    kpis_globales,
    ciclos_por_equipo,
    mtbf_por_equipo,
    mttr_por_equipo,
    posicion_en_fallo,
    serie_mensual,
    tasa_rechazo,
    tiempo_ciclo,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RANGO = ("2025-01-01", "2025-01-05")  # 4 días = 96 horas = 5760 minutos


def _evento(id_ev, id_eq, codigo, ts_ini, ts_rec, estado="resuelto"):
    return {
        "id_evento": id_ev,
        "id_equipo": id_eq,
        "codigo_error": codigo,
        "ts_inicio_fallo": pd.Timestamp(ts_ini),
        "ts_recuperacion": pd.Timestamp(ts_rec) if ts_rec else pd.NaT,
        "estado": estado,
    }


def _mision(id_mis, id_eq, ts_ini, ts_fin, estado="completada",
            pos_ini="P01-A01-C01", pos_fin="P01-A02-C01"):
    return {
        "id_mision": id_mis,
        "id_equipo": id_eq,
        "posicion_inicial": pos_ini,
        "posicion_final": pos_fin,
        "ts_inicio": pd.Timestamp(ts_ini),
        "ts_fin": pd.Timestamp(ts_fin),
        "estado": estado,
    }


@pytest.fixture
def eventos_simples():
    """EQ-A: 3 fallos de 60, 120 y 180 min → MTTR = 120 min."""
    return pd.DataFrame([
        _evento(1, "EQ-A", "E01", "2025-01-01 08:00", "2025-01-01 09:00"),  # 60 min
        _evento(2, "EQ-A", "E02", "2025-01-02 10:00", "2025-01-02 12:00"),  # 120 min
        _evento(3, "EQ-A", "E04", "2025-01-03 15:00", "2025-01-03 18:00"),  # 180 min
    ])


@pytest.fixture
def eventos_con_en_curso():
    """EQ-B: 2 resueltos + 1 en_curso."""
    return pd.DataFrame([
        _evento(1, "EQ-B", "E01", "2025-01-01 08:00", "2025-01-01 09:00"),  # 60 min
        _evento(2, "EQ-B", "E02", "2025-01-02 10:00", "2025-01-02 11:00"),  # 60 min
        _evento(3, "EQ-B", "E04", "2025-01-04 10:00", None, estado="en_curso"),
    ])


# ---------------------------------------------------------------------------
# MTTR
# ---------------------------------------------------------------------------

class TestMttr:
    def test_media_correcta(self, eventos_simples):
        mttr = mttr_por_equipo(eventos_simples)
        assert abs(mttr["EQ-A"] - 120.0) < 0.01

    def test_en_curso_excluido(self, eventos_con_en_curso):
        mttr = mttr_por_equipo(eventos_con_en_curso)
        # Solo los 2 resueltos (60 min cada uno) → MTTR = 60
        assert abs(mttr["EQ-B"] - 60.0) < 0.01

    def test_unidad_horas(self, eventos_simples):
        mttr_h = mttr_por_equipo(eventos_simples, unidad="horas")
        assert abs(mttr_h["EQ-A"] - 2.0) < 0.001  # 120 min = 2 h


# ---------------------------------------------------------------------------
# MTBF
# ---------------------------------------------------------------------------

class TestMtbf:
    def test_formula(self):
        """
        Periodo: 100 h. Equipo con 2 fallos de 10 h cada uno.
        tiempo_operativo = 100 - 20 = 80 h
        MTBF = 80 / 2 = 40 h
        """
        ev = pd.DataFrame([
            _evento(1, "EQ-C", "E01",
                    "2025-01-01 00:00", "2025-01-01 10:00"),
            _evento(2, "EQ-C", "E02",
                    "2025-01-02 00:00", "2025-01-02 10:00"),
        ])
        rango = ("2025-01-01 00:00", "2025-01-05 04:00")  # exactamente 100 h
        mtbf = mtbf_por_equipo(ev, rango, unidad="horas")
        assert abs(mtbf["EQ-C"] - 40.0) < 0.01

    def test_en_curso_no_cuenta_en_tiempo_caido(self):
        """Los en_curso no deben sumarse al tiempo caído."""
        ev = pd.DataFrame([
            _evento(1, "EQ-D", "E01",
                    "2025-01-01 00:00", "2025-01-01 10:00"),
            _evento(2, "EQ-D", "E02",
                    "2025-01-04 00:00", None, estado="en_curso"),
        ])
        rango = ("2025-01-01 00:00", "2025-01-05 04:00")  # 100 h
        mtbf = mtbf_por_equipo(ev, rango, unidad="horas")
        # tiempo_operativo = 100 - 10 = 90, n_fallos = 2 → MTBF = 45
        assert abs(mtbf["EQ-D"] - 45.0) < 0.01


# ---------------------------------------------------------------------------
# Disponibilidad
# ---------------------------------------------------------------------------

class TestDisponibilidad:
    def test_valor_conocido(self):
        """
        Periodo: 100 h. 20 h de fallo → disponibilidad = 80 %.
        """
        ev = pd.DataFrame([
            _evento(1, "EQ-E", "E01",
                    "2025-01-01 00:00", "2025-01-01 10:00"),
            _evento(2, "EQ-E", "E02",
                    "2025-01-02 00:00", "2025-01-02 10:00"),
        ])
        rango = ("2025-01-01 00:00", "2025-01-05 04:00")
        disp = disponibilidad_por_equipo(ev, rango)
        assert abs(disp["EQ-E"] - 80.0) < 0.01

    def test_sin_fallos_es_100(self):
        """Sin eventos el equipo debería tener 100 % (no aparece en la serie)."""
        ev = pd.DataFrame([
            _evento(1, "EQ-F", "E01",
                    "2025-01-01 00:00", "2025-01-01 01:00"),
        ])
        # EQ-G no tiene eventos → no aparece en el resultado
        rango = ("2025-01-01", "2025-01-05")
        disp = disponibilidad_por_equipo(ev, rango)
        assert "EQ-G" not in disp.index

    def test_en_curso_no_cuenta(self):
        """Los fallos en_curso no deben reducir la disponibilidad."""
        ev = pd.DataFrame([
            _evento(1, "EQ-H", "E01",
                    "2025-01-04 23:00", None, estado="en_curso"),
        ])
        rango = ("2025-01-01 00:00", "2025-01-05 04:00")
        disp = disponibilidad_por_equipo(ev, rango)
        assert abs(disp["EQ-H"] - 100.0) < 0.01


# ---------------------------------------------------------------------------
# Ciclos
# ---------------------------------------------------------------------------

class TestCiclos:
    def test_solo_completadas(self):
        mis = pd.DataFrame([
            _mision(1, "EQ-A", "2025-01-01 08:00", "2025-01-01 08:02"),
            _mision(2, "EQ-A", "2025-01-01 09:00", "2025-01-01 09:02"),
            _mision(3, "EQ-A", "2025-01-01 10:00", "2025-01-01 10:02", estado="abortada"),
        ])
        c = ciclos_por_equipo(mis)
        assert c["EQ-A"] == 2

    def test_doble_cuna_stv_salida(self):
        mis = pd.DataFrame([
            _mision(1, "STV-S-01", "2025-01-01 08:00", "2025-01-01 08:01"),
            _mision(2, "STV-S-01", "2025-01-01 09:00", "2025-01-01 09:01"),
        ])
        eq = pd.DataFrame([
            {"id": "STV-S-01", "tipo": "STV", "zona": "anillo_salida",
             "estado_operativo": "operativo"},
        ])
        c = ciclos_por_equipo(mis, equipos=eq)
        assert c["STV-S-01"] == 4  # 2 misiones × 2 pallets


# ---------------------------------------------------------------------------
# Tiempo de ciclo
# ---------------------------------------------------------------------------

class TestTiempoCiclo:
    def test_duracion_correcta(self):
        mis = pd.DataFrame([
            _mision(1, "EQ-A", "2025-01-01 08:00:00", "2025-01-01 08:02:00"),  # 120 s
            _mision(2, "EQ-A", "2025-01-01 09:00:00", "2025-01-01 09:03:00"),  # 180 s
            _mision(3, "EQ-A", "2025-01-01 10:00:00", "2025-01-01 10:01:00", estado="abortada"),
        ])
        tc = tiempo_ciclo(mis)
        assert set(tc.values) == {120.0, 180.0}

    def test_unidad_minutos(self):
        mis = pd.DataFrame([
            _mision(1, "EQ-A", "2025-01-01 08:00:00", "2025-01-01 08:02:00"),
        ])
        tc = tiempo_ciclo(mis, unidad="minutos")
        assert abs(tc.iloc[0] - 2.0) < 0.001


# ---------------------------------------------------------------------------
# Posición en el momento del fallo
# ---------------------------------------------------------------------------

class TestPosicionEnFallo:
    def test_encuentra_mision_activa(self):
        ev = pd.DataFrame([
            _evento(1, "EQ-A", "E01", "2025-01-01 08:01:00", "2025-01-01 08:30:00"),
        ])
        mis = pd.DataFrame([
            _mision(10, "EQ-A", "2025-01-01 08:00:00", "2025-01-01 08:10:00",
                    pos_ini="P01-A03-C05"),
        ])
        resultado = posicion_en_fallo(ev, mis)
        assert resultado["posicion_inicial"].iloc[0] == "P01-A03-C05"

    def test_sin_mision_activa_es_nan(self):
        ev = pd.DataFrame([
            _evento(1, "EQ-A", "E01", "2025-01-01 09:00:00", "2025-01-01 09:30:00"),
        ])
        mis = pd.DataFrame([
            _mision(10, "EQ-A", "2025-01-01 08:00:00", "2025-01-01 08:10:00"),
        ])
        resultado = posicion_en_fallo(ev, mis)
        assert pd.isna(resultado["posicion_inicial"].iloc[0])


# ---------------------------------------------------------------------------
# Tasa de rechazo
# ---------------------------------------------------------------------------

class TestTasaRechazo:
    def test_global(self):
        mis = pd.DataFrame([
            {"id_mision": i, "id_equipo": "EQ-A",
             "estado": "completada" if i < 9 else "rechazada"}
            for i in range(1, 11)
        ])
        assert abs(tasa_rechazo(mis) - 0.2) < 0.001

    def test_agrupado(self):
        mis = pd.DataFrame([
            {"id_mision": 1, "id_equipo": "EQ-A", "estado": "completada"},
            {"id_mision": 2, "id_equipo": "EQ-A", "estado": "rechazada"},
            {"id_mision": 3, "id_equipo": "EQ-B", "estado": "completada"},
            {"id_mision": 4, "id_equipo": "EQ-B", "estado": "completada"},
        ])
        tr = tasa_rechazo(mis, agrupar_por="id_equipo")
        assert abs(tr["EQ-A"] - 0.5) < 0.001
        assert abs(tr["EQ-B"] - 0.0) < 0.001

    def test_misiones_vacias_no_explota(self):
        """Sin misiones la tasa global debe ser 0.0 (no ZeroDivisionError)."""
        mis = pd.DataFrame(columns=["id_mision", "id_equipo", "estado"])
        assert tasa_rechazo(mis) == 0.0


# ---------------------------------------------------------------------------
# Serie mensual
# ---------------------------------------------------------------------------

class TestSerieMensual:
    def test_suma_por_mes(self):
        df = pd.DataFrame({
            "ts": ["2025-01-15", "2025-01-20", "2025-02-10"],
            "valor": [10, 20, 5],
        })
        s = serie_mensual(df, "ts", "valor", agg="sum")
        assert s[1] == 30
        assert s[2] == 5

    def test_doce_meses_posibles(self):
        df = pd.DataFrame({
            "ts": pd.date_range("2025-01-01", periods=365, freq="D"),
            "valor": 1.0,
        })
        s = serie_mensual(df, "ts", "valor", agg="count")
        assert len(s) == 12


# ---------------------------------------------------------------------------
# kpis_globales (smoke test)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Disponibilidad mensual
# ---------------------------------------------------------------------------

class TestDisponibilidadMensual:
    def test_mes_sin_fallos_es_100(self):
        """Enero sin fallos → 100 %. Febrero con 10 h de fallo sobre ~100 h."""
        ev = pd.DataFrame([
            # Fallo de 10 h en febrero (feb tiene 672 h, pero usamos 100 h de calendario)
            _evento(1, "EQ-A", "E01",
                    "2025-02-01 00:00", "2025-02-01 10:00"),
        ])
        rango = ("2025-01-01", "2025-02-04 04:00")  # ene completo + ~100 h de feb
        s = disponibilidad_mensual(ev, rango)
        assert abs(s[1] - 100.0) < 0.01   # enero sin fallos

    def test_disponibilidad_mes_con_fallo(self):
        """Un equipo, 10 h de fallo sobre 100 h de calendario → ~90 %."""
        ev = pd.DataFrame([
            _evento(1, "EQ-A", "E01",
                    "2025-01-01 00:00", "2025-01-01 10:00"),
        ])
        rango = ("2025-01-01 00:00", "2025-01-05 04:00")  # exactamente 100 h
        s = disponibilidad_mensual(ev, rango)
        assert abs(s[1] - 90.0) < 0.01

    def test_cruce_de_mes(self):
        """
        Fallo de 3 h cruzando el límite ene→feb (23:00 ene-31 → 02:00 feb-01).
        El clip debe repartir: 1 h en enero y 2 h en febrero.
        Rango: enero completo + primeras 100 h de febrero.
        """
        ev = pd.DataFrame([
            _evento(1, "EQ-A", "E01",
                    "2025-01-31 23:00", "2025-02-01 02:00"),
        ])
        rango = ("2025-01-01 00:00", "2025-02-05 04:00")  # ene(744h) + ~100h feb
        s = disponibilidad_mensual(ev, rango)
        # enero: 1 h caído / 744 h → ~99.87 %
        assert s[1] < 100.0
        # febrero: 2 h caído / ~100 h → ~98 %
        assert s[2] < s[1]

    def test_rango_parcial_un_mes(self):
        """Rango acotado a 10 días de enero → solo índice 1, resto NaN."""
        ev = pd.DataFrame([
            _evento(1, "EQ-A", "E01",
                    "2025-01-05 08:00", "2025-01-05 09:00"),
        ])
        rango = ("2025-01-01", "2025-01-10")
        s = disponibilidad_mensual(ev, rango)
        assert 1 in s.index
        assert 2 not in s.index


# ---------------------------------------------------------------------------
class TestKpisGlobales:
    def test_estructura(self, eventos_simples):
        mis = pd.DataFrame([
            _mision(i, "EQ-A", f"2025-01-0{i} 08:00", f"2025-01-0{i} 08:02")
            for i in range(1, 4)
        ])
        eq = pd.DataFrame([
            {"id": "EQ-A", "tipo": "SRM", "zona": "pasillo",
             "estado_operativo": "operativo"}
        ])
        resultado = kpis_globales(eventos_simples, mis, eq, RANGO)
        assert set(resultado.keys()) == {
            "disponibilidad_media", "n_fallos", "mttr_medio",
            "mtbf_medio", "ciclos_totales",
        }
        assert resultado["ciclos_totales"] == 3
        assert resultado["n_fallos"] == 3

    def test_dataframes_vacios_no_explota(self):
        """Periodo sin actividad: todo el dict debe ser numérico, no NaN/inf."""
        import math
        ev = pd.DataFrame(columns=[
            "id_evento", "id_equipo", "codigo_error",
            "ts_inicio_fallo", "ts_recuperacion", "estado",
        ])
        mis = pd.DataFrame(columns=[
            "id_mision", "id_equipo", "posicion_inicial",
            "posicion_final", "ts_inicio", "ts_fin", "estado",
        ])
        eq = pd.DataFrame(columns=["id", "tipo", "zona", "estado_operativo"])
        resultado = kpis_globales(ev, mis, eq, RANGO)
        for clave, valor in resultado.items():
            assert not (isinstance(valor, float) and (math.isnan(valor) or math.isinf(valor))), \
                f"{clave} es NaN/inf con datos vacíos"
        assert resultado["n_fallos"] == 0
        assert resultado["ciclos_totales"] == 0

    def test_n_fallos_incluye_en_curso(self, eventos_con_en_curso):
        """n_fallos cuenta TODOS los eventos (incl. en_curso) para ser coherente con MTBF."""
        mis = pd.DataFrame([
            _mision(1, "EQ-B", "2025-01-01 08:00", "2025-01-01 08:02"),
        ])
        eq = pd.DataFrame([
            {"id": "EQ-B", "tipo": "SRM", "zona": "pasillo",
             "estado_operativo": "operativo"}
        ])
        resultado = kpis_globales(eventos_con_en_curso, mis, eq, RANGO)
        # 2 resueltos + 1 en_curso = 3
        assert resultado["n_fallos"] == 3


class TestDeltaVsPeriodoAnterior:
    def test_devuelve_none_si_no_hay_periodo_anterior(self):
        """Sin datos en el periodo anterior, todos los deltas son None."""
        ev = pd.DataFrame([
            _evento(1, "EQ-A", "E01", "2025-06-01 08:00", "2025-06-01 09:00"),
        ])
        mis = pd.DataFrame([
            _mision(1, "EQ-A", "2025-06-01 08:00", "2025-06-01 08:02"),
        ])
        rango = ("2025-06-01", "2025-06-30")
        delta = delta_vs_periodo_anterior(ev, mis, rango)
        assert delta["delta_disponibilidad"] is None

    def test_calcula_delta_con_periodo_anterior(self):
        """Datos en periodo actual y anterior: deltas deben ser numéricos."""
        ev_global = pd.DataFrame([
            _evento(1, "EQ-A", "E01", "2025-05-15 08:00", "2025-05-15 10:00"),  # prev
            _evento(2, "EQ-A", "E02", "2025-06-10 08:00", "2025-06-10 09:00"),  # act
        ])
        mis_global = pd.DataFrame([
            _mision(1, "EQ-A", "2025-05-15 08:00", "2025-05-15 08:02"),
            _mision(2, "EQ-A", "2025-06-10 08:00", "2025-06-10 08:02"),
        ])
        # Periodo "actual" = junio; previo = mayo
        ev_act = ev_global[ev_global["ts_inicio_fallo"] >= "2025-06-01"]
        mis_act = mis_global[mis_global["ts_inicio"] >= "2025-06-01"]
        rango = ("2025-06-01", "2025-06-30")
        delta = delta_vs_periodo_anterior(ev_act, mis_act, rango,
                                          eventos_global=ev_global,
                                          misiones_global=mis_global)
        assert delta["delta_n_fallos"] == 0  # 1 vs 1
        assert delta["delta_ciclos"] == 0


class TestEdgeCases:
    def test_multiples_en_curso(self):
        """Varios eventos en_curso del mismo equipo no deben sumar tiempo caído."""
        ev = pd.DataFrame([
            _evento(1, "EQ-Z", "E01",
                    "2025-01-01 00:00", "2025-01-01 05:00"),  # 5 h
            _evento(2, "EQ-Z", "E02",
                    "2025-01-02 00:00", None, estado="en_curso"),
            _evento(3, "EQ-Z", "E03",
                    "2025-01-03 00:00", None, estado="en_curso"),
        ])
        rango = ("2025-01-01 00:00", "2025-01-05 04:00")  # 100 h
        # Disponibilidad: solo 5 h de fallo resuelto → 95 %
        disp = disponibilidad_por_equipo(ev, rango)
        assert abs(disp["EQ-Z"] - 95.0) < 0.01
        # MTBF: (100 - 5) / 3 fallos = 31.66 h
        mtbf = mtbf_por_equipo(ev, rango, unidad="horas")
        assert abs(mtbf["EQ-Z"] - (95.0 / 3.0)) < 0.01

    def test_evento_completamente_fuera_de_rango_mensual(self):
        """Un evento que termina antes del rango global no debe afectar la disponibilidad."""
        ev = pd.DataFrame([
            _evento(1, "EQ-A", "E01",
                    "2024-12-15 10:00", "2024-12-15 12:00"),
        ])
        rango = ("2025-01-01", "2025-01-10")
        s = disponibilidad_mensual(ev, rango)
        # Enero está dentro del rango y sin eventos en él → 100 %
        if 1 in s.index:
            assert abs(s[1] - 100.0) < 0.01
