"""
Iconos SVG lineales inline.

Sustituyen a los emojis del proyecto por iconos de trazo (estilo Lucide / Feather,
licencia ISC/MIT), monocromos y sobrios. Se inyectan como HTML inline vía
`st.markdown(..., unsafe_allow_html=True)` o dentro del HTML de las tarjetas KPI
(`kpi_card_html(icono=icon("wrench"))`).

Ventaja frente a una fuente de iconos o un CDN: no hay dependencia externa, así
que renderizan igual offline y en Streamlit Cloud.

Por defecto el trazo es `currentColor`, de modo que el icono hereda el color del
contenedor (el gris del label en las tarjetas KPI, el acento en navegación).
"""

from __future__ import annotations

# Cada entrada es el contenido interno de un <svg viewBox="0 0 24 24">.
# Trazos basados en Lucide (https://lucide.dev), normalizados a stroke-width 2.
_PATHS: dict[str, str] = {
    # --- KPI / métricas ---
    "wrench":         '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4l-6 6a2 2 0 1 0 2.8 2.8l6-6a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.4-.4-2.4 2.5-2.5z"/>',
    "rotate":         '<path d="M21 12a9 9 0 1 1-2.6-6.4"/><path d="M21 3v5h-5"/>',
    "alert-triangle": '<path d="M10.3 3.7 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.7a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "alert-circle":   '<circle cx="12" cy="12" r="9"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
    "clock":          '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "package":        '<path d="M16.5 9.4 7.5 4.2"/><path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
    "x-circle":       '<circle cx="12" cy="12" r="9"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>',
    "truck":          '<path d="M14 17V5a1 1 0 0 0-1-1H2a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h2"/><path d="M14 9h4l3 3v4a1 1 0 0 1-1 1h-1"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
    "bar-chart":      '<path d="M3 21h18"/><rect x="5" y="11" width="3" height="7"/><rect x="10.5" y="6" width="3" height="12"/><rect x="16" y="9" width="3" height="9"/>',
    "gauge":          '<path d="M12 14 16 9"/><path d="M3.5 18a9 9 0 1 1 17 0"/><circle cx="12" cy="14" r="1.4"/>',
    "check-circle":   '<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.5 2.5L16 9"/>',
    "cpu":            '<rect x="6" y="6" width="12" height="12" rx="1.5"/><rect x="9.5" y="9.5" width="5" height="5"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
    "map-pin":        '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="2.5"/>',

    # --- navegación ---
    "layout-dashboard": '<rect x="3" y="3" width="8" height="9" rx="1"/><rect x="13" y="3" width="8" height="5" rx="1"/><rect x="13" y="11" width="8" height="10" rx="1"/><rect x="3" y="15" width="8" height="6" rx="1"/>',
    "git-compare":      '<circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><path d="M11 18H8a2 2 0 0 1-2-2V9"/>',

    # --- utilidades ---
    "download":  '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
    "search":    '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
}


def icon(nombre: str, size: int = 16, stroke: float = 1.8,
         color: str = "currentColor") -> str:
    """
    Devuelve el HTML de un icono SVG inline de trazo.

    nombre  : clave de `_PATHS` (p.ej. "wrench", "truck"). Si no existe,
              devuelve cadena vacía (degradación silenciosa).
    size    : ancho/alto en px.
    stroke  : grosor del trazo.
    color   : color del trazo. Por defecto `currentColor` (hereda del contenedor).
    """
    cuerpo = _PATHS.get(nombre)
    if cuerpo is None:
        return ""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
        f'stroke-linejoin="round" '
        f'style="vertical-align:-0.18em;margin-right:6px;flex:0 0 auto;">'
        f'{cuerpo}</svg>'
    )


def _hex_a_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def chip(nombre: str, color: str, size: int = 34) -> str:
    """
    Devuelve un "chip" de icono: un cuadrado redondeado con fondo del color
    en tono suave y el icono de trazo en ese mismo color. Da identidad y color
    a cada tarjeta KPI según el tipo de métrica, sin recurrir a emojis.

    nombre : clave de icono (`_PATHS`).
    color  : color de acento del KPI (p.ej. CRITICO para fallos, EXITO para
             disponibilidad). El fondo se deriva del color al 14 % de alpha.
    size   : lado del chip en px.
    """
    cuerpo = _PATHS.get(nombre)
    if cuerpo is None:
        return ""
    svg = (
        f'<svg width="{int(size * 0.56)}" height="{int(size * 0.56)}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.9" '
        f'stroke-linecap="round" stroke-linejoin="round">{cuerpo}</svg>'
    )
    return (
        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
        f'width:{size}px;height:{size}px;border-radius:9px;flex:0 0 auto;'
        f'background:{_hex_a_rgba(color, 0.14)};margin-right:11px;">{svg}</span>'
    )
