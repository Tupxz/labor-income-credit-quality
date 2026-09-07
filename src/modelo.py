"""
Estimación: mercado laboral, ingreso real y calidad de cartera por tipo de crédito.

Especificación y por qué
------------------------
Todo va en VARIACIONES A 12 MESES, no en niveles ni en primeras diferencias:

  · En niveles casi todas las series son I(1) (ADF+KPSS, tabla2): regresar
    niveles contra niveles es regresión espuria.
  · En primeras diferencias mensuales domina el calendario: la tasa de desempleo
    salta +3,2 pp cada enero (tabla4). Ahí se usa además la serie
    DESESTACIONALIZADA del DANE, no la original.
  · La diferencia a 12 meses quita tendencia y estacionalidad de una, y es la
    ventana a la que la inflación lidera la mora de consumo (ρ = 0,77 a t−12).

Variable dependiente: Δ₁₂ ICV del producto, en puntos porcentuales.

Controles que no son opcionales:
  · `cartera_var_real_anual` — EFECTO DENOMINADOR. El ICV es un cociente: si la
    originación se frena, el denominador deja de crecer mientras el vencido
    acumula y el ICV sube sin que ningún deudor se comporte peor. Ojo: parte de
    este coeficiente es mecánica (la cartera bruta está en el denominador de la
    dependiente), así que se reporta como control, nunca como hallazgo causal.
  · Tasa de política en términos REALES. La nominal mezcla apretón monetario con
    inflación esperada: en dic-2022 la TPM nominal iba en 11,4 % y la real en
    −1,5 %.

Errores estándar: Driscoll-Kraay. Los regresores macro son comunes a los 32
productos, así que los choques están correlacionados en el corte transversal;
agrupar solo por producto subestimaría los errores. Por lo mismo NO se incluyen
efectos fijos de tiempo: absorberían toda la variación que se quiere medir.

Cuatro modelos
--------------
1. Panel producto × mes, efectos fijos de producto. El efecto promedio.
2. Heterogeneidad: el choque de ingreso interactuado con el DISEÑO del producto
   (descuento de nómina / garantía real / sin garantía / microcrédito).
3. **La prueba central.** Tarjeta de crédito abierta por ingreso del
   tarjetahabiente. Se estima la BRECHA (ICV del tramo bajo menos el alto) contra
   el choque de ingreso: al diferenciar entre tramos se cancelan la regulación,
   la mezcla de entidades, el calendario y cualquier choque común. Lo único que
   queda es el ingreso del deudor.
4. Moderación por costo del crédito: el mismo choque de ingreso pega más fuerte
   cuando la tasa real está alta, porque el servicio de la deuda es mayor.

Uso:  python src/modelo.py
"""

from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from linearmodels.panel import PanelOLS

sys.path.insert(0, str(Path(__file__).resolve().parent))
import viz  # noqa: E402

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parents[1]
PROC = RAIZ / "data" / "processed"

# Diseño del producto: qué tan expuesto está el deudor a una caída de su ingreso.
DISENO = {
    "nomina": ["LIBRANZA", "LIBRANZA VIVIENDA VIS", "LIBRANZA VIVIENDA NO VIS",
               "CREDITOS DE CONSUMO PARA EMPLEADOS",
               "CREDITOS DE VIVIENDA PARA EMPLEADOS VIS",
               "CREDITOS DE VIVIENDA PARA EMPL NO VIS"],
    "sin_garantia": ["TARJETAS DE CRÉDITO", "LIBRE INVERSIÓN", "CRÉDITO ROTATIVO",
                     "OTROS PORTAFOLIOS DE CONSUMO", "CONSUMO BAJO MONTO"],
    "garantia_real": ["VEHÍCULO", "VIVIENDA VIS PESOS", "VIVIENDA VIS UVR",
                      "VIVIENDA NO VIS PESOS", "VIVIENDA NO VIS UVR",
                      "LEASING HABITACIONAL VIS PESOS", "LEASING HABITACIONAL VIS UVR",
                      "LEASING HABITACIONAL NO VIS PESOS", "LEASING HABITACIONAL NO VIS UVR"],
    "microcredito": ["MICROCREDITOS < O IGUALES A 25 SMMLV",
                     "MICROCREDITOS > 25  Y HASTA 120 SMMLV"],
}
ETIQUETA_DISENO = {"nomina": "Descuento de nómina", "sin_garantia": "Sin garantía",
                   "garantia_real": "Con garantía real", "microcredito": "Microcrédito",
                   "comercial": "Comercial (empresas)"}


def d12(s):
    return s.diff(12)


def preparar(nivel_producto: bool = True) -> pd.DataFrame:
    p = pd.read_csv(PROC / "panel_calidad_cartera.csv")
    p["fecha"] = pd.PeriodIndex(p["fecha"], freq="M")
    p = p.sort_values(["unicap", "fecha"])

    p["diseno"] = "comercial"
    for k, prods in DISENO.items():
        p.loc[p["producto"].isin(prods), "diseno"] = k

    g = p.groupby("unicap", observed=True)
    p["d_icv"] = g["icv"].transform(d12) * 100            # pp
    p["d_icv_temp"] = g["icv_temprano"].transform(d12) * 100
    p["d_icr"] = g["icr_riesgosa"].transform(d12) * 100
    p["crec_cartera"] = p["cartera_var_real_anual"]       # ya es var. anual (%)

    # macro (idénticos para todos los productos)
    m = (p.drop_duplicates("fecha").set_index("fecha")
           [["td_sa_pct", "tpm_real", "informalidad_pct",
             "total_mediana_var_real_anual", "total_media_var_real_anual",
             "ipc_var_anual"]])
    macro = pd.DataFrame({
        "ing_real": m["total_mediana_var_real_anual"],
        "ing_real_media": m["total_media_var_real_anual"],
        "d_td": d12(m["td_sa_pct"]),
        "d_tasa_real": d12(m["tpm_real"]),
        "d_informal": d12(m["informalidad_pct"]),
        "inflacion": m["ipc_var_anual"],
        "tasa_real_nivel": m["tpm_real"],
    })
    for k in (6, 12):
        macro[f"ing_real_l{k}"] = macro["ing_real"].shift(k)

    p = p.merge(macro.reset_index(), on="fecha", how="left")
    # linearmodels exige un índice de tiempo tipo fecha, no Period
    p["t"] = p["fecha"].dt.to_timestamp()
    return p


def dk(res):
    """Resumen compacto de un PanelOLS ya estimado."""
    return pd.DataFrame({"coef": res.params, "ee": res.std_errors,
                         "t": res.tstats, "p": res.pvalues}).round(4)


def estrellas(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def modelo1(p):
    print("\n" + "=" * 74)
    print("MODELO 1 — Panel producto × mes, efectos fijos de producto")
    print("=" * 74)
    d = p.set_index(["unicap", "t"])
    y = "d_icv"
    X = ["ing_real", "d_td", "d_tasa_real", "crec_cartera", "d_informal"]
    m = d[[y] + X].dropna()
    res = PanelOLS(m[y], sm.add_constant(m[X]), entity_effects=True).fit(
        cov_type="kernel", kernel="bartlett")   # Driscoll-Kraay
    print(f"  n = {res.nobs:,}   productos = {m.index.get_level_values(0).nunique()}"
          f"   meses = {m.index.get_level_values(1).nunique()}   R²within = {res.rsquared_within:.3f}")
    print(dk(res).to_string())
    return res


def modelo2(p):
    print("\n" + "=" * 74)
    print("MODELO 2 — El mismo choque de ingreso, según el diseño del producto")
    print("=" * 74)
    d = p.copy()
    for k in ETIQUETA_DISENO:
        d[f"ing_x_{k}"] = d["ing_real"] * (d["diseno"] == k)
    inter = [f"ing_x_{k}" for k in ETIQUETA_DISENO]
    X = inter + ["d_td", "d_tasa_real", "crec_cartera"]
    d = d.set_index(["unicap", "t"])
    m = d[["d_icv"] + X].dropna()
    res = PanelOLS(m["d_icv"], sm.add_constant(m[X]), entity_effects=True).fit(
        cov_type="kernel", kernel="bartlett")
    print(f"  n = {res.nobs:,}   R²within = {res.rsquared_within:.3f}\n")
    t = dk(res)
    print("  Efecto de 1 pp más de crecimiento del ingreso real sobre Δ₁₂ ICV (pp):")
    for k, et in ETIQUETA_DISENO.items():
        c = f"ing_x_{k}"
        if c in t.index:
            print(f"    {et:<24} {t.loc[c,'coef']:+.4f} {estrellas(t.loc[c,'p']):<3} "
                  f"(ee {t.loc[c,'ee']:.4f})")
    print("\n  controles:")
    print(t.loc[[c for c in t.index if not c.startswith('ing_x_')]].to_string())
    return res


def modelo3(p):
    print("\n" + "=" * 74)
    print("MODELO 3 — LA PRUEBA CENTRAL: tarjeta de crédito por ingreso del deudor")
    print("=" * 74)
    tj = pd.read_csv(PROC / "sfc_tarjeta_por_ingreso_mensual.csv")
    tj["fecha"] = pd.PeriodIndex(tj["fecha"], freq="M")
    piv = tj.pivot(index="fecha", columns="tramo_ingreso", values="icv") * 100
    brecha = (piv["hasta_2_smmlv"] - piv["mas_de_2_smmlv"]).rename("brecha")

    macro = (p.drop_duplicates("fecha").set_index("fecha")
               [["ing_real", "ing_real_l6", "d_td", "d_tasa_real", "inflacion"]])
    # El archivo de tarjeta trae el crecimiento NOMINAL de la cartera (fracción);
    # se pasa a real con la inflación anual y a puntos porcentuales.
    nom = (tj.pivot(index="fecha", columns="tramo_ingreso", values="cartera_var_anual")
             .mean(axis=1))
    infl = (p.drop_duplicates("fecha").set_index("fecha")["ipc_var_anual"]) / 100
    cart = (((1 + nom) / (1 + infl) - 1) * 100).rename("crec_cartera_tj")

    d = pd.concat([d12(brecha).rename("d_brecha"), macro, cart], axis=1).dropna()
    X = ["ing_real", "d_td", "d_tasa_real", "crec_cartera_tj"]
    res = sm.OLS(d["d_brecha"], sm.add_constant(d[X])).fit(
        cov_type="HAC", cov_kwds={"maxlags": 12})
    print("  Dependiente: Δ₁₂ de la BRECHA de ICV (tramo ≤2 SMMLV menos tramo >2 SMMLV), en pp")
    print("  Al diferenciar entre tramos se cancelan regulación, mezcla de entidades,")
    print("  calendario y todo choque común: queda el ingreso del deudor.\n")
    print(f"  n = {int(res.nobs)}   R² = {res.rsquared:.3f}   EE Newey-West (12 rezagos)")
    t = pd.DataFrame({"coef": res.params, "ee": res.bse, "t": res.tvalues,
                      "p": res.pvalues}).round(4)
    t["sig"] = [estrellas(x) for x in t["p"]]
    print(t.to_string())
    return res, d


def modelo4(p):
    print("\n" + "=" * 74)
    print("MODELO 4 — ¿El costo del crédito amplifica el choque de ingreso?")
    print("=" * 74)
    d = p.copy()
    d["tasa_c"] = d["tasa_real_nivel"] - d["tasa_real_nivel"].mean()   # centrada
    d["ing_x_tasa"] = d["ing_real"] * d["tasa_c"]
    X = ["ing_real", "tasa_c", "ing_x_tasa", "d_td", "crec_cartera"]
    d = d.set_index(["unicap", "t"])
    m = d[["d_icv"] + X].dropna()
    res = PanelOLS(m["d_icv"], sm.add_constant(m[X]), entity_effects=True).fit(
        cov_type="kernel", kernel="bartlett")
    print(f"  n = {res.nobs:,}   R²within = {res.rsquared_within:.3f}")
    print("  tasa_c está centrada, así que 'ing_real' es el efecto a tasa real promedio.\n")
    print(dk(res).to_string())
    t = dk(res)
    if "ing_x_tasa" in t.index:
        b, bi = t.loc["ing_real", "coef"], t.loc["ing_x_tasa", "coef"]
        sd = m["tasa_c"].std()
        print(f"\n  Efecto de 1 pp de ingreso real sobre Δ₁₂ ICV:")
        print(f"    con tasa real 1 d.e. por DEBAJO del promedio: {b - bi * sd:+.4f} pp")
        print(f"    a tasa real promedio:                         {b:+.4f} pp")
        print(f"    con tasa real 1 d.e. por ENCIMA:              {b + bi * sd:+.4f} pp")
    return res


def robustez(p):
    print("\n" + "=" * 74)
    print("ROBUSTEZ")
    print("=" * 74)
    base = ["ing_real", "d_td", "d_tasa_real", "crec_cartera"]
    pruebas = {
        "Base (Δ₁₂ ICV)": ("d_icv", base, p),
        "Mora temprana (1-3 meses)": ("d_icv_temp", base, p),
        "Calidad por riesgo (B..E)": ("d_icr", base, p),
        "Sin 2020 (pandemia)": ("d_icv", base, p[p.fecha.dt.year != 2020]),
        "Solo consumo": ("d_icv", base, p[p.familia == "consumo"]),
        "Ingreso: media en vez de mediana": ("d_icv", ["ing_real_media"] + base[1:], p),
        "Ingreso rezagado 6 meses": ("d_icv", ["ing_real_l6"] + base[1:], p),
    }
    filas = []
    for nombre, (y, X, datos) in pruebas.items():
        d = datos.set_index(["unicap", "t"])
        m = d[[y] + X].dropna()
        if len(m) < 100:
            continue
        try:
            r = PanelOLS(m[y], sm.add_constant(m[X]), entity_effects=True).fit(
                cov_type="kernel", kernel="bartlett")
        except Exception as e:
            print(f"  {nombre}: no estimó ({str(e)[:40]})")
            continue
        c = X[0]
        filas.append({"Especificación": nombre, "coef. ingreso real": round(r.params[c], 4),
                      "ee": round(r.std_errors[c], 4), "sig": estrellas(r.pvalues[c]),
                      "n": int(r.nobs), "R²w": round(r.rsquared_within, 3)})
    t = pd.DataFrame(filas)
    print(t.to_string(index=False))
    return t


def main():
    p = preparar()
    faltan = p.groupby("fecha")["ing_real"].apply(lambda s: s.isna().all()).sum()
    if faltan:
        print(f"AVISO: {faltan} meses sin ingreso laboral — correr src/bajar_geih.py")

    viz.TABLAS.mkdir(parents=True, exist_ok=True)
    r1 = modelo1(p)
    r2 = modelo2(p)
    r3, _ = modelo3(p)
    r4 = modelo4(p)
    rb = robustez(p)
    rvar = modelo_var(p)
    figura_heterogeneidad(r2)

    dk(r1).to_csv(viz.TABLAS / "modelo1_panel_base.csv")
    dk(r2).to_csv(viz.TABLAS / "modelo2_heterogeneidad.csv")
    pd.DataFrame({"coef": r3.params, "ee": r3.bse, "p": r3.pvalues}).round(4).to_csv(
        viz.TABLAS / "modelo3_tarjeta_brecha.csv")
    dk(r4).to_csv(viz.TABLAS / "modelo4_moderacion_tasa.csv")
    rb.to_csv(viz.TABLAS / "modelo5_robustez.csv", index=False)
    print(f"\nTablas en {viz.TABLAS.relative_to(RAIZ)}/")




# ---------------------------------------------------------------------------
# El brief del curso sugiere un sistema de ecuaciones simultáneas entre
# desempleo, ingreso, inflación y calidad de cartera, con la política monetaria
# moderando. Se estima como VAR sobre el bloque macro y se reporta junto al
# panel, no en vez de él.
#
# Por qué el panel sigue siendo la especificación principal: un VAR macro
# identifica por orden de Cholesky, que es un supuesto, no un dato. El panel
# producto × mes y sobre todo la brecha de tarjeta por tramo de ingreso
# identifican por variación TRANSVERSAL — mismo mes, misma regulación, mismo
# producto, distinto deudor— que no depende de ningún orden de recursividad.
# El VAR responde a lo que pidió el brief y da la dinámica; el panel da la
# identificación.
# ---------------------------------------------------------------------------

def modelo_var(p, salida_fig=True):
    """
    Sistema de ecuaciones simultáneas entre precios, mercado laboral, ingreso,
    política monetaria y calidad de cartera.

    Se estima como VECM, no como VAR. Motivo: las cinco series son I(1) (ADF y
    KPSS, tabla2). Un VAR en diferencias a 12 meses sale explosivo —el filtro
    induce una MA(12) no invertible, se probó— y un VAR en niveles con series
    I(1) tiene una raíz unitaria por construcción, así que `is_stable()` siempre
    falla y las IRF no se pueden leer. El VECM es la forma correcta: modela la
    relación de largo plazo (cointegración) y la dinámica de corto plazo a la vez,
    y ahí la inferencia sí es estándar.
    """
    from statsmodels.tsa.vector_ar.vecm import VECM, select_coint_rank, select_order
    print("\n" + "=" * 74)
    print("MODELO 5 — Sistema de ecuaciones simultáneas (VECM)")
    print("=" * 74)

    fam = pd.read_csv(PROC / "panel_calidad_cartera_familia.csv")
    fam["fecha"] = pd.PeriodIndex(fam["fecha"], freq="M")
    cons = fam[fam.familia == "consumo"].set_index("fecha")

    d = pd.DataFrame({
        "inflacion": cons["ipc_var_anual"],
        "td": cons["td_sa_pct"],
        "ing_real": np.log(cons["total_mediana_real"]) * 100,
        "tasa_real": cons["tpm_real"],
        "icv_consumo": cons["icv"] * 100,
    }).dropna()

    k = max(1, (select_order(d, maxlags=6, deterministic="ci").aic or 2))
    rango = select_coint_rank(d, det_order=0, k_ar_diff=k - 1, signif=0.05)
    r = max(1, rango.rank)
    print(f"  n = {len(d)}   rezagos en diferencias = {k - 1}   "
          f"rango de cointegración (Johansen, 5 %) = {rango.rank}")
    print(f"  variables: {list(d.columns)}")

    res = VECM(d, k_ar_diff=k - 1, coint_rank=r, deterministic="ci").fit()

    # Ajuste al desequilibrio de largo plazo: si el ICV es la variable que
    # corrige, la relación de cointegración le pone ancla.
    alpha = pd.DataFrame(res.alpha, index=d.columns,
                         columns=[f"ec{i+1}" for i in range(r)])
    print("\n  Velocidad de ajuste al equilibrio de largo plazo (alpha):")
    print(alpha.round(4).to_string())

    irf = res.irf(24)
    j_ing, j_icv = list(d.columns).index("ing_real"), list(d.columns).index("icv_consumo")
    resp = irf.irfs[:, j_icv, j_ing]
    acum = np.cumsum(resp)
    pico = int(np.argmax(np.abs(resp)))
    print(f"\n  Respuesta del ICV de consumo a un choque de +1 % en el ingreso real:")
    print(f"    impacto (mes 0): {resp[0]:+.4f} pp")
    print(f"    máximo:          {resp[pico]:+.4f} pp en el mes {pico}")
    print(f"    acumulado 24m:   {acum[-1]:+.4f} pp")

    print("\n  Granger (H0: la variable NO ayuda a predecir el ICV de consumo)")
    for v in ["ing_real", "td", "inflacion", "tasa_real"]:
        try:
            g = res.test_granger_causality(caused="icv_consumo", causing=[v])
            print(f"    {v:<12} p = {g.pvalue:.4f} {estrellas(g.pvalue)}")
        except Exception as e:
            print(f"    {v:<12} no se pudo: {str(e)[:45]}")

    if salida_fig:
        import matplotlib.pyplot as plt
        viz.aplicar_estilo()
        fig, ax = plt.subplots(figsize=(7.6, 3.8))
        h = np.arange(len(resp))
        ax.axhline(0, color=viz.EJE, lw=0.8)
        ax.fill_between(h, np.minimum(resp, 0), 0, color=viz.SERIES[0], alpha=0.15, lw=0)
        ax.plot(h, resp, color=viz.SERIES[0])
        ax.plot([pico], [resp[pico]], "o", ms=6, color=viz.SERIES[0],
                mec=viz.SUPERFICIE, mew=2, zorder=5)
        ax.annotate(f"máximo {resp[pico]:.3f} pp\nmes {pico}", xy=(pico, resp[pico]),
                    xytext=(8, -2), textcoords="offset points", fontsize=8,
                    color=viz.SERIES[0], fontweight="bold")
        ax.set_xlabel("Meses después del choque")
        ax.set_ylabel("Respuesta del ICV de consumo (pp)")
        ax.set_title("En el agregado de consumo el efecto del ingreso no se distingue de cero:\n"
                     "por eso el agregado es la unidad de análisis equivocada")
        fig.text(0.0, -0.07, "Impulso-respuesta de un VECM de cinco variables (inflación, desempleo "
                             "desestacionalizado, ingreso laboral real,\ntasa real de política y ICV de "
                             "consumo) ante un choque de +1 % en el ingreso real. El ICV de consumo "
                             "agrega libranza\n—protegida por el descuento de nómina— con tarjeta y libre "
                             "inversión, y al promediarlos el efecto se diluye.",
                 fontsize=7, color=viz.MUTED)
        viz.guardar(fig, "fig7_irf_ingreso_mora.png")
        print("\n  figura: output/figuras/fig7_irf_ingreso_mora.png")
    return res


def figura_heterogeneidad(res2):
    """Coeficientes del modelo 2: un solo estimador por diseño de producto."""
    import matplotlib.pyplot as plt
    viz.aplicar_estilo()
    filas = [(ETIQUETA_DISENO[k], res2.params.get(f"ing_x_{k}"), res2.std_errors.get(f"ing_x_{k}"))
             for k in ETIQUETA_DISENO if f"ing_x_{k}" in res2.params.index]
    filas.sort(key=lambda r: r[1])
    et = [r[0] for r in filas]
    co = np.array([r[1] for r in filas])
    ee = np.array([r[2] for r in filas])

    fig, ax = plt.subplots(figsize=(7.6, 3.4))
    y = np.arange(len(co))
    ax.axvline(0, color=viz.EJE, lw=0.8)
    ax.errorbar(co, y, xerr=1.96 * ee, fmt="o", ms=7, color=viz.SERIES[0],
                ecolor=viz.SERIES[0], elinewidth=2, capsize=0,
                markeredgecolor=viz.SUPERFICIE, markeredgewidth=2)
    ax.set_yticks(y, et)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Efecto sobre Δ₁₂ del ICV de 1 pp más de ingreso real (pp)")
    ax.set_title("El choque de ingreso se concentra en la cartera sin garantía")
    for yi, c in zip(y, co):
        ax.annotate(f"{c:+.3f}", xy=(c, yi), xytext=(0, 11), textcoords="offset points",
                    ha="center", fontsize=8, color=viz.TINTA_2)
    fig.text(0.0, -0.08, "Panel producto × mes con efectos fijos de producto, errores Driscoll-Kraay. "
                         "Barras: intervalo del 95 %.\nEl coeficiente de la cartera sin garantía es "
                         "significativo al 10 %; su intervalo al 95 % roza el cero. Los demás no se "
                         "distinguen de cero.", fontsize=7, color=viz.MUTED)
    viz.guardar(fig, "fig8_heterogeneidad_diseno.png")
    print("  figura: output/figuras/fig8_heterogeneidad_diseno.png")


if __name__ == "__main__":
    main()
