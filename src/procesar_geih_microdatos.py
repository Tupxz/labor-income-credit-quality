"""
Ingreso laboral mensual a partir de los MICRODATOS de la GEIH (DANE).

Por qué microdatos y no los anexos
-----------------------------------
Los anexos mensuales de la GEIH (data/raw/dane_geih/) NO publican ingreso
laboral: se revisaron las hojas de los 137 archivos y la única que suena a
ingreso, `Total_nacional_IML_Sexo`, es en realidad "Indicadores de Mercado
Laboral por sexo" (TGP/TO/TD/TS). El ingreso solo existe a nivel de persona,
en el módulo de Ocupados de los microdatos.

Qué calcula
-----------
Por mes, ponderando siempre por el factor de expansión:
    media y MEDIANA del ingreso laboral de los ocupados
    lo mismo abierto por formalidad (cotiza a pensión) y por posición
    ocupacional (asalariado / cuenta propia)
    número de ocupados expandido

La mediana importa: la distribución del ingreso laboral colombiano es muy
asimétrica a la derecha, así que la media se mueve con la cola alta y no con el
deudor típico. Para la capacidad de pago agregada sirve la media; para el
deudor representativo, la mediana. El modelo debería correrse con las dos.

Cómo conseguir los datos (no hay red desde aquí, toca a mano)
--------------------------------------------------------------
1. Entrar a https://microdatos.dane.gov.co/index.php/catalog/
   y buscar "Gran Encuesta Integrada de Hogares".
2. Bajar, mes a mes, el archivo de microdatos (viene en .zip).
3. Dejar los .zip TAL CUAL en data/raw/geih_microdatos/ — este script los abre
   sin descomprimir. El nombre debe contener el mes y el año en algún formato
   reconocible (p. ej. GEIH_ENERO_2024.zip o geih-2024-01.zip).
4. Correr:  python src/procesar_geih_microdatos.py

Empezar por UN mes y revisar el diagnóstico que imprime antes de bajar los 138.

Salida: data/processed/geih_ingreso_laboral_mensual.csv
"""

from pathlib import Path
import io
import re
import sys
import unicodedata
import zipfile

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CRUDO = RAIZ / "data" / "raw" / "geih_microdatos"
SALIDA = RAIZ / "data" / "processed" / "geih_ingreso_laboral_mensual.csv"

# El DANE cambia nombres de variables y de módulos entre años, así que todo se
# busca por alias y el script reporta qué encontró en vez de asumir.
ALIAS = {
    "ingreso": ["INGLABO", "INGTOT", "IMPA", "P6500"],
    "factor": ["FEX_C18", "FEX_C_2011", "FEX_C", "FEX_DPTO_2011", "FACTOR_EXPANSION", "FEX"],
    "cotiza_pension": ["P6920"],
    "posicion": ["P6430"],
    "tam_empresa": ["P6870"],
    "mes": ["MES"],
    "anio": ["ANIO", "AÑO", "ANO", "PERIODO"],
}
# El zip trae "Ocupados" y "No ocupados": hay que excluir el segundo o se
# terminaría calculando el ingreso de los desocupados. Y viene en CSV, DTA y SAV;
# el CSV pesa 10 MB contra 990 MB del DTA, así que se prefiere CSV.
PATRON_OCUPADOS = re.compile(r"\bocupados?\b", re.I)
PATRON_NO_OCUPADOS = re.compile(r"(^|[^a-z])(no[\s_]*ocupad|desocupad)", re.I)
PRIORIDAD_FORMATO = [".csv", ".dta", ".txt"]

# Los meses anteriores a 2022 parten el módulo por dominio geográfico:
#   "Cabecera - Ocupados.CSV", "Resto - Ocupados.CSV", "Área - Ocupados.CSV".
# Cabecera + Resto = total nacional; ÁREA ES UN SUBCONJUNTO DE CABECERA (las 13
# o 23 áreas metropolitanas), no un tercer dominio. Verificado en ene-2021:
#   Cabecera 15,656 M + Resto 4,312 M = 19,968 M contra 19,106 M oficial,
#   mientras que sumando también Área da 29,563 M, un 55 % de más.
# Por eso se toman Cabecera y Resto y se descarta Área.
DOMINIOS_NACIONALES = ("cabecera", "resto")

MESES_TXT = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
             "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
             "noviembre": 11, "diciembre": 12,
             "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
             "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}


def sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def hallar(cols, claves) -> str | None:
    norm = {sin_tildes(str(c)).upper().strip(): c for c in cols}
    for k in claves:
        if k.upper() in norm:
            return norm[k.upper()]
    return None


def periodo_desde_nombre(nombre: str) -> pd.Period | None:
    n = sin_tildes(nombre).lower()
    m = re.search(r"(20\d{2})[^0-9]{0,3}(0[1-9]|1[0-2])(?!\d)", n)
    if m:
        return pd.Period(f"{m.group(1)}-{m.group(2)}", freq="M")
    m = re.search(r"(0[1-9]|1[0-2])[^0-9]{0,3}(20\d{2})", n)
    if m:
        return pd.Period(f"{m.group(2)}-{m.group(1)}", freq="M")
    for txt, num in MESES_TXT.items():
        if txt in n:
            a = re.search(r"(20\d{2})", n)
            if a:
                return pd.Period(f"{a.group(1)}-{num:02d}", freq="M")
    return None


def periodo_desde_contenido(nombres, anio_pista: int | None) -> pd.Period | None:
    """
    Deduce el mes leyendo el nombre de la carpeta interna del zip, que el DANE
    siempre nombra con el mes ("Ene_2024/", "Enero/", "GEIH_Enero_2022.../",
    "1.Enero/", "Enero 2025/"). Es lo único fiable cuando el .zip llegó del
    navegador con un nombre temporal.
    """
    raiz = {n.split("/")[0] for n in nombres if "/" in n}
    for r in raiz:
        n = sin_tildes(r).lower()
        mes = next((v for k, v in MESES_TXT.items() if k in n), None)
        if mes is None:
            continue
        m = re.search(r"(20\d{2})", n)
        anio = int(m.group(1)) if m else anio_pista
        if anio:
            return pd.Period(f"{anio}-{mes:02d}", freq="M")
    return None


def buscar_ocupados(z: zipfile.ZipFile):
    """
    Devuelve (etiqueta, [bytes, ...]) de los módulos de Ocupados que hay que
    juntar para cubrir el total nacional, o (None, None).
    """
    cand = [n for n in z.namelist()
            if PATRON_OCUPADOS.search(Path(n).name)
            and not PATRON_NO_OCUPADOS.search(Path(n).name)
            and Path(n).suffix.lower() in PRIORIDAD_FORMATO]
    if not cand:
        return None, None

    fmt = min(PRIORIDAD_FORMATO.index(Path(n).suffix.lower()) for n in cand)
    cand = [n for n in cand if PRIORIDAD_FORMATO.index(Path(n).suffix.lower()) == fmt]

    if len(cand) > 1:
        nacionales = [n for n in cand
                      if sin_tildes(Path(n).name).lower().startswith(DOMINIOS_NACIONALES)]
        if nacionales:
            cand = nacionales
    return " + ".join(Path(n).name for n in cand), [z.read(n) for n in cand]


def leer_tabla(datos: bytes, nombre: str) -> pd.DataFrame | None:
    """Los microdatos vienen en CSV con ';' y latin-1, pero no siempre."""
    if nombre.lower().endswith(".dta"):
        try:
            return pd.read_stata(io.BytesIO(datos), convert_categoricals=False)
        except Exception:
            pass
        # pandas no lee los .dta de Stata 110 (sep-2021, entre otros). pyreadstat
        # sí, pero necesita una ruta en disco, no un buffer.
        try:
            import pyreadstat
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".dta", delete=False) as t:
                t.write(datos)
                ruta = t.name
            try:
                d, _ = pyreadstat.read_dta(ruta)
                return d
            finally:
                Path(ruta).unlink(missing_ok=True)
        except ImportError:
            print(f"      {nombre}: formato Stata viejo. Instalar:  pip3 install pyreadstat")
        except Exception as e:
            print(f"      no pude leer {nombre}: {str(e)[:80]}")
        return None
    for sep in [";", ",", "\t", "|"]:
        for enc in ["latin-1", "utf-8-sig"]:
            try:
                d = pd.read_csv(io.BytesIO(datos), sep=sep, encoding=enc,
                                low_memory=False, decimal=",")
                if d.shape[1] > 3:
                    return d
            except Exception:
                continue
    # Algunos meses (sep-2021, por ejemplo) vienen separados por espacios en
    # blanco en vez de ';' o ','. Va de último porque el motor de python es lento.
    for enc in ["latin-1", "utf-8-sig"]:
        try:
            d = pd.read_csv(io.BytesIO(datos), sep=r"\s+", engine="python",
                            encoding=enc, decimal=",")
            if d.shape[1] > 3:
                return d
        except Exception:
            continue
    return None


def cuantil_ponderado(x: np.ndarray, w: np.ndarray, q: float) -> float:
    """Mediana (o cualquier cuantil) usando el factor de expansión."""
    ok = np.isfinite(x) & np.isfinite(w) & (w > 0)
    x, w = x[ok], w[ok]
    if len(x) == 0:
        return np.nan
    o = np.argsort(x)
    x, w = x[o], w[o]
    acum = np.cumsum(w) - 0.5 * w
    acum /= w.sum()
    return float(np.interp(q, acum, x))


def resumir(d: pd.DataFrame, col_ing: str, col_fex: str, etiqueta: str) -> dict:
    x = pd.to_numeric(d[col_ing], errors="coerce").to_numpy(dtype=float)
    w = pd.to_numeric(d[col_fex], errors="coerce").to_numpy(dtype=float)
    ok = np.isfinite(x) & np.isfinite(w) & (w > 0) & (x > 0)
    x, w = x[ok], w[ok]
    if len(x) == 0:
        return {f"{etiqueta}_media": np.nan, f"{etiqueta}_mediana": np.nan,
                f"{etiqueta}_p25": np.nan, f"{etiqueta}_p75": np.nan,
                f"{etiqueta}_ocupados": np.nan, f"{etiqueta}_n": 0}
    return {
        f"{etiqueta}_media": float(np.average(x, weights=w)),
        f"{etiqueta}_mediana": cuantil_ponderado(x, w, 0.50),
        f"{etiqueta}_p25": cuantil_ponderado(x, w, 0.25),
        f"{etiqueta}_p75": cuantil_ponderado(x, w, 0.75),
        f"{etiqueta}_ocupados": float(w.sum()),
        f"{etiqueta}_n": int(len(x)),
    }


def procesar_zip(ruta: Path, diagnostico: bool, anio_pista: int | None = None) -> dict | None:
    periodo = periodo_desde_nombre(ruta.name)
    try:
        with zipfile.ZipFile(ruta) as _z:
            _z.namelist()   # solo el directorio central: no descomprime nada
    except Exception as e:
        print(f"  {ruta.name}: zip corrupto o incompleto ({str(e)[:50]}) — se omite")
        return None
    with zipfile.ZipFile(ruta) as z:
        if periodo is None:
            periodo = periodo_desde_contenido(z.namelist(), anio_pista)

        nombre, datos = buscar_ocupados(z)

        # Algunos meses vienen como zip dentro de zip: el paquete del mes trae
        # CSV.zip / DTA.zip / SAV.zip y el módulo está un nivel más abajo.
        if nombre is None:
            internos = [n for n in z.namelist() if n.lower().endswith(".zip")]
            internos.sort(key=lambda n: 0 if "csv" in n.lower() else 1)
            for interno in internos:
                try:
                    with zipfile.ZipFile(io.BytesIO(z.read(interno))) as zi:
                        if periodo is None:
                            periodo = periodo_desde_contenido(zi.namelist(), anio_pista)
                        nombre, datos = buscar_ocupados(zi)
                        if nombre:
                            nombre = f"{interno}!{nombre}"
                            break
                except zipfile.BadZipFile:
                    continue

        if nombre is None:
            print(f"  {ruta.name}: no encuentro módulo de Ocupados. Archivos dentro:")
            for n in z.namelist()[:15]:
                print(f"      {n}")
            return None
        partes = [leer_tabla(b, nombre) for b in datos]
        partes = [x for x in partes if x is not None and not x.empty]
        d = pd.concat(partes, ignore_index=True, sort=False) if partes else None

    if d is None or d.empty:
        print(f"  {ruta.name}: no pude leer {nombre}")
        return None

    col_ing = hallar(d.columns, ALIAS["ingreso"])
    col_fex = hallar(d.columns, ALIAS["factor"])
    if col_ing is None or col_fex is None:
        print(f"  {ruta.name}: falta ingreso ({col_ing}) o factor ({col_fex}).")
        print(f"      columnas disponibles: {list(d.columns)[:40]}")
        return None

    if diagnostico:
        print(f"\n  DIAGNÓSTICO {ruta.name}")
        print(f"      módulo:  {nombre}")
        print(f"      filas:   {len(d):,}")
        print(f"      ingreso: {col_ing}   factor: {col_fex}")
        for k in ["cotiza_pension", "posicion", "tam_empresa"]:
            print(f"      {k}: {hallar(d.columns, ALIAS[k])}")

    if periodo is None:  # último recurso: leerlo de las columnas
        cm, ca = hallar(d.columns, ALIAS["mes"]), hallar(d.columns, ALIAS["anio"])
        try:
            mes = int(pd.to_numeric(d[cm], errors="coerce").dropna().iloc[0]) if cm else None
            anio = None
            if ca:
                # PERIODO viene como 20240835 y similares: el año son los 4 primeros dígitos
                v = int(pd.to_numeric(d[ca], errors="coerce").dropna().iloc[0])
                anio = int(str(v)[:4]) if v > 9999 else v
            anio = anio if (anio and 2000 <= anio <= 2100) else anio_pista
            if anio and mes and 1 <= mes <= 12:
                periodo = pd.Period(f"{anio}-{mes:02d}", freq="M")
        except Exception:
            periodo = None
    if periodo is None:
        print(f"  {ruta.name}: no pude deducir el mes; renombrar a algo tipo geih-2024-01.zip")
        return None

    fila = {"fecha": periodo}
    fila.update(resumir(d, col_ing, col_fex, "total"))

    # Guarda de cobertura. En marzo-julio de 2020, con el operativo telefónico de
    # la pandemia, el DANE imputó INGLABO solo para ~9 % de los ocupados (1.969
    # de 21.881 en marzo). La variable existe pero está casi vacía, así que la
    # media y la mediana de esos meses no representan nada. Si menos de la mitad
    # de la muestra tiene ingreso, se avisa: son meses que no se deben usar.
    cobertura = fila["total_n"] / max(len(d), 1)
    if cobertura < 0.5:
        print(f"      AVISO {periodo}: solo {cobertura:.0%} de los ocupados tiene "
              f"{col_ing} ({fila['total_n']:,} de {len(d):,}). Mes NO utilizable.")
        fila["cobertura_ingreso"] = cobertura

    # Formalidad: cotizar a pensión es el proxy que más se usa en la literatura
    # colombiana de crédito, porque separa justo a quien tiene vida financiera
    # formal (y por tanto acceso a crédito bancario) de quien no.
    col_pen = hallar(d.columns, ALIAS["cotiza_pension"])
    if col_pen:
        pen = pd.to_numeric(d[col_pen], errors="coerce")
        fila.update(resumir(d[pen == 1], col_ing, col_fex, "formal"))
        fila.update(resumir(d[pen != 1], col_ing, col_fex, "informal"))

    # Posición ocupacional: 1 empresa particular, 2 gobierno -> asalariado;
    # 4 cuenta propia, 5 patrón -> independiente.
    col_pos = hallar(d.columns, ALIAS["posicion"])
    if col_pos:
        pos = pd.to_numeric(d[col_pos], errors="coerce")
        fila.update(resumir(d[pos.isin([1, 2])], col_ing, col_fex, "asalariado"))
        fila.update(resumir(d[pos.isin([4, 5])], col_ing, col_fex, "independiente"))

    return fila


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anio", type=int, default=None,
                    help="Año de los zips en la carpeta, para los que llegan con nombre temporal")
    ap.add_argument("--carpeta", type=Path, default=None,
                    help="Carpeta con los zips (por defecto data/raw/geih_microdatos)")
    ap.add_argument("--max", type=int, default=None,
                    help="Procesa a lo sumo N archivos en esta corrida")
    ap.add_argument("--borrar", action="store_true",
                    help="Borra cada zip después de procesarlo (los zips pesan 10-70 MB c/u)")
    args = ap.parse_args()

    carpeta = args.carpeta or CRUDO
    carpeta.mkdir(parents=True, exist_ok=True)
    zips = sorted(carpeta.glob("*.zip"))

    # Incremental: lo ya calculado no se vuelve a calcular.
    previos = pd.DataFrame()
    if SALIDA.exists():
        previos = pd.read_csv(SALIDA)
        print(f"Ya calculados: {len(previos)} meses ({previos.fecha.min()} a {previos.fecha.max()})")
    hechos = set(previos.fecha) if len(previos) else set()

    if not zips:
        print(f"No hay .zip nuevos en {carpeta}.")
        if not len(previos):
            sys.exit("Bajar los microdatos con el navegador (ver LEEME.md de esa carpeta).")
        return

    if args.max:
        zips = zips[:args.max]
    print(f"{len(zips)} zip(s) por procesar" + (f" (año {args.anio})" if args.anio else ""))

    def guardar(nuevas):
        """Se guarda después de CADA mes: una corrida interrumpida no pierde trabajo."""
        if not nuevas:
            return previos
        d = pd.concat([previos, pd.DataFrame(nuevas).assign(fecha=lambda x: x.fecha.astype(str))],
                      ignore_index=True)
        d = d.drop_duplicates("fecha", keep="last").sort_values("fecha").reset_index(drop=True)
        SALIDA.parent.mkdir(parents=True, exist_ok=True)
        d.to_csv(SALIDA, index=False)
        return d

    filas, procesados = [], []
    for i, z in enumerate(zips):
        try:
            f = procesar_zip(z, diagnostico=(i == 0 and not len(previos)), anio_pista=args.anio)
        except Exception as e:
            # Un archivo raro no puede tumbar la corrida entera.
            print(f"  {z.name}: falló ({type(e).__name__}: {str(e)[:70]}) — se omite")
            continue
        if not f:
            continue
        clave = str(f["fecha"])
        if clave in hechos:
            print(f"  {clave} ya estaba — se omite")
        else:
            filas.append(f)
            guardar(filas)
            print(f"  ok {clave}  media {f['total_media']:,.0f}  mediana {f['total_mediana']:,.0f}")
        procesados.append(z)
        if args.borrar:
            z.unlink()   # se borra de una: 60-70 MB por mes que no hacen falta

    if filas:
        d = pd.concat([previos, pd.DataFrame(filas).assign(fecha=lambda x: x.fecha.astype(str))],
                      ignore_index=True)
        d = d.drop_duplicates("fecha", keep="last").sort_values("fecha").reset_index(drop=True)
        SALIDA.parent.mkdir(parents=True, exist_ok=True)
        d.to_csv(SALIDA, index=False)
        print(f"\n{SALIDA.relative_to(RAIZ)}: {len(d)} meses, {d.fecha.min()} a {d.fecha.max()}")

        esperados = pd.period_range("2015-01", "2026-06", freq="M").astype(str)
        faltan = [m for m in esperados if m not in set(d.fecha)]
        print(f"faltan {len(faltan)} de 138 meses" +
              (f": {faltan[0]} … {faltan[-1]}" if faltan else " — completo"))
    else:
        print("\nNingún mes nuevo.")

    if args.borrar and procesados:
        print(f"borrados {len(procesados)} zip(s)")


if __name__ == "__main__":
    main()
