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
    n_columnas: int = 60,
    n_alturas: int = 12,
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
        mode="gauge+number",
        value=valor,
        number=dict(suffix=" %", font=dict(size=42, color=GRIS_900)),
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
                     color: str | None = None) -> go.Figure:
    """
    Serie mensual con área bajo la curva (gradiente) y máx/mín marcados.

    serie: indexada por mes (1..12).
    """
    color = color or PRIMARIO
    meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    df = serie.reindex(range(1, 13)).reset_index()
    df.columns = ["mes", "valor"]
    df["mes_label"] = df["mes"].apply(lambda m: meses[m - 1])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["mes_label"], y=df["valor"],
        mode="lines+markers",
        line=dict(color=color, width=3),
        marker=dict(size=8, color=color, line=dict(color="white", width=1.5)),
        fill="tozeroy",
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
        hovertemplate="<b>%{label}</b><br>%{value:,} fallos<br>%{percent}<extra></extra>",
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


def banda_tramos(serie: pd.Series, titulo: str, label_y: str = "",
                 color: str | None = None) -> go.Figure:
    """
    Distribución a lo largo de tramos lineales (anillo entrada/salida).

    serie: indexada por etiqueta de tramo (T01..T40), valor = nº de eventos/rechazos.
    Útil para "ver" la concentración geográfica como una banda.
    """
    color = color or PRIMARIO
    df = serie.reset_index()
    df.columns = ["tramo", "valor"]

    fig = go.Figure(go.Bar(
        x=df["tramo"], y=df["valor"],
        marker=dict(color=df["valor"],
                    colorscale=[[0.0, "#EAF2F9"], [0.5, PRIMARIO_CLARO], [1.0, color]],
                    showscale=False,
                    line=dict(color="white", width=0.5)),
        hovertemplate="<b>%{x}</b><br>" + label_y + ": %{y:,}<extra></extra>",
    ))
    media = float(df["valor"].mean())
    fig.add_hline(y=media, line_dash="dash", line_color=GRIS_500,
                  annotation_text=f"Media: {media:.1f}",
                  annotation_position="top right",
                  annotation_font_color=GRIS_700)

    fig.update_layout(
        title=titulo,
        xaxis_title="Tramo",
        yaxis_title=label_y,
        bargap=0.15,
        showlegend=False,
        height=300,
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


def plano_almacen(
    fallos_pasillos: dict[int, int],
    fallos_entrada:  dict[int, int],
    fallos_salida:   dict[int, int],
    titulo: str = "Plano de la instalación — concentración de fallos",
) -> go.Figure:
    """
    Plano esquemático del almacén AS/RS.

    - 20 pasillos SRM como rectángulos verticales en grid 5×4.
    - Banda superior con los 20 tramos del anillo de entrada.
    - Banda inferior con los 10 tramos del anillo de salida.
    - Color por intensidad de fallos.

    Parámetros:
        fallos_pasillos: {pasillo (1..20): n_fallos}
        fallos_entrada:  {tramo (1..20): n_fallos}
        fallos_salida:   {tramo (1..10): n_fallos}
    """
    fig = go.Figure()

    # Normalizador para colorscale
    all_vals = (list(fallos_pasillos.values())
                + list(fallos_entrada.values())
                + list(fallos_salida.values()))
    vmax = max(all_vals) if all_vals else 1

    def _color(v: int) -> str:
        if vmax == 0:
            return "#EAF2F9"
        ratio = v / vmax
        if ratio < 0.33:
            return "#A8C8E0"
        elif ratio < 0.66:
            return PRIMARIO_CLARO
        elif ratio < 0.85:
            return ADVERTENCIA
        else:
            return CRITICO

    # ----- Anillo entrada (banda superior) -----
    y_ent = 11
    for t in range(1, 21):
        v = fallos_entrada.get(t, 0)
        fig.add_shape(
            type="rect",
            x0=(t - 1) * 1.0 + 0.5, x1=t * 1.0 + 0.4,
            y0=y_ent, y1=y_ent + 0.9,
            line=dict(color="white", width=1),
            fillcolor=_color(v),
        )
        fig.add_trace(go.Scatter(
            x=[(t - 1) * 1.0 + 0.95], y=[y_ent + 0.45],
            mode="markers", marker=dict(opacity=0, size=22),
            showlegend=False,
            hovertemplate=f"<b>Entrada · T{t:02d}</b><br>{v:,} fallos<extra></extra>",
        ))

    fig.add_annotation(x=10.5, y=y_ent + 1.2,
                       text=f"<b>Anillo de entrada</b> · 20 tramos",
                       showarrow=False, font=dict(size=12, color=GRIS_700))

    # ----- Pasillos SRM (rejilla central) -----
    # Disposición: 20 pasillos en 1 fila horizontal larga
    y_pas_bot = 4
    y_pas_top = 10
    for p in range(1, 21):
        v = fallos_pasillos.get(p, 0)
        fig.add_shape(
            type="rect",
            x0=(p - 1) * 1.0 + 0.55, x1=p * 1.0 + 0.35,
            y0=y_pas_bot, y1=y_pas_top,
            line=dict(color="white", width=1.5),
            fillcolor=_color(v),
        )
        fig.add_annotation(
            x=(p - 1) * 1.0 + 0.95, y=(y_pas_top + y_pas_bot) / 2,
            text=f"P{p:02d}<br><b>{v}</b>",
            showarrow=False,
            font=dict(size=10, color="white" if v >= vmax * 0.5 else GRIS_900),
        )
        fig.add_trace(go.Scatter(
            x=[(p - 1) * 1.0 + 0.95], y=[(y_pas_top + y_pas_bot) / 2],
            mode="markers", marker=dict(opacity=0, size=30),
            showlegend=False,
            hovertemplate=f"<b>Pasillo P{p:02d}</b><br>{v:,} fallos<extra></extra>",
        ))

    fig.add_annotation(x=10.5, y=y_pas_top + 0.5,
                       text="<b>20 pasillos SRM · 12 alturas cada uno</b>",
                       showarrow=False, font=dict(size=12, color=GRIS_700))

    # ----- Anillo salida (banda inferior, 10 tramos centrados) -----
    y_sal = 2.0
    offset_sal = 5.5  # centrado bajo los pasillos 6..15
    for t in range(1, 11):
        v = fallos_salida.get(t, 0)
        fig.add_shape(
            type="rect",
            x0=offset_sal + (t - 1) * 1.0 + 0.55,
            x1=offset_sal + t * 1.0 + 0.35,
            y0=y_sal, y1=y_sal + 0.9,
            line=dict(color="white", width=1),
            fillcolor=_color(v),
        )
        fig.add_trace(go.Scatter(
            x=[offset_sal + (t - 1) * 1.0 + 0.95], y=[y_sal + 0.45],
            mode="markers", marker=dict(opacity=0, size=22),
            showlegend=False,
            hovertemplate=f"<b>Salida · T{t:02d}</b><br>{v:,} fallos<extra></extra>",
        ))

    fig.add_annotation(
        x=10.5, y=y_sal - 0.4,
        text="<b>Anillo de salida</b> · 10 tramos (doble cuna)",
        showarrow=False, font=dict(size=12, color=GRIS_700),
    )

    # Leyenda manual (colorbar discreta)
    leyenda_y = 0.4
    leyenda_items = [("Bajo", "#A8C8E0"),
                     ("Medio", PRIMARIO_CLARO),
                     ("Alto", ADVERTENCIA),
                     ("Crítico", CRITICO)]
    for i, (etq, col) in enumerate(leyenda_items):
        fig.add_shape(
            type="rect",
            x0=7.5 + i * 1.5, x1=7.7 + i * 1.5,
            y0=leyenda_y, y1=leyenda_y + 0.35,
            line=dict(color="white", width=0),
            fillcolor=col,
        )
        fig.add_annotation(
            x=8.0 + i * 1.5, y=leyenda_y + 0.18,
            text=etq, showarrow=False,
            font=dict(size=11, color=GRIS_700), xanchor="left",
        )

    fig.update_layout(
        title=titulo,
        xaxis=dict(range=[-0.5, 22], showgrid=False, zeroline=False,
                   showticklabels=False, fixedrange=True),
        yaxis=dict(range=[-0.5, 13.5], showgrid=False, zeroline=False,
                   showticklabels=False, fixedrange=True,
                   scaleanchor="x", scaleratio=0.7),
        height=480,
        margin=dict(l=10, r=10, t=60, b=10),
        showlegend=False,
        plot_bgcolor="#F9FAFB",
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
