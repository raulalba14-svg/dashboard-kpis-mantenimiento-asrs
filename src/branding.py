"""
Identidad de marca del proyecto.

Centraliza nombre del autor, claim, ruta del favicon, logo SVG inline y un
pie de página común. Llamar a `pie_pagina()` al final de cada página
Streamlit para identificar consistentemente al autor sin invadir el cuerpo.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.theme import GRIS_500, GRIS_300


# ---------------------------------------------------------------------------
# Datos de marca
# ---------------------------------------------------------------------------

AUTOR = "Raúl Alba"
PROYECTO = "ASRS Analytics"
CONTEXTO_ACADEMICO = "TFC · Ciclo Superior de Robótica"
ANYO = 2026
VERSION = "v1.0"
CLAIM = "Del log del WMS a la decisión de mantenimiento"

# Ruta del favicon — se pasa a st.set_page_config(page_icon=...)
RAIZ = Path(__file__).resolve().parent.parent
FAVICON = RAIZ / "assets" / "favicon.svg"
LOGO = RAIZ / "assets" / "logo.svg"


# ---------------------------------------------------------------------------
# Componentes visuales
# ---------------------------------------------------------------------------

def logo_inline(alto_px: int = 56) -> None:
    """Renderiza el logo SVG completo (monograma + wordmark) inline."""
    if not LOGO.exists():
        return
    svg = LOGO.read_text(encoding="utf-8")
    st.markdown(
        f'<div style="display:flex;align-items:center;height:{alto_px}px;">{svg}</div>',
        unsafe_allow_html=True,
    )


_PIE_CSS = f"""
<style>
.asrs-footer {{
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid {GRIS_300};
    color: {GRIS_500};
    font-size: 0.78rem;
    line-height: 1.5;
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
}}
.asrs-footer__left {{ font-weight: 500; }}
.asrs-footer__right {{ letter-spacing: 0.04em; }}
</style>
"""


def pie_pagina() -> None:
    """Pie de página común. Llamar al final de cada página Streamlit."""
    st.markdown(
        _PIE_CSS
        + f"""
<div class="asrs-footer">
    <div class="asrs-footer__left">
        {PROYECTO} · {AUTOR} · {CONTEXTO_ACADEMICO} · {ANYO}
    </div>
    <div class="asrs-footer__right">
        Demo · datos simulados · {VERSION}
    </div>
</div>
""",
        unsafe_allow_html=True,
    )
