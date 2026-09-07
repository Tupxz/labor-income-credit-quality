"""
Descarga y procesa los microdatos de la GEIH que falten, de una sola pasada.

CORRERLO EN TU TERMINAL, no desde Claude: la máquina donde corre Claude no tiene
salida a microdatos.dane.gov.co, la tuya sí.

    cd <carpeta del proyecto>
    python3 src/bajar_geih.py

Es reanudable: mira qué meses ya están en data/processed/geih_ingreso_laboral_mensual.csv
y solo baja los que faltan. Si lo cortas con Ctrl-C, lo vuelves a lanzar y sigue
donde iba. Cada mes pesa 10-70 MB, se procesa y se borra de inmediato, así que
nunca ocupa más de un archivo a la vez en disco.

Opciones:
    --anios 2015 2016 2017      solo esos años
    --conservar                 no borra los zip (ocupa ~9 GB, normalmente no quieres)
"""

from pathlib import Path
import argparse
import sys
import time

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geih_recursos import BASE, CATALOGO_POR_ANIO, RECURSOS   # noqa: E402
from procesar_geih_microdatos import CRUDO, SALIDA, procesar_zip  # noqa: E402

try:
    import requests
except ImportError:
    sys.exit("Falta requests:  pip3 install requests")

CABECERAS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


def ya_calculados() -> tuple[pd.DataFrame, set]:
    if SALIDA.exists():
        d = pd.read_csv(SALIDA)
        return d, set(d.fecha.astype(str))
    return pd.DataFrame(), set()


def guardar(previos: pd.DataFrame, fila: dict) -> pd.DataFrame:
    nuevo = pd.DataFrame([fila]).assign(fecha=lambda x: x.fecha.astype(str))
    d = pd.concat([previos, nuevo], ignore_index=True)
    d = d.drop_duplicates("fecha", keep="last").sort_values("fecha").reset_index(drop=True)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(SALIDA, index=False)
    return d


def descargar(url: str, destino: Path, intentos: int = 3) -> bool:
    for k in range(intentos):
        try:
            with requests.get(url, headers=CABECERAS, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(destino, "wb") as f:
                    for trozo in r.iter_content(1 << 20):
                        f.write(trozo)
            return True
        except Exception as e:
            print(f"      intento {k + 1}/{intentos} falló: {str(e)[:60]}")
            time.sleep(3 * (k + 1))
    return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anios", type=int, nargs="*", default=None)
    ap.add_argument("--conservar", action="store_true")
    a = ap.parse_args()

    CRUDO.mkdir(parents=True, exist_ok=True)
    previos, hechos = ya_calculados()
    print(f"Ya calculados: {len(hechos)} meses\n")

    # 1) primero, lo que ya esté descargado en la carpeta
    for z in sorted(CRUDO.glob("*.zip")):
        try:
            f = procesar_zip(z, diagnostico=False, anio_pista=None)
        except Exception as e:
            print(f"  {z.name}: falló ({str(e)[:60]})")
            f = None
        if f and str(f["fecha"]) not in hechos:
            previos = guardar(previos, f)
            hechos.add(str(f["fecha"]))
            print(f"  ok {f['fecha']} (ya estaba descargado)")
        if not a.conservar:
            z.unlink(missing_ok=True)

    # 2) luego, lo que falte
    anios = a.anios or sorted(RECURSOS)
    pendientes = [(anio, i + 1, rid)
                  for anio in anios
                  for i, (_, rid) in enumerate(RECURSOS[anio])
                  if f"{anio}-{i + 1:02d}" not in hechos]

    print(f"\nFaltan {len(pendientes)} meses. Empezando.\n")
    for n, (anio, mes, rid) in enumerate(pendientes, 1):
        etiqueta = f"{anio}-{mes:02d}"
        url = BASE.format(cat=CATALOGO_POR_ANIO[anio], rid=rid)
        destino = CRUDO / f"_descarga_{etiqueta}.zip"
        print(f"[{n}/{len(pendientes)}] {etiqueta}", end="  ", flush=True)

        if not descargar(url, destino):
            print("NO SE PUDO DESCARGAR — se salta")
            destino.unlink(missing_ok=True)
            continue

        mb = destino.stat().st_size / 1e6
        try:
            f = procesar_zip(destino, diagnostico=False, anio_pista=anio)
        except Exception as e:
            print(f"({mb:.0f} MB) falló al procesar: {str(e)[:60]}")
            f = None

        if f:
            detectado = str(f["fecha"])
            if detectado != etiqueta:
                print(f"({mb:.0f} MB) OJO: pedí {etiqueta} y el archivo dice {detectado}")
            previos = guardar(previos, f)
            hechos.add(detectado)
            print(f"({mb:.0f} MB) media {f['total_media']:,.0f}  mediana {f['total_mediana']:,.0f}")
        if not a.conservar:
            destino.unlink(missing_ok=True)

    d, _ = ya_calculados()
    esperados = pd.period_range("2015-01", "2026-06", freq="M").astype(str)
    faltan = [m for m in esperados if m not in set(d.fecha.astype(str))]
    print(f"\nTerminado: {len(d)} meses en {SALIDA.relative_to(Path(__file__).resolve().parents[1])}")
    print(f"Faltan {len(faltan)} de 138" + (f": {', '.join(faltan[:10])}" if faltan else " — completo"))


if __name__ == "__main__":
    main()
