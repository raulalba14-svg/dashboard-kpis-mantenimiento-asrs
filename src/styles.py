"""
CSS global inyectado por las páginas Streamlit.

`inyectar_css()` aplica el sistema visual del proyecto:
- Tipografía IBM Plex Sans (UI) + IBM Plex Mono (cifras) desde Google Fonts.
- Tarjetas st.metric con borde, padding y fondo claros.
- Espaciado superior reducido para aprovechar el viewport.
- Cabeceras de tabla con color corporativo.
- Bordes y radios consistentes.

Llamar al inicio de cada página, justo después de `aplicar_tema()`.
"""

from __future__ import annotations

import streamlit as st

from src.theme import EXITO, ADVERTENCIA, CRITICO, ACENTO_TEXTO


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


# Color de acento de la síntesis según el estado global de la página.
_ESTADO_COLOR = {
    "ok":       EXITO,
    "vigilar":  ADVERTENCIA,
    "critico":  CRITICO,
    "info":     ACENTO_TEXTO,
}


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"], .stApp, .stMarkdown, .stMetric, .stDataFrame {
    font-family: 'IBM Plex Sans', -apple-system, 'Segoe UI', Roboto, system-ui, sans-serif !important;
}

/* Reducir padding superior del contenedor principal */
.block-container {
    padding-top: 1.6rem !important;
    padding-bottom: 3rem !important;
    max-width: 1400px !important;
}

/* Títulos */
h1, h2, h3, h4 {
    color: #0F1722 !important;
    letter-spacing: -0.01em !important;
}
h1 { font-weight: 700 !important; }
h2 { font-weight: 600 !important; }
h3 { font-weight: 600 !important; font-size: 1.15rem !important; }

/* Tarjetas st.metric */
div[data-testid="stMetric"] {
    background: #F9FAFB;
    border: 1px solid #E4E7EC;
    padding: 16px 18px;
    border-radius: 8px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}
div[data-testid="stMetric"] > div:first-child {
    color: #667085 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #0F1722 !important;
    font-family: 'IBM Plex Mono', 'Consolas', 'SFMono-Regular', monospace !important;
    font-weight: 600 !important;
    font-size: 1.6rem !important;
    font-variant-numeric: tabular-nums;
}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    font-size: 0.85rem !important;
    font-weight: 500 !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #F9FAFB;
    border-right: 1px solid #E4E7EC;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #1E4D72 !important;
}

/* === Menú de navegación del sidebar === */
/* Cada entrada es un enlace; afinamos reposo, hover y página activa. */
[data-testid="stSidebarNav"] a {
    border-radius: 7px !important;
    border-left: 3px solid transparent !important;
    transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease !important;
}
/* Hover: se "enciende" en cian suave (convención de navegación). */
[data-testid="stSidebarNav"] a:hover {
    background: rgba(24, 182, 201, 0.10) !important;
    border-left-color: #18B6C9 !important;
}
[data-testid="stSidebarNav"] a:hover span {
    color: #0E7C8B !important;
}
/* Página activa: marca permanente para indicar dónde estás. */
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(24, 182, 201, 0.14) !important;
    border-left-color: #18B6C9 !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] span {
    color: #0E7C8B !important;
    font-weight: 600 !important;
}

/* Divisores más sutiles */
hr {
    border-color: #E4E7EC !important;
    margin: 1.4rem 0 !important;
}

/* Tabs */
button[data-baseweb="tab"] {
    font-weight: 500 !important;
    color: #667085 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #1E4D72 !important;
}

/* DataFrame: cabecera con color corporativo suave; celdas numéricas en mono */
.stDataFrame thead tr th {
    background-color: #F2F4F7 !important;
    color: #0F1722 !important;
    font-weight: 600 !important;
    border-bottom: 2px solid #1E4D72 !important;
}
.stDataFrame tbody tr td {
    font-variant-numeric: tabular-nums;
}

/* Caption */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #667085 !important;
    font-size: 0.85rem !important;
}

/* Botón */
.stButton button {
    border-radius: 6px !important;
    border: 1px solid #D0D5DD !important;
    font-weight: 500 !important;
}

/* Expander */
details {
    border: 1px solid #E4E7EC !important;
    border-radius: 8px !important;
    background: #FFFFFF !important;
}
details summary {
    font-weight: 600 !important;
    color: #1E4D72 !important;
}

/* Plotly chart sin sombra ni borde */
.stPlotlyChart {
    border-radius: 8px;
}

/* ===================================================================== */
/* RESPONSIVE — móvil (<= 640px)                                         */
/* Streamlit no apila st.columns() en pantallas estrechas: las mantiene  */
/* lado a lado encogiéndolas hasta volverlas ilegibles. Forzamos el wrap */
/* del contenedor horizontal para que cada columna pase a ancho completo.*/
/* ===================================================================== */
@media (max-width: 640px) {
    /* Aprovechar todo el ancho del viewport */
    .block-container {
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        padding-top: 1rem !important;
    }

    /* Apilar cualquier fila de columnas (st.columns) en vertical */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 0.75rem !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        flex: 1 1 100% !important;
        width: 100% !important;
        min-width: 100% !important;
    }

    /* Métricas y títulos un punto más compactos */
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.3rem !important; }

    /* La barra de herramientas de Plotly estorba en táctil; ya la ocultamos
       por configuración, pero reforzamos por si alguna queda visible. */
    .stPlotlyChart .modebar {
        display: none !important;
    }

    /* === Gráficos: que el scroll de la página NUNCA quede atrapado ===
       No necesitamos interacción interna (zoom/pan) en ninguna gráfica en
       móvil. Plotly coloca capas transparentes de captura de gestos encima
       del SVG (.nsewdrag, .drag, .draglayer) cuyos manejadores táctiles hacen
       preventDefault y "secuestran" el scroll, creando recuadros de zoom al
       deslizar el dedo. Las neutralizamos: el gesto pasa directo a la página. */
    .stPlotlyChart, .stPlotlyChart .plot-container,
    .stPlotlyChart .svg-container,
    .stPlotlyChart .main-svg {
        touch-action: pan-y !important;
    }
    .stPlotlyChart .nsewdrag,
    .stPlotlyChart .drag,
    .stPlotlyChart .draglayer,
    .stPlotlyChart .draglayer * {
        pointer-events: none !important;
        touch-action: pan-y !important;
    }
}
</style>
"""


_HERO = """
<style>
.asrs-hero {{
    background: linear-gradient(135deg, #12233A 0%, #0E1A2B 60%);
    color: #F4F7FA;
    padding: 28px 32px 26px 30px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-left: 4px solid #18B6C9;
    border-radius: 8px;
    margin-bottom: 1.5rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}}
.asrs-hero__inner {{
    display: flex; gap: 28px; align-items: center; flex-wrap: wrap;
}}
.asrs-hero__text {{ flex: 1 1 460px; min-width: 280px; }}
.asrs-hero__kicker {{
    display: inline-block;
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.14em;
    text-transform: uppercase; color: #18B6C9;
    margin-bottom: 10px;
}}
.asrs-hero__title {{
    color: #F4F7FA !important;
    margin: 0 0 8px 0;
    font-size: 1.95rem; font-weight: 700; line-height: 1.15;
    letter-spacing: -0.02em;
}}
.asrs-hero__divider {{
    width: 48px; height: 2px;
    background: #18B6C9;
    margin: 10px 0 12px 0;
}}
.asrs-hero__subtitle {{
    color: #AEBDCC; font-size: 0.98rem; line-height: 1.55; max-width: 720px;
}}
.asrs-hero__subtitle b {{ color: #FFFFFF; font-weight: 600; }}
.asrs-hero__stats {{
    display: flex; gap: 12px; flex-wrap: wrap;
    flex: 0 0 auto;
}}
.asrs-hero__stat {{
    min-width: 92px;
    padding: 12px 16px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.10);
    text-align: center;
}}
.asrs-hero__stat-num {{
    font-family: 'IBM Plex Mono', 'Consolas', monospace;
    font-size: 1.6rem; font-weight: 600; color: #18B6C9;
    line-height: 1; letter-spacing: -0.01em;
    font-variant-numeric: tabular-nums;
}}
.asrs-hero__stat-label {{
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.12em;
    text-transform: uppercase; color: #7E8FA1;
    margin-top: 6px;
}}
@media (max-width: 720px) {{
    .asrs-hero {{ padding: 22px 20px; }}
    .asrs-hero__title {{ font-size: 1.5rem; }}
    .asrs-hero__stat {{ min-width: 76px; padding: 10px 12px; }}
    .asrs-hero__stat-num {{ font-size: 1.35rem; }}
}}
</style>
<div class="asrs-hero">
    <div class="asrs-hero__inner">
        <div class="asrs-hero__text">
            <div class="asrs-hero__kicker">{kicker}</div>
            <h1 class="asrs-hero__title">{titulo}</h1>
            <div class="asrs-hero__divider"></div>
            <div class="asrs-hero__subtitle">{subtitulo}</div>
        </div>
        <div class="asrs-hero__stats">
            <div class="asrs-hero__stat">
                <div class="asrs-hero__stat-num">8</div>
                <div class="asrs-hero__stat-label">SRM</div>
            </div>
            <div class="asrs-hero__stat">
                <div class="asrs-hero__stat-num">15</div>
                <div class="asrs-hero__stat-label">STV</div>
            </div>
            <div class="asrs-hero__stat">
                <div class="asrs-hero__stat-num">23</div>
                <div class="asrs-hero__stat-label">Equipos</div>
            </div>
        </div>
    </div>
</div>
"""


_BADGE = """
<span style="
    display: inline-block;
    background: {bg};
    color: {fg};
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    border: 1px solid {border};
">{texto}</span>
"""


# Icono SVG inline (clipboard / análisis) para el bloque de síntesis.
_LECTURA_ICONO = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M9 4h6a1 1 0 0 1 1 1v1H8V5a1 1 0 0 1 1-1z"/>'
    '<rect x="5" y="6" width="14" height="15" rx="2"/>'
    '<path d="M9 12h6M9 16h4"/></svg>'
)


def _lectura_html(texto: str, color: str) -> str:
    """
    HTML de la síntesis sobre fondo CLARO tintado del color del estado
    (verde/ámbar/rojo/cian). Distinto del hero oscuro: se lee como conclusión
    semáforo de la página. HTML compacto (sin sangría) para que Streamlit no lo
    trate como bloque de código.
    """
    insight = (
        f"display:flex;gap:13px;align-items:flex-start;"
        f"background:{_rgba(color, 0.08)};border:1px solid {_rgba(color, 0.28)};"
        f"border-left:5px solid {color};padding:15px 18px;border-radius:8px;"
        f"margin:0.4rem 0 1.2rem 0;box-shadow:0 1px 3px rgba(16,24,40,0.05);"
    )
    icono_box = (
        f"flex:0 0 auto;width:32px;height:32px;border-radius:8px;"
        f"background:{_rgba(color, 0.16)};color:{color};display:flex;"
        f"align-items:center;justify-content:center;margin-top:1px;"
    )
    body = "flex:1 1 auto;color:#344054;font-size:0.95rem;line-height:1.55;"
    kicker = (
        f"display:block;font-size:0.72rem;font-weight:700;letter-spacing:0.12em;"
        f"text-transform:uppercase;color:{color};margin-bottom:4px;"
    )
    return (
        f'<div style="{insight}">'
        f'<div style="{icono_box}">{_LECTURA_ICONO}</div>'
        f'<div style="{body}">'
        f'<span style="{kicker}">Síntesis</span>{texto}'
        f'</div></div>'
    )


def inyectar_css() -> None:
    """Aplica el CSS global del proyecto."""
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(kicker: str, titulo: str, subtitulo: str) -> None:
    """Cabecera destacada en gradiente azul para la home y módulos."""
    st.markdown(
        _HERO.format(kicker=kicker, titulo=titulo, subtitulo=subtitulo),
        unsafe_allow_html=True,
    )


def lectura_ejecutiva(texto: str, estado: str = "info") -> None:
    """
    Renderiza un bloque "Síntesis": interpretación en lenguaje natural de
    los KPIs de la página, como conclusión semáforo. Acepta HTML inline
    (usa <b> para resaltar cifras y nombres de equipo).

    estado: "ok" (verde) | "vigilar" (ámbar) | "critico" (rojo) | "info"
            (cian neutro, por defecto). Tiñe el fondo y el acento del bloque.
    """
    color = _ESTADO_COLOR.get(estado, _ESTADO_COLOR["info"])
    st.markdown(_lectura_html(texto, color), unsafe_allow_html=True)


def badge(texto: str, color: str = "info") -> str:
    """
    Devuelve HTML de un badge inline (no lo renderiza).
    color: 'info' | 'success' | 'warning' | 'danger' | 'neutral'
    """
    palette = {
        "info":    ("#E7F0F6", "#1E4D72", "#BCD3E2"),
        "success": ("#E6F4EC", "#15703D", "#BFE2CC"),
        "warning": ("#FBF0DC", "#8A560F", "#F0DCAE"),
        "danger":  ("#FBE7E7", "#C0303A", "#F2C4C6"),
        "neutral": ("#F2F4F7", "#344054", "#D0D5DD"),
    }
    bg, fg, border = palette.get(color, palette["info"])
    return _BADGE.format(bg=bg, fg=fg, border=border, texto=texto)
