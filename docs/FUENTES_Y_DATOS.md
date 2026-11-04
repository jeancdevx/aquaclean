# Actualización V2 de fuentes

El corpus activo `knowledge/*.md` contiene procedimientos sintéticos aprobados para el laboratorio al detalle. Se reingirieron 18 fragmentos con Gemini reales de 768 dimensiones el 2026-11-04 y se comprobó consulta vectorial; modelo/dimensión y filtros se conservan. El corpus V1 está en antecedentes/v1/knowledge. Las referencias públicas CPSC no autorizan tratamientos, compensaciones ni cierre y no son historia interna. Las cifras y fechas que siguen son el registro histórico V1, no resultados nuevos.

---

# Procedencia, fechas y separación de datos

Fecha de preparación: **16/10/2026, America/Lima**. La instrucción inicial pedía históricos reales de Aqua Clean; no se proporcionaron registros operativos autorizados. Después se autorizó utilizar datos que parecieran reales. Por ello se entrega un histórico **sintético y explícitamente etiquetado**, junto con referencias públicas auténticas. Ningún registro sintético se presenta como un cliente, empleado, pedido, guía o incidente real de la empresa.

## Inventario

| Conjunto | Procedencia | Persistencia | Tratamiento |
|---|---|---|---|
| Dos clientes base y agenda futura | Construidos para laboratorio | `app.customers`, `app.slots` | `synthetic=true`; direcciones ficticias y correos `example.invalid` |
| 150 clientes, 3.000 pedidos, 12.750 eventos históricos | Generador determinista `history_seed.py` | Tablas de negocio; `cases.data_origin=synthetic_history_v1` | Fechas coherentes; códigos `HIST-DEMO-*`; mensajes/eventos indican su carácter sintético |
| Cuatro documentos y 14 fragmentos de procedimientos | Corpus demo redactado y aprobado exclusivamente para pruebas | `app.documents`, `app.chunks` | No constituyen políticas confirmadas por Aqua Clean; embeddings Gemini reales |
| 151 avisos de retirada de productos/textiles | U.S. Consumer Product Safety Commission, API oficial | Esquema `reference` y snapshot versionado | Hechos publicados externos; no autorizan disposiciones comerciales o de calidad |
| Archivos de guía, imagen de inyección y voz | Fixtures sintéticos generados para evaluación | `tests/fixtures/`; subidas en volumen de medios | La voz se sintetizó con Gemini TTS; no representa una persona/solicitud real |
| Casos `QA` creados por pruebas | Ejecuciones del producto, con datos sintéticos | Negocio, chat, ledger y checkpoints | Sus trazas sí corresponden a herramientas/modelos ejecutados durante las pruebas |

Las cifras del inventario son las del seed. Las pruebas posteriores añaden casos/pedidos QA; `/api/data-summary` informa los conteos actuales sin confundirlos con operaciones reales.

## Fuente pública verificable

La [documentación oficial de la API CPSC](https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information) permite recuperar avisos públicos en JSON. El [catálogo gubernamental data.gov](https://catalog.data.gov/dataset/recalls-api) identifica al publicador, el acceso público y sus metadatos de licencia. No se utilizó una base comercial, información privada ni una respuesta de un LLM como fuente histórica.

Endpoint: `https://www.saferproducts.gov/RestWebServices/Recall`. Parámetros: `format=json` y `ProductName` para `washing`, `laundry`, `clothes dryer`, `garment steamer`, `clothing`, `sleepwear`, `pajamas`, `bathrobe`, `towel`, `blanket`. Se deduplicó por `RecallID`. Es una selección temática de 151 avisos, no el universo de incidentes de lavandería ni una muestra representativa de Perú.

Se conservan ID, número de aviso, fecha, título, URL oficial, productos, peligros y remedios. Se excluyen contactos, domicilios, fabricantes/importadores como entidades de clientes y reportes individuales de lesiones. No se crean pedidos a partir de avisos públicos.

- Primer aviso incluido: **1974-02-15**.
- Último aviso incluido: **2026-09-17**.
- Corte inclusivo: **2026-10-16**.
- Snapshot: [`reference_data/cpsc-recalls.json`](../reference_data/cpsc-recalls.json).
- SHA-256: `95ba45593d96f7f3952e78766102562f8e81440179fce094dc4be1e1517ed1f4`.
- Cada consulta conserva URL, cantidad devuelta y hash de la respuesta; cada registro conserva el hash de sus campos normalizados. `retrieved_at` distingue fecha de descarga de fecha del acontecimiento.

Las fechas CPSC son fechas de publicación del aviso, sin una hora conocida. Se almacenan como `date`; no se inventa una hora ni se desplazan a Lima. El año presente en la URL o el número fiscal del aviso puede diferir del año calendario de publicación.

## Tres escenarios para contrastar

| Número normalizado | Fecha publicada | Hecho verificable | Fuente primaria |
|---|---|---|---|
| `17028` / 17-028 | 2016-11-04 | Retirada de lavadoras Samsung de carga superior por riesgo de impacto al desprenderse la cubierta | [CPSC Samsung 2016](https://www.cpsc.gov/Recalls/2017/Samsung-Recalls-Top-Load-Washing-Machines) |
| `23080` / 23-080 | 2022-12-22 | Retirada de modelos Samsung por sobrecalentamiento/cortocircuito y riesgo de incendio | [CPSC Samsung 2022](https://www.cpsc.gov/Recalls/2023/Samsung-Recalls-Top-Load-Washing-Machines-Due-to-Fire-Hazard-Software-Repair-Available) |
| `24189` / 24-189 | 2024-04-05 | Aviso sobre bolsas defectuosas de cápsulas Tide/Gain/Ace/Ariel; riesgo de acceso al contenido por fallo del envase | [CPSC P&G 2024](https://www.cpsc.gov/Recalls/2024/Procter-Gamble-Recalls-8-2-Million-Defective-Bags-of-Tide-Gain-Ace-and-Ariel-Laundry-Detergent-Packets-Distributed-in-US-Due-to-Risk-of-Serious-Injury) |

Estos hechos sirven para probar atribución, búsqueda, cronología y distinción entre evidencia externa y reglas internas. No prueban que Aqua Clean haya utilizado esos productos o sufrido esos incidentes. No sustituyen procedimientos técnicos, instrucciones vigentes del fabricante ni decisiones del responsable de seguridad.

## Reproducción y actualización

```bash
sha256sum reference_data/cpsc-recalls.json
docker compose exec api python -m aquaclean.cli import-public-history
docker compose exec api python -m aquaclean.cli import-public-history
```

La segunda importación devuelve `inserted: 0`. El importador valida checksum general, hash de cada registro, fecha de corte y dominio oficial. No modifica pedidos ni introduce estos registros en el corpus aprobado.

Para obtener una nueva descarga explícita:

```bash
uv run python scripts/fetch_public_history.py
```

La API pública puede haber actualizado la información. Revisar el diff, el corte temporal y los hashes antes de aceptar un snapshot nuevo. Las filas históricas existentes no se sobrescriben silenciosamente: una corrección de fuente ya importada exige una revisión/migración que conserve procedencia. El snapshot incluido permite repetir la demostración sin depender de la disponibilidad de esa API.

## Coherencia del histórico sintético

El seed usa un namespace UUID fijo. Para cada pedido genera solicitud, recojo posterior, inspección y entrega; P3 incorpora conformidad y P4 observación, aceptación, cumplimiento y criterio de cierre, todos identificados como ficticios. Las fechas del primer seed abarcan 2024-10-16–2026-10-08. Repetir el seed utiliza su ancla original y no crea duplicados ni altera operaciones existentes. No atribuye ejecución pasada a Gemini ni a empleados reales.

Se pueden agregar registros operativos reales en una futura importación autorizada, con validación, minimización de datos, documentos originales y trazabilidad por lote. Esa importación no fue realizada ni se acredita en esta entrega.
