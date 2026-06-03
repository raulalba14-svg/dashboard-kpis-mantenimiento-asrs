"""
Generador de datos simulados para el proyecto AS/RS.

Uso:
    python scripts/generar_datos.py --semilla 42 --salida data/

Genera cuatro CSV coherentes entre sí:
    equipos.csv, tipos_error.csv, misiones.csv, eventos_incidencia.csv
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Catálogos estáticos
# ---------------------------------------------------------------------------

# Geometría del pasillo (alturas × columnas de doble fondo por cara).
N_PASILLOS    = 8
N_ALTURAS     = 16
N_COLUMNAS    = 48
N_STV         = 15   # vehículos del anillo único
N_TRAMOS      = 24   # tramos del anillo

# Cada código de error lleva su duración media de reparación (minutos).
# La duración real de cada fallo se sortea lognormal alrededor de esa media
# y se multiplica por un factor aleatorio adicional para más variabilidad.
TIPOS_ERROR = [
    ("E01", "Fallo encoder eje X",                40),
    ("E02", "Fallo encoder eje Y",                45),
    ("E03", "Desviación posición por láser",      30),
    ("E04", "Timeout comunicación PLC",           25),
    ("E05", "Pérdida heartbeat WCS",              60),
    ("E06", "Sobrecarga motor traslación",        90),
    ("E07", "Sobrecarga motor elevación",        110),
    ("E08", "Fallo variador de frecuencia",      180),
    ("E09", "Rotura cadena elevación",           360),
    ("E10", "Desgaste rodamiento traslación",    150),
    ("E11", "Fallo sensor fin de carrera",        20),
    ("E12", "Fallo telescópico de horquillas",    35),
    ("E13", "Fallo freno electromagnético",      120),
    ("E14", "Vibración excesiva mástil",         240),
    ("E15", "Desalineación guía mástil",         200),
    ("E16", "Fallo rueda motriz STV",            130),
    ("E17", "Desvío en transferencia de pallet",  25),
    ("E18", "Fallo batería / carga STV",          70),
]

# Probabilidad relativa de cada código por tipo de equipo (se normaliza).
_P_SRM = {
    "E01":0.13,"E02":0.11,"E03":0.10,"E04":0.08,"E05":0.04,
    "E06":0.09,"E07":0.09,"E08":0.05,"E09":0.04,"E10":0.08,
    "E11":0.06,"E12":0.05,"E13":0.04,"E14":0.02,"E15":0.02,
}
_P_STV = {
    "E04":0.12,"E05":0.05,"E10":0.10,"E11":0.10,"E13":0.06,
    "E16":0.18,"E17":0.16,"E18":0.13,"E06":0.06,"E08":0.04,
}

CODIGOS = [r[0] for r in TIPOS_ERROR]

def _norm(d: dict) -> np.ndarray:
    v = np.array([d.get(c, 0.0) for c in CODIGOS])
    return v / v.sum()

PROBS_ERROR = {"SRM": _norm(_P_SRM), "STV": _norm(_P_STV)}

# Dispersión lognormal alrededor de la duración media de cada código
DURACION_SIGMA = 0.6

# Multiplicador estacional por mes (índice 1..12)
ESTACIONALIDAD = np.array([0,
    1.00, 0.95, 1.00, 1.05, 1.05, 0.90,
    0.85, 0.75, 0.95, 1.10, 1.25, 1.30,
])

# Misiones completadas por día y equipo (base antes de estacionalidad).
# Un SRM combina almacenamiento y extracción dentro de su pasillo. Cada STV
# del anillo encadena transferencias cortas, con cadencia algo menor por
# vehículo para que el dataset total quede manejable.
CADENCIA_BASE = {"SRM": 140, "STV": 95}

# Tasa base de fallos por cada 1000 misiones
TASA_FALLOS = {"SRM": 2.2, "STV": 2.6}

FECHA_INICIO = pd.Timestamp("2025-01-01")
FECHA_FIN    = pd.Timestamp("2025-12-31")
SEGUNDOS_DIA = 86_400


# ---------------------------------------------------------------------------
# Generadores
# ---------------------------------------------------------------------------

def generar_tipos_error() -> pd.DataFrame:
    return pd.DataFrame(TIPOS_ERROR,
                        columns=["codigo","descripcion","duracion_media_min"])


def generar_equipos() -> pd.DataFrame:
    filas = (
        [(f"SRM-{i:02d}", "SRM", "pasillo", "operativo") for i in range(1, N_PASILLOS + 1)]
        + [(f"STV-{i:02d}", "STV", "anillo", "operativo") for i in range(1, N_STV + 1)]
    )
    return pd.DataFrame(filas, columns=["id", "tipo", "zona", "estado_operativo"])


def _pos_srm(rng: np.random.Generator, n: int) -> np.ndarray:
    p = rng.integers(1, N_PASILLOS + 1, n)
    a = rng.integers(1, N_ALTURAS + 1, n)
    c = rng.integers(1, N_COLUMNAS + 1, n)
    return np.array([f"P{pi:02d}-A{ai:02d}-C{ci:02d}" for pi, ai, ci in zip(p, a, c)])


def _pos_stv(rng: np.random.Generator, n: int) -> np.ndarray:
    """Posición de un STV en el anillo: tramo de origen → cabecera de pasillo."""
    t = rng.integers(1, N_TRAMOS + 1, n)
    return np.array([f"T{ti:02d}" for ti in t])


def generar_misiones(equipos: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    dias = pd.date_range(FECHA_INICIO, FECHA_FIN, freq="D")
    meses = dias.month
    epoch_dias = np.array([d.timestamp() for d in dias], dtype="int64")

    partes = []
    id_offset = 1

    for _, eq in equipos.iterrows():
        eid  = eq["id"]
        tipo = eq["tipo"]
        cad  = CADENCIA_BASE[tipo]

        # Número de misiones por día vectorizado
        medias = cad * ESTACIONALIDAD[meses]
        n_por_dia = rng.poisson(medias).astype(int)
        total = int(n_por_dia.sum())

        # Duración media de misión en segundos: el SRM hace un ciclo completo
        # en altura; el STV encadena transferencias más cortas en el anillo.
        dur_s = 120 if tipo == "SRM" else 45

        # Repetir epoch de cada día n_por_dia veces
        epochs_base = np.repeat(epoch_dias, n_por_dia)

        # Offset aleatorio dentro del día (segundos)
        offsets = rng.integers(0, SEGUNDOS_DIA, size=total)
        ts_inicio_s = epochs_base + offsets

        # Duración lognormal
        duraciones = np.maximum(10, rng.lognormal(np.log(dur_s), 0.4, size=total)).astype(int)
        ts_fin_s = ts_inicio_s + duraciones

        # Estado: la mayoría completadas, una pequeña fracción abortadas.
        r = rng.random(total)
        estado = np.where(r < 0.97, "completada", "abortada")

        # Posiciones según el tipo de equipo
        if tipo == "SRM":
            pos_ini = _pos_srm(rng, total)
            pos_fin = _pos_srm(rng, total)
        else:
            pos_ini = _pos_stv(rng, total)
            pos_fin = _pos_stv(rng, total)

        ids = np.arange(id_offset, id_offset + total)
        id_offset += total

        df = pd.DataFrame({
            "id_mision":       ids,
            "id_equipo":       eid,
            "posicion_inicial": pos_ini,
            "posicion_final":   pos_fin,
            "ts_inicio":        pd.to_datetime(ts_inicio_s, unit="s"),
            "ts_fin":           pd.to_datetime(ts_fin_s,   unit="s"),
            "estado":           estado,
        })
        partes.append(df)

    return pd.concat(partes, ignore_index=True).sort_values("ts_inicio").reset_index(drop=True)


def generar_eventos(
    misiones:    pd.DataFrame,
    tipos_error: pd.DataFrame,
    equipos:     pd.DataFrame,
    rng:         np.random.Generator,
) -> pd.DataFrame:
    duracion_map = dict(zip(tipos_error["codigo"], tipos_error["duracion_media_min"]))
    tipo_por_equipo = dict(zip(equipos["id"], equipos["tipo"]))

    comp = misiones[misiones["estado"] == "completada"].copy()
    comp["dur_s"] = (comp["ts_fin"] - comp["ts_inicio"]).dt.total_seconds().clip(lower=1).astype(int)

    partes = []
    id_evento = 1

    for eid, grp in comp.groupby("id_equipo"):
        tipo = tipo_por_equipo.get(eid, "SRM")
        n_mis  = len(grp)
        n_fallos = int(rng.poisson(TASA_FALLOS[tipo] * n_mis / 1000))
        if n_fallos == 0:
            continue

        n_fallos = min(n_fallos, n_mis)
        idx = rng.choice(n_mis, size=n_fallos, replace=False)
        sel = grp.iloc[idx]

        # ts_inicio_fallo dentro del intervalo de cada misión
        offsets = np.array([
            rng.integers(0, int(d)) for d in sel["dur_s"].values
        ])
        ts_fallos = sel["ts_inicio"].values + offsets.astype("timedelta64[s]")

        # Códigos de error según el tipo de equipo
        codigos = rng.choice(CODIGOS, size=n_fallos, p=PROBS_ERROR[tipo])

        # Duración del fallo: lognormal alrededor de la media del código,
        # con un multiplicador uniforme extra (0.7-1.4) para más variabilidad
        medias = np.array([duracion_map[c] for c in codigos], dtype=float)
        jitter = rng.uniform(0.7, 1.4, size=n_fallos)
        durs = np.maximum(
            1.0,
            rng.lognormal(np.log(medias), DURACION_SIGMA) * jitter,
        )
        ts_rec = ts_fallos + (durs * 60).astype("timedelta64[s]")

        # Acotar la recuperación al final del periodo del dataset:
        # un fallo que arranca el 31-dic a las 23h no debe recuperarse en 2026.
        limite = np.datetime64(FECHA_FIN + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))
        ts_rec = np.minimum(ts_rec, limite)

        # en_curso: ~5% de los fallos de nov-dic
        meses_fallo = pd.DatetimeIndex(ts_fallos).month
        en_curso = (meses_fallo >= 11) & (rng.random(n_fallos) < 0.05)

        ts_rec_final = np.where(en_curso, pd.NaT, ts_rec)
        estados = np.where(en_curso, "en_curso", "resuelto")

        df = pd.DataFrame({
            "id_evento":      np.arange(id_evento, id_evento + n_fallos),
            "id_equipo":      eid,
            "codigo_error":   codigos,
            "ts_inicio_fallo":ts_fallos,
            "ts_recuperacion":ts_rec_final,
            "estado":         estados,
        })
        partes.append(df)
        id_evento += n_fallos

    result = pd.concat(partes, ignore_index=True).sort_values("ts_inicio_fallo")
    # Reindexar id_evento tras el sort
    result["id_evento"] = np.arange(1, len(result) + 1)
    return result.reset_index(drop=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Genera datos simulados AS/RS")
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--salida",  type=str, default="data/")
    args = parser.parse_args()

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.semilla)

    print("Generando tipos_error...", end=" ")
    te = generar_tipos_error()
    te.to_csv(salida / "tipos_error.csv", index=False, encoding="utf-8")
    print(f"{len(te)} registros")

    print("Generando equipos...", end=" ")
    eq = generar_equipos()
    eq.to_csv(salida / "equipos.csv", index=False, encoding="utf-8")
    print(f"{len(eq)} registros")

    print("Generando misiones...", end=" ", flush=True)
    mis = generar_misiones(eq, rng)
    mis.to_csv(salida / "misiones.csv", index=False, encoding="utf-8")
    print(f"{len(mis):,} registros")

    print("Generando eventos_incidencia...", end=" ", flush=True)
    ev = generar_eventos(mis, te, eq, rng)
    ev.to_csv(salida / "eventos_incidencia.csv", index=False, encoding="utf-8")
    print(f"{len(ev):,} registros")

    print(f"\nDatos escritos en: {salida.resolve()}")


if __name__ == "__main__":
    main()
