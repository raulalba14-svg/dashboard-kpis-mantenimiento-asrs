"""Módulo 5 — Acerca del proyecto."""

import streamlit as st

from src.theme import (
    aplicar_tema, PRIMARIO, PRIMARIO_CLARO, EXITO, ADVERTENCIA,
    GRIS_500, GRIS_700, GRIS_900,
)
from src.styles import inyectar_css, hero, badge
from src.sidebar import render_sidebar_filtros
from src.config import init_session_state
from src.branding import (
    FAVICON, pie_pagina, logo_inline,
    AUTOR, PROYECTO, CONTEXTO_ACADEMICO, ANYO, VERSION,
)

st.set_page_config(
    page_title="Acerca del proyecto",
    page_icon=str(FAVICON) if FAVICON.exists() else None,
    layout="wide",
)
aplicar_tema()
inyectar_css()
init_session_state()
render_sidebar_filtros()

hero(
    kicker="Acerca de",
    titulo="Sobre el proyecto y su autor",
    subtitulo=(
        "Contexto, motivación y arquitectura de la herramienta — "
        "una pantalla para entender el qué, el por qué y el cómo."
    ),
)

# ---------------------------------------------------------------------------
# Identidad
# ---------------------------------------------------------------------------

col_logo, col_id = st.columns([1, 3])
with col_logo:
    logo_inline(alto_px=72)
with col_id:
    st.markdown(
        f"""
        <div style="padding-top:6px;">
            <div style="font-size:1.3rem;font-weight:700;color:{GRIS_900};">
                {PROYECTO}
            </div>
            <div style="color:{GRIS_700};font-size:1rem;margin-top:4px;">
                Autor: <b>{AUTOR}</b> · {CONTEXTO_ACADEMICO} · {ANYO} · {VERSION}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("")

# ---------------------------------------------------------------------------
# Qué + Por qué
# ---------------------------------------------------------------------------

col_q, col_p = st.columns(2)

with col_q:
    st.markdown(f"<h3 style='color:{PRIMARIO};'>Qué es</h3>", unsafe_allow_html=True)
    st.markdown(
        """
        Una herramienta de análisis operacional para almacenes automatizados
        (AS/RS). Toma como entrada los registros del WMS/WCS — cada incidencia
        de avería y cada misión ejecutada por los equipos — y los transforma en
        indicadores de mantenimiento (**MTTR**, **MTBF**, **disponibilidad**)
        por equipo, zona y código de error.

        Está pensada para que un equipo de mantenimiento decida, en menos de
        un minuto, qué transelevador necesita atención prioritaria, en qué
        pasillo se concentran los fallos y cómo evoluciona la disponibilidad
        mes a mes.
        """
    )

with col_p:
    st.markdown(f"<h3 style='color:{PRIMARIO};'>Por qué existe</h3>", unsafe_allow_html=True)
    st.markdown(
        """
        Los sistemas WMS/WCS registran automáticamente todas las incidencias,
        pero esos datos quedan **sin explotar**. No existe ningún mecanismo que
        los transforme en indicadores accionables. La consecuencia: las
        decisiones de mantenimiento se toman por intuición, no por dato.

        Esta herramienta cierra ese hueco. La motivación es operativa, no
        académica: reducir paros no programados, anticipar fallos y priorizar
        ventanas de mantenimiento basándose en evidencia cuantitativa.
        """
    )

st.divider()

# ---------------------------------------------------------------------------
# Esquema de datos — 4 tablas
# ---------------------------------------------------------------------------

st.markdown(f"<h3 style='color:{PRIMARIO};'>Esquema de datos</h3>", unsafe_allow_html=True)
st.markdown(
    f"<div style='color:{GRIS_700};margin-bottom:1rem;'>"
    "El modelo de datos replica el esquema típico de un WMS/WCS. La migración "
    "futura a datos reales no requeriría reescribir la lógica de análisis."
    "</div>",
    unsafe_allow_html=True,
)

_tablas = [
    ("eventos_incidencia", "Registro de cada avería detectada",
     "id_evento · id_equipo · codigo_error · ts_inicio_fallo · ts_recuperacion · estado",
     PRIMARIO),
    ("equipos", "Inventario de transelevadores (SRM) y vehículos del anillo (STV)",
     "id · tipo (SRM/STV) · zona · estado_operativo",
     PRIMARIO_CLARO),
    ("misiones", "Cada movimiento ejecutado por un equipo",
     "id_mision · id_equipo · posicion_inicial · posicion_final · ts_inicio · ts_fin · estado",
     EXITO),
    ("tipos_error", "Catálogo de códigos de error del WCS",
     "codigo · descripcion · duracion_media_min",
     ADVERTENCIA),
]

cols = st.columns(2)
for i, (nombre, descripcion, campos, color) in enumerate(_tablas):
    with cols[i % 2]:
        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid #E4E7EC;border-radius:12px;
                        padding:14px 18px;margin-bottom:14px;
                        border-left:4px solid {color};
                        box-shadow:0 1px 2px rgba(16,24,40,0.04);">
                <div style="font-family:'JetBrains Mono', 'Consolas', monospace;
                            font-weight:700;color:{GRIS_900};font-size:0.95rem;">
                    {nombre}
                </div>
                <div style="color:{GRIS_700};font-size:0.88rem;margin-top:4px;">
                    {descripcion}
                </div>
                <div style="color:{GRIS_500};font-size:0.78rem;margin-top:8px;
                            font-family:'JetBrains Mono', 'Consolas', monospace;
                            line-height:1.5;">
                    {campos}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# ---------------------------------------------------------------------------
# Cómo está hecho
# ---------------------------------------------------------------------------

col_stack, col_metrics = st.columns([3, 2])

with col_stack:
    st.markdown(f"<h3 style='color:{PRIMARIO};'>Cómo está hecho</h3>", unsafe_allow_html=True)
    st.markdown(
        """
        - **Lenguaje y framework**: Python 3 · Streamlit · pandas · Plotly.
        - **Capa de cálculo separada de la visualización**: `src/kpis.py`
          contiene funciones puras de pandas sin dependencias de Streamlit,
          validadas con tests unitarios.
        - **Generador de datos sintéticos**: `scripts/generar_datos.py`
          produce ~0,94 M de misiones y ~2.170 eventos con estacionalidad,
          correlación ciclos↔fallos y coherencia temporal verificada.
        - **Sistema de diseño propio**: paleta corporativa, tipografía Inter,
          template Plotly compartido y componentes reutilizables
          (`hero`, `lectura_ejecutiva`, `badge`).
        - **Insights accionables**: cada módulo incluye una lectura ejecutiva
          que traduce los KPIs a recomendaciones operativas, recalculada con
          los filtros activos.
        """
    )

with col_metrics:
    st.markdown(f"<h3 style='color:{PRIMARIO};'>El dataset</h3>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="background:#F9FAFB;border:1px solid #E4E7EC;border-radius:10px;
                    padding:16px 18px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
                <span style="color:{GRIS_700};">Misiones</span>
                <span style="color:{GRIS_900};font-weight:700;">939.994</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
                <span style="color:{GRIS_700};">Eventos de incidencia</span>
                <span style="color:{GRIS_900};font-weight:700;">2.167</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
                <span style="color:{GRIS_700};">SRM (transelevadores)</span>
                <span style="color:{GRIS_900};font-weight:700;">8</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
                <span style="color:{GRIS_700};">STV (anillo único)</span>
                <span style="color:{GRIS_900};font-weight:700;">15</span>
            </div>
            <div style="display:flex;justify-content:space-between;">
                <span style="color:{GRIS_700};">Alturas × columnas por pasillo</span>
                <span style="color:{GRIS_900};font-weight:700;">16 × 48</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Roadmap (atemporal, sin "TFC")
# ---------------------------------------------------------------------------

st.markdown(f"<h3 style='color:{PRIMARIO};'>Roadmap</h3>", unsafe_allow_html=True)

col_r1, col_r2, col_r3 = st.columns(3)
_roadmap = [
    ("Datos reales",
     "Conexión a una base de datos del WMS/WCS manteniendo el "
     "mismo esquema y la misma capa de cálculo.",
     PRIMARIO),
    ("Integración Grafana",
     "Integración con sistemas de monitorización en tiempo real, ofreciendo "
     "una vista analítica complementaria.",
     PRIMARIO_CLARO),
    ("Despliegue webapp",
     "Migración a una arquitectura persistente (p. ej. Next.js + base de "
     "datos gestionada) para acceso multi-usuario y autenticación.",
     EXITO),
]
for col, (titulo, texto, color) in zip([col_r1, col_r2, col_r3], _roadmap):
    with col:
        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid #E4E7EC;border-radius:12px;
                        padding:16px 20px;border-top:3px solid {color};
                        box-shadow:0 1px 2px rgba(16,24,40,0.04);height:100%;">
                <div style="font-weight:700;color:{GRIS_900};margin-bottom:6px;">
                    {titulo}
                </div>
                <div style="color:{GRIS_700};font-size:0.9rem;line-height:1.55;">
                    {texto}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("")

# ---------------------------------------------------------------------------
# Nota sobre los datos
# ---------------------------------------------------------------------------

st.markdown(
    f"""
<div style="background:#F2F4F7;border-radius:10px;padding:14px 18px;
            color:{GRIS_700};font-size:0.88rem;line-height:1.55;margin-top:1rem;">
    {badge("Demo · datos simulados", "neutral")}
    &nbsp;&nbsp;La herramienta opera sobre datos sintéticos
    que reproducen el esquema, los rangos y los patrones típicos de un almacén
    automático AS/RS. La lógica de análisis es idéntica a la que se aplicaría
    sobre datos reales.
</div>
""",
    unsafe_allow_html=True,
)

pie_pagina()
