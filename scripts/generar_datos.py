"""
Generador de datos simulados para el proyecto AS/RS.

Uso:
    python scripts/generar_datos.py --semilla 42 --salida data/

Genera cuatro CSV coherentes entre sí:
    equipos.csv, tipos_error.csv, misiones.csv, eventos_incidencia.csv
"""

import argparse
import bisect
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Permite importar desde src/ aunque el script se ejecute como
# `python scripts/generar_datos.py` (cwd = raíz del repo) o se cargue por ruta
# de fichero desde src/data_loader (spec_from_file_location).
_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from src.intervalos import union_solape_segundos

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

# Inspección de pallets en recepción: los rechazos los detecta un puesto de
# inspección genérico (origen INSP-xx) y un STV del anillo los transporta al
# puesto de rechazo. No revela la topología real de la instalación.
N_INSPECTORES = 4
POS_RECHAZO = "RECHAZO"
MOTIVOS_RECHAZO   = ["fuera_de_dimensiones", "exceso_de_peso", "hueco_pallet_incorrecto"]
P_MOTIVOS_RECHAZO = [0.45, 0.30, 0.25]

# Pedidos de expedición: todos los pedidos son iguales — un trailer completo
# de 28 pallets. Los STV del anillo tienen cuna simple (1 pallet por misión),
# así que un trailer son 28 misiones de salida. La expedición carga en paralelo
# en varios muelles: cada misión completada se asigna a un muelle y cada muelle
# llena sus trailers secuencialmente.
PALLETS_POR_PEDIDO   = 28
MISIONES_POR_PEDIDO  = PALLETS_POR_PEDIDO   # cuna simple: 1 pallet/misión
N_MUELLES_EXPEDICION = 6

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

        # Estado: la mayoría completadas; una fracción abortada y, en los STV,
        # una pequeña proporción rechazada (pallets que la inspección descarta).
        r = rng.random(total)
        if tipo == "STV":
            estado = np.where(r < 0.95, "completada",
                     np.where(r < 0.98, "abortada", "rechazada"))
        else:
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

        estados = np.where(en_curso, "en_curso", "resuelto")

        # ts_recuperacion como columna datetime real: los en_curso son NaT.
        # NO usar np.where(en_curso, pd.NaT, ts_rec): numpy degrada el array
        # datetime64 a int64 (nanosegundos crudos), y al volcarlo a CSV salen
        # enteros de 19 dígitos en vez de fechas, que luego revientan al
        # parsear con OutOfBoundsDatetime.
        ts_rec_final = pd.Series(pd.to_datetime(ts_rec))
        ts_rec_final[en_curso] = pd.NaT

        df = pd.DataFrame({
            "id_evento":      np.arange(id_evento, id_evento + n_fallos),
            "id_equipo":      eid,
            "codigo_error":   codigos,
            "ts_inicio_fallo":ts_fallos,
            "ts_recuperacion":ts_rec_final.values,
            "estado":         estados,
        })
        partes.append(df)
        id_evento += n_fallos

    result = pd.concat(partes, ignore_index=True).sort_values("ts_inicio_fallo")
    # Reindexar id_evento tras el sort
    result["id_evento"] = np.arange(1, len(result) + 1)
    return result.reset_index(drop=True)


def asignar_rechazos_inspeccion(
    misiones: pd.DataFrame,
    equipos:  pd.DataFrame,
    rng:      np.random.Generator,
) -> pd.DataFrame:
    """
    Post-procesado de las misiones rechazadas de STV.

    Un pallet rechazado no es un movimiento normal del anillo: lo detecta un
    puesto de inspección genérico en recepción (origen INSP-xx), viaja al
    puesto de rechazo (destino RECHAZO) transportado por un STV del anillo, y
    lleva un motivo de rechazo (dimensiones, peso o hueco de pallet incorrecto).

    Se aplica con un RNG independiente del generador principal para no
    alterar el resto del dataset: mismos conteos, estados, timestamps y
    eventos que sin este paso.
    """
    misiones["motivo_rechazo"] = ""

    ids_stv = set(equipos.loc[equipos["tipo"] == "STV", "id"])
    ids_anillo = equipos.loc[equipos["zona"] == "anillo", "id"].to_numpy()

    mask = (misiones["estado"] == "rechazada") & misiones["id_equipo"].isin(ids_stv)
    n = int(mask.sum())
    if n == 0:
        return misiones

    inspectores = rng.integers(1, N_INSPECTORES + 1, size=n)
    misiones.loc[mask, "id_equipo"]        = rng.choice(ids_anillo, size=n)
    misiones.loc[mask, "posicion_inicial"] = [f"INSP-{i:02d}" for i in inspectores]
    misiones.loc[mask, "posicion_final"]   = POS_RECHAZO
    misiones.loc[mask, "motivo_rechazo"]   = rng.choice(
        MOTIVOS_RECHAZO, size=n, p=P_MOTIVOS_RECHAZO
    )
    return misiones


def asignar_pedidos_expedicion(
    misiones: pd.DataFrame,
    equipos:  pd.DataFrame,
    rng:      np.random.Generator,
) -> pd.DataFrame:
    """
    Post-procesado de las misiones completadas del anillo (expedición).

    Todos los pedidos de expedición son iguales: un trailer completo de
    28 pallets. Los STV del anillo tienen cuna simple (1 pallet/misión), así
    que un trailer son 28 misiones. La expedición carga varios trailers en
    paralelo: cada misión se asigna a uno de los muelles y cada muelle llena
    sus trailers secuencialmente en orden cronológico, de modo que cualquier
    STV del anillo puede transportar pallets del mismo pedido. El tiempo de
    completado del pedido es el intervalo entre el inicio de su primera misión
    y el fin de la última. Las misiones sobrantes al cierre del año (trailer
    sin completar en cada muelle) quedan sin pedido.

    Se aplica con un RNG independiente del generador principal para no
    alterar el resto del dataset: mismos conteos, estados, timestamps y
    eventos que sin este paso.
    """
    misiones["id_pedido"] = ""
    misiones["muelle"] = ""
    misiones["origen_pasillo"] = ""

    ids_anillo = set(equipos.loc[equipos["zona"] == "anillo", "id"])
    mask = (misiones["estado"] == "completada") & misiones["id_equipo"].isin(ids_anillo)
    if not mask.any():
        return misiones

    sub = misiones.loc[mask, ["ts_inicio"]].sort_values("ts_inicio")
    n = len(sub)

    # Muelle aleatorio por misión; dentro de cada muelle, trailers de
    # MISIONES_POR_PEDIDO misiones consecutivas en el tiempo.
    muelle = rng.integers(0, N_MUELLES_EXPEDICION, size=n)
    etiqueta = np.full(n, -1, dtype=np.int64)
    pedido_global = 0
    for m in range(N_MUELLES_EXPEDICION):
        pos = np.flatnonzero(muelle == m)
        k = len(pos) // MISIONES_POR_PEDIDO
        completos = pos[: k * MISIONES_POR_PEDIDO]
        etiqueta[completos] = pedido_global + np.repeat(np.arange(k), MISIONES_POR_PEDIDO)
        pedido_global += k

    # Renumerar cronológicamente (por la primera misión de cada pedido)
    asignados = etiqueta >= 0
    primera = (
        pd.Series(np.flatnonzero(asignados))
        .groupby(etiqueta[asignados]).min().sort_values()
    )
    mapa = {et: f"PED-{i + 1:06d}" for i, et in enumerate(primera.index)}
    valores = np.full(n, "", dtype=object)
    valores[asignados] = pd.Series(etiqueta[asignados]).map(mapa).to_numpy()

    # Muelle como etiqueta legible (M-1..M-6); solo en las misiones con pedido,
    # para que la columna no sugiera muelle en misiones sueltas sin trailer.
    muelle_lbl = np.full(n, "", dtype=object)
    muelle_lbl[asignados] = [f"M-{m + 1}" for m in muelle[asignados]]

    # Pasillo SRM de origen de cada misión con pedido: el pallet se extrajo de
    # un pasillo del almacén (P01..P08, un SRM por pasillo) antes de llegar al
    # anillo. Permite el análisis de extremo a extremo origen→muelle.
    origen = np.full(n, "", dtype=object)
    pasillos = rng.integers(1, N_PASILLOS + 1, size=int(asignados.sum()))
    origen[asignados] = [f"P{p:02d}" for p in pasillos]

    misiones.loc[sub.index, "id_pedido"] = valores
    misiones.loc[sub.index, "muelle"] = muelle_lbl
    misiones.loc[sub.index, "origen_pasillo"] = origen
    return misiones


def aplicar_paradas_a_pedidos(
    misiones: pd.DataFrame,
    eventos:  pd.DataFrame,
    equipos:  pd.DataFrame,
) -> pd.DataFrame:
    """
    Post-procesado: el tiempo de completado de un pedido se alarga por las paradas
    que afectan a su recorrido de extremo a extremo, en dos etapas:

    1. **Anillo (STV)**: los STV trabajan EN SERIE en un mismo circuito, así que
       la avería de cualquier STV detiene el flujo y afecta a TODOS los pedidos
       que se cargan en ese momento.
    2. **Traslos (SRM) de origen**: cada pallet del pedido se extrajo de un pasillo
       (`origen_pasillo` → SRM-xx). Si ese SRM está parado durante la ventana del
       pedido, el pallet no llega a tiempo y retrasa el pedido. Solo afecta a los
       pedidos cuyos pallets vienen de ese pasillo.

    Para cada pedido se toma la UNIÓN de los intervalos de avería de
    (todos los STV del anillo) ∪ (los SRM de sus orígenes) solapados con su ventana
    [primera misión .. última] —averías simultáneas no cuentan doble— y ese retraso
    desplaza el `ts_fin` de su última misión, de modo que el tiempo de completado
    que calcula la app crece.

    Determinista (no usa RNG): el retraso sale del solape real avería×ventana.
    Solo toca misiones de anillo con pedido; el resto del dataset no cambia.
    """
    if "id_pedido" not in misiones.columns:
        return misiones

    ids_anillo = set(equipos.loc[equipos["zona"] == "anillo", "id"])
    mask_ped = (
        (misiones["estado"] == "completada")
        & misiones["id_equipo"].isin(ids_anillo)
        & misiones["id_pedido"].astype(str).str.startswith("PED-")
    )
    if not mask_ped.any():
        return misiones

    cols = ["id_pedido", "ts_inicio", "ts_fin"]
    if "origen_pasillo" in misiones.columns:
        cols.append("origen_pasillo")
    sub = misiones.loc[mask_ped, cols].copy()

    # Averías resueltas, separadas por origen: STV del anillo (comunes a todos los
    # pedidos, circuito en serie) y SRM (por pasillo de origen del pallet).
    ev = eventos[eventos["ts_recuperacion"].notna()].copy()
    ev_stv = ev[ev["id_equipo"].isin(ids_anillo)]
    averias_stv = sorted(zip(ev_stv["ts_inicio_fallo"].tolist(),
                             ev_stv["ts_recuperacion"].tolist()))
    av_stv_ini = [a[0] for a in averias_stv]

    # Averías de SRM indexadas por pasillo (SRM-03 sirve el pasillo P03).
    averias_por_pasillo: dict[str, list] = {}
    if "origen_pasillo" in sub.columns:
        ev_srm = ev[ev["id_equipo"].astype(str).str.startswith("SRM-")].copy()
        ev_srm["pasillo"] = "P" + ev_srm["id_equipo"].str.extract(r"SRM-(\d+)")[0]
        for pas, g in ev_srm.groupby("pasillo"):
            averias_por_pasillo[pas] = sorted(
                zip(g["ts_inicio_fallo"].tolist(), g["ts_recuperacion"].tolist())
            )

    ped = sub.groupby("id_pedido").agg(
        ts_ini=("ts_inicio", "min"),
        ts_fin=("ts_fin", "max"),
    ).sort_values("ts_ini")
    pasillos_por_pedido = (
        sub.groupby("id_pedido")["origen_pasillo"].agg(set)
        if "origen_pasillo" in sub.columns else {}
    )

    if not averias_stv and not averias_por_pasillo:
        return misiones

    retraso_s: dict[str, float] = {}
    for pid, row in ped.iterrows():
        p_ini, p_fin = row["ts_ini"], row["ts_fin"]
        # STV del anillo: candidatas acotadas por el inicio antes del fin del pedido.
        hi = bisect.bisect_right(av_stv_ini, p_fin)
        candidatas = [a for a in averias_stv[:hi] if a[1] > p_ini]
        # SRM de los pasillos de origen de este pedido.
        for pas in pasillos_por_pedido.get(pid, ()):
            candidatas += [
                a for a in averias_por_pasillo.get(pas, ())
                if a[0] < p_fin and a[1] > p_ini
            ]
        s = union_solape_segundos(candidatas, p_ini, p_fin)
        if s > 0:
            retraso_s[pid] = s

    if not retraso_s:
        return misiones

    # Aplicar el retraso al ts_fin de la última misión de cada pedido afectado.
    sub_aff = sub[sub["id_pedido"].isin(retraso_s)]
    idx_ultima = sub_aff.groupby("id_pedido")["ts_fin"].idxmax()
    for pid, idx in idx_ultima.items():
        misiones.at[idx, "ts_fin"] = (
            misiones.at[idx, "ts_fin"] + pd.Timedelta(seconds=retraso_s[pid])
        )
    return misiones


# ---------------------------------------------------------------------------
# Orquestación reutilizable
# ---------------------------------------------------------------------------

def generar_dataset(salida, semilla: int = 42, verbose: bool = False) -> None:
    """
    Genera los 4 CSV coherentes y los escribe en `salida`.

    Reutilizable desde el CLI (`main`) y desde la app (`src.data_loader`),
    de modo que la lógica de generación vive en un único sitio. La semilla
    fija (42 por defecto) garantiza un dataset reproducible bit-a-bit: los
    KPIs (MTTR, MTBF, disponibilidad) son idénticos en cada arranque.
    """
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(semilla)

    def _log(msg, **kw):
        if verbose:
            print(msg, **kw)

    _log("Generando tipos_error...", end=" ")
    te = generar_tipos_error()
    te.to_csv(salida / "tipos_error.csv", index=False, encoding="utf-8")
    _log(f"{len(te)} registros")

    _log("Generando equipos...", end=" ")
    eq = generar_equipos()
    eq.to_csv(salida / "equipos.csv", index=False, encoding="utf-8")
    _log(f"{len(eq)} registros")

    _log("Generando misiones...", end=" ", flush=True)
    mis = generar_misiones(eq, rng)
    _log(f"{len(mis):,} registros")

    _log("Generando eventos_incidencia...", end=" ", flush=True)
    ev = generar_eventos(mis, te, eq, rng)
    _log(f"{len(ev):,} registros")

    # RNG aparte: no perturba el stream principal (mismas cifras agregadas)
    _log("Asignando rechazos a la inspección de recepción...", end=" ", flush=True)
    rng_rechazos = np.random.default_rng(semilla + 1)
    mis = asignar_rechazos_inspeccion(mis, eq, rng_rechazos)
    _log(f"{int((mis['motivo_rechazo'] != '').sum()):,} rechazos")

    # RNG aparte por el mismo motivo: solo añade columnas de pedido
    _log("Agrupando la expedición en pedidos...", end=" ", flush=True)
    rng_pedidos = np.random.default_rng(semilla + 2)
    mis = asignar_pedidos_expedicion(mis, eq, rng_pedidos)
    _log(f"{mis.loc[mis['id_pedido'] != '', 'id_pedido'].nunique():,} pedidos")

    # Las paradas de los STV del anillo alargan el completado de los pedidos que
    # cargaban en ese momento (determinista, a partir del solape avería×pedido).
    _log("Aplicando paradas al tiempo de completado de pedidos...", end=" ", flush=True)
    mis = aplicar_paradas_a_pedidos(mis, ev, eq)
    _log("hecho")

    mis.to_csv(salida / "misiones.csv", index=False, encoding="utf-8")
    ev.to_csv(salida / "eventos_incidencia.csv", index=False, encoding="utf-8")

    _log(f"\nDatos escritos en: {salida.resolve()}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Genera datos simulados AS/RS")
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--salida",  type=str, default="data/")
    args = parser.parse_args()

    generar_dataset(args.salida, semilla=args.semilla, verbose=True)


if __name__ == "__main__":
    main()
