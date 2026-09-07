"""
Deflactación de series nominales y descomposición del salario real.

Este es el módulo que reemplaza el atajo de "salario mínimo real". No fija la
fuente del ingreso: recibe cualquier serie nominal mensual (ingreso medio o
mediano de la GEIH, IBC de PILA, salario mínimo si se quiere como contraste) y
devuelve su versión real y la descomposición crecimiento nominal / inflación.

Dos cosas que se hacen bien aquí
--------------------------------
1) La tasa real es multiplicativa, no aditiva:
       g_real = (1 + g_nominal) / (1 + π) - 1
   y NO g_nominal - π. Con la inflación colombiana de 2022-2023 (13,1 % anual en
   marzo de 2023) la aproximación aditiva se equivoca en más de un punto
   porcentual, que es justo el orden de magnitud del efecto que buscamos.

2) La base de deflactación es explícita y arbitraria. Elegir dic-2018 o
   dic-2025 cambia el NIVEL de la serie real, nunca su tasa de crecimiento ni
   su correlación con la mora. Cualquier resultado del modelo que dependa de la
   base elegida es un error de especificación, no un hallazgo.

Uso:
    from deflactar import cargar_ipc, deflactar, descomponer

    ipc = cargar_ipc()
    d = deflactar(ingresos, "ingreso_nominal", ipc, base="2018-12")
    d = descomponer(d, "ingreso_nominal", "ingreso_real", ipc)
"""

from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RUTA_IPC = RAIZ / "data" / "processed" / "dane_ipc_mensual.csv"

BASE_POR_DEFECTO = "2018-12"


def cargar_ipc(ruta: Path = RUTA_IPC) -> pd.DataFrame:
    """Panel mensual del IPC. Correr antes src/procesar_ipc.py."""
    if not ruta.exists():
        raise FileNotFoundError(f"Falta {ruta}. Correr primero: python src/procesar_ipc.py")
    ipc = pd.read_csv(ruta)
    ipc["fecha"] = pd.PeriodIndex(ipc["fecha"], freq="M")
    return ipc[["fecha", "ipc_indice", "ipc_var_mensual", "ipc_var_anual"]]


def _preparar(df: pd.DataFrame, col_fecha: str) -> pd.DataFrame:
    d = df.copy()
    if not isinstance(d[col_fecha].dtype, pd.PeriodDtype):
        d[col_fecha] = pd.PeriodIndex(d[col_fecha].astype(str), freq="M")
    return d


def deflactar(df: pd.DataFrame, columnas, ipc: pd.DataFrame | None = None,
              base: str = BASE_POR_DEFECTO, col_fecha: str = "fecha",
              sufijo: str = "_real") -> pd.DataFrame:
    """
    Pasa una o varias series nominales a pesos constantes de `base`.

        valor_real = valor_nominal * (IPC_base / IPC_t)

    `base` es un mes 'AAAA-MM'. Solo reescala el nivel.
    """
    if isinstance(columnas, str):
        columnas = [columnas]
    ipc = cargar_ipc() if ipc is None else ipc

    d = _preparar(df, col_fecha)
    # Si el IPC ya viene en el DataFrame (p. ej. desde consolidar_panel), no se
    # vuelve a pegar: un segundo merge crearía ipc_indice_x / ipc_indice_y.
    if "ipc_indice" not in d.columns:
        d = d.merge(ipc[["fecha", "ipc_indice"]].rename(columns={"fecha": col_fecha}),
                    on=col_fecha, how="left")

    faltan = d["ipc_indice"].isna().sum()
    if faltan:
        rango = f"{ipc.fecha.min()} a {ipc.fecha.max()}"
        print(f"  aviso: {faltan} filas sin IPC (el IPC cubre {rango})")

    per_base = pd.Period(base, freq="M")
    fila = ipc.loc[ipc["fecha"] == per_base, "ipc_indice"]
    if fila.empty:
        raise ValueError(f"El IPC no tiene el mes base {base}")
    ipc_base = float(fila.iloc[0])

    for c in columnas:
        d[f"{c}{sufijo}"] = d[c] * ipc_base / d["ipc_indice"]

    d.attrs["base_deflactacion"] = base
    return d


def descomponer(df: pd.DataFrame, col_nominal: str, col_real: str | None = None,
                ipc: pd.DataFrame | None = None, col_fecha: str = "fecha",
                grupo: list | None = None, meses: int = 12) -> pd.DataFrame:
    """
    Descompone el crecimiento del ingreso en sus dos piezas:
    lo que subió el salario nominal y lo que subieron los precios.

    Devuelve, en variación a `meses` (12 = anual):
        var_nominal   crecimiento del ingreso nominal (%)
        inflacion     variación del IPC en la misma ventana (%)
        var_real      crecimiento real exacto, (1+g)/(1+π)-1 (%)
        var_real_aprox   la resta g - π, solo para mostrar el error de la
                         aproximación aditiva; no usar en el modelo
        brecha_aprox  var_real_aprox - var_real (pp)
    """
    col_real = col_real or f"{col_nominal}_real"
    ipc = cargar_ipc() if ipc is None else ipc
    d = _preparar(df, col_fecha)

    if "ipc_indice" not in d.columns:
        d = d.merge(ipc[["fecha", "ipc_indice"]].rename(columns={"fecha": col_fecha}),
                    on=col_fecha, how="left")

    d = d.sort_values((grupo or []) + [col_fecha])
    g = d.groupby(grupo, observed=True) if grupo else d

    d["var_nominal"] = (g[col_nominal].pct_change(meses, fill_method=None) if grupo
                        else d[col_nominal].pct_change(meses, fill_method=None)) * 100
    d["inflacion"] = (g["ipc_indice"].pct_change(meses, fill_method=None) if grupo
                      else d["ipc_indice"].pct_change(meses, fill_method=None)) * 100

    if col_real in d.columns:
        d["var_real"] = (g[col_real].pct_change(meses, fill_method=None) if grupo
                         else d[col_real].pct_change(meses, fill_method=None)) * 100
    else:
        d["var_real"] = ((1 + d["var_nominal"] / 100) / (1 + d["inflacion"] / 100) - 1) * 100

    d["var_real_aprox"] = d["var_nominal"] - d["inflacion"]
    d["brecha_aprox"] = d["var_real_aprox"] - d["var_real"]
    return d


def salario_minimo_mensual(desde: int = 2003, hasta: int = 2026) -> pd.DataFrame:
    """
    SMMLV mensual (sin auxilio de transporte), expandido a serie mensual.

    Está aquí SOLO para poder mostrar el contraste con el ingreso de la GEIH en
    la nota metodológica: el mínimo es un precio administrado que salta una vez
    al año, no una medida de la capacidad de pago del deudor. No usarlo como
    regresor principal.
    """
    smmlv = {2003: 332000, 2004: 358000, 2005: 381500, 2006: 408000, 2007: 433700,
             2008: 461500, 2009: 496900, 2010: 515000, 2011: 535600, 2012: 566700,
             2013: 589500, 2014: 616000, 2015: 644350, 2016: 689455, 2017: 737717,
             2018: 781242, 2019: 828116, 2020: 877803, 2021: 908526, 2022: 1000000,
             2023: 1160000, 2024: 1300000, 2025: 1423500, 2026: 1750905}
    filas = [{"fecha": pd.Period(f"{a}-{m:02d}", freq="M"), "smmlv": v}
             for a, v in smmlv.items() if desde <= a <= hasta for m in range(1, 13)]
    return pd.DataFrame(filas).sort_values("fecha").reset_index(drop=True)


if __name__ == "__main__":
    # Demostración con el SMMLV: cuánto se equivoca la aproximación aditiva y
    # qué tan poca información mensual tiene el mínimo.
    ipc = cargar_ipc()
    d = salario_minimo_mensual()
    d = deflactar(d, "smmlv", ipc)
    d = descomponer(d, "smmlv", "smmlv_real", ipc)
    d = d[d.fecha >= pd.Period("2015-01", freq="M")]

    print("SMMLV real (pesos constantes de dic-2018) y descomposición\n")
    print(d[d.fecha.astype(str).str.endswith(("-01", "-12"))]
          .tail(16)[["fecha", "smmlv", "smmlv_real", "var_nominal",
                     "inflacion", "var_real", "var_real_aprox", "brecha_aprox"]]
          .round(2).to_string(index=False))
    print(f"\nError máximo de la aproximación aditiva (g - π): "
          f"{d.brecha_aprox.abs().max():.2f} pp")
    print(f"Meses del año en que cambia el SMMLV nominal: "
          f"{(d.groupby(d.fecha.dt.year).smmlv.nunique()).max()} valor distinto por año")
