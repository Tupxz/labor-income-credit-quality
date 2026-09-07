"""
Procesa el reporte de la SFC "Distribución de cartera por producto" (Formato 341)
y construye el panel de calidad de cartera a nivel PRODUCTO x MES, 2015-01 a 2026-06.

Sustituye a procesar_sfc_calidad_cartera.py, que leía los Excel agregados
(solo llegaban a 2023-12 y solo traían 5 segmentos).

Dos trampas del archivo crudo que este script resuelve explícitamente
--------------------------------------------------------------------
1) RENGLON. Para cada entidad-mes-producto, RENGLON=5 es el TOTAL del producto y
   los renglones 10/15/20/25 son su desagregación (verificado: suman exacto al
   total, ratio 1.0000). Cuatro productos tienen desagregación —tarjeta de
   crédito, libranza, construcción y leasing financiero—, así que NO filtrar
   RENGLON infla la cartera bruta del sistema en +27,2 %.

2) Buckets de mora. Las columnas (3)…(15) NO son acumulables: cada familia de
   cartera reporta en un esquema distinto y excluyente. Sumar (3)+(4)+(8)+(9)
   para todo —el atajo intuitivo— deja la cartera de vivienda con mora 0,00 %,
   comercial en 0,55 % en vez de 3,78 % y microcrédito en 2,15 % en vez de 7,37 %.
   El mapeo correcto está en ESQUEMAS_MORA y el script lo AUDITA contra los datos
   antes de calcular nada (ver auditar_esquemas_mora).

   Además, en VIVIENDA el umbral de mora del ICV que publica la SFC no arranca
   en el primer mes: el bucket (10) "Vencida 1-4 meses" queda POR DEBAJO del
   umbral y no entra en la cartera vencida. Se verificó contra la serie oficial
   (data/processed/sfc_icv_mensual.csv, 108 meses): incluyéndolo el ICV de
   vivienda se va +3,5 pp por encima del oficial; excluyéndolo el error cae a
   0,11 pp. Ese bucket se conserva aparte, en la columna `mora_pre_umbral`,
   porque es la mora más temprana de vivienda —la que primero reacciona a un
   choque de ingreso— y justamente el indicador oficial no la muestra.

Validación contra la fuente oficial
-----------------------------------
Reconstruyendo el ICV por familia y cruzándolo con el Excel agregado de la SFC
(2015-01 a 2023-12, 108 meses), el error absoluto medio es:
   comercial 0,002 pp | consumo 0,001 pp | microcrédito 0,005 pp | vivienda 0,115 pp
Los tres primeros reproducen la cifra oficial al tercer decimal. Vivienda queda
con un sesgo estable de -0,11 pp (nivel, no forma: no se mueve entre 2015 y
2023), diferencia de perímetro que se documenta como tal.

Salidas en data/processed/:
  sfc_cartera_producto_mensual.csv     producto x mes (32 productos x 138 meses)
  sfc_cartera_familia_mensual.csv      familia x mes  (comercial/consumo/vivienda/microcredito + total)
  sfc_tarjeta_por_ingreso_mensual.csv  tarjeta de crédito abierta por ingreso del
                                       tarjetahabiente (hasta 2 SMMLV vs. más de 2 SMMLV)
  sfc_auditoria_esquemas_mora.csv      evidencia del punto (2)

Uso:  python src/procesar_sfc_producto.py
"""

from pathlib import Path
import sys
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "data" / "raw" / "sfc" / "Distribución_de_cartera_por_producto_20260904.csv"
SALIDA = RAIZ / "data" / "processed"

# --- Universo de entidades -------------------------------------------------
# Establecimientos de crédito = bancos (1), corporaciones financieras (2),
# compañías de financiamiento (4) y cooperativas financieras (32).
# Se excluye el tipo 22 (instituciones oficiales especiales: FNA, FDN, Caja
# Promotora de Vivienda Militar), que NO son establecimientos de crédito y por
# tanto no entran en el ICV que publica la SFC para el sistema.
TIPOS_EC = {"1", "2", "4", "32"}
INCLUIR_IOE = False

# --- Columnas del formato --------------------------------------------------
SALDO = "(1) Saldo de la cartera a la fecha de corte del reporte"
VIGENTE = "(2) Vigente"
CLIENTES_MORA30 = "(16) Número de clientes Mora > 30 días"

MORA = {
    3: "(3) Vencida 1-2 Meses",
    4: "(4) Vencida 2-3 Meses",
    5: "(5) Vencida 1-3 Meses",
    6: "(6) Vencida 3-4 Meses",
    7: "(7) Vencida > de 4 Meses",
    8: "(8) Vencida 3-6 Meses",
    9: "(9) Vencida +6 meses",
    10: "(10) Vencida 1-4 meses",
    11: "(11) Vencida 4-6 meses",
    12: "(12) Vencida 6-12 meses",
    13: "(13) Vencida 12-18 meses",
    14: "(14) Vencida > 12 meses",
    15: "(15) Vencida > 18 meses",
}

CALIF_SALDO = {
    "A": "(18) Calificación de Riesgo A / Saldo",
    "B": "(20) Calificación de Riesgo B / Saldo",
    "C": "(22) Calificación de Riesgo C / Saldo",
    "D": "(24) Calificación de Riesgo D / Saldo",
    "E": "(26) Calificación de Riesgo E / Saldo",
}

# --- Familias de cartera y esquema de mora que usa cada una ----------------
# La familia se define por UNICAP (código estable), no por el texto de
# DESCRIP_UC/DESC_RENGLON, que viene con tildes y typos inconsistentes en el
# tiempo ("CONSTRUCCION"/"CONSTRUCCIÓN", "PROYACTOS", "LEASIN FINANCI"...).
FAMILIA_POR_UNICAP = {
    **{u: "consumo" for u in [1, 2, 3, 4, 5, 6, 29, 30]},
    **{u: "microcredito" for u in [7, 8]},
    **{u: "vivienda" for u in [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 31, 32]},
    **{u: "comercial" for u in [19, 20, 21, 22, 23, 24, 25, 26, 27, 28]},
}

# Para cada familia: qué columnas de mora aplican, separadas en mora temprana
# (el deudor acaba de dejar de pagar: responde rápido a choques de ingreso) y
# mora tardía (deterioro consolidado, camino al castigo).
# "pre_umbral" son buckets de mora reales que NO entran en la cartera vencida del
# indicador oficial (solo vivienda tiene uno). Se guardan aparte, no se botan.
ESQUEMAS_MORA = {
    "consumo":      {"temprana": [3, 4], "tardia": [8, 9],           "pre_umbral": []},    # 1-2, 2-3 | 3-6, +6
    "microcredito": {"temprana": [3, 4], "tardia": [6, 7],           "pre_umbral": []},    # 1-2, 2-3 | 3-4, >4
    "comercial":    {"temprana": [5],    "tardia": [8, 12, 14],      "pre_umbral": []},    # 1-3      | 3-6, 6-12, >12
    "vivienda":     {"temprana": [11],   "tardia": [12, 13, 15],     "pre_umbral": [10]},  # 4-6      | 6-12, 12-18, >18   (1-4 aparte)
}

TARJETA_UNICAP = 2
TARJETA_RENGLONES = {10: "hasta_2_smmlv", 15: "mas_de_2_smmlv"}


def a_numero(s: pd.Series) -> pd.Series:
    """Convierte el formato de miles colombiano ('1.234.567,89') a float."""
    return pd.to_numeric(
        s.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce",
    )


def cargar() -> pd.DataFrame:
    if not ENTRADA.exists():
        sys.exit(f"No encuentro {ENTRADA}")

    usar = ["TIPO_ENTIDAD", "CODIGO_ENTIDAD", "NOMBREENTIDAD", "FECHA_CORTE",
            "UNICAP", "DESCRIP_UC", "RENGLON", SALDO, VIGENTE, CLIENTES_MORA30]
    usar += list(MORA.values()) + list(CALIF_SALDO.values())

    df = pd.read_csv(ENTRADA, usecols=usar, dtype=str, encoding="utf-8-sig")

    df["fecha"] = pd.to_datetime(df["FECHA_CORTE"], format="%d/%m/%Y").dt.to_period("M")
    df["UNICAP"] = df["UNICAP"].astype(int)
    df["RENGLON"] = df["RENGLON"].astype(int)
    df["familia"] = df["UNICAP"].map(FAMILIA_POR_UNICAP)

    for c in [SALDO, VIGENTE, CLIENTES_MORA30] + list(MORA.values()) + list(CALIF_SALDO.values()):
        df[c] = a_numero(df[c])

    sin_familia = df.loc[df["familia"].isna(), "UNICAP"].unique()
    if len(sin_familia):
        sys.exit(f"UNICAP sin familia asignada: {sorted(sin_familia)} — actualizar FAMILIA_POR_UNICAP")

    return df


def auditar_renglones(df: pd.DataFrame) -> None:
    """Verifica que los subrenglones sumen el renglón 5 antes de descartarlos."""
    print("\n[1] Auditoría de RENGLON (subrenglones vs. total del producto)")
    con_sub = sorted(df.loc[df["RENGLON"] != 5, "UNICAP"].unique())
    for u in con_sub:
        s = df[df["UNICAP"] == u]
        tot = s.loc[s["RENGLON"] == 5, SALDO].sum()
        sub = s.loc[s["RENGLON"] != 5, SALDO].sum()
        marca = "ok" if abs(sub / tot - 1) < 1e-6 else "¡REVISAR!"
        print(f"    UNICAP {u:>2}  subrenglones/total = {sub / tot:.6f}  {marca}")
    infla = df[SALDO].sum() / df.loc[df["RENGLON"] == 5, SALDO].sum() - 1
    print(f"    -> no filtrar RENGLON=5 inflaría la cartera bruta en {infla:+.1%}")


def auditar_esquemas_mora(df: pd.DataFrame) -> pd.DataFrame:
    """
    Para cada familia, calcula el peso de CADA columna de mora sobre el saldo.
    Las columnas que no pertenecen al esquema de esa familia deben dar 0.
    Si alguna no da 0, ESQUEMAS_MORA está mal y hay que corregirlo.
    """
    print("\n[2] Auditoría de esquemas de mora (peso de cada columna sobre el saldo, %)")
    base = df[df["RENGLON"] == 5]
    g = base.groupby("familia")
    tabla = pd.DataFrame({k: g[c].sum() / g[SALDO].sum() * 100 for k, c in MORA.items()}).T
    tabla.index.name = "columna_mora"

    problemas = []
    for fam, esq in ESQUEMAS_MORA.items():
        propias = set(esq["temprana"] + esq["tardia"] + esq["pre_umbral"])
        for col in MORA:
            peso = tabla.loc[col, fam]
            if col not in propias and peso > 0.001:
                problemas.append((fam, col, peso))

    print(tabla.round(3).to_string())
    if problemas:
        print("\n    ¡ATENCIÓN! columnas fuera del esquema con saldo distinto de cero:")
        for fam, col, peso in problemas:
            print(f"      {fam}: {MORA[col]} = {peso:.3f} %")
        sys.exit("ESQUEMAS_MORA no cuadra con los datos. Corregir antes de seguir.")
    print("\n    -> ok: cada familia reporta únicamente en su propio esquema de buckets.")
    return tabla


def agregar(base: pd.DataFrame, llaves: list) -> pd.DataFrame:
    """Suma entidades y arma los indicadores de calidad para el nivel pedido."""
    piezas = []
    for fam, esq in ESQUEMAS_MORA.items():
        s = base[base["familia"] == fam].copy()
        if s.empty:
            continue
        s["vencida_temprana"] = s[[MORA[c] for c in esq["temprana"]]].sum(axis=1)
        s["vencida_tardia"] = s[[MORA[c] for c in esq["tardia"]]].sum(axis=1)
        s["mora_pre_umbral"] = (s[[MORA[c] for c in esq["pre_umbral"]]].sum(axis=1)
                                if esq["pre_umbral"] else 0.0)
        piezas.append(s)
    d = pd.concat(piezas, ignore_index=True)
    d["vencida"] = d["vencida_temprana"] + d["vencida_tardia"]

    for cal, col in CALIF_SALDO.items():
        d[f"saldo_{cal}"] = d[col]

    sumas = {
        "cartera_bruta": (SALDO, "sum"),
        "vigente": (VIGENTE, "sum"),
        "vencida": ("vencida", "sum"),
        "vencida_temprana": ("vencida_temprana", "sum"),
        "vencida_tardia": ("vencida_tardia", "sum"),
        "mora_pre_umbral": ("mora_pre_umbral", "sum"),
        "clientes_mora_30d": (CLIENTES_MORA30, "sum"),
        "n_entidades": ("CODIGO_ENTIDAD", "nunique"),
    }
    sumas.update({f"saldo_{c}": (f"saldo_{c}", "sum") for c in CALIF_SALDO})

    out = d.groupby(llaves, observed=True).agg(**sumas).reset_index()

    # Indicadores
    out["icv"] = out["vencida"] / out["cartera_bruta"]
    out["icv_temprano"] = out["vencida_temprana"] / out["cartera_bruta"]
    out["icv_tardio"] = out["vencida_tardia"] / out["cartera_bruta"]
    # Solo vivienda: mora de 1 a 4 meses, por debajo del umbral del ICV oficial.
    out["icv_pre_umbral"] = out["mora_pre_umbral"] / out["cartera_bruta"]
    # Calidad por riesgo: cartera riesgosa = B..E; incumplida = C..E
    out["icr_riesgosa"] = out[["saldo_B", "saldo_C", "saldo_D", "saldo_E"]].sum(axis=1) / out["cartera_bruta"]
    out["icr_incumplida"] = out[["saldo_C", "saldo_D", "saldo_E"]].sum(axis=1) / out["cartera_bruta"]
    # Crecimiento nominal anual de la cartera bruta: controla el "efecto
    # denominador" (el ICV sube cuando la originación se frena, sin que ningún
    # deudor se comporte peor).
    llave_serie = [k for k in llaves if k != "fecha"]
    out = out.sort_values(llaves)
    if llave_serie:
        out["cartera_var_anual"] = out.groupby(llave_serie, observed=True)["cartera_bruta"].pct_change(12, fill_method=None)
    else:
        out["cartera_var_anual"] = out["cartera_bruta"].pct_change(12, fill_method=None)

    out["fecha"] = out["fecha"].astype(str)
    return out


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    df = cargar()
    print(f"Leído: {len(df):,} filas | {df['fecha'].min()} a {df['fecha'].max()}")

    auditar_renglones(df)
    tabla_mora = auditar_esquemas_mora(df)
    tabla_mora.to_csv(SALIDA / "sfc_auditoria_esquemas_mora.csv")

    # Universo y nivel de producto
    base = df[df["RENGLON"] == 5].copy()
    if not INCLUIR_IOE:
        antes = base[SALDO].sum()
        base = base[base["TIPO_ENTIDAD"].isin(TIPOS_EC)]
        print(f"\n[3] Universo: establecimientos de crédito "
              f"(excluye IOE, {1 - base[SALDO].sum() / antes:.1%} del saldo)")

    dup = base.duplicated(["CODIGO_ENTIDAD", "TIPO_ENTIDAD", "fecha", "UNICAP"]).sum()
    print(f"    llave entidad×fecha×producto duplicada: {dup} filas")

    # a) producto x mes
    prod = agregar(base, ["fecha", "UNICAP", "DESCRIP_UC", "familia"])
    prod = prod.rename(columns={"UNICAP": "unicap", "DESCRIP_UC": "producto"})
    prod.to_csv(SALIDA / "sfc_cartera_producto_mensual.csv", index=False)

    # b) familia x mes (comparable con el ICV que publica la SFC)
    fam = agregar(base, ["fecha", "familia"])
    total = agregar(base.assign(familia_total="total"), ["fecha", "familia_total"])
    total = total.rename(columns={"familia_total": "familia"})
    fam = pd.concat([fam, total], ignore_index=True).sort_values(["familia", "fecha"])
    fam.to_csv(SALIDA / "sfc_cartera_familia_mensual.csv", index=False)

    # c) tarjeta de crédito por nivel de ingreso del tarjetahabiente
    tj = df[(df["UNICAP"] == TARJETA_UNICAP) & (df["RENGLON"].isin(TARJETA_RENGLONES))].copy()
    if not INCLUIR_IOE:
        tj = tj[tj["TIPO_ENTIDAD"].isin(TIPOS_EC)]
    tj["tramo_ingreso"] = tj["RENGLON"].map(TARJETA_RENGLONES)
    tj = agregar(tj, ["fecha", "tramo_ingreso"])
    tj.to_csv(SALIDA / "sfc_tarjeta_por_ingreso_mensual.csv", index=False)

    # Chequeo de identidad contable de la fuente
    for nombre, d in [("producto", prod), ("familia", fam)]:
        exceso = (d["vigente"] + d["vencida"] + d["mora_pre_umbral"]) / d["cartera_bruta"] - 1
        malas = d[exceso > 1e-4]
        if len(malas):
            print(f"\n[!] {nombre}: {len(malas)} de {len(d)} celdas donde "
                  f"vigente+vencida+mora_pre_umbral supera la cartera bruta "
                  f"(máx {exceso.max():.2%}). Inconsistencia de la fuente, no del cálculo.")
            print(malas[["fecha", "cartera_bruta"]].head(6).to_string(index=False))
            print("    No afecta el ICV (vencida <= bruta en todas las celdas); "
                  "sí afecta icv_pre_umbral en esas fechas.")

    print("\n[4] Salidas escritas en data/processed/")
    for nombre, d in [("sfc_cartera_producto_mensual.csv", prod),
                      ("sfc_cartera_familia_mensual.csv", fam),
                      ("sfc_tarjeta_por_ingreso_mensual.csv", tj)]:
        print(f"    {nombre:<38} {len(d):>6,} filas")

    print("\n[5] ICV por familia (%), últimos meses")
    piv = fam.pivot(index="fecha", columns="familia", values="icv").mul(100).round(2)
    print(piv.tail(6).to_string())


if __name__ == "__main__":
    main()
