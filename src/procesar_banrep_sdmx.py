"""
Parsea los archivos SDMX (XML) descargados por src/descargar_datos.py desde
la API de BanRep y arma un panel mensual consolidado.

Los archivos .xml que descarga descargar_datos.py vienen en formato SDMX
"Generic Data" — son XML reales con las observaciones adentro, pero no son
directamente legibles como tabla (por eso, al abrirlos, parecen "no tener
datos"). Este script los convierte en un CSV normal.

Uso:
    python src/procesar_banrep_sdmx.py

Lee de:  data/raw/banrep_sdmx/*.xml
Escribe: data/processed/banrep_mensual.csv  (una fila por mes, ene-2015 a dic-2025)

Columnas de salida:
    fecha                    "YYYY-MM"
    tpm_pct                  Tasa de política monetaria, promedio mensual (%)
    dtf_pct                  DTF, promedio mensual (%)
    ibr_pct_prom_mensual     IBR diaria promediada a mensual (%)
    trm_prom_mensual         TRM diaria promediada a mensual (COP/USD)
    m1_mm_cop, m2_mm_cop,
    m3_mm_cop                Agregados monetarios M1/M2/M3 (unidad tal como la
                              reporta BanRep vía SDMX — VERIFICAR el orden de
                              magnitud contra una cifra oficial conocida antes
                              de usarlos en el modelo; el atributo UNIT_MULT
                              del XML no deja 100% claro si ya vienen en miles
                              de millones o en otra escala).
"""
import os
import xml.etree.ElementTree as ET
import pandas as pd

NS = {"generic": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic"}
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "banrep_sdmx")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


def parse_sdmx_generic(path):
    """Convierte un archivo SDMX-ML (Generic Data) en un DataFrame largo
    con una fila por observación (columnas de la SeriesKey + fecha + valor)."""
    tree = ET.parse(path)
    root = tree.getroot()
    rows = []
    tag_series = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic}Series"
    for series in root.iter(tag_series):
        key = {}
        keyset = series.find("generic:SeriesKey", NS)
        for v in keyset.findall("generic:Value", NS):
            key[v.get("id")] = v.get("value")
        for obs in series.findall("generic:Obs", NS):
            dim = obs.find("generic:ObsDimension", NS).get("value")
            val = obs.find("generic:ObsValue", NS).get("value")
            row = dict(key)
            row["fecha"] = dim
            row["valor"] = float(val)
            rows.append(row)
    return pd.DataFrame(rows)


def a_mensual_desde_diaria(df, col_salida):
    """Recibe un DataFrame largo con fechas diarias en formato YYYYMMDD y
    devuelve una serie mensual (promedio del mes) indexada por 'YYYY-MM'."""
    d = df.copy()
    d["fecha_dt"] = pd.to_datetime(d["fecha"], format="%Y%m%d")
    d["mes"] = d["fecha_dt"].dt.to_period("M").astype(str)
    return d.groupby("mes")["valor"].mean().rename(col_salida)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    tpm = parse_sdmx_generic(os.path.join(RAW_DIR, "tpm_mensual.xml")).set_index("fecha")["valor"].rename("tpm_pct")
    dtf = parse_sdmx_generic(os.path.join(RAW_DIR, "dtf_mensual.xml")).set_index("fecha")["valor"].rename("dtf_pct")

    ibr = parse_sdmx_generic(os.path.join(RAW_DIR, "ibr_diaria.xml"))
    ibr_m = a_mensual_desde_diaria(ibr, "ibr_pct_prom_mensual")

    trm = parse_sdmx_generic(os.path.join(RAW_DIR, "trm_diaria.xml"))
    trm_m = a_mensual_desde_diaria(trm, "trm_prom_mensual")

    agg = parse_sdmx_generic(os.path.join(RAW_DIR, "agregados_monetarios_mensual.xml"))
    m1 = agg[(agg.SUBJECT == "M1") & (agg.ADJUSTMENT == "N")].set_index("fecha")["valor"].rename("m1_mm_cop")
    m2 = agg[(agg.SUBJECT == "M2") & (agg.ADJUSTMENT == "N")].set_index("fecha")["valor"].rename("m2_mm_cop")
    m3 = agg[(agg.SUBJECT == "M3") & (agg.ADJUSTMENT == "N")].set_index("fecha")["valor"].rename("m3_mm_cop")

    panel = pd.concat([tpm, dtf, ibr_m, trm_m, m1, m2, m3], axis=1)
    panel.index.name = "fecha"
    panel = panel.sort_index()
    panel = panel.loc["2015-01":"2025-12"]  # recorta a la ventana objetivo del caso

    ruta_salida = os.path.join(OUT_DIR, "banrep_mensual.csv")
    panel.to_csv(ruta_salida)
    print(f"Panel mensual BanRep guardado en {ruta_salida}")
    print(panel.shape)
    print(panel.head())
    print(panel.tail())


if __name__ == "__main__":
    main()
