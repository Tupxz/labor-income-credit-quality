# Calidad de cartera, mercado laboral e ingreso real en Colombia
## Caso 3 — Economía Financiera y Bancaria (Universidad EAFIT)

Repositorio de trabajo para el Caso 3 del curso *Economía Financiera y Bancaria*: la relación
entre el mercado laboral (desempleo, informalidad, ingreso real) y la calidad de la cartera del
sistema financiero colombiano (mora, cartera vencida y provisiones) por tipo de crédito, con el
costo del crédito (tasa de política/IBR) como variable moderadora.

**Documento de planeación:** [`PLAN_DE_TRABAJO.md`](./PLAN_DE_TRABAJO.md) — pregunta de
investigación, hipótesis, fuentes de datos, metodología, cronograma (5 semanas) y roles del
equipo.

**Fuentes de datos:** [`docs/fuentes_de_datos.md`](./docs/fuentes_de_datos.md)

### Estructura del repositorio

```
.
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
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Equipo

_Completar con los 5 integrantes y su rol (ver tabla de roles en `PLAN_DE_TRABAJO.md`, sección 7)._

### Curso

Economía Financiera y Bancaria — Pregrado en Economía, Universidad EAFIT. Entregable según el
formato de "Casos" del curso: Contexto, Marco teórico-regulatorio, Datos, Metodología,
Resultados, Conclusiones/política (máx. 10 páginas en Word + modelo en Python; sustentación de
20 minutos).
