"""Entry point de la aplicación Streamlit AS/RS."""

import streamlit as st

from src.theme import aplicar_tema, GRIS_500, GRIS_700, GRIS_900, PRIMARIO
from src.styles import inyectar_css, hero, badge
from src.sidebar import render_sidebar_filtros
from src.branding import FAVICON, pie_pagina, PROYECTO, CLAIM

st.set_page_config(
    page_title=f"{PROYECTO} — Análisis operacional AS/RS",
    page_icon=str(FAVICON) if FAVICON.exists() else "🔧",
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
        "Cada incidencia del almacén se registra automáticamente en el WMS/WCS, "
        "pero queda sin explotar. Esta herramienta transforma <b>939.994 misiones</b> y "
        "<b>2.167 eventos</b> en indicadores accionables — <b>MTTR</b>, <b>MTBF</b>, "
        "<b>disponibilidad</b> — para anticipar fallos y priorizar mantenimientos."
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
    background: #FFFFFF;
    border: 1px solid #E4E7EC;
    border-radius: 12px;
    padding: 18px 22px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}}
.asrs-intro__card--accent {{
    border-left: 4px solid {PRIMARIO};
}}
.asrs-intro__card--warn {{
    border-left: 4px solid #C73E1D;
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
        <div class="asrs-intro__title">Datos que no se traducen en decisiones</div>
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
            Varios módulos analíticos convierten los datos crudos en una <b>vista de 30
            segundos</b> del estado de la instalación, con detalle por transelevador y código
            de error. Cada módulo incluye una lectura ejecutiva accionable.
        </div>
    </div>
</div>
"""
st.markdown(_intro_css, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Glosario rápido (plegable, no invasivo)
# ---------------------------------------------------------------------------

with st.expander("📖 Glosario rápido — siglas y conceptos", expanded=False):
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

# Paleta por módulo: (color principal, color claro para gradiente, número visible)
# Streamlit 1.36+ con `st.container(key=...)` añade clase `st-key-<key>` al DOM,
# lo que nos permite estilar cada tarjeta de forma estable.
_CARDS = [
    # (key, icono, titulo, descripcion, page, color, claro, num)
    ("nav_0", "📊", "Resumen general",
     "KPIs globales · disponibilidad · MTTR · MTBF",
     "pages/0_Resumen_general.py", "#1F4E79", "#E8F0F9", "0"),
    ("nav_1", "📍", "Fallos por zona",
     "Plano de la instalación · concentración geográfica",
     "pages/1_Fallos_por_zona_y_equipo.py", "#C0392B", "#FDECEA", "1"),
    ("nav_2", "🤖", "Rendimiento SRM",
     "8 transelevadores · MTTR/MTBF/disponibilidad",
     "pages/2_Rendimiento_SRM.py", "#2E86AB", "#E6F3F9", "2"),
    ("nav_3", "🚚", "Rendimiento STV",
     "15 vehículos del anillo · MTTR/MTBF/disponibilidad",
     "pages/3_Rendimiento_STV.py", "#F18F01", "#FEF3E2", "3"),
    ("nav_4", "⚖️", "Comparativa de periodos",
     "Compara dos rangos · variación de KPIs",
     "pages/4_Comparativa_periodos.py", "#6B4E9C", "#EFE9F7", "4"),
]

# CSS base + per-card (usa clase `st-key-<key>` que Streamlit inyecta al pasar `key=` a un container)
_per_card_css = []
for key, _icono, _titulo, _desc, _page, color, claro, num in _CARDS:
    _per_card_css.append(f"""
    .st-key-{key} div[data-testid="stButton"] > button {{
        background: linear-gradient(135deg, {claro} 0%, #FFFFFF 70%) !important;
        border-left: 5px solid {color} !important;
    }}
    .st-key-{key} div[data-testid="stButton"] > button::before {{
        content: "{num}";
        position: absolute;
        right: 20px;
        top: 6px;
        font-size: 3.6rem;
        font-weight: 800;
        line-height: 1;
        color: {color};
        opacity: 0.12;
        pointer-events: none;
    }}
    .st-key-{key} div[data-testid="stButton"] > button::after {{
        color: {color};
    }}
    .st-key-{key} div[data-testid="stButton"] > button:hover {{
        border-color: {color} !important;
        border-left: 5px solid {color} !important;
    }}
    .st-key-{key} div[data-testid="stButton"] > button:hover::before {{
        opacity: 0.22;
    }}
    """)

_card_css = """
<style>
/* === Base de las tarjetas-botón de navegación === */
div[data-testid="stButton"] > button {
    border: 1px solid #E4E7EC !important;
    border-radius: 16px !important;
    padding: 22px 24px 38px 24px !important;
    box-shadow: 0 1px 3px rgba(16,24,40,0.05) !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease !important;
    height: 100% !important;
    min-height: 140px !important;
    width: 100% !important;
    text-align: left !important;
    white-space: normal !important;
    line-height: 1.5 !important;
    color: #101828 !important;
    font-weight: 500 !important;
    position: relative !important;
    overflow: hidden !important;
}
div[data-testid="stButton"] > button:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 14px 26px rgba(16,24,40,0.12) !important;
}
div[data-testid="stButton"] > button:focus:not(:active) {
    box-shadow: 0 0 0 3px rgba(31,78,121,0.18) !important;
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
/* Flecha → en esquina inferior derecha */
div[data-testid="stButton"] > button::after {
    content: "→";
    position: absolute;
    right: 22px;
    bottom: 12px;
    font-size: 1.5rem;
    font-weight: 700;
    opacity: 0.45;
    transition: transform 0.18s ease, opacity 0.18s ease;
}
div[data-testid="stButton"] > button:hover::after {
    opacity: 1;
    transform: translateX(5px);
}
</style>
"""

st.markdown(_card_css + "<style>" + "\n".join(_per_card_css) + "</style>", unsafe_allow_html=True)


def _card_button(key: str, icono: str, titulo: str, descripcion: str, page: str) -> None:
    # `st.container(key=...)` añade la clase `st-key-<key>` al wrapper en el DOM.
    with st.container(key=key):
        label = f"{icono}  **{titulo}**  \n\n{descripcion}"
        if st.button(label, key=f"btn_{key}", use_container_width=True):
            st.switch_page(page)


# Layout: 5 módulos en filas de 3 columnas (0,1,2 · 3,4)
for fila_inicio in range(0, len(_CARDS), 3):
    cols = st.columns(3, gap="medium")
    for col, card in zip(cols, _CARDS[fila_inicio:fila_inicio + 3]):
        with col:
            _card_button(*card[:5])

st.markdown("")
st.markdown(
    f"<div style='color:{GRIS_700};font-size:0.9rem;margin-top:1rem;'>"
    "💡 Usa el menú superior de Streamlit para navegar entre módulos. "
    "Los filtros del sidebar persisten entre páginas. "
    "Más contexto en <b>Acerca del proyecto</b>."
    "</div>",
    unsafe_allow_html=True,
)

pie_pagina()
