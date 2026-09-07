"""
Mapa de recursos de microdatos de la GEIH en el catálogo NADA del DANE.

Los microdatos NO se publican por mes sino en catálogos ANUALES; dentro de cada
catálogo hay un recurso por mes. La URL de descarga es
    https://microdatos.dane.gov.co/index.php/catalog/{catalogo}/download/{rid}

Los IDs se extrajeron de /index.php/catalog/{id}/get-microdata el 7-sep-2026.
Cuando existe una variante ".csv.zip" se prefiere: pesa ~10 MB contra ~68 MB del
paquete completo (que trae además DTA y SAV, que no usamos).
"""

CATALOGO_POR_ANIO = {2015: 356, 2016: 427, 2017: 458, 2018: 547, 2019: 599,
                     2020: 780, 2021: 701, 2022: 771, 2023: 782, 2024: 819,
                     2025: 853, 2026: 900}

# {anio: [(nombre_del_recurso, rid), ...]}  — tal cual los publica el DANE
RECURSOS = {
2015: [("Enero.csv.zip",13056),("Febrero.csv.zip",13057),("Marzo.csv.zip",13058),("Abril.csv.zip",13059),("Mayo.csv.zip",13060),("Junio.csv.zip",13061),("Julio.csv.zip",13062),("Agosto.csv.zip",13063),("Septiembre.csv.zip",13064),("Octubre.csv.zip",13065),("Noviembre.csv.zip",13066),("Diciembre.csv.zip",13067)],
2016: [("Enero.csv.zip",13101),("Febrero.csv.zip",13102),("Marzo.csv.zip",13103),("Abril.csv.zip",13104),("Mayo.csv.zip",13105),("Junio.csv.zip",13106),("Julio.csv.zip",13107),("Agosto.csv.zip",13108),("Septiembre.csv.zip",13109),("Octubre.csv.zip",13110),("Noviembre.csv.zip",13111),("Diciembre.csv.zip",13112)],
2017: [("Enero.csv.zip",13294),("Febrero.csv.zip",13295),("Marzo.csv.zip",13296),("Abril.csv.zip",13297),("Mayo.csv.zip",13298),("Junio.csv.zip",13299),("Julio.csv.zip",13300),("Agosto.csv.zip",13301),("Septiembre.csv.zip",9035),("Octubre.csv.zip",9038),("Noviembre.csv.zip",9342),("Diciembre.csv.zip",9282)],
2018: [("Enero.csv.zip",12198),("Febrero.csv.zip",12201),("Marzo.csv.zip",12204),("Abril.csv.zip",12207),("Mayo.csv.zip",12210),("Junio.csv.zip",9909),("Julio.csv.zip",10017),("Agosto.csv.zip",10102),("Septiembre.csv.zip",10115),("Octubre.csv.zip",10205),("Noviembre.csv.zip",10341),("Diciembre.csv.zip",10443)],
2019: [("Enero.csv.zip",10719),("Febrero.csv.zip",10964),("Marzo.csv.zip",11117),("Abril.csv.zip",11184),("Mayo.csv.zip",11300),("Junio.csv.zip",12068),("Julio.csv.zip",12100),("Agosto.csv.zip",12221),("Septiembre.csv.zip",12275),("Octubre.csv.zip",12365),("Noviembre.csv.zip",12444),("Diciembre.csv.zip",12516)],
2020: [("1.Enero.zip",22286),("2.Febrero.zip",22287),("3.Marzo.zip",22288),("4.Abril.zip",22289),("5.Mayo.zip",22290),("6.Junio.zip",22291),("7.Julio.zip",22292),("8.Agosto.zip",22293),("9.Septiembre.zip",22294),("10.Octubre.zip",22295),("11.Noviembre.zip",22296),("12.Diciembre.zip",22297)],
2021: [("Enero.csv.zip",23451),("Febrero.csv.zip",23454),("Marzo.csv.zip",23457),("Abril.csv.zip",23460),("Mayo.csv.zip",20528),("Junio.csv.zip",20551),("Julio.csv.zip",20630),("Agosto.csv.zip",20673),("Septiembre.csv.zip",20676),("Octubre.csv.zip",20707),("Noviembre.csv.zip",20833),("Diciembre.csv.zip",20902)],
2022: [("GEIH_Enero_2022_Marco_2018.zip",22688),("GEIH_Febrero_2022_Marco_2018.zip",22689),("GEIH_Marzo_2022_Marco_2018.zip",22690),("GEIH_Abril_2022_Marco_2018_Act.zip",22894),("GEIH_Mayo_2022_Marco_2018.zip",22692),("GEIH_Junio_2022_Marco_2018.zip",22693),("GEIH_Julio_2022_Marco_2018.zip",22694),("GEIH_Agosto_2022_Marco_2018.zip",22695),("GEIH_Septiembre_Marco_2018.zip",22696),("GEIH_Octubre_Marco_2018.zip",22697),("GEIH_Noviembre_2022_Marco_2018.act.zip",23016),("GEIH_Diciembre_2022_Marco_2018.zip",22699)],
2023: [("Enero.zip",22349),("Febrero.zip",22466),("Marzo.zip",22553),("Abril.zip",22610),("Mayo.zip",22819),("Junio.zip",22888),("Julio.zip",22917),("Agosto.zip",22946),("Septiembre.zip",23017),("Octubre.zip",23081),("Noviembre.zip",23115),("Diciembre.zip",23243)],
2024: [("Ene_2024.zip",23313),("Febrero_2024.zip",23362),("Marzo 2024.zip",23596),("Abril 2024.zip",23496),("Mayo_2024 1.zip",23598),("Junio_2024.zip",23625),("Julio_2024.zip",23631),("Agosto_2024.zip",23651),("Septiembre_2024.zip",23671),("Octubre_2024.zip",23677),("Noviembre_ 2024.zip",23729),("Diciembre_2024.zip",23794)],
2025: [("Enero 2025.zip",24263),("Febrero 2025.zip",24264),("Marzo 2025.zip",24267),("Abril 2025.zip",24269),("Mayo 2025.zip",24268),("Junio 2025.zip",24266),("Julio 2025.zip",24265),("Agosto 2025.zip",24307),("Septiembre 2025.zip",24324),("Octubre 2025.zip",24382),("Noviembre 2025.zip",24406),("Diciembre 2025.zip",24463)],
2026: [("Enero 2026.zip",24530),("Febrero 2026.zip",24594),("Marzo 2026.zip",24674),("Abril 2026.zip",24703),("Mayo 2026.zip",24731),("Junio 2026.zip",24760)],
}

BASE = "https://microdatos.dane.gov.co/index.php/catalog/{cat}/download/{rid}"


def urls(anio: int):
    """[(mes, url), ...] en orden de enero a diciembre."""
    cat = CATALOGO_POR_ANIO[anio]
    return [(i + 1, BASE.format(cat=cat, rid=rid))
            for i, (_, rid) in enumerate(RECURSOS[anio])]


if __name__ == "__main__":
    import sys
    a = int(sys.argv[1])
    for mes, u in urls(a):
        print(f"{a}-{mes:02d}  {u}")
