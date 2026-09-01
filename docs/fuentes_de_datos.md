# Fuentes de datos — Caso 3

Ventana objetivo: **mensual, enero 2015 – diciembre 2025**. Actualizar la columna
"Fecha de descarga" cada vez que se corra `src/descargar_datos.py` o se descargue
algo manualmente, para dejar trazable qué tan reciente es cada dato citado en el
documento final.

## Estado actual (actualizado 21-jul-2026, tras la primera corrida real)

- **SFC — calidad de cartera**: descargado y funcionando (2 archivos Excel).
- **BanRep — SDMX**: descargado y funcionando. Los `.xml` que llegan a
  `data/raw/banrep_sdmx/` **no son tablas legibles directamente** (son
  SDMX-XML con las observaciones adentro) — hay que correr
  `python src/procesar_banrep_sdmx.py` después de descargarlos, que los
  convierte en `data/processed/banrep_mensual.csv` (panel mensual limpio,
  132 filas, ene-2015 a dic-2025, columnas tpm/dtf/ibr/trm/M1/M2/M3). Ya se
  probó de punta a punta con los archivos reales y funciona.
- **DANE — GEIH**: **ventana completa 2015-2025 cubierta**. El script prueba
  4 patrones de nombre/carpeta/extensión por mes (DANE reorganizó su sitio
  varias veces, y usó `.xls` en vez de `.xlsx` hasta abril-2017). Verificado
  puntualmente en todos los tramos, incluyendo los bordes (ene-2015,
  abr-2017/may-2017, dic-2022/ene-2023, mar-2023/abr-2023/may-2023).

## Nota técnica sobre el entorno

Esta investigación de fuentes (URLs, FLOW_ID, patrones de nombre) se hizo
desde una sesión de Cowork en la nube cuyo sandbox no tiene acceso de red
abierto a superfinanciera.gov.co/dane.gov.co/banrep.gov.co — por eso no se
pudo descargar ni depurar todo directamente ahí. La descarga real (la que
importa) se corre y se valida desde un computador con internet normal, como
ya hizo el equipo con éxito para SFC y BanRep.

## 1. Superintendencia Financiera de Colombia (SFC) — calidad de cartera

**Verificado, automatizado y ya descargado:**

- Calidad de cartera por modalidad, **sin castigos** (cartera vencida, cartera
  bruta y provisiones por modalidad — consumo, vivienda, microcrédito, comercial):
  https://www.superfinanciera.gov.co/loader.php?lServicio=Tools2&lTipo=descargas&lFuncion=descargar&idFile=1070109
- Calidad de cartera por modalidad, **incluyendo castigos**:
  https://www.superfinanciera.gov.co/loader.php?lServicio=Tools2&lTipo=descargas&lFuncion=descargar&idFile=1070110
- Metodología: idFile=1005086 (estándar) e idFile=1005088 (incluyendo castigos),
  mismo patrón de URL que arriba.
- Dashboard interactivo (PowerBI) equivalente: https://www.superfinanciera.gov.co/powerbi/reportes/510

**Pendiente de gestión manual** (no se encontró un único archivo que cubra todo
2015-2025 en un solo clic):

- Cartera bruta total del sistema y por tipo de entidad: serie mensual
  "Sistema financiero colombiano en cifras" — buscar la edición de cada mes en
  https://www.superfinanciera.gov.co/ (ej. marzo 2026:
  https://www.superfinanciera.gov.co/publicaciones/10116133/sistema-financiero-colombiano-en-cifras-marzo-de-2026/).
  Si el equipo tiene acceso al Formato 341 agregado, ese es el detalle más granular.

## 2. Banco de la República (BanRep) — API SDMX (verificada, descargada y procesada)

BanRep expone una API REST estándar SDMX 2.1. Base:
`https://totoro.banrep.gov.co/nsi-jax-ws/rest/data`

Formato de consulta: `.../data/ESTAT,<FLOW_ID>,1.0/all/ALL/?startPeriod=2015&endPeriod=2026&dimensionAtObservation=TIME_PERIOD&detail=full`

Documentación técnica oficial: https://suameca.banrep.gov.co/archivos/webservices/documento_tecnico_ws_consumo_sdmx.pdf

FLOW_ID confirmados y usados en `descargar_datos.py`:

| Serie | FLOW_ID histórico | Periodicidad |
|---|---|---|
| Tasa de política monetaria (TPM) | `DF_CBR_MONTHLY_HIST` | Mensual (promedio) |
| IBR | `DF_IBR_DAILY_HIST` | Diaria (promediar a mensual) |
| DTF | `DF_DTF_MONTHLY_HIST` | Mensual |
| Agregados monetarios (M1, M2, M3) | `DF_MONAGG_MONTHLY_HIST` | Mensual |
| TRM (tasa de cambio) | `DF_TRM_DAILY_HIST` | Diaria (opcional, control macro) |

Otros FLOW_ID disponibles en el mismo servicio (no usados por ahora, por si el
equipo los necesita): `DF_IR_DAILY_HIST` (tasa interbancaria TIB),
`DF_COLCAP_MONTHLY_HIST` (índice bursátil COLCAP), `DF_UVR_DAILY_HIST` (UVR),
`DF_DTF_TRIM_ANTICIPADO_HIST`.

**IMPORTANTE — formato de los archivos:** la respuesta es SDMX-ML "Generic
Data" (XML real, con las observaciones adentro), no una tabla plana. Al abrir
el `.xml` directamente parece "no tener datos" porque son tags XML, no
columnas. El script `src/procesar_banrep_sdmx.py` lo parsea y arma
`data/processed/banrep_mensual.csv`. Ya se verificó con los archivos reales
descargados por el equipo: 132 filas (ene-2015 a dic-2025), TPM arrancando en
4.5% en ene-2015 y llegando a 11.25% en jun-2026 — consistente con la
trayectoria de tasas conocida.

**Pendiente de verificar:** la escala de M1/M2/M3 (columnas `m1_mm_cop`,
`m2_mm_cop`, `m3_mm_cop`) — el atributo `UNIT_MULT` del XML no deja 100%
claro el orden de magnitud. Antes de usarlos en el modelo, comparar un dato
puntual (p. ej. M2 de un mes reciente) contra una cifra oficial conocida de
BanRep para confirmar la unidad.

**Esta API SDMX no cubre IPC, PIB/ISE ni cartera de crédito** — esas siguen la
ruta de DANE/SFC descrita en esta misma página.

**Portal interactivo (si se prefiere navegar en vez de la API):**
https://suameca.banrep.gov.co/estadisticas-economicas/ — es una aplicación de
una sola página (SPA), así que no se puede *scrapear* directamente; hay que
usar el "buscador de series" o la "descarga múltiple de datos" desde un
navegador normal.

## 3. DANE — mercado laboral (GEIH e informalidad)

**Verificado y automatizado, con un patrón por tramo de fechas** (DANE
reorganizó la carpeta/nombre/extensión de sus anexos varias veces en la
ventana 2015-2025; `_candidatos_geih()` en `descargar_datos.py` prueba los 4
patrones conocidos, en este orden, hasta que uno responda):

| Tramo | Patrón | Estado |
|---|---|---|
| may-2023 en adelante | `operaciones/GEIH/anex-GEIH-{mes}{aaaa}.xlsx` | Confirmado, descargado |
| abr-2023 (excepción) | `operaciones/GEIH/EMPLEO_DESEMPLEO/anex-GEIH-{mes}{aaaa}.xlsx` | Confirmado |
| may-2017 a mar-2023 | `investigaciones/boletines/ech/ech/anexo_empleo_{mes}_{aa}.xlsx` | Confirmado (2022-2025 descargado; 2017-2021 verificado por muestreo) |
| ene-2015 a abr-2017 | `investigaciones/boletines/ech/ech/anexo_empleo_{mes}_{aa}.xls` (formato Excel viejo) | Confirmado por muestreo (ene-2015, jun-2015, oct-2016, dic-2016, abr-2017) |

Con esto la ventana completa 2015-01 a 2025-12 debería quedar cubierta. El
archivo local se guarda con la extensión real de la fuente (`.xls` o
`.xlsx`) — por eso se agregó `xlrd` a `requirements.txt` (pandas/openpyxl no
leen `.xls` viejo sin esa librería). Si algún mes puntual sigue fallando,
revisar a mano en:
https://www.dane.gov.co/index.php/estadisticas-por-tema/mercado-laboral/empleo-y-desempleo/geih-historicos

- Serie desestacionalizada: mismo patrón con
  `anex-GEIH-Desestacionalizado-{mes}{aaaa}.xlsx` (no descargada aún, agregar
  al script si se necesita).
- Informalidad (anexos GEIHEISS, agregados por trimestre móvil):
  patrón `anex-GEIHEISS-{mes-inicio}-{mes-fin}{aaaa}.xlsx`, ver
  https://www.dane.gov.co/index.php/estadisticas-por-tema/salud/informalidad-y-seguridad-social/empleo-informal-y-seguridad-social-historicos
  (no incluida todavía en `descargar_datos.py` — pendiente).

**Pendiente de gestión manual:**

- IPC (inflación): no se encontró un único archivo consolidado 2015-2025;
  usar el visor interactivo https://sitios.dane.gov.co/ipc/visorIPC/#!/ o
  consolidar los boletines mensuales desde
  https://www.dane.gov.co/index.php/estadisticas-por-tema/precios-y-costos/indice-de-precios-al-consumidor-ipc/ipc-historico
  (hay un archivo de "Reconstrucción histórica 2009-2018" mencionado en esa
  página, útil para empalmar cambios de metodología/base).
- ISE (proxy mensual del PIB, ya que el PIB oficial es trimestral): boletines
  mensuales en
  https://www.dane.gov.co/index.php/estadisticas-por-tema/cuentas-nacionales/indicador-de-seguimiento-a-la-economia-ise/historicos-ise-comunicados-y-boletines
  — tampoco hay un archivo único; toca consolidar los anexos mes a mes.

## 4. Prensa especializada (contexto, no fuente primaria)

- "Sistema financiero modera ganancias en el arranque de 2026, aunque mejora
  el crédito y baja la morosidad", El Tiempo (jul. 2026):
  https://www.eltiempo.com/economia/sector-financiero/sistema-financiero-modera-ganancias-en-el-arranque-de-2026-aunque-mejora-el-credito-y-baja-la-morosidad-3557770

## Registro de descargas

| Serie | Fuente | Fecha de corte de la serie | Fecha de descarga | Responsable | Notas |
|---|---|---|---|---|---|
| Calidad de cartera (sin/con castigos) | SFC | Ver contenido del archivo | 21-jul-2026 | — | OK, 687 KB c/u |
| TPM, DTF, IBR, TRM, M1/M2/M3 mensual | BanRep SDMX | 2015-01 a 2026-06 | 21-jul-2026 | — | Requiere `procesar_banrep_sdmx.py`; verificar unidad M1/M2/M3 |
| Anexos GEIH mensuales | DANE | may-2023 a dic-2025 | 21-jul-2026 | — | Faltan ene-2015 a abr-2023 (parcial, ver sección 3) |
| | | | | | |

## Semana 2 — Limpieza y consolidación (avance 1-sep-2026)

Se implementaron 3 scripts nuevos de procesamiento en `src/`, cada uno leyendo
de `data/raw/` y escribiendo un CSV limpio en `data/processed/`:

- **`src/procesar_sfc_calidad_cartera.py`** → `data/processed/sfc_icv_mensual.csv`.
  Los 2 archivos Excel de la SFC no son tablas planas: cada hoja "ICV Sistema"
  apila 5 bloques (Total, Comercial, Consumo, Vivienda, Microcrédito), cada uno
  con el ICV por tipo de entidad y una fila de agregado
  **"Establecimientos de Crédito"** que es la que se usa como ICV del sistema
  por segmento. Panel largo: `fecha, segmento, icv_sin_castigos, icv_con_castigos`.
  **Ventana real: 2011-01 a 2023-12** — el archivo descargado NO llega a
  2024-2025; sigue pendiente la gestión manual mencionada en la sección 1 de
  este documento para extender la serie.
- **`src/procesar_geih.py`** → `data/processed/dane_mercado_laboral_mensual.csv`.
  Cada anexo mensual de la GEIH trae en la hoja "Total nacional" la serie
  histórica completa (2001 hasta el mes de corte del archivo), así que basta
  con el anexo más reciente (`anex-GEIH-dic2025.xlsx`) para tener TGP, TO y TD
  (desempleo) nacional 2001-2025, sin parsear los ~130 archivos mensuales uno
  por uno. **Faltan 5 meses** de TD/TGP/TO por vacío de la encuesta durante el
  primer choque de la pandemia (2020-03 a 2020-07). **Aún no incluye
  informalidad ni ingreso laboral real** (pendiente, ver sección 3 más abajo:
  anexos GEIHEISS e ingresos).
- **`src/consolidar_panel.py`** → `data/processed/panel_calidad_cartera.csv`.
  Panel final `segmento × mes` (5 segmentos × 108 meses = 540 filas), ventana
  **2015-01 a 2023-12** (acotada por el archivo de la SFC, el más corto de
  las 3 fuentes). Columnas: ICV (SFC), tasas/agregados (BanRep), TGP/TO/TD
  (GEIH). BanRep y GEIH ya cubren hasta 2025-12, así que en cuanto se
  consiga la actualización 2024-2025 de la SFC, `consolidar_panel.py` no
  necesita cambios — solo ajustar `FECHA_FIN`.

**Pendiente antes de pasar a la Semana 3 (especificación del modelo):**
1. Conseguir SFC 2024-2025 (o aceptar la ventana 2015-2023 y documentarlo
   como limitación del alcance).
2. Conseguir informalidad (GEIHEISS) e ingreso laboral real + IPC para
   deflactar, o decidir excluir esas hipótesis del modelo final por falta de
   datos.
3. Estadística descriptiva y gráficos exploratorios del panel consolidado
   (NPL por segmento vs. desempleo/TPM) — insumo de la Sección 3 del
   entregable.
