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

PRIMARIO        = "#1F4E79"   # azul principal
PRIMARIO_CLARO  = "#2E86AB"   # teal acento
EXITO           = "#2E7D32"   # verde — buen estado
ADVERTENCIA     = "#F18F01"   # ámbar — atención
CRITICO         = "#C73E1D"   # rojo — fuera de umbral

GRIS_900 = "#101828"   # texto principal
GRIS_700 = "#344054"   # texto secundario
GRIS_500 = "#667085"   # caption
GRIS_300 = "#D0D5DD"   # bordes
GRIS_100 = "#F2F4F7"   # fondo secundario
GRIS_50  = "#F9FAFB"   # fondo tarjeta

# Secuencia para series categóricas (varios elementos con la misma escala)
SECUENCIA = [
    PRIMARIO, PRIMARIO_CLARO, ADVERTENCIA, EXITO, CRITICO,
    "#7E57C2", "#26A69A", "#EC407A", "#5C6BC0", "#8D6E63",
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
    "alta":     "#E67E22",
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
            family="Inter, -apple-system, 'Segoe UI', system-ui, sans-serif",
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
        xaxis=dict(
            gridcolor="#E4E7EC",
            linecolor=GRIS_300,
            zerolinecolor="#E4E7EC",
            ticks="outside",
            ticklen=4,
            tickcolor=GRIS_300,
            tickfont=dict(color=GRIS_700),
            title=dict(font=dict(color=GRIS_700)),
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
            font=dict(color=GRIS_900, family="Inter, sans-serif"),
        ),
        colorscale=dict(
            sequential=[
                [0.0, "#EAF2F9"], [0.25, "#9DBFD9"],
                [0.5, "#5E92BC"], [0.75, "#2F669E"],
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
