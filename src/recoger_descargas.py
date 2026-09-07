"""
Mueve a data/raw/geih_microdatos/ los zips de microdatos GEIH recién bajados.

Seguridad: NUNCA se decide por el nombre del archivo. La carpeta de Descargas es
del usuario y tiene sus cosas; se mueve un archivo solo si cumple las tres:
  1. fue modificado hace menos de MINUTOS minutos,
  2. abre como zip válido y completo,
  3. contiene un módulo "Ocupados" — la firma de un paquete de microdatos GEIH.
Cualquier otra cosa se deja intacta.

Uso:  python src/recoger_descargas.py [--minutos 45] [--descargas RUTA]
"""

from pathlib import Path
import argparse
import shutil
import time
import zipfile

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "data" / "raw" / "geih_microdatos"
DESCARGAS = Path.home() / "mnt" / "Downloads"


def es_microdato_geih(p: Path) -> bool:
    try:
        with zipfile.ZipFile(p) as z:
            if z.testzip() is not None:
                return False
            return any("ocupados" in Path(n).name.lower()
                       and not Path(n).name.lower().startswith("no")
                       for n in z.namelist())
    except Exception:
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--minutos", type=int, default=45)
    ap.add_argument("--descargas", type=Path, default=DESCARGAS)
    a = ap.parse_args()

    DESTINO.mkdir(parents=True, exist_ok=True)
    corte = time.time() - a.minutos * 60
    movidos, saltados, i = 0, 0, 0

    for p in sorted(a.descargas.iterdir()):
        if not p.is_file() or p.stat().st_mtime < corte:
            continue
        if not es_microdato_geih(p):
            saltados += 1
            continue
        i += 1
        destino = DESTINO / f"descarga_{int(time.time())}_{i}.zip"
        shutil.move(str(p), destino)
        movidos += 1

    print(f"movidos {movidos} paquete(s) de microdatos GEIH")
    if saltados:
        print(f"  ({saltados} archivo(s) recientes NO son microdatos GEIH — no se tocaron)")


if __name__ == "__main__":
    main()
