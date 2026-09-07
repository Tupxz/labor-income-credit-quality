"""
Estilo y paleta para las figuras del Caso 3.

Las figuras salen en PNG a 200 dpi para pegar en el Word (máx. 10 páginas) y se
proyectan en la sustentación, así que están pensadas para leerse a distancia:
trazos delgados, rejilla de un solo tono por debajo de la superficie, y la
identidad de cada serie por color + etiqueta directa, nunca por color solo.

Dos reglas que no se rompen
---------------------------
1. **Nada de eje secundario.** Un gráfico con dos escalas verticales inventa una
   correlación que no está en los datos: el alineamiento entre las dos escalas es
   arbitrario y quien lo lee cree ver co-movimiento donde solo hay dos ejes mal
   puestos. Cuando hay dos medidas de escala distinta se usan dos paneles
   apilados que comparten el eje del tiempo (`paneles_apilados`), o se indexan
   ambas a una base común. (El stub anterior de este archivo pedía justamente un
   eje secundario; se descartó por esto.)
2. **El color sigue a la entidad, no al puesto.** Cada segmento tiene su color
   fijo en todas las figuras: si consumo es azul en una, es azul en todas.

La paleta está validada para daltonismo en el orden en que se asignan las
ranuras; no reordenar ni agregar una novena serie (la cola se agrupa en "otros").
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parents[1]
FIGURAS = RAIZ / "output" / "figuras"
TABLAS = RAIZ / "output" / "tablas"

# Ranuras categóricas, en orden
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
          "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

# Rampa secuencial (una sola tonalidad, claro -> oscuro)
SECUENCIAL = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
              "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
              "#184f95", "#104281", "#0d366b"]

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
MUTED = "#898781"
REJILLA = "#e1e0d9"
EJE = "#c3c2b7"

# Color fijo por familia de cartera, igual en todas las figuras
COLOR_FAMILIA = {
    "consumo": SERIES[0],
    "comercial": SERIES[1],
    "vivienda": SERIES[2],
    "microcredito": SERIES[3],
    "total": TINTA_2,
}

ETIQUETA_FAMILIA = {
    "consumo": "Consumo",
    "comercial": "Comercial",
    "vivienda": "Vivienda",
    "microcredito": "Microcrédito",
    "total": "Total",
}

# Episodios que se sombrean para dar contexto
EPISODIOS = [
    ("2020-03", "2020-12", "Pandemia"),
    ("2022-06", "2023-12", "Choque inflacionario"),
]


def aplicar_estilo() -> None:
    mpl.rcParams.update({
        "figure.facecolor": SUPERFICIE,
        "axes.facecolor": SUPERFICIE,
        "savefig.facecolor": SUPERFICIE,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlecolor": TINTA,
        "axes.titlelocation": "left",
        "axes.titlepad": 10,
        "axes.labelsize": 9,
        "axes.labelcolor": TINTA_2,
        "axes.edgecolor": EJE,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": REJILLA,
        "grid.linewidth": 0.7,
        "grid.linestyle": "-",          # nunca punteada: la rejilla no es un umbral
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "legend.frameon": False,
        "legend.fontsize": 8,
        "lines.linewidth": 2.0,
        "lines.solid_capstyle": "round",
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
    })


def sombrear_episodios(ax, x, etiquetar: bool = True) -> None:
    """Sombra gris muy tenue sobre los episodios de contexto."""
    idx = list(x)
    for inicio, fin, nombre in EPISODIOS:
        if inicio not in idx or fin not in idx:
            continue
        i0, i1 = idx.index(inicio), idx.index(fin)
        ax.axvspan(i0, i1, color=TINTA, alpha=0.045, lw=0, zorder=0)
        if etiquetar:
            ax.annotate(nombre, xy=((i0 + i1) / 2, 0.99), xycoords=("data", "axes fraction"),
                        xytext=(0, -2), textcoords="offset points",
                        ha="center", va="top", fontsize=7, color=MUTED)


def etiquetar_extremo(ax, x, y, texto, color, dx=6) -> None:
    """Etiqueta directa en el último punto: identidad sin depender del color."""
    ax.annotate(f" {texto}", xy=(x, y), xytext=(dx, 0), textcoords="offset points",
                va="center", ha="left", fontsize=8, color=color, fontweight="bold",
                annotation_clip=False)


def eje_tiempo(ax, fechas, cada: int = 12) -> None:
    """Marcas de año sobre un eje categórico de periodos 'AAAA-MM'."""
    pos = [i for i, f in enumerate(fechas) if f.endswith("-01")]
    ax.set_xticks(pos)
    ax.set_xticklabels([fechas[i][:4] for i in pos])
    ax.set_xlim(-1, len(fechas))


def guardar(fig, nombre: str) -> Path:
    FIGURAS.mkdir(parents=True, exist_ok=True)
    ruta = FIGURAS / nombre
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


# Nombres de producto legibles. La fuente trae mayúsculas sostenidas, tildes
# inconsistentes y typos propios ("FACTOTING", "FINAN E INSTITUCIO"), así que el
# mapeo es explícito y no un .title().
NOMBRE_PRODUCTO = {
    "CRÉDITO ROTATIVO": "Crédito rotativo",
    "TARJETAS DE CRÉDITO": "Tarjeta de crédito",
    "LIBRE INVERSIÓN": "Libre inversión",
    "LIBRANZA": "Libranza",
    "VEHÍCULO": "Vehículo",
    "OTROS PORTAFOLIOS DE CONSUMO": "Otros portafolios de consumo",
    "MICROCREDITOS < O IGUALES A 25 SMMLV": "Microcrédito ≤ 25 SMMLV",
    "MICROCREDITOS > 25  Y HASTA 120 SMMLV": "Microcrédito 25–120 SMMLV",
    "VIVIENDA VIS PESOS": "Vivienda VIS, pesos",
    "VIVIENDA VIS UVR": "Vivienda VIS, UVR",
    "VIVIENDA NO VIS PESOS": "Vivienda no VIS, pesos",
    "VIVIENDA NO VIS UVR": "Vivienda no VIS, UVR",
    "LEASING HABITACIONAL VIS PESOS": "Leasing habitacional VIS, pesos",
    "LEASING HABITACIONAL VIS UVR": "Leasing habitacional VIS, UVR",
    "LEASING HABITACIONAL NO VIS PESOS": "Leasing habitacional no VIS, pesos",
    "LEASING HABITACIONAL NO VIS UVR": "Leasing habitacional no VIS, UVR",
    "LIBRANZA VIVIENDA VIS": "Libranza vivienda VIS",
    "LIBRANZA VIVIENDA NO VIS": "Libranza vivienda no VIS",
    "CARTERA COMERCIAL CORPORATIVO": "Comercial corporativo",
    "CARTERA COMERCIAL EMPRESARIAL": "Comercial empresarial",
    "CARTERA COMERCIAL PYMES": "Comercial pymes",
    "CARTERA COMERCIAL MICROEMPRESA": "Comercial microempresa",
    "CARTERA COMERCIAL OFICIAL O GOBIERNO": "Comercial oficial o gobierno",
    "CARTERA COMERCIAL FACTOTING": "Comercial factoring",
    "CARTERA COMERCIAL FINAN E INSTITUCIO": "Comercial financiero e institucional",
    "CARTERA COMERCIAL MONEDA EXTRANJERA": "Comercial moneda extranjera",
    "CARTERA COMERCIAL CONSTRUCCION": "Comercial construcción",
    "CARTERA COMERCIAL LEASING FINANCIERO": "Comercial leasing financiero",
    "CONSUMO BAJO MONTO": "Consumo de bajo monto",
    "CREDITOS DE CONSUMO PARA EMPLEADOS": "Consumo, empleados de la entidad",
    "CREDITOS DE VIVIENDA PARA EMPLEADOS VIS": "Vivienda VIS, empleados de la entidad",
    "CREDITOS DE VIVIENDA PARA EMPL NO VIS": "Vivienda no VIS, empleados de la entidad",
}


def nombre_producto(p: str) -> str:
    return NOMBRE_PRODUCTO.get(p, p.capitalize())
