"""
Gráficos y tablas para el documento final y la sustentación del Caso 3.

Mantener los gráficos simples y legibles a distancia (la sustentación es de
20 minutos, con énfasis en gráficos/tablas y poco texto). Guardar las
figuras finales en output/figuras/ y las tablas en output/tablas/.
"""

import matplotlib.pyplot as plt
import pandas as pd


def graficar_npl_vs_desempleo(panel: pd.DataFrame, segmento: str, ruta_salida: str) -> None:
    """Serie de tiempo de NPL (por segmento) vs. tasa de desempleo.

    TODO: implementar con eje secundario para las dos escalas.
    """
    raise NotImplementedError


def tabla_resultados_modelo(resultados, ruta_salida: str) -> None:
    """Exporta una tabla de coeficientes lista para pegar en el Word/slides.

    TODO: dar formato (nombres de variable en español, estrellas de
    significancia, errores estándar entre paréntesis).
    """
    raise NotImplementedError
