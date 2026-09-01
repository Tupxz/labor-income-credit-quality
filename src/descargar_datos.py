"""
Script de descarga de datos crudos para el Caso 3 (calidad de cartera /
mercado laboral), 2015-01 a 2025-12.

IMPORTANTE — léelo antes de correrlo:
Este script se construyó durante una sesión de Cowork en la nube, cuyo
sandbox tiene el acceso de red restringido a un listado cerrado de
dominios (no puede llegar directamente a superfinanciera.gov.co, dane.gov.co
ni banrep.gov.co). Por eso NO se pudieron descargar los archivos reales
desde esa sesión. Corre este script desde un computador con internet normal
(tu laptop, un Colab, etc.) para que sí funcione.

Requisitos:
    pip install requests

Uso:
    python src/descargar_datos.py

Qué descarga:
    1. SFC — calidad de cartera por modalidad (2 archivos Excel, con y sin
       castigos). Fuente verificada y funcionando.
    2. DANE — anexos mensuales de la GEIH (desempleo, ocupación, ingreso
       laboral), 2015-2025. El script prueba 3 patrones de nombre/carpeta
       conocidos (confirmados desde sep-2022 en adelante); para 2015-01 a
       2022-08 el patrón NO está confirmado y es probable que varios meses
       queden en "NO DISPONIBLE" — el script imprime al final la lista
       exacta de meses pendientes para revisarlos a mano.
    3. BanRep — series vía la API SDMX (tasa de política monetaria mensual,
       IBR diaria, DTF mensual, agregados monetarios M1/M2/M3 mensual).
       FLOW_ID confirmados en la documentación técnica oficial (ver
       docs/fuentes_de_datos.md).

IMPORTANTE — los .xml de BanRep NO son tablas legibles directamente: son
SDMX-XML con las observaciones adentro. Después de correr este script,
corre también:
    python src/procesar_banrep_sdmx.py
para convertirlos en data/processed/banrep_mensual.csv (panel mensual con
tpm, dtf, ibr, trm y M1/M2/M3, ya en filas ene-2015 a dic-2025).

Qué NO descarga (requiere gestión manual, ver docs/fuentes_de_datos.md):
    - IPC (inflación) e ISE (proxy mensual del PIB) de DANE: no se
      encontró un archivo único consolidado; hay que ir al visor de datos
      o consolidar los boletines mensuales.
    - Cartera bruta total/por modalidad de la SFC ("Sistema financiero
      colombiano en cifras"): el listado de reportes mensuales está en
      docs/fuentes_de_datos.md, pero no tiene un idFile único que cubra
      todo 2015-2025 (hay que ubicar el reporte de cada mes o usar el
      Formato 341 agregado).
"""

import os
import time
import requests

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
}

TIMEOUT = 30

# ---------------------------------------------------------------------------
# 1. Superintendencia Financiera de Colombia — calidad de cartera
# ---------------------------------------------------------------------------
SFC_FILES = {
    "sfc_calidad_cartera_sin_castigos.xlsx": (
        "https://www.superfinanciera.gov.co/loader.php?lServicio=Tools2"
        "&lTipo=descargas&lFuncion=descargar&idFile=1070109"
    ),
    "sfc_calidad_cartera_con_castigos.xlsx": (
        "https://www.superfinanciera.gov.co/loader.php?lServicio=Tools2"
        "&lTipo=descargas&lFuncion=descargar&idFile=1070110"
    ),
}


def descargar_sfc():
    destino = os.path.join(RAW_DIR, "sfc")
    os.makedirs(destino, exist_ok=True)
    for nombre, url in SFC_FILES.items():
        ruta = os.path.join(destino, nombre)
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            with open(ruta, "wb") as f:
                f.write(r.content)
            print(f"[OK] {nombre} ({len(r.content) / 1024:.0f} KB)")
        except Exception as e:
            print(f"[FALLA] {nombre}: {e}")


# ---------------------------------------------------------------------------
# 2. DANE — anexos mensuales GEIH (desempleo, ocupación, ingreso laboral)
# ---------------------------------------------------------------------------
MESES = ["ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic"]


def _candidatos_geih(mes, anio):
    """
    DANE ha reorganizado la carpeta/nombre de los anexos GEIH varias veces
    en la ventana 2015-2025. Patrones confirmados navegando
    https://www.dane.gov.co/.../mercado-laboral-historicos y probando
    URLs directamente:

      - may-2023 en adelante:   operaciones/GEIH/anex-GEIH-{mes}{aaaa}.xlsx
      - abr-2023 (excepción):   operaciones/GEIH/EMPLEO_DESEMPLEO/anex-GEIH-{mes}{aaaa}.xlsx
      - may-2017 a mar-2023:    investigaciones/boletines/ech/ech/anexo_empleo_{mes}_{aa}.xlsx
      - ene-2015 a abr-2017:    investigaciones/boletines/ech/ech/anexo_empleo_{mes}_{aa}.xls
        (mismo esquema de nombre, formato Excel viejo .xls)

    Con estos 4 patrones la ventana completa 2015-01 a 2025-12 queda
    cubierta (verificado probando puntualmente varios meses de cada tramo,
    incluyendo los bordes ene-2015, abr-2017/may-2017 y dic-2022/ene-2023).
    Si algún mes puntual sigue fallando, revisar a mano en:
    https://www.dane.gov.co/index.php/estadisticas-por-tema/mercado-laboral/empleo-y-desempleo/geih-historicos
    """
    aa = str(anio)[-2:]
    return [
        f"https://www.dane.gov.co/files/operaciones/GEIH/anex-GEIH-{mes}{anio}.xlsx",
        f"https://www.dane.gov.co/files/operaciones/GEIH/EMPLEO_DESEMPLEO/anex-GEIH-{mes}{anio}.xlsx",
        f"https://www.dane.gov.co/files/investigaciones/boletines/ech/ech/anexo_empleo_{mes}_{aa}.xlsx",
        f"https://www.dane.gov.co/files/investigaciones/boletines/ech/ech/anexo_empleo_{mes}_{aa}.xls",
    ]


def descargar_geih(anio_inicio=2015, anio_fin=2025):
    """Descarga los anexos mensuales de la GEIH, probando varios patrones de
    nombre/carpeta por mes (ver _candidatos_geih) hasta que uno responda."""
    destino = os.path.join(RAW_DIR, "dane_geih")
    os.makedirs(destino, exist_ok=True)
    fallidos = []
    for anio in range(anio_inicio, anio_fin + 1):
        for mes in MESES:
            logrado = False
            for url in _candidatos_geih(mes, anio):
                ext = url.rsplit(".", 1)[-1]  # respeta la extensión real (.xls o .xlsx)
                nombre = f"anex-GEIH-{mes}{anio}.{ext}"
                ruta = os.path.join(destino, nombre)
                try:
                    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                    if r.status_code == 200 and len(r.content) > 1000:
                        with open(ruta, "wb") as f:
                            f.write(r.content)
                        print(f"[OK] {nombre}  <- {url}")
                        logrado = True
                        break
                except Exception:
                    pass
                time.sleep(0.3)
            if not logrado:
                print(f"[NO DISPONIBLE] anex-GEIH-{mes}{anio}.* (ningún patrón conocido funcionó)")
                fallidos.append(f"{mes}{anio}")
    if fallidos:
        print(f"\n{len(fallidos)} meses sin descargar. Revisar manualmente en:")
        print("https://www.dane.gov.co/index.php/estadisticas-por-tema/mercado-laboral/empleo-y-desempleo/geih-historicos")
        print("Meses pendientes:", ", ".join(fallidos))


# ---------------------------------------------------------------------------
# 3. Banco de la República — API SDMX
# ---------------------------------------------------------------------------
SDMX_BASE = "https://totoro.banrep.gov.co/nsi-jax-ws/rest/data"

# FLOW_ID confirmados en el documento técnico oficial:
# https://suameca.banrep.gov.co/archivos/webservices/documento_tecnico_ws_consumo_sdmx.pdf
SDMX_FLOWS = {
    "tpm_mensual": "DF_CBR_MONTHLY_HIST",       # Tasa de política monetaria, promedio mensual
    "ibr_diaria": "DF_IBR_DAILY_HIST",          # IBR (promediar a mensual en el procesamiento)
    "dtf_mensual": "DF_DTF_MONTHLY_HIST",       # DTF, periodicidad mensual
    "agregados_monetarios_mensual": "DF_MONAGG_MONTHLY_HIST",  # M1, M2, M3
    "trm_diaria": "DF_TRM_DAILY_HIST",          # Tasa de cambio (control macro opcional)
}


def descargar_sdmx(start="2015", end="2026"):
    destino = os.path.join(RAW_DIR, "banrep_sdmx")
    os.makedirs(destino, exist_ok=True)
    for nombre, flow_id in SDMX_FLOWS.items():
        url = (
            f"{SDMX_BASE}/ESTAT,{flow_id},1.0/all/ALL/"
            f"?startPeriod={start}&endPeriod={end}"
            f"&dimensionAtObservation=TIME_PERIOD&detail=full"
        )
        ruta = os.path.join(destino, f"{nombre}.xml")
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            with open(ruta, "wb") as f:
                f.write(r.content)
            print(f"[OK] {nombre} ({len(r.content) / 1024:.0f} KB)")
        except Exception as e:
            print(f"[FALLA] {nombre}: {e}")


if __name__ == "__main__":
    print("== SFC: calidad de cartera ==")
    descargar_sfc()
    print("\n== DANE: anexos GEIH mensuales 2015-2025 (puede tardar varios minutos) ==")
    descargar_geih()
    print("\n== BanRep: series SDMX ==")
    descargar_sdmx()
    print("\nListo. Revisa data/raw/ y anota en docs/fuentes_de_datos.md "
          "cualquier archivo que haya fallado.")
