"""
Especificación y estimación del modelo econométrico del Caso 3.

Especificación base (panel dinámico, ver PLAN_DE_TRABAJO.md sección 5):

    NPL_ratio(s, t) = f(desempleo(t-k), informalidad(t-k), delta_ingreso_real(t-k),
                        inflacion(t), tasa_politica(t), controles(t)) + efectos_fijos(s)

con una interacción desempleo(t-k) * tasa_politica(t) para probar el rol
moderador de la política monetaria (hipótesis H2 del pre-plan).

Robustez sugerida: VAR/VECM agregado (statsmodels.tsa.api.VAR) entre
desempleo, ingreso real, NPL agregado y tasa de política, para funciones
impulso-respuesta (hipótesis H3, simultaneidad).
"""

import pandas as pd


def preparar_variables(panel: pd.DataFrame, rezagos: int = 2) -> pd.DataFrame:
    """Genera rezagos, diferencias e interacciones necesarias para el modelo.

    TODO: construir desempleo(t-k), delta_ingreso_real(t-k) y la interacción
    desempleo(t-k) * tasa_politica(t).
    """
    raise NotImplementedError


def estimar_panel_efectos_fijos(panel: pd.DataFrame):
    """Estima el panel dinámico de efectos fijos por segmento.

    TODO: usar linearmodels.PanelOLS (o Arellano-Bond si N x T lo justifica).
    """
    raise NotImplementedError


def estimar_var_robustez(series_agregadas: pd.DataFrame):
    """Estima el VAR agregado para robustez y funciones impulso-respuesta.

    TODO: usar statsmodels.tsa.api.VAR; revisar estacionariedad (ADF/KPSS)
    antes de estimar.
    """
    raise NotImplementedError
