"""
Panel final del Caso 3: PRODUCTO DE CARTERA × MES, 2015-01 a 2026-06.

Une la calidad de cartera (SFC, nivel producto) con las variables nacionales
—costo del crédito y agregados (BanRep), mercado laboral (GEIH), precios (IPC)
e ingreso laboral (microdatos GEIH)—, que no varían por producto y por tanto se
repiten en cada celda.

Criterio de ventana
-------------------
El panel se arma sobre la ventana COMPLETA de la cartera (2015-01 a 2026-06) y
deja NaN donde una fuente todavía no llega, en vez de recortar a la intersección.
Así, cuando entren los datos que faltan, no hay que reestructurar nada: se vuelve
a correr y se llena. El bloque de cobertura que imprime al final dice exactamente
hasta dónde llega cada serie.

Variables derivadas que se construyen aquí
-------------------------------------------
- `tpm_real`: tasa de política en términos reales, (1+i)/(1+π)−1. La nominal
  mezcla dos cosas distintas —el apretón monetario y la inflación esperada— y es
  la real la que pesa sobre la capacidad de pago del deudor.
- `cartera_real` y `cartera_var_real_anual`: controla el EFECTO DENOMINADOR. El
  ICV es un cociente: si la originación se frena, el denominador deja de crecer
  mientras el vencido acumula, y el ICV sube sin que nadie se comporte peor.
  Sin este control el modelo confunde deterioro con desaceleración del crédito.
- `ingreso_*_real` y su variación: cuando existan los microdatos.

Uso:  python src/consolidar_panel.py
"""

from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deflactar import cargar_ipc, deflactar  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
PROC = RAIZ / "data" / "processed"

VENTANA_INICIO = "2015-01"
BASE_REAL = "2018-12"   # solo fija el nivel de las series reales, no su crecimiento

FUENTES = {
    "cartera_producto": PROC / "sfc_cartera_producto_mensual.csv",
    "cartera_familia": PROC / "sfc_cartera_familia_mensual.csv",
    "banrep": PROC / "banrep_mensual.csv",
    "laboral": PROC / "dane_mercado_laboral_mensual.csv",
    "ipc": PROC / "dane_ipc_mensual.csv",
    "ingreso": PROC / "geih_ingreso_laboral_mensual.csv",   # opcional, aún no existe
}


def leer(clave: str, obligatoria: bool = True) -> pd.DataFrame | None:
    ruta = FUENTES[clave]
    if not ruta.exists():
        if obligatoria:
            sys.exit(f"Falta {ruta.relative_to(RAIZ)}. Ver el pipeline en el README.")
        return None
    return pd.read_csv(ruta)


def construir(nivel: str) -> pd.DataFrame:
    """nivel: 'producto' o 'familia'."""
    cartera = leer(f"cartera_{nivel}")
    banrep = leer("banrep")
    laboral = leer("laboral")
    ipc = leer("ipc")
    ingreso = leer("ingreso", obligatoria=False)

    llave = ["unicap", "producto", "familia"] if nivel == "producto" else ["familia"]

    p = cartera.merge(banrep, on="fecha", how="left")
    p = p.merge(laboral, on="fecha", how="left")
    p = p.merge(ipc, on="fecha", how="left")

    if ingreso is not None:
        p = p.merge(ingreso, on="fecha", how="left")

    p = p[p["fecha"] >= VENTANA_INICIO].copy()

    # --- Costo del crédito en términos reales -----------------------------
    for nominal in ["tpm_pct", "dtf_pct", "ibr_pct_prom_mensual"]:
        if nominal in p.columns:
            p[nominal.replace("_pct", "").replace("_prom_mensual", "") + "_real"] = (
                ((1 + p[nominal] / 100) / (1 + p["ipc_var_anual"] / 100) - 1) * 100
            )

    # --- Cartera en términos reales (efecto denominador) ------------------
    ipc_df = cargar_ipc()
    p = deflactar(p, "cartera_bruta", ipc_df, base=BASE_REAL)
    p["fecha"] = p["fecha"].astype(str)
    p = p.sort_values(llave + ["fecha"])
    p["cartera_var_real_anual"] = (
        p.groupby(llave, observed=True)["cartera_bruta_real"]
        .pct_change(12, fill_method=None) * 100
    )

    # --- Informalidad, calculada desde los microdatos ---------------------
    # La serie que publica el DANE ("Prop informalidad" del anexo GEIHEISS) solo
    # arranca en 2021 y cambió de definición en 2022. Desde los microdatos se
    # obtiene una medida consistente para los 138 meses: proporción de ocupados
    # que NO cotiza a pensión (la definición de "informalidad fuerte"). No es
    # idéntica a la oficial —para 2021 da ~63 % contra ~61 % del DANE— pero es
    # la misma definición de punta a punta, que es lo que necesita el modelo.
    if {"formal_ocupados", "informal_ocupados"} <= set(p.columns):
        p["informalidad_pct"] = (p["informal_ocupados"] /
                                 (p["formal_ocupados"] + p["informal_ocupados"]) * 100)

    # --- Ingreso laboral real ---------------------------------------------
    # Solo las medidas que entran al modelo: deflactar las 10 aperturas
    # llenaría el panel de columnas que nadie usa.
    cols_ing = [c for c in ["total_media", "total_mediana",
                            "formal_mediana", "informal_mediana"] if c in p.columns]
    if cols_ing:
        p = deflactar(p, cols_ing, ipc_df, base=BASE_REAL)
        p["fecha"] = p["fecha"].astype(str)
        p = p.sort_values(llave + ["fecha"])
        for c in cols_ing:
            p[f"{c}_var_real_anual"] = (
                p.groupby(llave, observed=True)[f"{c}_real"]
                .pct_change(12, fill_method=None) * 100
            )

    return p.drop(columns=["ipc_indice"], errors="ignore").reset_index(drop=True)


def cobertura(p: pd.DataFrame, llave: list) -> pd.DataFrame:
    """Hasta dónde llega cada serie y cuánto le falta para cerrar la ventana."""
    fin = p["fecha"].max()
    filas = []
    for c in p.columns:
        if c in llave + ["fecha"]:
            continue
        con_dato = p.loc[p[c].notna(), "fecha"]
        if con_dato.empty:
            filas.append({"variable": c, "hasta": "—", "faltan_meses": None, "% NaN": 100.0})
            continue
        ultimo = con_dato.max()
        faltan = len(pd.period_range(ultimo, fin, freq="M")) - 1
        filas.append({"variable": c, "hasta": ultimo, "faltan_meses": faltan,
                      "% NaN": round(p[c].isna().mean() * 100, 1)})
    return pd.DataFrame(filas)


def main() -> None:
    for nivel, salida in [("producto", "panel_calidad_cartera.csv"),
                          ("familia", "panel_calidad_cartera_familia.csv")]:
        p = construir(nivel)
        p.to_csv(PROC / salida, index=False)
        llave = ["unicap", "producto", "familia"] if nivel == "producto" else ["familia"]
        print(f"\n{'=' * 68}\nNIVEL {nivel.upper()}  ->  data/processed/{salida}")
        print(f"  {len(p):,} filas × {p.shape[1]} columnas | "
              f"{p.fecha.min()} a {p.fecha.max()} ({p.fecha.nunique()} meses)")
        if nivel == "producto":
            print(f"  {p.producto.nunique()} productos")

            cob = cobertura(p, llave)
            incompletas = cob[cob.faltan_meses.fillna(999) > 0].sort_values("faltan_meses",
                                                                           ascending=False)
            print("\n  Series que NO cierran la ventana de la cartera:")
            if incompletas.empty:
                print("    ninguna — el panel está completo.")
            else:
                print(incompletas.to_string(index=False))


if __name__ == "__main__":
    main()
