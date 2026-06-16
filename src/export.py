"""
Exportación de datasets a CSV.

Centraliza el botón "Descargar CSV" para que cada módulo exponga, sin
duplicación, los dataframes derivados que el responsable de mantenimiento
querría llevarse a Excel.
"""

from __future__ import annotations

from typing import Mapping

import pandas as pd
import streamlit as st


def _df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def boton_descarga(
    df: pd.DataFrame,
    nombre_fichero: str,
    etiqueta: str = "Descargar CSV",
    key: str | None = None,
) -> None:
    """Renderiza un botón de descarga para un único dataframe.

    Usa separador `;` y decimal `,` (formato Excel ES) y BOM UTF-8 para
    que Excel reconozca las tildes correctamente.
    """
    if df is None or df.empty:
        st.caption("Sin datos para exportar en el periodo actual.")
        return
    st.download_button(
        label=etiqueta,
        data=_df_to_csv_bytes(df),
        file_name=nombre_fichero,
        mime="text/csv",
        key=key,
        use_container_width=False,
    )


def panel_exportacion(datasets: Mapping[str, pd.DataFrame], prefijo: str) -> None:
    """Renderiza un expander con un botón de descarga por cada dataset.

    `datasets` es un mapping `{etiqueta_humana: dataframe}`. `prefijo` se
    usa para nombrar los ficheros (p. ej. `prefijo='resumen'` produce
    `resumen_<slug>.csv`).
    """
    datasets_no_vacios = {k: v for k, v in datasets.items() if v is not None and not v.empty}
    if not datasets_no_vacios:
        return

    st.markdown(
        "### Descargar datos del módulo"
    )
    st.caption(
        "Descarga los datasets de esta página con los filtros actuales "
        "aplicados. Formato Excel ES (separador `;`, decimal `,`)."
    )
    cols = st.columns(min(len(datasets_no_vacios), 3))
    for i, (etiqueta, df) in enumerate(datasets_no_vacios.items()):
        slug = (
            etiqueta.lower()
            .replace(" ", "_").replace("·", "")
            .replace("á", "a").replace("é", "e").replace("í", "i")
            .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        )
        slug = "".join(c for c in slug if c.isalnum() or c == "_")
        with cols[i % len(cols)]:
            boton_descarga(
                df,
                nombre_fichero=f"{prefijo}_{slug}.csv",
                etiqueta=etiqueta,
                key=f"dl_{prefijo}_{slug}",
            )
