# Calidad de cartera, mercado laboral e ingreso real en Colombia

## Caso 3 — Economía Financiera y Bancaria (Universidad EAFIT)

<p align="left">
  <a href="https://tupxz.github.io/labor-income-credit-quality/">
    <img alt="Ver página de avance del equipo" src="https://img.shields.io/badge/%F0%9F%93%88_Ver_avance_del_equipo-1d3557?style=for-the-badge&logoColor=white">
  </a>
</p>

Repositorio de trabajo para el Caso 3 del curso *Economía Financiera y Bancaria*: la relación
entre el mercado laboral (desempleo, informalidad, ingreso real) y la calidad de la cartera del
sistema financiero colombiano (mora, cartera vencida y provisiones) por tipo de crédito, con el
costo del crédito (tasa de política/IBR) como variable moderadora.

**Página de avance del equipo (estado actual, pendientes y guía de trabajo en Git):**
👉 **https://tupxz.github.io/labor-income-credit-quality/**

**Documento de planeación:** [`PLAN_DE_TRABAJO.md`](./PLAN_DE_TRABAJO.md) — pregunta de
investigación, hipótesis, fuentes de datos, metodología, cronograma (5 semanas) y roles del
equipo.

**Fuentes de datos:** [`docs/fuentes_de_datos.md`](./docs/fuentes_de_datos.md)

### Estado actual (1-sep-2026)

| Bloque | Estado |
|---|---|
| Descarga de datos crudos (SFC, BanRep, DANE-GEIH) | ✅ Completo |
| Procesamiento BanRep (`src/procesar_banrep_sdmx.py`) | ✅ 2015-2025 |
| Procesamiento SFC (`src/procesar_sfc_calidad_cartera.py`) | ⚠️ 2011-2023 (falta 2024-2025) |
| Procesamiento GEIH (`src/procesar_geih.py`) | ⚠️ TD/TGP/TO 2001-2025 (falta informalidad e ingreso real) |
| Panel consolidado (`src/consolidar_panel.py`) | ✅ 2015-2023, 540 filas |
| Estadística descriptiva y gráficos exploratorios | 🔲 Pendiente |
| Especificación y estimación del modelo | 🔲 Pendiente (Semana 3) |
| Documento final y sustentación | 🔲 Pendiente (Semana 5) |

Detalle completo, reparto de tareas y guía paso a paso para trabajar en equipo con Git en la
[página de avance](https://tupxz.github.io/labor-income-credit-quality/).

### Estructura del repositorio

```
.
├── index.html              # Página de avance del equipo (GitHub Pages)
├── PLAN_DE_TRABAJO.md      # Pre-plan detallado del caso
├── docs/                   # Enunciados del curso + notas teóricas/regulatorias
│   └── fuentes_de_datos.md
├── data/
│   ├── raw/                # Datos descargados sin modificar (no versionar archivos pesados)
│   └── processed/          # Panel limpio y listo para el modelo
├── notebooks/              # Exploración y prototipado (Jupyter)
├── src/                    # Código reutilizable (ingesta, modelo, gráficos)
├── output/
│   ├── figuras/
│   ├── tablas/
│   └── entregable/         # Word final (máx. 10 páginas) y slides de la sustentación
├── requirements.txt
└── .gitignore
```

### Cómo empezar

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Pipeline de datos (orden de ejecución)

```bash
python src/procesar_banrep_sdmx.py
python src/procesar_sfc_calidad_cartera.py
python src/procesar_geih.py
python src/consolidar_panel.py
```

Cada script lee de `data/raw/` (sin modificarlo) y escribe su salida limpia en
`data/processed/`. Ver la [página de avance](https://tupxz.github.io/labor-income-credit-quality/)
para la guía completa de cómo trabajar en equipo con Git (ramas, commits, Pull Requests).

### Equipo

_Completar con los 5 integrantes y su rol (ver tabla de roles en `PLAN_DE_TRABAJO.md`, sección 7)._

### Curso

Economía Financiera y Bancaria — Pregrado en Economía, Universidad EAFIT. Entregable según el
formato de "Casos" del curso: Contexto, Marco teórico-regulatorio, Datos, Metodología,
Resultados, Conclusiones/política (máx. 10 páginas en Word + modelo en Python; sustentación de
20 minutos).

