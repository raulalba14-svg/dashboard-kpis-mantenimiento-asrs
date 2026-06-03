"""Tests unitarios de src/data_loader.py — aplicar_filtros_globales."""

import pandas as pd
import pytest

from src.data_loader import aplicar_filtros_globales


# ---------------------------------------------------------------------------
# Fixture: parque mínimo de 4 transelevadores SRM, todos en zona pasillo
# ---------------------------------------------------------------------------

@pytest.fixture
def tablas():
    equipos = pd.DataFrame([
        {"id": "SRM-01", "tipo": "SRM", "zona": "pasillo", "estado_operativo": "operativo"},
        {"id": "SRM-02", "tipo": "SRM", "zona": "pasillo", "estado_operativo": "operativo"},
        {"id": "SRM-03", "tipo": "SRM", "zona": "pasillo", "estado_operativo": "operativo"},
        {"id": "SRM-04", "tipo": "SRM", "zona": "pasillo", "estado_operativo": "operativo"},
    ])
    tipos_error = pd.DataFrame([
        {"codigo": "E01", "descripcion": "X", "duracion_media_min": 30},
    ])
    misiones = pd.DataFrame([
        {"id_mision": 1, "id_equipo": "SRM-01", "posicion_inicial": "A", "posicion_final": "B",
         "ts_inicio": pd.Timestamp("2025-01-15 08:00"), "ts_fin": pd.Timestamp("2025-01-15 08:02"),
         "estado": "completada"},
        {"id_mision": 2, "id_equipo": "SRM-02", "posicion_inicial": "A", "posicion_final": "B",
         "ts_inicio": pd.Timestamp("2025-06-10 09:00"), "ts_fin": pd.Timestamp("2025-06-10 09:02"),
         "estado": "completada"},
        {"id_mision": 3, "id_equipo": "SRM-03", "posicion_inicial": "A", "posicion_final": "B",
         "ts_inicio": pd.Timestamp("2025-06-10 09:00"), "ts_fin": pd.Timestamp("2025-06-10 09:02"),
         "estado": "completada"},
        {"id_mision": 4, "id_equipo": "SRM-04", "posicion_inicial": "A", "posicion_final": "B",
         "ts_inicio": pd.Timestamp("2025-12-20 10:00"), "ts_fin": pd.Timestamp("2025-12-20 10:02"),
         "estado": "completada"},
    ])
    eventos = pd.DataFrame([
        {"id_evento": 1, "id_equipo": "SRM-01", "codigo_error": "E01",
         "ts_inicio_fallo": pd.Timestamp("2025-01-15 08:00"),
         "ts_recuperacion": pd.Timestamp("2025-01-15 08:30"), "estado": "resuelto"},
        {"id_evento": 2, "id_equipo": "SRM-02", "codigo_error": "E01",
         "ts_inicio_fallo": pd.Timestamp("2025-06-10 09:00"),
         "ts_recuperacion": pd.Timestamp("2025-06-10 09:30"), "estado": "resuelto"},
        {"id_evento": 3, "id_equipo": "SRM-03", "codigo_error": "E01",
         "ts_inicio_fallo": pd.Timestamp("2025-06-10 09:00"),
         "ts_recuperacion": pd.Timestamp("2025-06-10 09:30"), "estado": "resuelto"},
        {"id_evento": 4, "id_equipo": "SRM-04", "codigo_error": "E01",
         "ts_inicio_fallo": pd.Timestamp("2025-12-20 10:00"),
         "ts_recuperacion": pd.Timestamp("2025-12-20 10:30"), "estado": "resuelto"},
    ])
    return {"equipos": equipos, "tipos_error": tipos_error,
            "misiones": misiones, "eventos": eventos}


# ---------------------------------------------------------------------------
# Sin filtros: identidad
# ---------------------------------------------------------------------------

class TestSinFiltros:
    def test_sin_filtros_devuelve_todo(self, tablas):
        out = aplicar_filtros_globales(tablas)
        assert len(out["equipos"]) == 4
        assert len(out["misiones"]) == 4
        assert len(out["eventos"]) == 4

    def test_no_muta_original(self, tablas):
        """El filtrado no debe modificar las tablas de entrada."""
        ids_originales = list(tablas["equipos"]["id"])
        aplicar_filtros_globales(tablas, tipos_equipo=["SRM"])
        assert list(tablas["equipos"]["id"]) == ids_originales


# ---------------------------------------------------------------------------
# Filtro por tipo de equipo
# ---------------------------------------------------------------------------

class TestFiltroTipo:
    def test_solo_srm(self, tablas):
        out = aplicar_filtros_globales(tablas, tipos_equipo=["SRM"])
        assert set(out["equipos"]["tipo"]) == {"SRM"}
        assert len(out["equipos"]) == 4

    def test_tipo_inexistente_vacia(self, tablas):
        """Filtrar por un tipo que no existe deja el parque vacío."""
        out = aplicar_filtros_globales(tablas, tipos_equipo=["NO_EXISTE"])
        assert out["equipos"].empty
        assert out["misiones"].empty
        assert out["eventos"].empty


# ---------------------------------------------------------------------------
# Filtro por zona
# ---------------------------------------------------------------------------

class TestFiltroZona:
    def test_solo_pasillo(self, tablas):
        out = aplicar_filtros_globales(tablas, zonas=["pasillo"])
        assert set(out["equipos"]["zona"]) == {"pasillo"}
        assert len(out["equipos"]) == 4

    def test_combina_tipo_y_zona(self, tablas):
        """tipos_equipo=[SRM] + zonas=[pasillo] → los 4 SRM."""
        out = aplicar_filtros_globales(
            tablas, tipos_equipo=["SRM"], zonas=["pasillo"]
        )
        assert set(out["equipos"]["id"]) == {"SRM-01", "SRM-02", "SRM-03", "SRM-04"}


# ---------------------------------------------------------------------------
# Filtro por rango de fechas
# ---------------------------------------------------------------------------

class TestFiltroFechas:
    def test_rango_junio(self, tablas):
        """Solo eventos/misiones de junio quedan dentro."""
        out = aplicar_filtros_globales(
            tablas, rango_fechas=("2025-06-01", "2025-06-30")
        )
        assert set(out["misiones"]["id_mision"]) == {2, 3}
        assert set(out["eventos"]["id_evento"]) == {2, 3}
        # Las tablas de equipos no se filtran por fecha
        assert len(out["equipos"]) == 4

    def test_fin_de_dia_inclusivo(self, tablas):
        """
        Una misión a las 10:00 del último día del rango debe incluirse.
        El código suma 1 día − 1 segundo al ts_fin para cubrir todo el día final.
        """
        out = aplicar_filtros_globales(
            tablas, rango_fechas=("2025-12-20", "2025-12-20")
        )
        assert 4 in set(out["misiones"]["id_mision"])

    def test_rango_vacio_no_explota(self, tablas):
        """Rango fuera del dataset → DataFrames vacíos pero válidos."""
        out = aplicar_filtros_globales(
            tablas, rango_fechas=("2024-01-01", "2024-01-31")
        )
        assert out["misiones"].empty
        assert out["eventos"].empty


# ---------------------------------------------------------------------------
# Tipos_error nunca se filtra
# ---------------------------------------------------------------------------

class TestTiposError:
    def test_catalogo_intacto(self, tablas):
        """tipos_error es un catálogo, no se filtra nunca."""
        out = aplicar_filtros_globales(
            tablas, tipos_equipo=["SRM"], zonas=["pasillo"],
            rango_fechas=("2025-06-01", "2025-06-30"),
        )
        assert len(out["tipos_error"]) == len(tablas["tipos_error"])
