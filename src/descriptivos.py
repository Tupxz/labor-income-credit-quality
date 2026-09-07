"""
Estadística descriptiva y figuras exploratorias del panel — insumo de la
Sección 3 del entregable.

Produce en output/figuras/ y output/tablas/:

  fig1_icv_por_familia          panorama de la calidad de cartera 2015-2026
  fig2_tarjeta_por_ingreso      la brecha de mora por ingreso del tarjetahabiente
  fig3_exposicion_producto      mora temprana: libranza vs. libre inversión vs. tarjeta
  fig4_efecto_denominador       ICV contra crecimiento real de la cartera
  fig5_tasa_nominal_vs_real     el apretón monetario llega un año después
  fig6_icv_por_producto         ICV de cada producto en el último corte

  tabla1_descriptivas           momentos del panel por familia
  tabla2_raices_unitarias       ADF y KPSS sobre las series del modelo
  tabla3_correlaciones_rezagos  co-movimiento de la mora con desempleo y tasa real

Uso:  python src/descriptivos.py
"""

from pathlib import Path
import sys
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import viz  # noqa: E402

warnings.filterwarnings("ignore")

RAIZ = Path(__file__).resolve().parents[1]
PROC = RAIZ / "data" / "processed"


def cargar():
    fam = pd.read_csv(PROC / "panel_calidad_cartera_familia.csv")
    prod = pd.read_csv(PROC / "panel_calidad_cartera.csv")
    tj = pd.read_csv(PROC / "sfc_tarjeta_por_ingreso_mensual.csv")
    return fam, prod, tj


# ---------------------------------------------------------------- figuras ---

def fig1_icv_por_familia(fam):
    familias = ["consumo", "microcredito", "vivienda", "comercial"]
    piv = (fam[fam.familia.isin(familias)]
           .pivot(index="fecha", columns="familia", values="icv").mul(100))
    fechas = list(piv.index)

    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    viz.sombrear_episodios(ax, fechas)
    for f in familias:
        c = viz.COLOR_FAMILIA[f]
        ax.plot(range(len(piv)), piv[f], color=c, label=viz.ETIQUETA_FAMILIA[f])
        viz.etiquetar_extremo(ax, len(piv) - 1, piv[f].iloc[-1], viz.ETIQUETA_FAMILIA[f], c)

    viz.eje_tiempo(ax, fechas)
    ax.set_xlim(-1, len(fechas) + 22)
    ax.set_ylabel("ICV — cartera vencida / cartera bruta (%)")
    ax.set_title("La calidad de cartera se deterioró en todos los segmentos, pero no al mismo tiempo")
    ax.legend(loc="upper left", ncols=4)
    fig.text(0.0, -0.03, "Establecimientos de crédito. Fuente: SFC, cálculos propios.",
             fontsize=7, color=viz.MUTED)
    return viz.guardar(fig, "fig1_icv_por_familia.png")


def fig2_tarjeta_por_ingreso(tj):
    piv = tj.pivot(index="fecha", columns="tramo_ingreso", values="icv").mul(100)
    brecha = piv["hasta_2_smmlv"] - piv["mas_de_2_smmlv"]
    fechas = list(piv.index)

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.6, 5.4), sharex=True,
                                 gridspec_kw={"height_ratios": [2.1, 1]})

    etiquetas = {"hasta_2_smmlv": "Ingreso ≤ 2 SMMLV", "mas_de_2_smmlv": "Ingreso > 2 SMMLV"}
    colores = {"hasta_2_smmlv": viz.SERIES[1], "mas_de_2_smmlv": viz.SERIES[0]}

    viz.sombrear_episodios(a1, fechas)
    for k in ["hasta_2_smmlv", "mas_de_2_smmlv"]:
        a1.plot(range(len(piv)), piv[k], color=colores[k], label=etiquetas[k])
        viz.etiquetar_extremo(a1, len(piv) - 1, piv[k].iloc[-1], etiquetas[k], colores[k])
    a1.set_ylabel("ICV de tarjeta de crédito (%)")
    a1.set_title("Mismo producto, mismo mes, misma regulación:\nlo único que cambia es el ingreso del deudor")
    a1.legend(loc="upper left", ncols=2)

    viz.sombrear_episodios(a2, fechas, etiquetar=False)
    a2.fill_between(range(len(piv)), 0, brecha, color=viz.SERIES[1], alpha=0.18, lw=0)
    a2.plot(range(len(piv)), brecha, color=viz.SERIES[1])
    pico = int(np.argmax(brecha.values))
    a2.plot([pico], [brecha.iloc[pico]], "o", ms=6, color=viz.SERIES[1],
            mec=viz.SUPERFICIE, mew=2, zorder=5)
    a2.annotate(f"{brecha.iloc[pico]:.1f} pp\n{fechas[pico]}", xy=(pico, brecha.iloc[pico]),
                xytext=(6, 6), textcoords="offset points", fontsize=8,
                color=viz.SERIES[1], fontweight="bold")
    a2.set_ylabel("Brecha (pp)")
    a2.axhline(0, color=viz.EJE, lw=0.8)

    viz.eje_tiempo(a2, fechas)
    for a in (a1, a2):
        a.set_xlim(-1, len(fechas) + 20)
    fig.text(0.0, -0.02, "Tarjeta de crédito, establecimientos de crédito. Tramos según el "
                         "ingreso reportado del tarjetahabiente. Fuente: SFC, cálculos propios.",
             fontsize=7, color=viz.MUTED)
    fig.subplots_adjust(hspace=0.18)
    return viz.guardar(fig, "fig2_tarjeta_por_ingreso.png")


def fig3_exposicion_producto(prod):
    # Tres productos de consumo con la misma población pero distinta exposición
    # al choque de ingreso, por el diseño del producto.
    sel = {"LIBRANZA": "Libranza", "LIBRE INVERSIÓN": "Libre inversión",
           "TARJETAS DE CRÉDITO": "Tarjeta de crédito"}
    piv = (prod[prod.producto.isin(sel)]
           .pivot(index="fecha", columns="producto", values="icv_temprano").mul(100))
    fechas = list(piv.index)

    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    viz.sombrear_episodios(ax, fechas)
    for i, (col, etiqueta) in enumerate(sel.items()):
        ax.plot(range(len(piv)), piv[col], color=viz.SERIES[i], label=etiqueta)
        viz.etiquetar_extremo(ax, len(piv) - 1, piv[col].iloc[-1], etiqueta, viz.SERIES[i])

    viz.eje_tiempo(ax, fechas)
    ax.set_xlim(-1, len(fechas) + 26)
    ax.set_ylabel("Mora temprana — 1 a 3 meses (% de la cartera)")
    ax.set_title("El descuento de nómina aísla a la libranza del mismo choque de ingreso")
    ax.legend(loc="upper left", ncols=1)
    fig.text(0.0, -0.03, "Mora de 1 a 3 meses, el margen que primero reacciona a una caída del "
                         "ingreso. Fuente: SFC, cálculos propios.", fontsize=7, color=viz.MUTED)
    return viz.guardar(fig, "fig3_exposicion_producto.png")


def fig4_efecto_denominador(fam):
    t = fam[fam.familia == "total"].set_index("fecha")
    fechas = list(t.index)
    icv = t["icv"] * 100
    crec = t["cartera_var_real_anual"]

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.6, 5.4), sharex=True,
                                 gridspec_kw={"height_ratios": [1, 1]})

    viz.sombrear_episodios(a1, fechas)
    a1.plot(range(len(t)), icv, color=viz.SERIES[0])
    pico = int(np.argmax(icv.values))
    a1.plot([pico], [icv.iloc[pico]], "o", ms=6, color=viz.SERIES[0],
            mec=viz.SUPERFICIE, mew=2, zorder=5)
    a1.annotate(f"máximo {icv.iloc[pico]:.2f}%\n{fechas[pico]}", xy=(pico, icv.iloc[pico]),
                xytext=(8, -2), textcoords="offset points", fontsize=8,
                color=viz.SERIES[0], fontweight="bold")
    a1.set_ylabel("ICV del sistema (%)")
    a1.set_title("El pico de mora coincide con la mayor contracción real del crédito:\n"
                 "parte del deterioro es denominador, no comportamiento del deudor")

    viz.sombrear_episodios(a2, fechas, etiquetar=False)
    a2.axhline(0, color=viz.EJE, lw=0.8)
    a2.plot(range(len(t)), crec, color=viz.SERIES[1])
    a2.fill_between(range(len(t)), 0, crec, where=(crec < 0),
                    color=viz.SERIES[1], alpha=0.18, lw=0)
    a2.plot([pico], [crec.iloc[pico]], "o", ms=6, color=viz.SERIES[1],
            mec=viz.SUPERFICIE, mew=2, zorder=5)
    a2.annotate(f"{crec.iloc[pico]:.1f}%", xy=(pico, crec.iloc[pico]),
                xytext=(8, -10), textcoords="offset points", fontsize=8,
                color=viz.SERIES[1], fontweight="bold")
    a2.set_ylabel("Cartera bruta real, var. anual (%)")

    viz.eje_tiempo(a2, fechas)
    fig.text(0.0, -0.02, "Cartera deflactada con el IPC (base dic-2018). "
                         "Fuente: SFC y DANE, cálculos propios.", fontsize=7, color=viz.MUTED)
    fig.subplots_adjust(hspace=0.18)
    return viz.guardar(fig, "fig4_efecto_denominador.png")


def fig5_tasa_nominal_vs_real(fam):
    # Ambas series están en la misma unidad (% anual), así que van en un solo eje.
    t = fam[fam.familia == "total"].set_index("fecha")
    fechas = list(t.index)

    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    viz.sombrear_episodios(ax, fechas)
    ax.axhline(0, color=viz.EJE, lw=0.8)
    ax.plot(range(len(t)), t["tpm_pct"], color=viz.SERIES[0], label="TPM nominal")
    ax.plot(range(len(t)), t["tpm_real"], color=viz.SERIES[1], label="TPM real")
    ax.fill_between(range(len(t)), t["tpm_real"], 0, where=(t["tpm_real"] < 0),
                    color=viz.SERIES[1], alpha=0.15, lw=0)
    viz.etiquetar_extremo(ax, len(t) - 1, t["tpm_pct"].iloc[-1], "Nominal", viz.SERIES[0])
    viz.etiquetar_extremo(ax, len(t) - 1, t["tpm_real"].iloc[-1], "Real", viz.SERIES[1])

    i = fechas.index("2022-12")
    coma = lambda v: f"{v:.1f}".replace("-", "−").replace(".", ",")
    ax.annotate(f"dic−2022: la nominal iba en {coma(t['tpm_pct'].iloc[i])}%,\n"
                f"la real todavía en {coma(t['tpm_real'].iloc[i])}%",
                xy=(i, t["tpm_real"].iloc[i]), xytext=(fechas.index("2016-03"), -4.2),
                textcoords="data", fontsize=8, color=viz.TINTA_2, va="center",
                arrowprops=dict(arrowstyle="-", color=viz.MUTED, lw=0.8,
                                connectionstyle="arc3,rad=-0.15"))
    ax.set_ylim(bottom=min(-5.2, t["tpm_real"].min() - 0.6))

    viz.eje_tiempo(ax, fechas)
    ax.set_xlim(-1, len(fechas) + 14)
    ax.set_ylabel("Tasa de política monetaria (% anual)")
    ax.set_title("El apretón monetario real llega más de un año después del nominal")
    ax.legend(loc="upper left", ncols=2)
    fig.text(0.0, -0.03, "Tasa real ex post: (1+i)/(1+π)−1, con π la variación anual del IPC. "
                         "Fuente: BanRep y DANE, cálculos propios.", fontsize=7, color=viz.MUTED)
    return viz.guardar(fig, "fig5_tasa_nominal_vs_real.png")


def fig6_icv_por_producto(prod):
    ult = prod.fecha.max()
    d = prod[(prod.fecha == ult) & (prod.cartera_bruta > 1e12)].copy()
    d = d.sort_values("icv")
    # El tamaño de la cartera va en la etiqueta: una barra larga de ICV sobre un
    # producto de 2 billones no significa lo mismo que sobre uno de 150.
    etiquetas = [f"{viz.nombre_producto(p)}  ({c / 1e12:,.0f} bn)"
                 for p, c in zip(d.producto, d.cartera_bruta)]

    fig, ax = plt.subplots(figsize=(7.6, max(4.0, 0.28 * len(d))))
    y = np.arange(len(d))
    ax.barh(y, d.icv * 100, height=0.62,
            color=[viz.COLOR_FAMILIA[f] for f in d.familia])
    ax.set_yticks(y, etiquetas, fontsize=8)
    ax.set_xlabel("ICV (%)")
    ax.set_title(f"Calidad de cartera por producto, {ult}")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)

    for yi, v in zip(y, d.icv * 100):
        ax.annotate(f"{v:.1f}", xy=(v, yi), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=7.5, color=viz.TINTA_2)
    ax.set_xlim(0, (d.icv * 100).max() * 1.12)

    manejadores = [plt.Line2D([], [], color=viz.COLOR_FAMILIA[f], lw=6,
                              label=viz.ETIQUETA_FAMILIA[f])
                   for f in ["consumo", "comercial", "vivienda", "microcredito"]
                   if f in set(d.familia)]
    ax.legend(handles=manejadores, loc="lower right", ncols=2)
    fig.text(0.0, -0.02, "Productos con cartera bruta superior a 1 billón de pesos; entre "
                         "paréntesis, el saldo en billones. La longitud de la barra es el ICV y no "
                         "refleja el tamaño del producto:\n\"Otros portafolios de consumo\" es una "
                         "categoría residual que pesa 0,9 % de la cartera de consumo. "
                         "Fuente: SFC, cálculos propios.", fontsize=7, color=viz.MUTED)
    return viz.guardar(fig, "fig6_icv_por_producto.png")


# ----------------------------------------------------------------- tablas ---

def tabla1_descriptivas(fam, prod):
    filas = []
    for f in ["consumo", "comercial", "vivienda", "microcredito", "total"]:
        d = fam[fam.familia == f]
        filas.append({
            "Segmento": viz.ETIQUETA_FAMILIA[f],
            "Cartera jun-2026 (billones)": round(d.cartera_bruta.iloc[-1] / 1e12, 1),
            "ICV medio (%)": round(d.icv.mean() * 100, 2),
            "ICV d.e. (pp)": round(d.icv.std() * 100, 2),
            "ICV mín (%)": round(d.icv.min() * 100, 2),
            "ICV máx (%)": round(d.icv.max() * 100, 2),
            "Mes del máximo": d.loc[d.icv.idxmax(), "fecha"],
            "Mora temprana / total (%)": round((d.vencida_temprana.sum() / d.vencida.sum()) * 100, 1),
        })
    t = pd.DataFrame(filas)
    viz.TABLAS.mkdir(parents=True, exist_ok=True)
    t.to_csv(viz.TABLAS / "tabla1_descriptivas.csv", index=False)
    return t


def tabla2_raices_unitarias(fam):
    from statsmodels.tsa.stattools import adfuller, kpss

    t = fam[fam.familia == "total"].set_index("fecha")
    series = {
        "ICV total": t["icv"] * 100,
        "ICV consumo": fam[fam.familia == "consumo"].set_index("fecha")["icv"] * 100,
        "Tasa de desempleo": t["td_pct"],
        "TPM real": t["tpm_real"],
        "Inflación anual": t["ipc_var_anual"],
        "Cartera real, var. anual": t["cartera_var_real_anual"],
    }

    filas = []
    for nombre, s in series.items():
        for etiqueta, x in [("nivel", s.dropna()), ("1ª diferencia", s.diff().dropna())]:
            if len(x) < 24:
                continue
            p_adf = adfuller(x, autolag="AIC")[1]
            p_kpss = kpss(x, regression="c", nlags="auto")[1]
            # ADF: H0 = raíz unitaria. KPSS: H0 = estacionaria. Se leen juntos.
            if p_adf < 0.05 and p_kpss > 0.05:
                veredicto = "estacionaria"
            elif p_adf >= 0.05 and p_kpss <= 0.05:
                veredicto = "raíz unitaria"
            else:
                veredicto = "ambiguo"
            filas.append({"Serie": nombre, "Transformación": etiqueta,
                          "ADF (p)": round(p_adf, 3), "KPSS (p)": round(p_kpss, 3),
                          "Veredicto": veredicto})
    t2 = pd.DataFrame(filas)
    t2.to_csv(viz.TABLAS / "tabla2_raices_unitarias.csv", index=False)
    return t2


def tabla3_correlaciones_rezagos(fam):
    t = fam[fam.familia == "consumo"].set_index("fecha")
    base = fam[fam.familia == "total"].set_index("fecha")
    # Diferencias a 12 meses, no mensuales: la variación mes a mes de la tasa de
    # desempleo está dominada por el salto de enero (ver tabla 4), así que
    # correlacionar primeras diferencias mide estacionalidad, no economía.
    d12 = lambda s: s.diff(12)
    icv = d12(t["icv"] * 100)
    regresores = {
        "Tasa de desempleo": d12(base["td_pct"]),
        "TPM real": d12(base["tpm_real"]),
        "Inflación anual": d12(base["ipc_var_anual"]),
        "Cartera real, var. anual": d12(base["cartera_var_real_anual"]),
    }
    rezagos = [0, 3, 6, 9, 12]
    filas = []
    for nombre, x in regresores.items():
        fila = {"Regresor (Δ12)": nombre}
        for k in rezagos:
            fila[f"t−{k}"] = round(icv.corr(x.shift(k)), 3)
        filas.append(fila)
    t3 = pd.DataFrame(filas)
    t3.to_csv(viz.TABLAS / "tabla3_correlaciones_rezagos.csv", index=False)
    return t3


def tabla4_estacionalidad(fam):
    """
    Efecto de mes calendario sobre la variación mensual. Justifica dos decisiones
    de especificación: usar diferencias a 12 meses y pedirle al DANE la serie
    desestacionalizada de la GEIH.
    """
    t = fam[fam.familia == "total"].copy()
    t["mes"] = t.fecha.str[5:7].astype(int)
    series = {"Tasa de desempleo (pp)": t.set_index("mes")["td_pct"],
              "ICV total (pp)": t.set_index("mes")["icv"] * 100,
              "ICV consumo (pp)": fam[fam.familia == "consumo"]["icv"].values * 100}
    filas = []
    for nombre, s in series.items():
        v = pd.Series(np.asarray(s, dtype=float)).diff()
        v.index = t.mes.values
        m = v.groupby(level=0).mean()
        fila = {"Serie": nombre}
        fila.update({f"{k:02d}": round(m.get(k, np.nan), 2) for k in range(1, 13)})
        filas.append(fila)
    t4 = pd.DataFrame(filas)
    t4.to_csv(viz.TABLAS / "tabla4_estacionalidad.csv", index=False)
    return t4


def main():
    viz.aplicar_estilo()
    fam, prod, tj = cargar()

    print("Figuras:")
    for f in [fig1_icv_por_familia(fam), fig2_tarjeta_por_ingreso(tj),
              fig3_exposicion_producto(prod), fig4_efecto_denominador(fam),
              fig5_tasa_nominal_vs_real(fam), fig6_icv_por_producto(prod)]:
        print(f"  {f.relative_to(RAIZ)}")

    print("\nTABLA 1 — Descriptivas por segmento")
    print(tabla1_descriptivas(fam, prod).to_string(index=False))
    print("\nTABLA 2 — Raíces unitarias")
    print(tabla2_raices_unitarias(fam).to_string(index=False))
    print("\nTABLA 3 — Correlación de Δ12 ICV consumo con los regresores rezagados")
    print(tabla3_correlaciones_rezagos(fam).to_string(index=False))
    print("\nTABLA 4 — Efecto de mes calendario sobre la variación mensual (media 2015-2026)")
    print(tabla4_estacionalidad(fam).to_string(index=False))
    print(f"\nTablas en {viz.TABLAS.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
