"""
Parsea el anexo mensual de la GEIH (DANE) para extraer los indicadores
agregados de mercado laboral a nivel nacional: tasa de desempleo (TD), tasa
global de participación (TGP) y tasa de ocupación (TO).

A diferencia de lo que sugiere el nombre del archivo (que cambia cada mes),
cada anexo mensual de la GEIH trae en la hoja "Total nacional" la SERIE
HISTÓRICA COMPLETA (2001 hasta el mes de corte del archivo), en formato ancho
(un bloque de 12 columnas por año). Por eso basta con usar el archivo más
reciente disponible en data/raw/dane_geih/ para reconstruir toda la ventana
2015-2025, en vez de parsear los ~130 archivos mensuales uno por uno.

Estructura verificada de la hoja "Total nacional":
    fila 12   -> año (solo en la primera columna de cada bloque de 12 meses)
    fila 13   -> mes abreviado (Ene, Feb, ..., Dic)
    fila 14   -> % población en edad de trabajar
    fila 15   -> Tasa Global de Participación (TGP)
    fila 16   -> Tasa de Ocupación (TO)
    fila 17   -> Tasa de Desocupación (TD)  <- desempleo
    fila 18   -> Tasa de Subocupación (TS)

LIMITACIÓN IMPORTANTE (documentar en docs/fuentes_de_datos.md):
    - Este anexo NO trae informalidad ni ingreso laboral real; eso requiere
      los anexos GEIHEISS (informalidad) y una fuente adicional de ingresos
      (pendiente de gestión manual, ver docs/fuentes_de_datos.md).

Uso:
    python src/procesar_geih.py

Lee de:  data/raw/dane_geih/<archivo más reciente>.xlsx
Escribe: data/processed/dane_mercado_laboral_mensual.csv

Columnas de salida: fecha ("YYYY-MM"), tgp_pct, to_pct, td_pct
"""
import glob
import os
import re
import pandas as pd

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "dane_geih")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

HOJA = "Total nacional"
# Offsets relativos a la fila que contiene la etiqueta "Concepto" (fila ancla),
# porque la posición absoluta de las filas varía ligeramente entre anexos
# mensuales (verificado: en anex-GEIH-ago2025 "Concepto" está en la fila 12,
# en anex-GEIH-dic2025 está en la fila 11).
OFFSET_MES = 1
OFFSETS_INDICADOR = {
    "tgp_pct": 3,
    "to_pct": 4,
    "td_pct": 5,
}


def _fila_ancla_concepto(df):
    col0 = df.iloc[:, 0].astype(str).str.strip()
    filas = df.index[col0 == "Concepto"]
    if len(filas) == 0:
        raise ValueError("No se encontró la fila 'Concepto' en la hoja Total nacional")
    return filas[0]

MESES = {
    "Ene": "01", "Feb": "02", "Mar": "03", "Abr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Ago": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dic": "12",
}


def _archivo_mas_reciente():
    """Escoge el anexo GEIH con la ventana histórica más larga (el más
    reciente por fecha de publicación, no por nombre alfabético)."""
    candidatos = glob.glob(os.path.join(RAW_DIR, "anex-GEIH-*.xlsx"))
    if not candidatos:
        raise FileNotFoundError(f"No se encontraron anexos GEIH en {RAW_DIR}")

    orden_mes = {
        "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
        "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
    }

    def clave(path):
        m = re.search(r"anex-GEIH-([a-z]{3})(\d{4})\.xlsx$", os.path.basename(path))
        if not m:
            return (0, 0)
        mes, anio = m.group(1), int(m.group(2))
        return (anio, orden_mes.get(mes, 0))

    return max(candidatos, key=clave)


def construir_panel_mercado_laboral():
    path = _archivo_mas_reciente()
    df = pd.read_excel(path, sheet_name=HOJA, header=None)

    fila_concepto = _fila_ancla_concepto(df)
    fila_anio = fila_concepto
    fila_mes = fila_concepto + OFFSET_MES

    # Forward-fill del año a lo largo de las columnas.
    anios = df.iloc[fila_anio, 1:].ffill()
    meses = df.iloc[fila_mes, 1:]

    fechas = []
    for anio, mes in zip(anios, meses):
        if pd.isna(anio) or pd.isna(mes) or mes not in MESES:
            fechas.append(None)
        else:
            fechas.append(f"{int(anio)}-{MESES[mes]}")

    datos = {"fecha": fechas}
    for nombre, offset in OFFSETS_INDICADOR.items():
        datos[nombre] = df.iloc[fila_concepto + offset, 1:].values


    panel = pd.DataFrame(datos)
    panel = panel.dropna(subset=["fecha"]).reset_index(drop=True)
    panel = panel.drop_duplicates(subset=["fecha"], keep="last")
    return panel, path


if __name__ == "__main__":
    panel, path_usado = construir_panel_mercado_laboral()
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "dane_mercado_laboral_mensual.csv")
    panel.to_csv(out_path, index=False)
    print(f"Archivo fuente usado: {path_usado}")
    print(f"OK: {len(panel)} filas -> {out_path}")
    print(f"Rango de fechas: {panel['fecha'].min()} a {panel['fecha'].max()}")
