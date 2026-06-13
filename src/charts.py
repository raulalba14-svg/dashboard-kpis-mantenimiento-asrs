"""
Helpers de visualización con plotly.

Todas las funciones devuelven plotly.graph_objects.Figure.
No llaman a st.plotly_chart — eso lo hacen las páginas.
"""

from __future__ import annotations

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.theme import (
    COLOR_CATEGORIA, COLOR_SEVERIDAD,
    PRIMARIO, PRIMARIO_CLARO, EXITO, ADVERTENCIA, CRITICO,
    GRIS_100, GRIS_300, GRIS_500, GRIS_700, GRIS_900,
)
from src.format import fmt_es


# ---------------------------------------------------------------------------
# Helpers legacy (mantenidos, pero con polish de tema)
# ---------------------------------------------------------------------------

def barras_ranking(
    serie: pd.Series,
    titulo: str,
    label_x: str = "",
    top_n: int | None = None,
    invertir: bool = True,
) -> go.Figure:
    """Barras horizontales ordenadas (ranking). Conservada para retro-compat."""
    if top_n:
        serie = serie.nlargest(top_n)
    df = serie.reset_index()
    df.columns = ["etiqueta", "valor"]
    df = df.sort_values("valor", ascending=not invertir)

    fig = px.bar(
        df, x="valor", y="etiqueta", orientation="h",
        title=titulo, labels={"valor": label_x, "etiqueta": ""},
        text_auto=".1f",
    )
    fig.update_traces(marker_color=PRIMARIO, textposition="outside",
                      textfont=dict(color=GRIS_700, size=11))
    fig.update_layout(yaxis={"categoryorder": "total ascending" if not invertir
                             else "total descending"})
    return fig


def serie_anual(
    serie: pd.Series,
    titulo: str,
    label_y: str = "",
    referencia: float | None = None,
) -> go.Figure:
    """Línea de 12 meses. Conservada para retro-compat."""
    meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    df = serie.reindex(range(1, 13)).reset_index()
    df.columns = ["mes", "valor"]
    df["mes_label"] = df["mes"].apply(lambda m: meses[m - 1])

    fig = px.line(df, x="mes_label", y="valor", title=titulo,
                  labels={"mes_label": "", "valor": label_y}, markers=True)
    fig.update_traces(line=dict(color=PRIMARIO, width=3),
                      marker=dict(size=8, color=PRIMARIO))
    if referencia is not None:
        fig.add_hline(y=referencia, line_dash="dash", line_color=GRIS_500,
                      annotation_text=f"Ref: {referencia:.1f}",
                      annotation_font_color=GRIS_700)
    return fig


def heatmap_posicion(df: pd.DataFrame, col_x: str, col_y: str,
                     titulo: str = "Distribución geográfica de fallos") -> go.Figure:
    """Mapa de calor por posición. Mantenido pero con escala corporativa."""
    pivot = df.groupby([col_y, col_x]).size().unstack(fill_value=0)
    fig = px.imshow(
        pivot, title=titulo,
        labels={"x": col_x, "y": col_y, "color": "Nº fallos"},
        aspect="auto",
        color_continuous_scale=[
            [0.0, "#EAF2F9"], [0.5, PRIMARIO_CLARO], [1.0, CRITICO],
        ],
    )
    return fig


def heatmap_alzado_pasillo(
    df: pd.DataFrame,
    pasillo: str,
    n_columnas: int = 48,
    n_alturas: int = 16,
    titulo: str = "",
) -> go.Figure:
    """
    Vista de alzado de un pasillo concreto: eje X = columna (profundidad),
    eje Y = altura. Cada celda es una ubicación física exacta (Pxx-Ayy-Czz).

    `df` debe contener columnas 'pasillo', 'altura', 'columna' (texto Pxx/Ayy/Czz).
    """
    sub = df[df["pasillo"] == pasillo]

    cols_idx = [f"C{i:02d}" for i in range(1, n_columnas + 1)]
    alts_idx = [f"A{i:02d}" for i in range(1, n_alturas + 1)]

    pivot = (
        sub.groupby(["altura", "columna"]).size()
        .unstack(fill_value=0)
        .reindex(index=alts_idx, columns=cols_idx, fill_value=0)
    )

    # Customdata con el código de celda completo para el hover
    celdas = [[f"{pasillo}-{a}-{c}" for c in cols_idx] for a in alts_idx]

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=cols_idx,
            y=alts_idx,
            customdata=celdas,
            colorscale=[
                [0.0, "#F4F7FA"], [0.25, "#DCE7F2"],
                [0.55, PRIMARIO_CLARO], [1.0, CRITICO],
            ],
            colorbar=dict(title="Nº fallos", thickness=12),
            hovertemplate="<b>%{customdata}</b><br>Nº fallos: %{z}<extra></extra>",
            xgap=1, ygap=1,
        )
    )
    fig.update_layout(
        title=titulo,
        xaxis=dict(title="Columna (profundidad)", side="bottom",
                   tickmode="array",
                   tickvals=[cols_idx[i] for i in range(0, n_columnas, 5)]),
        yaxis=dict(title="Altura", autorange="reversed"),  # A01 arriba
        height=440,
        margin=dict(l=60, r=20, t=20, b=50),
    )
    return fig


def histograma_tiempos(serie: pd.Series, titulo: str,
                       label_x: str = "Duración", nbins: int = 40) -> go.Figure:
    """Histograma simple. Conservado."""
    fig = px.histogram(serie, nbins=nbins, title=titulo,
                       labels={"value": label_x, "count": "Nº misiones"})
    fig.update_traces(marker_color=PRIMARIO_CLARO,
                      marker_line=dict(color=PRIMARIO, width=0.5))
    fig.update_layout(showlegend=False)
    return fig


def barras_categoria(serie: pd.Series,
                     titulo: str = "Fallos por categoría") -> go.Figure:
    """Barras por categoría de error con paleta semántica."""
    df = serie.reset_index()
    df.columns = ["categoria", "valor"]
    fig = px.bar(df, x="categoria", y="valor", title=titulo,
                 labels={"categoria": "", "valor": "Nº fallos"},
                 color="categoria", color_discrete_map=COLOR_CATEGORIA,
                 text_auto=True)
    fig.update_layout(showlegend=False)
    return fig


def scatter_ciclos_fallos(df: pd.DataFrame, col_ciclos: str = "ciclos",
                          col_fallos: str = "n_fallos", col_label: str = "id_equipo",
                          titulo: str = "Relación ciclos vs. fallos") -> go.Figure:
    """Scatter ciclos vs. nº de fallos por equipo, con cuadrantes y tendencia."""
    fig = go.Figure()

    # Puntos con etiqueta
    fig.add_trace(go.Scatter(
        x=df[col_ciclos], y=df[col_fallos],
        mode="markers+text",
        text=df[col_label], textposition="top center",
        textfont=dict(size=10, color=GRIS_700),
        marker=dict(size=10, color=PRIMARIO,
                    line=dict(color="white", width=1.5)),
        hovertemplate=("<b>%{text}</b><br>"
                       "Ciclos: %{x:,}<br>"
                       "Fallos: %{y}<extra></extra>"),
        showlegend=False,
    ))

    # Línea de tendencia (regresión lineal por mínimos cuadrados, sin statsmodels)
    if len(df) >= 2 and df[col_ciclos].nunique() >= 2:
        x = df[col_ciclos].astype(float).to_numpy()
        y = df[col_fallos].astype(float).to_numpy()
        slope, intercept = np.polyfit(x, y, 1)
        x_line = np.array([x.min(), x.max()])
        y_line = slope * x_line + intercept
        fig.add_trace(go.Scatter(
            x=x_line, y=y_line,
            mode="lines",
            line=dict(color=ADVERTENCIA, width=2, dash="dash"),
            hoverinfo="skip",
            showlegend=False,
            name="Tendencia",
        ))

    # Cuadrantes (líneas en mediana)
    x_med = float(df[col_ciclos].median())
    y_med = float(df[col_fallos].median())
    fig.add_vline(x=x_med, line_dash="dot", line_color=GRIS_300)
    fig.add_hline(y=y_med, line_dash="dot", line_color=GRIS_300)

    fig.update_layout(
        title=titulo,
        xaxis_title="Ciclos",
        yaxis_title="Nº fallos",
    )
    return fig


def tabla_kpis(df: pd.DataFrame, columnas: list[str] | None = None,
               titulo: str = "") -> go.Figure:
    """Tabla formateada (legacy)."""
    if columnas:
        df = df[columnas]
    fig = go.Figure(go.Table(
        header=dict(values=list(df.columns), fill_color=PRIMARIO,
                    font_color="white", align="center"),
        cells=dict(values=[df[c].tolist() for c in df.columns], align="center"),
    ))
    if titulo:
        fig.update_layout(title=titulo)
    return fig


# ---------------------------------------------------------------------------
# Helpers nuevos — sistema visual rediseñado
# ---------------------------------------------------------------------------

def gauge_disponibilidad(valor: float, referencia: float = 95.0,
                         titulo: str = "Disponibilidad media") -> go.Figure:
    """
    Indicador semicircular (gauge) para la disponibilidad de la instalación.

    valor: % de disponibilidad (0..100).
    referencia: línea de objetivo (por defecto 95%).
    """
    if valor >= 95:
        color_bar = EXITO
    elif valor >= 90:
        color_bar = ADVERTENCIA
    else:
        color_bar = CRITICO

    fig = go.Figure(go.Indicator(
        mode="gauge",
        value=valor,
        title=dict(text=titulo, font=dict(size=14, color=GRIS_700)),
        gauge=dict(
            axis=dict(range=[80, 100], tickwidth=1, tickcolor=GRIS_300,
                      tickfont=dict(color=GRIS_500, size=11)),
            bar=dict(color=color_bar, thickness=0.32),
            bgcolor="white",
            borderwidth=0,
            steps=[
                {"range": [80, 90], "color": "#FDECEA"},
                {"range": [90, 95], "color": "#FFF4E5"},
                {"range": [95, 100], "color": "#E8F5E9"},
            ],
            threshold=dict(
                line=dict(color=GRIS_900, width=3),
                thickness=0.85,
                value=referencia,
            ),
        ),
    ))
    # Número central en formato español (Plotly formatea en inglés de fábrica).
    fig.add_annotation(
        x=0.5, y=0.0, xref="paper", yref="paper",
        text=f"{fmt_es(valor, 2)} %",
        showarrow=False, font=dict(size=42, color=GRIS_900),
    )
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=260)
    return fig


def gauge_objetivo(
    valor: float,
    rango: tuple[float, float],
    umbral_verde: float,
    umbral_ambar: float,
    objetivo: float,
    titulo: str = "",
    sufijo: str = " %",
    menor_es_mejor: bool = False,
    decimales: int = 2,
) -> go.Figure:
    """
    Indicador semicircular (gauge) genérico contra un objetivo, con semáforo.

    - rango: (min, max) del eje.
    - umbral_verde / umbral_ambar: cortes del semáforo.
    - objetivo: línea de referencia (threshold).
    - menor_es_mejor: si True (p. ej. tasa de rechazo), valores bajos = verde y
      altos = rojo; los `steps` se pintan en consecuencia. Si False, al revés
      (como la disponibilidad).
    - decimales: decimales del número central (se muestra en formato español).

    El número central se renderiza como anotación con `fmt_es` (punto de miles,
    coma decimal); el `Indicator` de Plotly formatea en inglés, por eso se usa
    `mode="gauge"` sin número automático y se añade el texto formateado aparte.
    """
    if menor_es_mejor:
        if valor <= umbral_verde:
            color_bar = EXITO
        elif valor <= umbral_ambar:
            color_bar = ADVERTENCIA
        else:
            color_bar = CRITICO
        steps = [
            {"range": [rango[0], umbral_verde], "color": "#E8F5E9"},
            {"range": [umbral_verde, umbral_ambar], "color": "#FFF4E5"},
            {"range": [umbral_ambar, rango[1]], "color": "#FDECEA"},
        ]
    else:
        if valor >= umbral_verde:
            color_bar = EXITO
        elif valor >= umbral_ambar:
            color_bar = ADVERTENCIA
        else:
            color_bar = CRITICO
        steps = [
            {"range": [rango[0], umbral_ambar], "color": "#FDECEA"},
            {"range": [umbral_ambar, umbral_verde], "color": "#FFF4E5"},
            {"range": [umbral_verde, rango[1]], "color": "#E8F5E9"},
        ]

    fig = go.Figure(go.Indicator(
        mode="gauge",
        value=valor,
        title=dict(text=titulo, font=dict(size=14, color=GRIS_700)),
        gauge=dict(
            axis=dict(range=list(rango), tickwidth=1, tickcolor=GRIS_300,
                      tickfont=dict(color=GRIS_500, size=11)),
            bar=dict(color=color_bar, thickness=0.32),
            bgcolor="white",
            borderwidth=0,
            steps=steps,
            threshold=dict(
                line=dict(color=GRIS_900, width=3),
                thickness=0.85,
                value=objetivo,
            ),
        ),
    ))
    # Número central en formato español (Plotly no lo soporta de fábrica).
    fig.add_annotation(
        x=0.5, y=0.0, xref="paper", yref="paper",
        text=f"{fmt_es(valor, decimales)}{sufijo}",
        showarrow=False, font=dict(size=42, color=GRIS_900),
    )
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=260)
    return fig


def sparkline(serie: pd.Series, color: str | None = None,
              altura: int = 60) -> go.Figure:
    """
    Mini gráfico de línea sin ejes ni leyenda — para incrustar en tarjetas KPI.

    serie: valores numéricos en orden temporal.
    """
    color = color or PRIMARIO
    vals = serie.dropna().tolist()
    if not vals:
        vals = [0]
    fig = go.Figure(go.Scatter(
        y=vals,
        mode="lines",
        line=dict(color=color, width=2.4),
        fill="tozeroy",
        fillcolor=f"rgba(31, 78, 121, 0.10)",
        hovertemplate="%{y:.1f}<extra></extra>",
    ))
    fig.update_layout(
        height=altura,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=[min(vals) * 0.9 if min(vals) > 0 else min(vals),
                                          max(vals) * 1.05]),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def serie_anual_area(serie: pd.Series, titulo: str, label_y: str = "",
                     referencia: float | None = None,
                     color: str | None = None,
                     rango_y: tuple[float, float] | None = None) -> go.Figure:
    """
    Serie mensual con área bajo la curva (gradiente) y máx/mín marcados.

    serie: indexada por mes (1..12).
    rango_y: si se especifica, acota el eje Y a (min, max) para que variaciones
      pequeñas se aprecien; en ese caso el relleno baja hasta el borde inferior
      del rango (no hasta cero) para que el área no quede cortada.
    """
    color = color or PRIMARIO
    meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    df = serie.reindex(range(1, 13)).reset_index()
    df.columns = ["mes", "valor"]
    df["mes_label"] = df["mes"].apply(lambda m: meses[m - 1])

    fig = go.Figure()
    # Con eje acotado, el relleno hasta cero quedaría fuera de la vista; se usa
    # una baseline invisible en el borde inferior del rango y se rellena hacia ella.
    if rango_y is not None:
        fig.add_trace(go.Scatter(
            x=df["mes_label"], y=[rango_y[0]] * len(df),
            mode="lines", line=dict(width=0),
            hoverinfo="skip", showlegend=False,
        ))
    fig.add_trace(go.Scatter(
        x=df["mes_label"], y=df["valor"],
        mode="lines+markers",
        line=dict(color=color, width=3),
        marker=dict(size=8, color=color, line=dict(color="white", width=1.5)),
        fill="tozeroy" if rango_y is None else "tonexty",
        fillcolor=f"rgba(31, 78, 121, 0.08)",
        name=label_y,
        hovertemplate="<b>%{x}</b><br>%{y:.2f}<extra></extra>",
    ))

    # Marcar máx y mín
    valores = df.dropna(subset=["valor"])
    if len(valores) >= 2:
        idx_max = valores["valor"].idxmax()
        idx_min = valores["valor"].idxmin()
        for idx, etiqueta, col in [(idx_max, "máx", EXITO), (idx_min, "mín", CRITICO)]:
            r = df.loc[idx]
            fig.add_annotation(
                x=r["mes_label"], y=r["valor"],
                text=f"{etiqueta}: {r['valor']:.1f}",
                showarrow=True, arrowhead=2, arrowcolor=col, arrowsize=1,
                font=dict(color=col, size=11, family="Inter, sans-serif"),
                bgcolor="white", bordercolor=col, borderwidth=1, borderpad=3,
                ax=0, ay=-30 if etiqueta == "máx" else 30,
            )

    if referencia is not None:
        fig.add_hline(y=referencia, line_dash="dash", line_color=GRIS_500,
                      annotation_text=f"Media: {referencia:.1f}",
                      annotation_position="top right",
                      annotation_font_color=GRIS_700)

    fig.update_layout(
        title=titulo,
        xaxis_title="",
        yaxis_title=label_y,
        yaxis=dict(range=list(rango_y)) if rango_y is not None else None,
        showlegend=False,
        height=320,
    )
    return fig


def barras_ranking_umbrales(
    serie: pd.Series,
    titulo: str,
    label_x: str = "",
    umbral_alto: float = 95.0,
    umbral_bajo: float = 90.0,
    top_n: int | None = None,
    invertir: bool = True,
    media: float | None = None,
) -> go.Figure:
    """
    Ranking de barras horizontales coloreadas por umbrales semánticos.

    Útil para disponibilidad (% mayor = mejor): verde >=alto, ámbar entre, rojo <bajo.
    media: si se especifica, dibuja línea vertical de media.
    """
    if top_n:
        serie = serie.nlargest(top_n) if invertir else serie.nsmallest(top_n)
    df = serie.reset_index()
    df.columns = ["etiqueta", "valor"]
    df = df.sort_values("valor", ascending=not invertir)

    df["color"] = df["valor"].apply(
        lambda v: EXITO if v >= umbral_alto
                 else (ADVERTENCIA if v >= umbral_bajo else CRITICO)
    )

    fig = go.Figure(go.Bar(
        x=df["valor"], y=df["etiqueta"], orientation="h",
        marker=dict(color=df["color"].tolist(),
                    line=dict(color="white", width=0.5)),
        text=df["valor"].map("{:.2f}".format),
        textposition="outside",
        textfont=dict(color=GRIS_700, size=11),
        hovertemplate="<b>%{y}</b><br>" + label_x + ": %{x:.2f}<extra></extra>",
    ))

    if media is not None:
        fig.add_vline(x=media, line_dash="dash", line_color=GRIS_500,
                      annotation_text=f"Media: {media:.2f}",
                      annotation_position="top",
                      annotation_font_color=GRIS_700)

    fig.update_layout(
        title=titulo,
        xaxis_title=label_x,
        yaxis_title="",
        height=max(280, 22 * len(df) + 80),
        bargap=0.25,
    )
    return fig


def histograma_distribucion(
    serie: pd.Series,
    titulo: str,
    label_x: str = "Duración",
    nbins: int = 40,
    mostrar_percentiles: bool = True,
) -> go.Figure:
    """
    Histograma con percentiles P25/P50/P75 anotados.
    """
    fig = go.Figure(go.Histogram(
        x=serie, nbinsx=nbins,
        marker=dict(color=PRIMARIO_CLARO,
                    line=dict(color=PRIMARIO, width=0.5)),
        hovertemplate="Rango: %{x}<br>Frecuencia: %{y}<extra></extra>",
    ))

    if mostrar_percentiles and len(serie) > 0:
        p25, p50, p75 = serie.quantile([0.25, 0.50, 0.75]).tolist()
        for p, etq, col in [(p25, "P25", GRIS_500),
                            (p50, "P50", PRIMARIO),
                            (p75, "P75", ADVERTENCIA)]:
            fig.add_vline(
                x=p, line_dash="dash", line_color=col,
                annotation_text=f"{etq}: {p:.1f}",
                annotation_position="top",
                annotation_font_color=col,
                annotation_font_size=11,
            )

    fig.update_layout(
        title=titulo,
        xaxis_title=label_x,
        yaxis_title="Frecuencia",
        showlegend=False,
        bargap=0.05,
    )
    return fig


def plano_almacen(
    fallos_pasillos: dict[int, int],
    fallos_stv: dict[int, int] | None = None,
    n_pasillos: int = 8,
    n_stv: int = 15,
    dias_periodo: float = 365.0,
    titulo: str = "Plano de la instalación — concentración de fallos",
) -> go.Figure:
    """
    Sinóptico esquemático del almacén AS/RS.

    8 pasillos en paralelo arriba, cada uno servido por su transelevador
    (SRM-XX), apoyados sobre un anillo único cerrado (circuito rectangular de
    esquinas redondeadas) situado debajo, que alimenta las cabeceras de los
    pasillos. Sobre el recorrido del anillo se distribuyen los 15 vehículos de
    transferencia (STV-XX) como cajas con su ID y nº de fallos.

    El color de cada equipo es un SEMÁFORO DE SALUD basado en su TASA de fallos
    (fallos/día), no en el nº absoluto ni en "el peor del grupo". Así significa
    lo mismo sea cual sea el rango de fechas: 130 fallos/año = sano (verde);
    los mismos 130 en una semana = crítico (rojo). Los cortes por tipo de
    equipo están en config.UMBRALES_TASA_FALLOS.

    Parámetros:
        fallos_pasillos: {pasillo (1..n_pasillos): n_fallos}  → SRM-XX
        fallos_stv:      {stv     (1..n_stv):      n_fallos}  → STV-XX
        dias_periodo:    nº de días del rango analizado (para la tasa fallos/día)
    """
    from src.config import UMBRALES_TASA_FALLOS

    fallos_stv = fallos_stv or {}
    fig = go.Figure()
    dias = max(float(dias_periodo), 1.0)

    def _color(v: int, tipo: str) -> str:
        """Color-semáforo según la tasa de fallos/día frente a los umbrales
        absolutos del tipo de equipo. Verde = sano · ámbar = vigilar ·
        rojo = fuera de umbral. Sin fallos → azul muy claro (neutro)."""
        if v <= 0:
            return "#EAF2F9"
        verde, ambar = UMBRALES_TASA_FALLOS.get(tipo, (0.40, 0.55))
        tasa = v / dias
        if tasa < verde:
            return EXITO
        elif tasa < ambar:
            return ADVERTENCIA
        else:
            return CRITICO

    # Texto en blanco sobre fondos oscuros (verde/rojo), gris sobre los claros.
    _TXT_OSCURO = {EXITO, CRITICO}
    def _txt_color(fill: str) -> str:
        return "white" if fill in _TXT_OSCURO else GRIS_900

    paso = 1.4          # separación horizontal entre pasillos
    x0_base = 1.0
    ancho_pasillos = n_pasillos * paso
    xc_total = x0_base + ancho_pasillos / 2 - 0.3

    # ----- Pasillos SRM (fila superior, apoyados sobre el anillo) -----
    y_pas_top = 9.8
    y_pas_bot = 4.8          # base de los pasillos = borde superior del anillo
    yc_pas = (y_pas_top + y_pas_bot) / 2
    for p in range(1, n_pasillos + 1):
        v = fallos_pasillos.get(p, 0)
        x0 = x0_base + (p - 1) * paso
        x1 = x0 + 1.0
        xc = (x0 + x1) / 2

        fill = _color(v, "SRM")
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y_pas_bot, y1=y_pas_top,
                      line=dict(color="white", width=1.5), fillcolor=fill)
        # ID en vertical (la caja del pasillo es alta y estrecha): así nunca se
        # solapa con el pasillo vecino aunque el plano se escale a un móvil.
        fig.add_annotation(
            x=xc, y=y_pas_top - 0.55,
            text=f"SRM-{p:02d}", textangle=-90,
            showarrow=False, yanchor="top",
            font=dict(size=10.5, color=_txt_color(fill)),
        )
        # Nº de fallos grande y horizontal, centrado en la caja.
        fig.add_annotation(
            x=xc, y=yc_pas - 0.6,
            text=f"<b>{v}</b>",
            showarrow=False,
            font=dict(size=13, color=_txt_color(fill)),
        )
        fig.add_trace(go.Scatter(
            x=[xc], y=[yc_pas],
            mode="markers", marker=dict(opacity=0, size=30),
            showlegend=False,
            hovertemplate=f"<b>Pasillo P{p:02d} · SRM-{p:02d}</b><br>{v:,} fallos<extra></extra>",
        ))

    # ----- Anillo único cerrado (circuito rectangular redondeado, abajo) -----
    # El borde superior coincide con la base de los pasillos (y_pas_bot): el
    # anillo alimenta las cabeceras. Los STV se reparten por todo el perímetro.
    rx_l = x0_base - 0.8                       # extremo izquierdo del circuito
    rx_r = x0_base + ancho_pasillos - 0.2      # extremo derecho
    ry_top = y_pas_bot                         # borde superior = base pasillos
    ry_bot = -1.6                              # borde inferior (alto para los STV)
    r_cor = 0.9                                # radio de las esquinas

    def _circuito(xl, xr, yb, yt, rc, n=260):
        """Perímetro de un rectángulo de esquinas redondeadas (sentido horario
        desde el centro del lado superior)."""
        # Tramos rectos + 4 cuartos de círculo. Devuelve (x, y) cerrados.
        cx_tl, cy_tl = xl + rc, yt - rc
        cx_tr, cy_tr = xr - rc, yt - rc
        cx_br, cy_br = xr - rc, yb + rc
        cx_bl, cy_bl = xl + rc, yb + rc
        nq = n // 4
        a_tr = np.linspace(np.pi / 2, 0, nq)
        a_br = np.linspace(0, -np.pi / 2, nq)
        a_bl = np.linspace(-np.pi / 2, -np.pi, nq)
        a_tl = np.linspace(np.pi, np.pi / 2, nq)
        xs = np.concatenate([
            np.array([cx_tl, cx_tr]), cx_tr + rc * np.cos(a_tr),
            np.array([xr, xr]), cx_br + rc * np.cos(a_br),
            np.array([cx_br, cx_bl]), cx_bl + rc * np.cos(a_bl),
            np.array([xl, xl]), cx_tl + rc * np.cos(a_tl),
        ]).astype(float)
        ys = np.concatenate([
            np.array([yt, yt]), cy_tr + rc * np.sin(a_tr),
            np.array([cy_tr, cy_br]), cy_br + rc * np.sin(a_br),
            np.array([yb, yb]), cy_bl + rc * np.sin(a_bl),
            np.array([cy_bl, cy_tl]), cy_tl + rc * np.sin(a_tl),
        ]).astype(float)
        return xs, ys

    x_ring, y_ring = _circuito(rx_l, rx_r, ry_bot, ry_top, r_cor)
    # Pista: dos trazos para dar sensación de carril doble. Las esquinas ya van
    # redondeadas por geometría, así que no usamos shape="spline" (su soporte
    # varía entre versiones de Plotly y rompía el render en Streamlit Cloud).
    for w, col in ((12, "#CBD5E1"), (6, "#F9FAFB")):
        fig.add_trace(go.Scatter(
            x=x_ring.tolist(), y=y_ring.tolist(), mode="lines",
            line=dict(color=col, width=w),
            hoverinfo="skip", showlegend=False,
        ))

    # ----- 15 STV como cajas sobre el recorrido del circuito -----
    # Se reparten por los tres lados accesibles (el superior lo ocupan los
    # pasillos): bajando por la izquierda, a lo largo del lado inferior y
    # subiendo por la derecha. Calculamos centros explícitos para que queden
    # equiespaciados y sin solaparse.
    bw, bh = 0.6, 0.5        # media-anchura / media-altura de la caja STV
    x_left = rx_l            # carril izquierdo
    x_right = rx_r           # carril derecho
    y_low = ry_bot           # carril inferior
    # Repartimos por los tres lados accesibles. Los laterales son cortos, así
    # que ponemos menos ahí (4) y el grueso en el lado inferior (7): 4+7+4=15.
    n_izq = 4
    n_der = 4
    n_inf = n_stv - n_izq - n_der

    # Cada centro lleva también el lado al que pertenece ("izq"/"inf"/"der"),
    # para colocar la etiqueta del ID fuera de la caja, sobre el fondo claro.
    centros = []
    # Lado izquierdo (de arriba hacia abajo), sin tocar las esquinas extremas.
    ys_izq = np.linspace(ry_top - r_cor - 0.3, ry_bot + r_cor + 0.3, n_izq)
    for yy in ys_izq:
        centros.append((x_left, yy, "izq"))
    # Lado inferior (izquierda → derecha), entre las dos esquinas.
    xs_inf = np.linspace(rx_l + r_cor + 0.4, rx_r - r_cor - 0.4, n_inf)
    for xx in xs_inf:
        centros.append((xx, y_low, "inf"))
    # Lado derecho (de abajo hacia arriba).
    ys_der = np.linspace(ry_bot + r_cor + 0.3, ry_top - r_cor - 0.3, n_der)
    for yy in ys_der:
        centros.append((x_right, yy, "der"))

    for i in range(n_stv):
        s = i + 1
        v = fallos_stv.get(s, 0)
        col = _color(v, "STV")
        cx, cy, lado = centros[i]
        fig.add_shape(type="rect",
                      x0=cx - bw, x1=cx + bw, y0=cy - bh, y1=cy + bh,
                      line=dict(color="white", width=1.5), fillcolor=col)
        # Dentro de la caja: solo el nº de fallos, grande y en negrita.
        fig.add_annotation(
            x=cx, y=cy, text=f"<b>{v}</b>",
            showarrow=False,
            font=dict(size=13, color=_txt_color(col)),
        )
        # Fuera de la caja: el ID, en gris sobre el fondo claro (alto contraste).
        if lado == "izq":
            lx, ly, xa, ya = cx - bw - 0.18, cy, "right", "middle"
        elif lado == "der":
            lx, ly, xa, ya = cx + bw + 0.18, cy, "left", "middle"
        else:  # inferior → etiqueta debajo
            lx, ly, xa, ya = cx, cy - bh - 0.16, "center", "top"
        fig.add_annotation(
            x=lx, y=ly, text=f"STV-{s:02d}",
            showarrow=False, xanchor=xa, yanchor=ya,
            font=dict(size=10.5, color=GRIS_700),
        )
        fig.add_trace(go.Scatter(
            x=[cx], y=[cy], mode="markers", marker=dict(opacity=0, size=24),
            showlegend=False,
            hovertemplate=f"<b>STV-{s:02d}</b><br>{v:,} fallos<extra></extra>",
        ))

    # ----- Rótulos -----
    fig.add_annotation(x=xc_total, y=y_pas_top + 0.6,
                       text=f"<b>{n_pasillos} pasillos · 1 transelevador por pasillo · 16 alturas</b>",
                       showarrow=False, font=dict(size=12, color=GRIS_700))
    fig.add_annotation(x=xc_total, y=(ry_top + ry_bot) / 2,
                       text=f"<b>Anillo único de STV · {n_stv} vehículos</b>",
                       showarrow=False, font=dict(size=11, color=GRIS_500))

    # ----- Leyenda manual (semáforo de salud por tasa de fallos/día) -----
    leyenda_y = ry_bot - 2.0
    leyenda_items = [("Sano", EXITO),
                     ("Vigilar", ADVERTENCIA),
                     ("Crítico", CRITICO)]
    paso_ley = 2.4
    lx0 = xc_total - (len(leyenda_items) * paso_ley) / 2 + 0.3
    for i, (etq, col) in enumerate(leyenda_items):
        fig.add_shape(
            type="rect",
            x0=lx0 + i * paso_ley, x1=lx0 + 0.32 + i * paso_ley,
            y0=leyenda_y, y1=leyenda_y + 0.35,
            line=dict(color="white", width=0),
            fillcolor=col,
        )
        fig.add_annotation(
            x=lx0 + 0.45 + i * paso_ley, y=leyenda_y + 0.18,
            text=etq, showarrow=False,
            font=dict(size=11, color=GRIS_700), xanchor="left",
        )

    # `fixedrange=True` evita que el gráfico capture los gestos táctiles: en
    # móvil el scroll de la página pasa limpio a través del plano. El sinóptico
    # ya queda legible sin zoom (IDs en vertical, sin solapes), así que no hace
    # falta zoom táctil que dificultaría desplazarse.
    fig.update_layout(
        title=titulo,
        xaxis=dict(range=[rx_l - 1.8, rx_r + 1.8], showgrid=False,
                   zeroline=False, showticklabels=False, fixedrange=True),
        yaxis=dict(range=[leyenda_y - 0.6, y_pas_top + 1.3], showgrid=False,
                   zeroline=False, showticklabels=False, fixedrange=True,
                   scaleanchor="x", scaleratio=0.7),
        height=600,
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=False,
        plot_bgcolor="#F9FAFB",
    )
    return fig


def barras_horizontales(
    serie: pd.Series,
    titulo: str = "",
    label_x: str = "",
    color: str = PRIMARIO,
    color_fn=None,
    formato_valor: str = "{:,.0f}",
    top_n: int | None = None,
) -> go.Figure:
    """
    Barras horizontales ordenadas por valor (mayor arriba), con el valor
    anotado al final de cada barra.

    Pensado para rankings simples: nº de fallos por tipo, horas de parada por
    tipo, etc. `formato_valor` controla la etiqueta y el hover (p. ej.
    "{:,.0f}" para enteros, "{:,.1f} h" para horas).

    Color: por defecto un color sólido del tema. Si se pasa `color_fn` (una
    función valor -> color), se colorea cada barra según su valor; se aplica
    tras ordenar, así que el color siempre corresponde a su barra.
    """
    s = serie.dropna().sort_values(ascending=True)  # ascending: mayor arriba en barh
    if top_n:
        s = s.tail(top_n)

    textos = [formato_valor.format(v) for v in s.values]
    color_barras = [color_fn(v) for v in s.values] if color_fn else color

    fig = go.Figure(go.Bar(
        x=s.values, y=s.index.tolist(), orientation="h",
        marker=dict(color=color_barras, line=dict(color="white", width=0.5)),
        text=textos, textposition="outside",
        textfont=dict(color=GRIS_700, size=11),
        hovertemplate="<b>%{y}</b><br>" + label_x + ": %{text}<extra></extra>",
    ))
    fig.update_layout(
        title=titulo,
        xaxis_title=label_x,
        yaxis_title="",
        height=max(300, 26 * len(s) + 90),
        bargap=0.22,
        margin=dict(r=60),  # espacio para la etiqueta de valor fuera de la barra
    )
    return fig


def donut_categoria(serie: pd.Series, titulo: str = "",
                    color_map: dict | None = None) -> go.Figure:
    """
    Donut chart con la paleta semántica por defecto.
    """
    df = serie.reset_index()
    df.columns = ["categoria", "valor"]
    color_map = color_map or COLOR_CATEGORIA
    colores = [color_map.get(c, PRIMARIO_CLARO) for c in df["categoria"]]

    total = df["valor"].sum()
    fig = go.Figure(go.Pie(
        labels=df["categoria"], values=df["valor"],
        hole=0.62,
        marker=dict(colors=colores, line=dict(color="white", width=2)),
        textinfo="label+percent",
        textposition="outside",
        hovertemplate="<b>%{label}</b><br>%{value:,} rechazos<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        title=titulo,
        showlegend=False,
        annotations=[dict(
            text=f"<b>{int(total):,}</b><br><span style='font-size:11px;color:{GRIS_500}'>Total</span>",
            x=0.5, y=0.5, font=dict(size=18, color=GRIS_900),
            showarrow=False,
        )],
        height=340,
    )
    return fig


def dual_axis(
    serie_a: pd.Series, label_a: str, color_a: str,
    serie_b: pd.Series, label_b: str, color_b: str,
    titulo: str,
) -> go.Figure:
    """
    Línea+barras en dos ejes Y (p. ej. TC medio vs. throughput).
    Ambas series indexadas por el mismo eje X (mes 1..12).
    """
    meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    x = [meses[m - 1] for m in serie_a.index]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x, y=serie_a.values, name=label_a,
        marker_color=color_a, opacity=0.78,
        yaxis="y", hovertemplate=f"{label_a}: %{{y:.1f}}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=serie_b.values, name=label_b,
        mode="lines+markers", line=dict(color=color_b, width=3),
        marker=dict(size=8), yaxis="y2",
        hovertemplate=f"{label_b}: %{{y:.1f}}<extra></extra>",
    ))
    fig.update_layout(
        title=titulo,
        xaxis=dict(title=""),
        yaxis=dict(title=label_a, color=color_a, gridcolor="#E4E7EC"),
        yaxis2=dict(title=label_b, color=color_b, overlaying="y",
                    side="right", showgrid=False),
        legend=dict(orientation="h", y=1.08, x=0),
        height=340,
    )
    return fig


def evolucion_dos_lineas(
    serie_a: pd.Series, label_a: str, color_a: str,
    serie_b: pd.Series, label_b: str, color_b: str,
    titulo: str, label_y: str = "",
) -> go.Figure:
    """Dos series mensuales superpuestas con leyenda."""
    meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    fig = go.Figure()
    for serie, label, color in [(serie_a, label_a, color_a),
                                 (serie_b, label_b, color_b)]:
        s = serie.reindex(range(1, 13))
        fig.add_trace(go.Scatter(
            x=[meses[i - 1] for i in s.index],
            y=s.values,
            mode="lines+markers",
            name=label,
            line=dict(color=color, width=3),
            marker=dict(size=8, color=color, line=dict(color="white", width=1.5)),
            hovertemplate=f"<b>{label}</b><br>%{{x}}: %{{y:.2f}}<extra></extra>",
        ))
    fig.update_layout(
        title=titulo,
        xaxis_title="",
        yaxis_title=label_y,
        legend=dict(orientation="h", y=1.08, x=0),
        height=340,
    )
    return fig


def evolucion_lineas_categoria(
    series: dict[str, pd.Series],
    titulo: str = "",
    label_y: str = "",
    color_map: dict[str, str] | None = None,
) -> go.Figure:
    """
    Varias series mensuales con leyenda, una línea de color por categoría.

    `series` es un dict {categoría: serie mensual indexada por mes 1..12}.
    Pensado para pocas categorías con identidad propia (p. ej. motivos de
    rechazo).
    """
    meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    x_meses = list(range(1, 13))
    paleta = [PRIMARIO, ADVERTENCIA, PRIMARIO_CLARO, CRITICO, EXITO]

    fig = go.Figure()
    for i, (categoria, serie) in enumerate(series.items()):
        color = (color_map or {}).get(categoria, paleta[i % len(paleta)])
        s = serie.reindex(x_meses)
        fig.add_trace(go.Scatter(
            x=[meses[m - 1] for m in x_meses],
            y=s.values,
            mode="lines+markers",
            name=categoria,
            line=dict(color=color, width=3),
            marker=dict(size=7, color=color, line=dict(color="white", width=1.5)),
            hovertemplate=f"<b>{categoria}</b><br>%{{x}}: %{{y:,.0f}}<extra></extra>",
        ))

    fig.update_layout(
        title=titulo,
        xaxis_title="",
        yaxis_title=label_y,
        legend=dict(orientation="h", y=1.10, x=0),
        height=360,
    )
    return fig


def kpi_card_html(label: str, valor: str, delta: str | None = None,
                  delta_positivo: bool | None = None,
                  icono: str = "") -> str:
    """
    Devuelve HTML de una tarjeta KPI estilo Linear/Stripe.
    Diseñada para que la página haga st.markdown(html, unsafe_allow_html=True).
    """
    if delta is None:
        delta_html = ""
    else:
        color = EXITO if delta_positivo else (CRITICO if delta_positivo is False else GRIS_500)
        flecha = "▲" if delta_positivo else ("▼" if delta_positivo is False else "—")
        delta_html = (
            f'<div style="color:{color};font-size:0.85rem;font-weight:500;'
            f'margin-top:4px;">{flecha} {delta}</div>'
        )

    return f"""
    <div style="
        background: #F9FAFB;
        border: 1px solid #E4E7EC;
        border-radius: 10px;
        padding: 16px 18px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
        height: 100%;
    ">
        <div style="color:{GRIS_500};font-size:0.78rem;font-weight:500;
                    text-transform:uppercase;letter-spacing:0.04em;
                    margin-bottom:6px;">{icono} {label}</div>
        <div style="color:{GRIS_900};font-size:1.65rem;font-weight:700;
                    line-height:1.1;">{valor}</div>
        {delta_html}
    </div>
    """
