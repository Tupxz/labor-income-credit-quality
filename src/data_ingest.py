"""
Ingesta de datos para el Caso 3 (calidad de cartera / mercado laboral).

Cada función debe:
1. Descargar o leer el archivo crudo correspondiente (guardado sin modificar en data/raw/).
2. Devolver un DataFrame con columnas estandarizadas: ['fecha', 'segmento' (si aplica), 'valor'].
3. Documentar en docs/fuentes_de_datos.md la fecha de corte y de descarga.

Ver docs/fuentes_de_datos.md para los enlaces exactos de cada fuente.
"""

import pandas as pd


def cargar_calidad_cartera_sfc(path_raw: str) -> pd.DataFrame:
    """Carga cartera bruta, cartera vencida y provisiones por modalidad (SFC).

    TODO: implementar lectura del archivo descargado de
    'Sistema financiero colombiano en cifras' (SFC) y calcular el indicador
    de calidad de cartera (ICV = cartera vencida / cartera bruta) por
    modalidad (consumo, vivienda, microcrédito, comercial).
    """
    raise NotImplementedError


def cargar_tasas_banrep(path_raw: str) -> pd.DataFrame:
    """Carga tasa de política, IBR y tasas de captación/colocación (BanRep).

    TODO: implementar lectura de las series descargadas del catálogo de
    estadísticas de BanRep (https://www.banrep.gov.co/es/estadisticas/catalogo).
    """
    raise NotImplementedError


def cargar_agregados_banrep(path_raw: str) -> pd.DataFrame:
    """Carga agregados monetarios y crediticios, PIB e inflación (BanRep/DANE).

    TODO: implementar lectura y homologación de periodicidad (mensual/trimestral).
    """
    raise NotImplementedError


def cargar_mercado_laboral_dane(path_raw: str) -> pd.DataFrame:
    """Carga tasa de desempleo, informalidad e ingreso laboral (GEIH, DANE).

    TODO: implementar lectura de series GEIH y deflactar el ingreso laboral
    nominal con el IPC para obtener ingreso laboral real.
    """
    raise NotImplementedError


def construir_panel(*dataframes: pd.DataFrame) -> pd.DataFrame:
    """Consolida las series individuales en el panel segmento x tiempo.

    TODO: hacer merge por fecha (y segmento cuando aplique), validar
    continuidad temporal y guardar el resultado en
    data/processed/panel_calidad_cartera.csv.
    """
    raise NotImplementedError
