"""
Consolida el panel final del Caso 3: segmento de cartera × mes, uniendo:
    - Calidad de cartera por segmento (SFC)        -> data/processed/sfc_icv_mensual.csv
    - Costo del crédito y agregados (BanRep)        -> data/processed/banrep_mensual.csv
    - Mercado laboral (DANE-GEIH, nivel nacional)   -> data/processed/dane_mercado_laboral_mensual.csv

Las variables de BanRep y GEIH son de nivel nacional (no varían por
segmento de cartera), así que se repiten para los 5 segmentos
(total, comercial, consumo, vivienda, microcredito) en cada mes.

Ventana de análisis: la intersección de las tres fuentes está acotada por
el archivo de la SFC, que solo llega hasta 2023-12 (ver limitación en
src/procesar_sfc_calidad_cartera.py). Por eso el panel consolidado cubre
2015-01 a 2023-12, aunque BanRep y GEIH ya tienen datos hasta 2025-12.

PENDIENTE (documentar como limitación en el entregable, Sección 3):
    - Actualizar SFC 2024-2025 (gestión manual, ver docs/fuentes_de_datos.md)
      para poder usar la ventana completa de BanRep/GEIH.
    - Incorporar informalidad e ingreso laboral real (pendientes de fuente,
      ver docs/fuentes_de_datos.md) — de momento el panel solo trae TD/TGP/TO.
    - Incorporar IPC para deflactar variables nominales (pendiente).

Uso:
    python src/consolidar_panel.py

Escribe: data/processed/panel_calidad_cartera.csv
"""
import os
import pandas as pd

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

FECHA_INICIO = "2015-01"
FECHA_FIN = "2023-12"


def consolidar():
    sfc = pd.read_csv(os.path.join(PROCESSED_DIR, "sfc_icv_mensual.csv"))
    banrep = pd.read_csv(os.path.join(PROCESSED_DIR, "banrep_mensual.csv"))
    geih = pd.read_csv(os.path.join(PROCESSED_DIR, "dane_mercado_laboral_mensual.csv"))

    panel = sfc.merge(banrep, on="fecha", how="left")
    panel = panel.merge(geih, on="fecha", how="left")

    panel = panel[(panel["fecha"] >= FECHA_INICIO) & (panel["fecha"] <= FECHA_FIN)]
    panel = panel.sort_values(["segmento", "fecha"]).reset_index(drop=True)
    return panel


if __name__ == "__main__":
    panel = consolidar()
    out_path = os.path.join(PROCESSED_DIR, "panel_calidad_cartera.csv")
    panel.to_csv(out_path, index=False)
    print(f"OK: {len(panel)} filas, {panel.shape[1]} columnas -> {out_path}")
    print(f"Ventana: {panel['fecha'].min()} a {panel['fecha'].max()}")
    print(f"Segmentos: {sorted(panel['segmento'].unique())}")
    print("\nValores faltantes por columna:")
    print(panel.isna().sum())
