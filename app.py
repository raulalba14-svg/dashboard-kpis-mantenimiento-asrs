"""Entry point de la aplicación Streamlit AS/RS."""

from urllib.parse import quote

import streamlit as st

from src.theme import (
    aplicar_tema, GRIS_500, GRIS_700, GRIS_900,
    PRIMARIO, PRIMARIO_CLARO, ACENTO, EXITO, ADVERTENCIA, CRITICO,
)
from src.styles import inyectar_css, hero, badge
from src.icons import icon


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina, PROYECTO, CLAIM

st.set_page_config(
    page_title=f"{PROYECTO} — Análisis operacional AS/RS",
    page_icon=str(FAVICON) if FAVICON.exists() else None,
    layout="wide",
)

aplicar_tema()
inyectar_css()

render_sidebar_filtros()

# ---------------------------------------------------------------------------
# Hero — propuesta de valor
# ---------------------------------------------------------------------------

hero(
    kicker="Mantenimiento basado en datos · AS/RS",
    titulo=CLAIM,
    subtitulo=(
        "Los eventos de avería y las misiones del WMS/WCS se registran de forma "
        "automática pero no se explotan. Esta herramienta calcula sobre "
        "<b>939.994 misiones</b> y <b>2.207 eventos</b> los indicadores de "
        "mantenimiento — <b>MTTR</b>, <b>MTBF</b> y <b>disponibilidad</b> — por "
        "equipo, zona y código de error."
    ),
)

# ---------------------------------------------------------------------------
# Problema → Propuesta
# ---------------------------------------------------------------------------

_intro_css = f"""
<style>
.asrs-intro {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 18px;
    margin-bottom: 1.6rem;
}}
.asrs-intro__card {{
    border-radius: 12px;
    padding: 18px 22px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}}
.asrs-intro__card--accent {{
    background: {_rgba(ACENTO, 0.10)};
    border: 1px solid {_rgba(ACENTO, 0.35)};
    border-top: 4px solid {ACENTO};
}}
.asrs-intro__card--warn {{
    background: {_rgba(CRITICO, 0.08)};
    border: 1px solid {_rgba(CRITICO, 0.32)};
    border-top: 4px solid {CRITICO};
}}
.asrs-intro__kicker {{
    font-size: 0.7rem; font-weight: 700;
    letter-spacing: 0.14em; text-transform: uppercase;
    color: {GRIS_500};
    margin-bottom: 6px;
}}
.asrs-intro__title {{
    font-size: 1.05rem; font-weight: 700;
    color: {GRIS_900};
    margin-bottom: 6px;
    line-height: 1.3;
}}
.asrs-intro__body {{
    font-size: 0.92rem; line-height: 1.55;
    color: {GRIS_700};
}}
@media (max-width: 720px) {{
    .asrs-intro {{ grid-template-columns: 1fr; }}
}}
</style>
<div class="asrs-intro">
    <div class="asrs-intro__card asrs-intro__card--warn">
        <div class="asrs-intro__kicker">El problema</div>
        <div class="asrs-intro__title">Datos sin explotar</div>
        <div class="asrs-intro__body">
            El WMS/WCS registra cada fallo y cada misión, pero <b>no calcula</b> MTTR,
            MTBF ni disponibilidad por equipo. Sin esos indicadores no se sabe qué
            transelevador prioriza el próximo mantenimiento ni dónde se concentran las
            paradas.
        </div>
    </div>
    <div class="asrs-intro__card asrs-intro__card--accent">
        <div class="asrs-intro__kicker">La propuesta</div>
        <div class="asrs-intro__title">Del log del WMS al cuadro de mando</div>
        <div class="asrs-intro__body">
            Varios módulos analíticos convierten los datos crudos en una <b>vista
            consolidada</b> del estado de la instalación, con detalle por transelevador y
            código de error. Cada módulo incluye una síntesis de los KPIs.
        </div>
    </div>
</div>
"""
st.markdown(_intro_css, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Glosario rápido (plegable, no invasivo)
# ---------------------------------------------------------------------------

with st.expander("Glosario rápido — siglas y conceptos", expanded=False):
    st.markdown(
        """
        - **AS/RS** *(Automated Storage and Retrieval System)* — almacén automatizado de gran altura, sin operarios en pasillo.
        - **SRM** *(Stacker / Storage and Retrieval Machine)* — transelevador, máquina que se desplaza por el pasillo y maneja los pallets en altura. La instalación tiene **8** (uno por pasillo).
        - **STV** *(Shuttle Transfer Vehicle)* — vehículo de transferencia. La instalación tiene **15** circulando por un **anillo único** que alimenta y evacúa las cabeceras de los pasillos (entradas y salidas).
        - **WMS / WCS** — *Warehouse Management System* / *Warehouse Control System*: sistemas que orquestan el almacén y registran cada incidencia.
        - **MTTR** *(Mean Time To Recovery)* — tiempo medio que un equipo permanece parado por avería. Bajar el MTTR = recuperarse antes.
        - **MTBF** *(Mean Time Between Failures)* — tiempo medio que un equipo opera entre avería y avería. Subir el MTBF = fallar menos.
        - **Disponibilidad** — porcentaje del tiempo en que el equipo está operativo. Objetivo de la instalación: **≥ 95 %**.
        """
    )

# ---------------------------------------------------------------------------
# Tarjetas de navegación
# ---------------------------------------------------------------------------

st.markdown("### Módulos analíticos")

# Cada módulo tiene su color, coherente con el tipo de contenido (mismo criterio
# que las tarjetas KPI). Streamlit 1.36+ con `st.container(key=...)` añade clase
# `st-key-<key>` al DOM, lo que nos permite estilar cada tarjeta de forma estable.
_CARDS = [
    # (key, icono, titulo, descripcion, page, color)
    ("nav_0", "layout-dashboard", "Resumen general",
     "KPIs globales · disponibilidad · MTTR · MTBF",
     "pages/0_Resumen_general.py", ACENTO),
    ("nav_1", "map-pin", "Fallos por zona",
     "Plano de la instalación · concentración geográfica",
     "pages/1_Fallos_por_zona_y_equipo.py", CRITICO),
    ("nav_2", "cpu", "Rendimiento SRM",
     "8 transelevadores · MTTR/MTBF/disponibilidad",
     "pages/2_Rendimiento_SRM.py", PRIMARIO),
    ("nav_3", "truck", "Rendimiento STV",
     "15 vehículos del anillo · MTTR/MTBF/disponibilidad",
     "pages/3_Rendimiento_STV.py", PRIMARIO_CLARO),
    ("nav_4", "x-circle", "Rechazos",
     "Inspección de recepción · tasa de rechazo · motivos",
     "pages/4_Rechazos.py", ADVERTENCIA),
    ("nav_5", "package", "Expedición",
     "Pedidos del anillo · tiempo de completado · throughput",
     "pages/5_Expedicion.py", EXITO),
    ("nav_6", "git-compare", "Comparativa de periodos",
     "Compara dos rangos · variación de KPIs",
     "pages/6_Comparativa_periodos.py", GRIS_700),
]


def _svg_data_uri(nombre: str, color: str) -> str:
    """SVG del icono codificado como data-URI, para usar en background-image."""
    svg = icon(nombre, size=22, stroke=1.8, color=color)
    # Quitar el style inline (no aplica en background) y empaquetar como data-URI.
    svg = svg.replace(
        'style="vertical-align:-0.18em;margin-right:6px;flex:0 0 auto;"', ''
    )
    encoded = quote(svg, safe="")
    return f"url(\"data:image/svg+xml,{encoded}\")"


# CSS base + per-card (usa clase `st-key-<key>` que Streamlit inyecta al pasar `key=` a un container).
# El icono se pinta vía ::before con un SVG data-URI: `st.button` escapa el HTML del
# label, así que no se puede inyectar el <svg> directamente en el texto.
_per_card_css = []
for key, _icono, _titulo, _desc, _page, _color in _CARDS:
    _per_card_css.append(f"""
    .st-key-{key} div[data-testid="stButton"] > button {{
        background: {_rgba(_color, 0.14)} !important;
        border-color: {_rgba(_color, 0.40)} !important;
        border-top: 4px solid {_color} !important;
        border-left: 1px solid {_rgba(_color, 0.40)} !important;
    }}
    .st-key-{key} div[data-testid="stButton"] > button::before {{
        content: "";
        position: absolute;
        right: 20px;
        top: 18px;
        width: 22px;
        height: 22px;
        background-image: {_svg_data_uri(_icono, _color)};
        background-repeat: no-repeat;
        background-size: contain;
        opacity: 0.85;
        pointer-events: none;
    }}
    .st-key-{key} div[data-testid="stButton"] > button:hover {{
        background: {_rgba(_color, 0.22)} !important;
        border-color: {_rgba(_color, 0.60)} !important;
        border-top: 4px solid {_color} !important;
    }}
    .st-key-{key} div[data-testid="stButton"] > button:hover::before {{
        opacity: 1;
    }}
    """)

_card_css = """
<style>
/* === Base de las tarjetas-botón de navegación === */
div[data-testid="stButton"] > button {
    border: 1px solid #E4E7EC !important;
    border-radius: 10px !important;
    padding: 20px 24px 34px 22px !important;
    box-shadow: 0 1px 2px rgba(16,24,40,0.04) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease !important;
    height: 100% !important;
    min-height: 132px !important;
    width: 100% !important;
    text-align: left !important;
    white-space: normal !important;
    line-height: 1.5 !important;
    color: #0F1722 !important;
    font-weight: 500 !important;
    position: relative !important;
    overflow: hidden !important;
}
div[data-testid="stButton"] > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 10px rgba(16,24,40,0.08) !important;
}
div[data-testid="stButton"] > button:focus:not(:active) {
    box-shadow: 0 0 0 3px rgba(24,182,201,0.22) !important;
}
div[data-testid="stButton"] > button p {
    text-align: left !important;
    margin: 0 !important;
    font-size: 1rem !important;
}
div[data-testid="stButton"] > button p strong {
    font-size: 1.08rem !important;
    font-weight: 700 !important;
}
/* Flecha → discreta en esquina inferior derecha (estática) */
div[data-testid="stButton"] > button::after {
    content: "→";
    position: absolute;
    right: 20px;
    bottom: 12px;
    font-size: 1.25rem;
    font-weight: 500;
    color: #667085;
    opacity: 0.5;
    transition: opacity 0.15s ease;
}
div[data-testid="stButton"] > button:hover::after {
    color: #344054;
    opacity: 0.9;
}
/* Móvil: tarjetas más compactas; el icono de fondo se mantiene discreto */
@media (max-width: 640px) {
    div[data-testid="stButton"] > button {
        min-height: 92px !important;
        padding: 16px 18px 28px 16px !important;
    }
    div[data-testid="stButton"] > button::before {
        top: 14px !important;
        right: 14px !important;
    }
}
</style>
"""

st.markdown(_card_css + "<style>" + "\n".join(_per_card_css) + "</style>", unsafe_allow_html=True)


def _card_button(key: str, icono: str, titulo: str, descripcion: str, page: str) -> None:
    # `st.container(key=...)` añade la clase `st-key-<key>` al wrapper en el DOM.
    # El icono no va en el label: se pinta vía ::before (CSS) porque st.button
    # escapa el HTML. `icono` se conserva en la firma para usarlo en el CSS por-card.
    with st.container(key=key):
        label = f"**{titulo}**  \n\n{descripcion}"
        if st.button(label, key=f"btn_{key}", use_container_width=True):
            st.switch_page(page)


# Layout: 3 columnas × 2 filas para los módulos 0-5 + fila final con comparativa
col1, col2, col3 = st.columns(3, gap="medium")
with col1:
    _card_button(*_CARDS[0][:5])
    _card_button(*_CARDS[3][:5])
with col2:
    _card_button(*_CARDS[1][:5])
    _card_button(*_CARDS[4][:5])
with col3:
    _card_button(*_CARDS[2][:5])
    _card_button(*_CARDS[5][:5])

st.markdown("")
_, col_comp, _ = st.columns([1, 2, 1], gap="medium")
with col_comp:
    _card_button(*_CARDS[6][:5])

st.markdown("")
st.markdown(
    f"<div style='color:{GRIS_700};font-size:0.9rem;margin-top:1rem;'>"
    "Usa el menú lateral para navegar entre módulos. "
    "Los filtros del sidebar persisten entre páginas. "
    "Más contexto en <b>Acerca del proyecto</b>."
    "</div>",
    unsafe_allow_html=True,
)

pie_pagina()
