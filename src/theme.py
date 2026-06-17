"""
Tema visual del proyecto AS/RS.

Define la paleta corporativa y un template de plotly registrado como
default. Importar `aplicar_tema()` al inicio de cada página.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio


# ---------------------------------------------------------------------------
# Paleta corporativa (clara)
# ---------------------------------------------------------------------------

FONDO_OSCURO    = "#0E1A2B"   # azul medianoche — fondo hero / superficies oscuras
PRIMARIO        = "#1E4D72"   # azul instrumento — marca, serie 1, widgets
PRIMARIO_CLARO  = "#2E86AB"   # azul medio — series secundarias
ACENTO          = "#18B6C9"   # cian técnico — focal: rellenos, bordes, sobre-oscuro
ACENTO_TEXTO    = "#0E7C8B"   # cian profundo — cian legible como texto sobre claro
EXITO           = "#2E8B6F"   # verde azulado (teal) — buen estado, armoniza con el cian
ADVERTENCIA     = "#E0A33C"   # ámbar dorado — atención
CRITICO         = "#D85C5C"   # rojo coral — fuera de umbral

GRIS_900 = "#0F1722"   # texto principal
GRIS_700 = "#344054"   # texto secundario
GRIS_500 = "#667085"   # caption
GRIS_300 = "#D0D5DD"   # bordes
GRIS_100 = "#F2F4F7"   # fondo secundario
GRIS_50  = "#F9FAFB"   # fondo tarjeta

# Secuencia para series categóricas (varios elementos con la misma escala)
SECUENCIA = [
    PRIMARIO, ACENTO, PRIMARIO_CLARO, ADVERTENCIA, EXITO, CRITICO,
    "#6B8AA6", "#4F9D8E", "#9B7BB8", "#8C99A8",
]

# Paletas semánticas por dominio
COLOR_CATEGORIA = {
    "electrica":       CRITICO,
    "mecanica":        PRIMARIO,
    "posicionamiento": PRIMARIO_CLARO,
    "comunicacion":    ADVERTENCIA,
}

COLOR_SEVERIDAD = {
    "baja":     EXITO,
    "media":    ADVERTENCIA,
    "alta":     "#D9822B",
    "critica":  CRITICO,
}

COLOR_ESTADO_MISION = {
    "completada": EXITO,
    "abortada":   CRITICO,
}


# ---------------------------------------------------------------------------
# Template plotly
# ---------------------------------------------------------------------------

def _construir_template() -> go.layout.Template:
    template = go.layout.Template()
    template.layout = go.Layout(
        font=dict(
            family="'IBM Plex Sans', -apple-system, 'Segoe UI', Roboto, system-ui, sans-serif",
            size=13,
            color=GRIS_900,
        ),
        title=dict(
            font=dict(size=16, color=GRIS_900),
            x=0.0,
            xanchor="left",
            pad=dict(l=4, t=4, b=12),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=SECUENCIA,
        # `fixedrange=True` por defecto: ninguna gráfica permite zoom/pan al
        # arrastrar. Es deseable en escritorio (los datos se leen tal cual) y
        # crítico en móvil, donde el gesto de zoom secuestraba el scroll de la
        # página. Las funciones que necesiten zoom pueden sobrescribirlo.
        xaxis=dict(
            gridcolor="#E4E7EC",
            linecolor=GRIS_300,
            zerolinecolor="#E4E7EC",
            ticks="outside",
            ticklen=4,
            tickcolor=GRIS_300,
            tickfont=dict(color=GRIS_700),
            title=dict(font=dict(color=GRIS_700)),
            fixedrange=True,
        ),
        yaxis=dict(
            gridcolor="#E4E7EC",
            linecolor=GRIS_300,
            zerolinecolor="#E4E7EC",
            ticks="outside",
            ticklen=4,
            tickcolor=GRIS_300,
            tickfont=dict(color=GRIS_700),
            title=dict(font=dict(color=GRIS_700)),
            fixedrange=True,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(color=GRIS_700),
        ),
        margin=dict(l=8, r=8, t=48, b=8),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor=GRIS_300,
            font=dict(color=GRIS_900, family="'IBM Plex Sans', sans-serif"),
        ),
        colorscale=dict(
            sequential=[
                [0.0, "#E6F4F6"], [0.25, "#A7E0E7"],
                [0.5, ACENTO], [0.75, PRIMARIO_CLARO],
                [1.0, PRIMARIO],
            ],
            diverging=[
                [0.0, CRITICO], [0.5, "#F9FAFB"], [1.0, EXITO],
            ],
        ),
    )
    return template


def aplicar_tema() -> None:
    """Registra el tema `asrs_corp` y lo activa como default de plotly."""
    pio.templates["asrs_corp"] = _construir_template()
    pio.templates.default = "asrs_corp"
