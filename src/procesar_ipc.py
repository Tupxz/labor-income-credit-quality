"""
Convierte los anexos del IPC del DANE (matriz mes x año) en un panel mensual limpio.

Sobre la base del índice
------------------------
El archivo de índices es la SERIE DE EMPALME 2003-2026 con base diciembre 2018 = 100.
Esa es la base oficial vigente del IPC colombiano y el empalme ya resuelve el cambio
de canasta y metodología de 2019 — no es un defecto de la fuente. Y en todo caso la
base es una normalización: cambiarla mueve el nivel del índice, no las tasas de
crecimiento reales. El problema de deflactar con el salario mínimo NO está en la
base del IPC sino en el numerador (ver docs/nota_metodologica.md).

Salida: data/processed/dane_ipc_mensual.csv
    fecha, ipc_indice, ipc_var_mensual, ipc_var_anual

Uso:  python src/procesar_ipc.py
"""

from pathlib import Path
import sys
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CRUDO = RAIZ / "data" / "raw" / "dane_ipc"
SALIDA = RAIZ / "data" / "processed" / "dane_ipc_mensual.csv"

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
         "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
         "noviembre": 11, "diciembre": 12}


def buscar(patron: str) -> Path:
    """Toma el archivo más reciente que haga match, para no romper al actualizar."""
    cands = sorted(CRUDO.glob(patron), key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands:
        sys.exit(f"No encuentro ningún archivo '{patron}' en {CRUDO}")
    return cands[0]


def leer_matriz_mes_anio(ruta: Path, hoja: str, nombre_valor: str) -> pd.DataFrame:
    """
    Los anexos del IPC vienen como matriz: filas = meses (Enero..Diciembre),
    columnas = años. La fila de encabezado se mueve entre ediciones, así que se
    detecta buscando la fila cuya primera celda dice 'Mes'.
    """
    crudo = pd.read_excel(ruta, sheet_name=hoja, header=None)

    fila_enc = None
    for i in range(len(crudo)):
        if str(crudo.iat[i, 0]).strip().lower() == "mes":
            fila_enc = i
            break
    if fila_enc is None:
        sys.exit(f"No encuentro la fila de encabezado ('Mes') en {ruta.name}")

    anios = {}
    for j in range(1, crudo.shape[1]):
        v = crudo.iat[fila_enc, j]
        try:
            a = int(float(v))
        except (TypeError, ValueError):
            continue
        if 1990 <= a <= 2100:
            anios[j] = a

    filas = []
    for i in range(fila_enc + 1, len(crudo)):
        etiqueta = str(crudo.iat[i, 0]).strip().lower()
        mes = MESES.get(etiqueta)
        if mes is None:
            continue
        for j, anio in anios.items():
            val = pd.to_numeric(crudo.iat[i, j], errors="coerce")
            if pd.notna(val):
                filas.append({"fecha": pd.Period(f"{anio}-{mes:02d}", freq="M"),
                              nombre_valor: float(val)})

    if not filas:
        sys.exit(f"No extraje ningún dato de {ruta.name}")
    return pd.DataFrame(filas).sort_values("fecha").reset_index(drop=True)


def main() -> None:
    f_idx = buscar("anex-IPC-Indices-*.xlsx")
    f_var = buscar("anex-IPC-Variacion-*.xlsx")
    print(f"Índices:   {f_idx.name}")
    print(f"Variación: {f_var.name}")

    idx = leer_matriz_mes_anio(f_idx, "IndicesIPC", "ipc_indice")
    var = leer_matriz_mes_anio(f_var, "VarNal", "ipc_var_mensual_dane")

    d = idx.merge(var, on="fecha", how="left")
    d["ipc_var_mensual"] = d["ipc_indice"].pct_change() * 100
    d["ipc_var_anual"] = d["ipc_indice"].pct_change(12) * 100

    # Control de calidad: la variación implícita en el índice tiene que coincidir
    # con la que publica el DANE (salvo redondeo del índice a 2 decimales).
    dif = (d["ipc_var_mensual"] - d["ipc_var_mensual_dane"]).abs()
    print(f"\nChequeo índice vs. variación publicada: dif. máx = {dif.max():.4f} pp, "
          f"media = {dif.mean():.4f} pp")
    if dif.max() > 0.1:
        print("  ¡OJO! divergencia mayor a 0,1 pp — revisar el empalme del archivo.")

    d = d.drop(columns=["ipc_var_mensual_dane"])
    d["fecha"] = d["fecha"].astype(str)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(SALIDA, index=False)

    print(f"\nEscrito {SALIDA.relative_to(RAIZ)}: {len(d)} meses, "
          f"{d.fecha.min()} a {d.fecha.max()}")
    base = d.loc[d.fecha == "2018-12", "ipc_indice"]
    if len(base):
        print(f"Base dic-2018 = {base.iloc[0]:.2f}  (debe ser 100)")
    print("\nÚltimos 6 meses:")
    print(d.tail(6).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
