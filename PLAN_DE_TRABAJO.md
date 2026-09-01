# Pre-plan de trabajo — Caso 3: Desempleo, ingreso laboral y calidad de cartera

**Curso:** Economía Financiera y Bancaria — Pregrado en Economía, Universidad EAFIT
**Caso:** 3 de 6 ("Desempleo, ingreso laboral y calidad de cartera", ver `docs/Casos Economia Financiera.pdf`)
**Fecha de elaboración del pre-plan:** 21 de julio de 2026
**Horizonte de trabajo:** 5 semanas (21 jul – 24 ago 2026)
**Equipo:** 5 integrantes

---

## 0. Ficha del caso

El profesor propone conectar el mercado laboral colombiano (desempleo, informalidad, ingreso real)
con la calidad de la cartera del sistema financiero (mora por tipo de crédito, cartera vencida y
provisiones), incorporando el costo del crédito (tasa de política/IBR) como variable moderadora.
La idea técnica sugerida en el enunciado es un **modelo de ecuaciones simultáneas** entre tasa de
desempleo, crecimiento del ingreso, inflación y calidad de cartera (NPL ratio), con rezagos que
capturen el deterioro, y con la política monetaria modulando el impacto del desempleo en la mora.

El entregable final (según el brief del curso) debe tener **6 secciones** (Contexto, Marco
teórico-regulatorio, Datos, Metodología, Resultados, Conclusiones/política), **máximo 10 páginas
en Word**, modelo econométrico **preferiblemente en Python**, y una **sustentación de 20 minutos**
con énfasis en gráficos/tablas y poco texto.

Este documento es el **pre-plan**: no es el entregable final, sino la hoja de ruta que el equipo
usará durante las 5 semanas para llegar a ese entregable de forma ordenada.

---

## 1. Pregunta de investigación e hipótesis

**Pregunta central:**
¿Cómo se transmite el deterioro (o mejora) del mercado laboral colombiano —desempleo,
informalidad e ingreso laboral real— a la calidad de la cartera del sistema financiero por tipo
de crédito (consumo, vivienda, microcrédito, comercial), y en qué medida el costo del crédito
(tasa de política/IBR) modera esa relación?

**Hipótesis de trabajo:**

- **H1 (transmisión laboral → mora):** un aumento del desempleo y la informalidad, y una caída
  del ingreso laboral real, elevan con rezago el indicador de mora (NPL) por tipo de cartera,
  con un efecto más rápido y de mayor magnitud en **consumo** (menor colateral, mayor
  sensibilidad al flujo de caja del hogar) que en **vivienda** o **microcrédito**.
- **H2 (rol moderador de la tasa de interés):** en entornos de tasa de política alta —como el
  actual, cercano a 12% a mediados de 2026 según el brief del curso, a validar con la cifra
  vigente al momento del análisis—, el mismo choque de desempleo produce un deterioro de cartera
  mayor que en entornos de tasas bajas, porque coincide con cuotas de crédito más costosas.
- **H3 (simultaneidad / retroalimentación):** la relación no es unidireccional: el deterioro de
  cartera induce a los bancos a endurecer condiciones de crédito (tasas, plazos, score), lo que
  retroalimenta el ciclo de ingreso/desempleo vía menor acceso al crédito. Esto justifica un
  enfoque de ecuaciones simultáneas o VAR en lugar de una regresión uniecuacional simple.

---

## 2. Contexto (insumo para la Sección 1 del entregable)

Cifras de referencia mencionadas en el brief del curso (`docs/Casos Economia Financiera.pdf`),
**a validar y actualizar con la última publicación disponible** al momento de escribir el
entregable:

- Tasa de política del BanRep cercana a **12%** a mediados de 2026 (ventana de tasas altas).
- Cartera total creciendo alrededor de **3,5% real anual**, con moderación en desembolsos y
  endurecimiento de condiciones de crédito.
- Mora del sistema en torno a **4,4%**, con tendencia a mejorar.
- Solvencia total del sistema alrededor de **17%**.

Contraste de coyuntura (prensa especializada, julio 2026): nota de *El Tiempo*, "Sistema
financiero modera ganancias en el arranque de 2026, aunque mejora el crédito y baja la
morosidad" — dirección consistente con lo señalado en el brief. Usar como contraste de
coyuntura, **no como fuente primaria** para el modelo.

Tareas del equipo en esta sección: actualizar estas cifras con la fuente oficial (BanRep/SFC) a
la fecha de corte del trabajo, y añadir el panorama de mercado laboral (desempleo, informalidad,
ingreso real) del DANE para el mismo periodo.

---

## 3. Marco teórico y regulatorio a revisar (insumo Sección 2)

**Teoría económica:**
- Ciclo crediticio y "acelerador financiero" (Bernanke, Gertler & Gilchrist) — por qué el ingreso
  y el empleo de los hogares afectan la capacidad de pago y, con ella, la mora.
- Literatura sobre determinantes macro de la cartera vencida en Colombia (papers/notas del
  BanRep sobre estabilidad financiera y determinantes de la mora por tipo de cartera).
- Mishkin (bibliografía base del curso): riesgo de crédito, selección adversa y racionamiento de
  crédito ante deterioro del ingreso.

**Marco regulatorio (Colombia):**
- Circular Básica Contable y Financiera de la SFC (Capítulo II — Reglas de calificación de
  cartera de créditos, categorías A–E, y constitución de provisiones), que define cómo se mide
  y reporta la "calidad de cartera" que se va a modelar.
- Definiciones de cartera vencida vs. cartera en mora, y provisiones individuales/generales.
- Mención breve al contexto de Basilea III (convergencia regulatoria colombiana) como telón de
  fondo, dado que la calidad de cartera alimenta los activos ponderados por riesgo y la
  solvencia (conexión con el Caso 6 del curso, útil para la sección de conclusiones/política).
- Metodología GEIH del DANE: definiciones de desempleo abierto, informalidad y cómo se calcula
  el ingreso laboral real (deflactado por IPC).

**Entregable de esta etapa:** medio párrafo por cada bloque (teoría, regulación SFC, GEIH) para
la Sección 2 del documento final — recordar que el límite total es 10 páginas, así que esta
sección no debe superar ~1.5 páginas.

---

## 4. Datos: fuentes, series y construcción del panel (insumo Sección 3)

Detalle completo de fuentes, series exactas y enlaces en
[`docs/fuentes_de_datos.md`](./docs/fuentes_de_datos.md). Resumen:

| Bloque | Fuente | Series clave | Periodicidad sugerida |
|---|---|---|---|
| Calidad de cartera | Superintendencia Financiera de Colombia (SFC) | Cartera vencida, cartera bruta y provisiones por modalidad (consumo, vivienda, microcrédito, comercial); indicador de mora (ICV) | Mensual (agregar a trimestral si hace falta) |
| Costo del crédito y agregados | Banco de la República (BanRep) | Tasa de política, IBR, tasas de captación/colocación, agregados monetarios y crediticios, TES | Mensual |
| Actividad real | BanRep / DANE | PIB, IPC (inflación) | Trimestral / mensual |
| Mercado laboral | DANE (GEIH) | Tasa de desempleo, tasa de informalidad, ingreso laboral (para deflactar a real con IPC) | Mensual (trimestre móvil) |

**Unidad de análisis propuesta:** panel trimestral **segmento de cartera × tiempo** (4 segmentos:
consumo, vivienda, microcrédito, comercial), lo que da un N pequeño pero permite explotar
heterogeneidad entre segmentos sin depender de una serie de tiempo agregada demasiado corta.

**Pasos de construcción (semana 2):**
1. Descargar series crudas → guardar sin modificar en `data/raw/`.
2. Homologar periodicidad (mensual → trimestral cuando aplique) y unidades (deflactar ingreso
   con IPC, expresar tasas en % efectivo anual consistente).
3. Consolidar panel limpio en `data/processed/panel_calidad_cartera.csv`.
4. Estadística descriptiva y gráficos exploratorios (tendencias de NPL por segmento vs.
   desempleo/ingreso real) antes de especificar el modelo.

---

## 5. Metodología econométrica propuesta (insumo Sección 4)

**Especificación base (panel dinámico):**

NPL_ratio(s,t) = f( desempleo(t-k), informalidad(t-k), Δingreso_real(t-k), inflación(t),
tasa_política/IBR(t), controles(crecimiento de cartera, PIB) ) + efectos fijos por segmento *s*

- Efectos fijos por segmento de cartera + rezagos distribuidos (ARDL/panel dinámico); considerar
  Arellano-Bond únicamente si el panel resultante lo justifica (N×T suficiente).
- La tasa de política/IBR entra como **moderador**: además del término lineal, incluir una
  interacción `desempleo × tasa_política` para probar H2.

**Robustez (elegir según tiempo disponible):**
- VAR/VECM agregado (sin desagregar por segmento) entre desempleo, ingreso real, NPL agregado y
  tasa de política, para obtener funciones impulso-respuesta y evaluar H3 (retroalimentación).
- *Stretch goal* si el equipo tiene margen: 2SLS con instrumento para desempleo (p. ej. choques
  sectoriales/regionales) para atender la simultaneidad de forma más rigurosa.

**Software:** Python — `pandas`/`numpy` para el panel, `statsmodels` y `linearmodels` (panel
efectos fijos, IV) para la estimación, `statsmodels.tsa.api.VAR` para la robustez de series de
tiempo. Ver stubs en `src/`.

**Supuestos a revisar antes de estimar:** estacionariedad de las series (ADF/KPSS), posibles
quiebres estructurales (pandemia 2020, choque inflacionario 2022-2023, ciclo de tasas altas
2023-2026) — incluir *dummies* de régimen si es necesario.

---

## 6. Mapeo al entregable final y a la sustentación

| # | Sección del Word | Contenido esperado | Página(s) aprox. (de 10) |
|---|---|---|---|
| 1 | Contexto | Coyuntura laboral y de cartera 2020-2026, cifras clave actualizadas | ~1 |
| 2 | Marco teórico-regulatorio | Teoría del ciclo crediticio, normativa SFC de calificación de cartera, metodología GEIH | ~1.5 |
| 3 | Datos | Fuentes, periodo, transformaciones, estadística descriptiva | ~1.5 |
| 4 | Metodología | Especificación del modelo, ecuaciones, supuestos | ~2 |
| 5 | Resultados | Tablas de coeficientes, gráficos/IRF, interpretación económica | ~2.5 |
| 6 | Conclusiones/política | Implicaciones para gestión de riesgo/provisiones, política monetaria e inclusión financiera | ~1.5 |

**Sustentación (20 min):** priorizar 8-10 slides con gráficos (series de NPL por segmento,
desempleo vs. mora, resultados del modelo) y muy poco texto, según lo pide el brief.

---

## 7. Cronograma (5 semanas) y roles

Roles sugeridos (ajustar con nombres reales del equipo). Todos participan en la interpretación y
redacción final de las semanas 4-5.

| Rol | Integrante | Responsabilidad principal |
|---|---|---|
| Coordinación + Marco teórico-regulatorio | Integrante 1 | Agenda, integra secciones, valida consistencia con normativa SFC |
| Datos BanRep | Integrante 2 | Tasa de política, IBR, TES, agregados monetarios y crediticios, PIB, inflación |
| Datos SFC + DANE | Integrante 3 | Calidad de cartera por segmento (mora, provisiones), GEIH (desempleo, informalidad, ingreso) |
| Modelación econométrica (Python) | Integrante 4 | Especifica, estima y valida el modelo (panel/VAR), corre robustez |
| Visualización y redacción/presentación | Integrante 5 | Gráficos, tablas, arma el Word final y las slides |

| Semana | Fechas | Hitos |
|---|---|---|
| 1 | 21–27 jul | Marco teórico-regulatorio, hipótesis final, plan de datos, primeras descargas |
| 2 | 28 jul–3 ago | Limpieza y consolidación del panel, estadística descriptiva y gráficos exploratorios |
| 3 | 4–10 ago | Especificación y primera estimación del modelo base; chequeo de supuestos |
| 4 | 11–17 ago | Robustez (VAR/IV), interpretación económica, borrador de las 6 secciones |
| 5 | 18–24 ago | Pulido del documento (≤10 páginas), presentación (20 min), ensayo y entrega |

---

## 8. Riesgos y supuestos a validar

- **Granularidad de la SFC:** la calidad de cartera por segmento puede no estar disponible con
  periodicidad mensual en formato fácil de descargar — validar en semana 1 si toca trabajar en
  trimestral.
- **Series cortas:** si se restringe a datos pos-2015, el T disponible puede ser insuficiente
  para un VAR robusto — mitigado por el panel de segmentos en la especificación base.
- **Endogeneidad:** mora y condiciones de crédito se determinan simultáneamente — de ahí el uso
  de rezagos y, si el tiempo lo permite, variables instrumentales.
- **Quiebres estructurales:** pandemia (2020), choque inflacionario (2022-2023) y ciclo de tasas
  altas (2023-2026) — usar dummies de régimen si las pruebas de estabilidad lo sugieren.
- **Restricción de 10 páginas:** priorizar resultados y conclusiones sobre extensión del marco
  teórico; mover detalle técnico adicional a un anexo/notebook si es necesario.

---

## 9. Checklist de entrega

- [ ] Documento Word ≤10 páginas con las 6 secciones completas
- [ ] Script/notebook Python reproducible con el modelo final (`src/`, `notebooks/`)
- [ ] Presentación de 20 minutos, poco texto, con gráficos y tablas
- [ ] Fuentes de datos y fecha de corte documentadas en `docs/fuentes_de_datos.md`
- [ ] Repositorio de GitHub actualizado con commits incrementales por semana
