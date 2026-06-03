"""Tests de coherencia del dataset generado por scripts/generar_datos.py."""

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
SCRIPT = ROOT / "scripts" / "generar_datos.py"


@pytest.fixture(scope="module")
def dataset():
    """Genera el dataset en data/ si no existe, luego lo carga."""
    csvs = ["equipos.csv", "tipos_error.csv", "misiones.csv", "eventos_incidencia.csv"]
    if not all((DATA / f).exists() for f in csvs):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--semilla", "42", "--salida", str(DATA)],
            capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr

    equipos = pd.read_csv(DATA / "equipos.csv")
    tipos_error = pd.read_csv(DATA / "tipos_error.csv")
    misiones = pd.read_csv(DATA / "misiones.csv", parse_dates=["ts_inicio", "ts_fin"])
    eventos = pd.read_csv(
        DATA / "eventos_incidencia.csv",
        parse_dates=["ts_inicio_fallo", "ts_recuperacion"],
    )
    return {"equipos": equipos, "tipos_error": tipos_error,
            "misiones": misiones, "eventos": eventos}


def test_equipos_conteo(dataset):
    eq = dataset["equipos"]
    assert len(eq) == 23
    assert (eq["tipo"] == "SRM").sum() == 8
    assert (eq["tipo"] == "STV").sum() == 15
    srm = eq[eq["tipo"] == "SRM"]
    stv = eq[eq["tipo"] == "STV"]
    assert (srm["zona"] == "pasillo").all()
    assert (stv["zona"] == "anillo").all()


def test_fks_misiones(dataset):
    ids_equipos = set(dataset["equipos"]["id"])
    ids_en_misiones = set(dataset["misiones"]["id_equipo"])
    assert ids_en_misiones.issubset(ids_equipos), \
        f"FKs inválidas en misiones: {ids_en_misiones - ids_equipos}"


def test_fks_eventos(dataset):
    ids_equipos = set(dataset["equipos"]["id"])
    codigos = set(dataset["tipos_error"]["codigo"])

    ev = dataset["eventos"]
    ids_eventos_eq = set(ev["id_equipo"])
    assert ids_eventos_eq.issubset(ids_equipos), \
        f"id_equipo inválido en eventos: {ids_eventos_eq - ids_equipos}"

    codigos_eventos = set(ev["codigo_error"])
    assert codigos_eventos.issubset(codigos), \
        f"codigo_error inválido: {codigos_eventos - codigos}"


def test_ts_recuperacion_posterior(dataset):
    """ts_recuperacion debe ser >= ts_inicio_fallo cuando existe."""
    ev = dataset["eventos"]
    resueltos = ev[ev["estado"] == "resuelto"]
    assert resueltos["ts_recuperacion"].notna().all()
    delta = resueltos["ts_recuperacion"] - resueltos["ts_inicio_fallo"]
    assert (delta >= pd.Timedelta(0)).all(), "Hay recuperaciones anteriores al inicio del fallo"


def test_en_curso_sin_recuperacion(dataset):
    ev = dataset["eventos"]
    en_curso = ev[ev["estado"] == "en_curso"]
    assert en_curso["ts_recuperacion"].isna().all()


def test_fallo_dentro_de_mision(dataset):
    """Cada evento debe tener una misión del mismo equipo que contiene ts_inicio_fallo."""
    ev = dataset["eventos"].copy()
    mis = dataset["misiones"].copy()

    # Muestra aleatoria de 200 eventos para no tardar demasiado en CI
    sample = ev.sample(min(200, len(ev)), random_state=42)

    for _, row in sample.iterrows():
        eid = row["id_equipo"]
        t = row["ts_inicio_fallo"]
        mis_equipo = mis[mis["id_equipo"] == eid]
        dentro = mis_equipo[
            (mis_equipo["ts_inicio"] <= t) & (mis_equipo["ts_fin"] >= t)
        ]
        assert len(dentro) >= 1, (
            f"No se encontró misión activa para equipo {eid} en {t}"
        )


def test_estacionalidad_misiones(dataset):
    """Noviembre y diciembre deben tener más misiones que agosto."""
    mis = dataset["misiones"].copy()
    mis["mes"] = mis["ts_inicio"].dt.month
    por_mes = mis.groupby("mes").size()
    assert por_mes[11] > por_mes[8], "Nov debería superar a Ago"
    assert por_mes[12] > por_mes[8], "Dic debería superar a Ago"


def test_estados_misiones(dataset):
    mis = dataset["misiones"]
    estados = set(mis["estado"].unique())
    assert estados == {"completada", "abortada"}
    completadas_pct = (mis["estado"] == "completada").mean()
    assert 0.90 <= completadas_pct <= 0.99


def test_rango_fechas(dataset):
    mis = dataset["misiones"]
    assert mis["ts_inicio"].dt.year.unique().tolist() == [2025]


def test_recuperacion_dentro_del_periodo(dataset):
    """Una recuperación no debe caer fuera del 2025 (clip a FECHA_FIN)."""
    ev = dataset["eventos"]
    resueltos = ev[ev["estado"] == "resuelto"]
    fin_2025 = pd.Timestamp("2025-12-31 23:59:59")
    assert (resueltos["ts_recuperacion"] <= fin_2025).all(), \
        "Hay ts_recuperacion fuera del año del dataset"


def test_idempotencia(dataset, tmp_path):
    """Misma semilla → mismo número de eventos."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--semilla", "42", "--salida", str(tmp_path)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    ev2 = pd.read_csv(tmp_path / "eventos_incidencia.csv")
    assert len(ev2) == len(dataset["eventos"])
