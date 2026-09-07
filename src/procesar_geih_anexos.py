"""
Serie mensual de mercado laboral desde los anexos de la GEIH — original y
desestacionalizada.

Sustituye a procesar_geih.py, que solo leía la serie original.

Por qué importa la desestacionalizada
-------------------------------------
La tasa de desempleo sube en promedio +3,2 pp cada enero y se mueve entre −1,3 y
+0,7 el resto del año (ver output/tablas/tabla4_estacionalidad.csv). Cualquier
modelo en primeras diferencias sobre la serie original está midiendo el
calendario, no el ciclo. El DANE publica la versión desestacionalizada y es la
que hay que usar como regresor; la original queda como referencia y para replicar
cifras publicadas.

Ambos anexos comparten el mismo diseño: fila "Concepto" con los años, la fila de
abajo con los meses, y los conceptos como filas.

Salida: data/processed/dane_mercado_laboral_mensual.csv
    fecha, tgp_pct, to_pct, td_pct, ocupados_miles, desocupados_miles,
    tgp_sa_pct, to_sa_pct, td_sa_pct, ocupados_sa_miles

Uso:  python src/procesar_geih_anexos.py
"""

from pathlib import Path
import re
import sys
import unicodedata

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CRUDO = RAIZ / "data" / "raw" / "dane_geih"
SALIDA = RAIZ / "data" / "processed" / "dane_mercado_laboral_mensual.csv"

MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
         "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}

# concepto en el anexo -> nombre de columna
CONCEPTOS = {
    "tasa global de participacion": "tgp",
    "tasa de ocupacion": "to",
    "tasa de desocupacion": "td",
    "poblacion ocupada": "ocupados_miles",
    "poblacion desocupada": "desocupados_miles",
}


def sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(s))
                   if unicodedata.category(c) != "Mn")


def mas_reciente(patron: str) -> Path:
    c = sorted(CRUDO.glob(patron), key=lambda p: p.stat().st_mtime, reverse=True)
    if not c:
        sys.exit(f"No encuentro '{patron}' en {CRUDO.relative_to(RAIZ)}")
    return c[0]


def leer_anexo(ruta: Path, sufijo: str = "") -> pd.DataFrame:
    d = pd.read_excel(ruta, sheet_name="Total nacional", header=None)

    fila_conc = next((i for i in range(len(d))
                      if sin_tildes(d.iat[i, 0]).strip().lower() == "concepto"), None)
    if fila_conc is None:
        sys.exit(f"{ruta.name}: no encuentro la fila 'Concepto'")
    fila_mes = fila_conc + 1

    # Los años aparecen una vez por bloque de 12 columnas; se propagan a la derecha.
    anio_col, actual = {}, None
    for j in range(1, d.shape[1]):
        v = d.iat[fila_conc, j]
        if isinstance(v, (int, float)) and v == v and 1990 < v < 2100:
            actual = int(v)
        if actual:
            anio_col[j] = actual

    col_periodo = {}
    for j, anio in anio_col.items():
        m = sin_tildes(d.iat[fila_mes, j]).strip().lower()[:3]
        if m in MESES:
            col_periodo[j] = pd.Period(f"{anio}-{MESES[m]:02d}", freq="M")

    filas = {}
    for i in range(fila_mes + 1, len(d)):
        etiqueta = sin_tildes(d.iat[i, 0]).strip().lower()
        etiqueta = re.sub(r"\s*\(.*?\)\s*", "", etiqueta).strip()
        col = next((v for k, v in CONCEPTOS.items() if etiqueta.startswith(k)), None)
        if col is None or col in filas:
            continue
        filas[col] = {col_periodo[j]: pd.to_numeric(d.iat[i, j], errors="coerce")
                      for j in col_periodo}

    if not filas:
        sys.exit(f"{ruta.name}: no reconocí ningún concepto")

    out = pd.DataFrame(filas)
    out.index.name = "fecha"
    out = out.reset_index().sort_values("fecha")
    ren = {c: (f"{c}_sa{'_pct' if c in ('tgp', 'to', 'td') else ''}" if sufijo
               else (f"{c}_pct" if c in ("tgp", "to", "td") else c))
           for c in out.columns if c != "fecha"}
    if sufijo:
        ren = {c: (f"{c}_sa_pct" if c in ("tgp", "to", "td") else f"{c}_sa")
               for c in out.columns if c != "fecha"}
    return out.rename(columns=ren)


def main() -> None:
    f_orig = mas_reciente("anex-GEIH-[a-z]*20*.xlsx")
    f_desest = mas_reciente("anex-GEIH-Desestacionalizado-*.xlsx")
    print(f"Original:          {f_orig.name}")
    print(f"Desestacionalizado: {f_desest.name}")

    orig = leer_anexo(f_orig)
    sa = leer_anexo(f_desest, sufijo="sa")
    d = orig.merge(sa, on="fecha", how="outer").sort_values("fecha")
    d = d.dropna(subset=[c for c in d.columns if c != "fecha"], how="all")

    # Control: la TD desestacionalizada debe seguir a la original de cerca en
    # nivel medio, pero sin el salto de enero.
    if {"td_pct", "td_sa_pct"} <= set(d.columns):
        cmp = d.dropna(subset=["td_pct", "td_sa_pct"]).copy()
        cmp["mes"] = cmp.fecha.dt.month
        e_orig = cmp[cmp.mes == 1].td_pct.diff().mean()
        salto_o = (cmp.groupby("mes").td_pct.mean() - cmp.td_pct.mean()).loc[1]
        salto_s = (cmp.groupby("mes").td_sa_pct.mean() - cmp.td_sa_pct.mean()).loc[1]
        print(f"\nDesviación de enero respecto de la media anual:")
        print(f"  TD original          {salto_o:+.2f} pp")
        print(f"  TD desestacionalizada {salto_s:+.2f} pp   "
              f"({'ok, el calendario se fue' if abs(salto_s) < abs(salto_o) / 2 else 'REVISAR'})")

    d["fecha"] = d["fecha"].astype(str)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(SALIDA, index=False)
    print(f"\n{SALIDA.relative_to(RAIZ)}: {len(d)} meses, {d.fecha.min()} a {d.fecha.max()}")
    print(d.tail(4).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
