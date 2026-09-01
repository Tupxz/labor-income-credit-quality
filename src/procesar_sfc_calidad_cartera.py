"""
Parsea los archivos Excel de la SFC ("Indicador de Calidad de Cartera por
Vencimiento") descargados por src/descargar_datos.py y arma un panel mensual
por segmento de cartera (total, comercial, consumo, vivienda, microcrédito).

Los archivos originales NO son tablas planas: son reportes con varios bloques
apilados en la misma hoja (uno por segmento de cartera), cada uno con el ICV
desagregado por *tipo de entidad* (bancos, compañías de financiamiento,
cooperativos, IOE, cooperativas financieras) y, al final de cada bloque, dos
filas de agregado del sistema:
    - "Establecimientos de Crédito + FNA"
    - "Establecimientos de Crédito"   <- fila que usamos (agregado del
      sistema de establecimientos de crédito, sin el FNA)

Estructura verificada (primera hoja de cada archivo, índice 0):
    fila 5        -> fechas (una por columna, desde la columna 5 en adelante)
    fila 6/20/34/48/62  -> título del bloque (Cartera Total/Comercial/
                           Consumo/Vivienda/Microcrédito)
    fila 15/29/43/57/71 -> fila "Establecimientos de Crédito" (agregado
                           del sistema) para ese segmento

Nota: el nombre de la primera hoja difiere entre archivos ("ICV  Sistema" en
el archivo sin castigos vs. "ICV+Castigos  Sistema" en el de con castigos),
por eso se referencia por índice (0) y no por nombre.

Uso:
    python src/procesar_sfc_calidad_cartera.py

Lee de:  data/raw/sfc/sfc_calidad_cartera_sin_castigos.xlsx
         data/raw/sfc/sfc_calidad_cartera_con_castigos.xlsx
Escribe: data/processed/sfc_icv_mensual.csv

Columnas de salida:
    fecha                 "YYYY-MM"
    segmento              total | comercial | consumo | vivienda | microcredito
    icv_sin_castigos      ICV del sistema de establecimientos de crédito (proporción, 0-1)
    icv_con_castigos      Idem, incluyendo cartera castigada

LIMITACIÓN IMPORTANTE (documentar en docs/fuentes_de_datos.md):
    - Los archivos descargados solo cubren 2011-01 a 2023-12. Falta gestionar
      manualmente la actualización 2024-2025 (ver "Sistema financiero
      colombiano en cifras" en la web de la SFC).
"""
import os
import pandas as pd

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "sfc")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

ARCHIVOS = {
    "icv_sin_castigos": "sfc_calidad_cartera_sin_castigos.xlsx",
    "icv_con_castigos": "sfc_calidad_cartera_con_castigos.xlsx",
}

# fila del bloque "Establecimientos de Crédito" -> segmento
FILAS_SEGMENTO = {
    15: "total",
    29: "comercial",
    43: "consumo",
    57: "vivienda",
    71: "microcredito",
}

FILA_FECHAS = 5
COL_INICIO_DATOS = 5


def _parsear_archivo(path, nombre_columna):
    df = pd.read_excel(path, sheet_name=0, header=None)
    fechas = df.iloc[FILA_FECHAS, COL_INICIO_DATOS:]
    fechas = pd.to_datetime(fechas, errors="coerce")

    registros = []
    for fila, segmento in FILAS_SEGMENTO.items():
        valores = df.iloc[fila, COL_INICIO_DATOS:]
        for fecha, valor in zip(fechas, valores):
            if pd.isna(fecha) or pd.isna(valor):
                continue
            registros.append(
                {
                    "fecha": fecha.strftime("%Y-%m"),
                    "segmento": segmento,
                    nombre_columna: float(valor),
                }
            )
    return pd.DataFrame(registros)


def construir_panel_sfc():
    paneles = []
    for nombre_columna, archivo in ARCHIVOS.items():
        path = os.path.join(RAW_DIR, archivo)
        paneles.append(_parsear_archivo(path, nombre_columna))

    panel = paneles[0]
    for otro in paneles[1:]:
        panel = panel.merge(otro, on=["fecha", "segmento"], how="outer")

    panel = panel.sort_values(["segmento", "fecha"]).reset_index(drop=True)
    return panel


if __name__ == "__main__":
    panel = construir_panel_sfc()
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "sfc_icv_mensual.csv")
    panel.to_csv(out_path, index=False)
    print(f"OK: {len(panel)} filas -> {out_path}")
    print(f"Rango de fechas: {panel['fecha'].min()} a {panel['fecha'].max()}")
    print(panel.groupby("segmento")["fecha"].agg(["min", "max", "count"]))
