"""
CSS global inyectado por las páginas Streamlit.

`inyectar_css()` aplica el sistema visual del proyecto:
- Tipografía Inter desde Google Fonts.
- Tarjetas st.metric con borde, padding y fondo claros.
- Espaciado superior reducido para aprovechar el viewport.
- Cabeceras de tabla con color corporativo.
- Bordes y radios consistentes.

Llamar al inicio de cada página, justo después de `aplicar_tema()`.
"""

from __future__ import annotations

import streamlit as st


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stApp, .stMarkdown, .stMetric, .stDataFrame {
    font-family: 'Inter', -apple-system, 'Segoe UI', system-ui, sans-serif !important;
}

/* Reducir padding superior del contenedor principal */
.block-container {
    padding-top: 1.6rem !important;
    padding-bottom: 3rem !important;
    max-width: 1400px !important;
}

/* Títulos */
h1, h2, h3, h4 {
    color: #101828 !important;
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
    border-radius: 10px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
}
div[data-testid="stMetric"] > div:first-child {
    color: #667085 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #101828 !important;
    font-weight: 700 !important;
    font-size: 1.65rem !important;
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
    color: #1F4E79 !important;
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
    color: #1F4E79 !important;
}

/* DataFrame: cabecera con color corporativo suave */
.stDataFrame thead tr th {
    background-color: #F2F4F7 !important;
    color: #101828 !important;
    font-weight: 600 !important;
    border-bottom: 2px solid #1F4E79 !important;
}

/* Caption */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #667085 !important;
    font-size: 0.85rem !important;
}

/* Botón */
.stButton button {
    border-radius: 8px !important;
    border: 1px solid #D0D5DD !important;
    font-weight: 500 !important;
}

/* Expander */
details {
    border: 1px solid #E4E7EC !important;
    border-radius: 10px !important;
    background: #FFFFFF !important;
}
details summary {
    font-weight: 600 !important;
    color: #1F4E79 !important;
}

/* Plotly chart sin sombra ni borde */
.stPlotlyChart {
    border-radius: 10px;
}
</style>
"""


_HERO = """
<style>
@keyframes asrs_hero_scan {{
    0%   {{ transform: translateX(-100%); opacity: 0; }}
    20%  {{ opacity: 1; }}
    80%  {{ opacity: 1; }}
    100% {{ transform: translateX(100%); opacity: 0; }}
}}
@keyframes asrs_hero_pulse {{
    0%, 100% {{ box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.55); }}
    50%      {{ box-shadow: 0 0 0 6px rgba(245, 158, 11, 0); }}
}}
.asrs-hero {{
    position: relative;
    overflow: hidden;
    background:
        radial-gradient(ellipse 80% 60% at 85% 0%, rgba(245, 158, 11, 0.18) 0%, transparent 55%),
        radial-gradient(ellipse 60% 80% at 10% 100%, rgba(46, 134, 171, 0.30) 0%, transparent 60%),
        linear-gradient(135deg, #0B1F33 0%, #122E4A 45%, #1F4E79 100%);
    color: #F8FAFC;
    padding: 34px 36px 32px 36px;
    border-radius: 14px;
    margin-bottom: 1.5rem;
    border: 1px solid rgba(148, 163, 184, 0.18);
    box-shadow:
        0 10px 30px rgba(8, 20, 36, 0.45),
        inset 0 1px 0 rgba(255, 255, 255, 0.06);
}}
.asrs-hero::before {{
    content: "";
    position: absolute; inset: 0;
    background-image:
        linear-gradient(rgba(148, 163, 184, 0.10) 1px, transparent 1px),
        linear-gradient(90deg, rgba(148, 163, 184, 0.10) 1px, transparent 1px);
    background-size: 32px 32px;
    mask-image: radial-gradient(ellipse 70% 80% at 50% 50%, black 40%, transparent 90%);
    -webkit-mask-image: radial-gradient(ellipse 70% 80% at 50% 50%, black 40%, transparent 90%);
    pointer-events: none;
}}
.asrs-hero::after {{
    content: "";
    position: absolute; top: 0; left: 0; height: 2px; width: 30%;
    background: linear-gradient(90deg, transparent, rgba(245, 158, 11, 0.85), transparent);
    animation: asrs_hero_scan 5.5s ease-in-out infinite;
}}
.asrs-hero__inner {{
    position: relative; z-index: 1;
    display: flex; gap: 28px; align-items: center; flex-wrap: wrap;
}}
.asrs-hero__text {{ flex: 1 1 460px; min-width: 280px; }}
.asrs-hero__kicker {{
    display: inline-flex; align-items: center; gap: 10px;
    font-size: 0.74rem; font-weight: 700; letter-spacing: 0.18em;
    text-transform: uppercase; color: #F59E0B;
    margin-bottom: 14px;
}}
.asrs-hero__dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: #F59E0B;
    animation: asrs_hero_pulse 2s ease-in-out infinite;
}}
.asrs-hero__title {{
    color: #FFFFFF !important;
    margin: 0 0 10px 0;
    font-size: 2.15rem; font-weight: 700; line-height: 1.1;
    letter-spacing: -0.025em;
}}
.asrs-hero__title-accent {{
    background: linear-gradient(90deg, #F8FAFC 0%, #93C5FD 100%);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.asrs-hero__divider {{
    width: 56px; height: 3px; border-radius: 2px;
    background: linear-gradient(90deg, #F59E0B 0%, transparent 100%);
    margin: 14px 0 14px 0;
}}
.asrs-hero__subtitle {{
    color: #CBD5E1; font-size: 1rem; line-height: 1.55; max-width: 720px;
}}
.asrs-hero__subtitle b {{ color: #F8FAFC; font-weight: 700; }}
.asrs-hero__stats {{
    display: flex; gap: 14px; flex-wrap: wrap;
    flex: 0 0 auto;
}}
.asrs-hero__stat {{
    min-width: 96px;
    padding: 14px 18px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(148, 163, 184, 0.22);
    backdrop-filter: blur(4px);
    text-align: center;
}}
.asrs-hero__stat-num {{
    font-size: 1.75rem; font-weight: 700; color: #FFFFFF;
    line-height: 1; letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
}}
.asrs-hero__stat-label {{
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.14em;
    text-transform: uppercase; color: #93C5FD;
    margin-top: 6px;
}}
@media (max-width: 720px) {{
    .asrs-hero {{ padding: 24px 22px; }}
    .asrs-hero__title {{ font-size: 1.65rem; }}
    .asrs-hero__stat {{ min-width: 78px; padding: 10px 14px; }}
    .asrs-hero__stat-num {{ font-size: 1.4rem; }}
}}
</style>
<div class="asrs-hero">
    <div class="asrs-hero__inner">
        <div class="asrs-hero__text">
            <div class="asrs-hero__kicker">
                <span class="asrs-hero__dot"></span>{kicker}
            </div>
            <h1 class="asrs-hero__title">
                <span class="asrs-hero__title-accent">{titulo}</span>
            </h1>
            <div class="asrs-hero__divider"></div>
            <div class="asrs-hero__subtitle">{subtitulo}</div>
        </div>
        <div class="asrs-hero__stats">
            <div class="asrs-hero__stat">
                <div class="asrs-hero__stat-num">8</div>
                <div class="asrs-hero__stat-label">Pasillos</div>
            </div>
            <div class="asrs-hero__stat">
                <div class="asrs-hero__stat-num">8</div>
                <div class="asrs-hero__stat-label">SRM</div>
            </div>
            <div class="asrs-hero__stat">
                <div class="asrs-hero__stat-num">16</div>
                <div class="asrs-hero__stat-label">Alturas</div>
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


_LECTURA_CSS = """
<style>
.asrs-insight {
    display: flex;
    gap: 14px;
    align-items: flex-start;
    background: #F9FAFB;
    border: 1px solid #E4E7EC;
    border-left: 4px solid #1F4E79;
    padding: 14px 18px;
    border-radius: 10px;
    margin: 0.4rem 0 1.2rem 0;
}
.asrs-insight__icon {
    flex: 0 0 auto;
    width: 28px; height: 28px;
    border-radius: 50%;
    background: #EAF2F9;
    color: #1F4E79;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; font-weight: 700;
    line-height: 1;
}
.asrs-insight__body {
    flex: 1 1 auto;
    color: #344054;
    font-size: 0.95rem;
    line-height: 1.55;
}
.asrs-insight__kicker {
    display: block;
    font-size: 0.7rem; font-weight: 700;
    letter-spacing: 0.14em; text-transform: uppercase;
    color: #1F4E79;
    margin-bottom: 4px;
}
.asrs-insight__body b { color: #101828; font-weight: 700; }
</style>
"""

_LECTURA_HTML = """
<div class="asrs-insight">
    <div class="asrs-insight__icon">💡</div>
    <div class="asrs-insight__body">
        <span class="asrs-insight__kicker">Lectura ejecutiva</span>
        {texto}
    </div>
</div>
"""


def inyectar_css() -> None:
    """Aplica el CSS global del proyecto."""
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(kicker: str, titulo: str, subtitulo: str) -> None:
    """Cabecera destacada en gradiente azul para la home y módulos."""
    st.markdown(
        _HERO.format(kicker=kicker, titulo=titulo, subtitulo=subtitulo),
        unsafe_allow_html=True,
    )


def lectura_ejecutiva(texto: str) -> None:
    """
    Renderiza un bloque "Lectura ejecutiva": interpretación en lenguaje
    natural de los KPIs de la página. Acepta HTML inline (usa <b> para
    resaltar cifras y nombres de equipo).
    """
    st.markdown(_LECTURA_CSS + _LECTURA_HTML.format(texto=texto),
                unsafe_allow_html=True)


def badge(texto: str, color: str = "info") -> str:
    """
    Devuelve HTML de un badge inline (no lo renderiza).
    color: 'info' | 'success' | 'warning' | 'danger' | 'neutral'
    """
    palette = {
        "info":    ("#EAF2F9", "#1F4E79", "#BFD8EA"),
        "success": ("#E8F5E9", "#2E7D32", "#C8E6C9"),
        "warning": ("#FFF4E5", "#B25C00", "#FFE0B2"),
        "danger":  ("#FDECEA", "#C73E1D", "#F5C6CB"),
        "neutral": ("#F2F4F7", "#344054", "#D0D5DD"),
    }
    bg, fg, border = palette.get(color, palette["info"])
    return _BADGE.format(bg=bg, fg=fg, border=border, texto=texto)
