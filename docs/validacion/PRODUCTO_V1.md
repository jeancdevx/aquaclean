# Resultados de la aplicación V1

**Cierre de validación: 16/10/2026, America/Lima.** Aplicación ejecutándose en http://localhost:8000. Estas comprobaciones corresponden al código de `src/aquaclean` y `web/`, no solo a los diagramas del diseño original. Los resultados de validación documental anteriores se conservan en `RESULTADOS.md`.

## Corrección posterior al reporte del usuario

Se reprodujo y corrigió el error al enviar la sugerencia «Programar un recojo» con CLI-0001. Esa entrada ahora inicia Atención, solicita los campos faltantes y permite confirmar en la misma conversación. La prueba original solo pulsaba la sugerencia; se amplió para enviarla y completar el flujo. La protección también funciona si el clasificador propone P2 por error, sin conceder permisos. [Causa, reproducción y evidencias](CORRECCION_RECOJO.md). Las cifras y XML de este informe corresponden a la verificación posterior a esa corrección; el recorrido P1–P4 con reinicio de la sección siguiente conserva la evidencia de la entrega inicial.

## Resultado y entorno

La V1 local ejecuta supervisor y cuatro especialistas con Gemini real, herramientas LangChain, subgrafos LangGraph, revisión humana persistente y comandos deterministas. Docker Compose sirve Astro/React desde FastAPI y mantiene API, worker y PostgreSQL saludables; `migrate` terminó con código 0. Solo se publica `127.0.0.1:8000`; PostgreSQL permanece en la red interna.

| Elemento | Configuración comprobada |
|---|---|
| Imagen API/worker | `aquaclean-local:0.1.0`, imagen ejecutada `sha256:584a6a9d31d459f37844dad95d2dc63ca63b64a7912e241d4eb5dc63e477ccd2` |
| Python / dependencias | Python 3.12.15; `pyproject.toml` y `uv.lock` |
| Frontend | Astro 7.4.0, React 19.3.1, TypeScript 6.0.3, Tailwind 4.3.3, componentes shadcn/ui |
| Gestión frontend | pnpm 10.33.2 y `web/pnpm-lock.yaml`; build Docker con pnpm |
| IA | `gemini-3.5-flash-lite`, comprobado en el catálogo de la cuenta y mediante llamadas reales |
| Embeddings | `gemini-embedding-001`, dimensión 768, normalización L2 |
| Persistencia | PostgreSQL 17, pgvector 0.8.2, migraciones hasta versión 4; checkpoints en otro esquema |
| Identidad | `demo_operator`, organización `org_demo_aquaclean`, fijados en backend |
| Prompts | `aquaclean-boundaries-1.1`; contratos Pydantic por especialista |

El catálogo de la cuenta también ofrecía `gemini-3.8-flash`. Una primera clasificación fue correcta, pero otras llamadas produjeron 429/504 y latencias; por eso se seleccionó y comprobó 3.5 Flash Lite. `provider-first-live.json` conserva únicamente aquel primer sondeo, no acredita el modelo final ni todas las modalidades. El catálogo final y las evaluaciones se entregan junto a este informe. No hay fallback simulado en el runtime.

## Pruebas ejecutadas

| Batería | Resultado | Alcance y evidencia |
|---|---|---|
| `pytest`, con `TEST_DATABASE_URL` de `aquaclean_test` | **62 pasadas**, 10 omitidas deliberadamente | Dominio, integración PostgreSQL real y grafos con proveedores controlados. Las 10 omitidas son las evaluaciones externas opt-in. [`tests-deterministic.xml`](tests-deterministic.xml) |
| `RUN_REAL_PROVIDER=1 uv run pytest tests/evaluations` | **10 pasadas**, sin omisiones | Catálogo/contrato, streaming nativo, PNG/JPG/WebP/PDF/MP3/WAV, embeddings y prompt adversario. [`tests-gemini-live.xml`](tests-gemini-live.xml) |
| `RUN_REAL_PROVIDER=1 pnpm --dir web test:ui` | **8 pasadas**, sin omisiones | Chromium a 360/768/1440 px, teclado/temas, sugerencias sin ejecución, carga real/error, fuentes/recursos, contraste, fixture explícito sin clave y envío de la sugerencia inicial con Gemini, aclaración, datos completos, aprobación/recarga. [`tests-browser.xml`](tests-browser.xml) |
| `uv run python scripts/run_demo.py --restart` | **P1–P4 completo, pasado** | HTTP real, percepción de guía, Gemini, DB, HITL, reinicio, reserva, liberación humana y cierre posterior al cumplimiento. [`full-demo-real.json`](full-demo-real.json) |
| Ruff check y format | Pasados | Código, pruebas y scripts; 63 archivos con formato correcto |
| mypy | Pasado | 6 archivos de dominio, configuración y contratos tipados; no se afirma tipado estricto de toda la aplicación |
| `pnpm --dir web check` / `build` | Pasados | 28 archivos comprobados, cero errores/advertencias; build Astro estático correcto |
| Compose / CLI | Pasados | Build, migración, healthchecks, seed, importación, ingesta, consulta vectorial y smoke real |

Son **80 pruebas automatizadas pasadas**, además del recorrido completo y las verificaciones de CLI. Los proveedores controlados de `_test` no acreditan razonamiento de Gemini: la segunda batería y la demo completa comprueban por separado el proveedor real. La prueba visual sin clave usa una respuesta de sesión interceptada explícitamente; la indisponibilidad real del adaptador se prueba en integración.

Para replicar: seguir la [guía de 25 pruebas](../GUIA_PRUEBAS_DETALLADA.md), también disponible en [PDF de 16 páginas](../GUIA_PRUEBAS_DETALLADA.pdf). La guía explica cómo crear una base `_test` separada; no se ejecutan tests destructivos sobre la base demo. Las llamadas Gemini pueden generar consumo. Sus respuestas literales y latencias pueden variar; los resultados persistidos y las invariantes son el criterio de aceptación.

## Evidencia del recorrido completo final

Pedido sintético **`DEMO-28CA13D45D`**. El script registró fuentes realmente recuperadas para cada etapa.

| Etapa | Caso | Estado comprobado |
|---|---|---|
| P1 | `1693f4e0-ebb6-4d42-9f76-0ce3d26c6952` | `registered`, después de confirmar los siete campos; 3 bolsas extraídas de la imagen |
| P2 | Mismo caso | `scheduled`, después de seleccionar una opción calculada y reservar atómicamente |
| P3 | `a13957e9-36b5-4c60-a9d5-1882dbd6ee62` | `released`, con inspección, conformidad y revisión humana |
| P4, plan | `8f9734ae-4256-41bb-8ee2-7e156a2c5894` | `awaiting_customer_acceptance_and_fulfillment`: aprobar el plan no cerró la incidencia |
| P4, cierre | Mismo caso P4 | `closed`, después de eventos humanos posteriores de aceptación, cumplimiento y conformidad y otra aprobación |

Durante P1 se reiniciaron API y worker con una revisión pendiente. Se recuperó el mismo ID de aprobación y se descargó el mismo adjunto; SHA-256 `2f95059d670a8751daad507d6f14078b2c38fa4b6c7b95bb4f3e1d06c7afe6bf`. Los volúmenes se conservaron. La recuperación tras un commit antes de responder y tras preparar una revisión antes del `interrupt()` también pasó en integración.

La UI recibió eventos persistidos y texto público validado transmitido en deltas SSE. El streaming nativo del proveedor se comprueba en una evaluación separada; el chat no retransmite sin validación tokens de una propuesta JSON ni delega el consentimiento a una segunda redacción del modelo.

## Controles de seguridad comprobados

- Cambio de rol/organización por cabecera, campo extra o chat no concede permisos. Lecturas, herramientas, medios, fuentes y efectos vuelven a verificar el alcance y rol.
- Contratos estrictos y allowlists rechazan acciones ajenas al proceso; no hay shell, SQL libre ni pagos disponibles para los modelos.
- Un cliente bloqueado exige autorización administrativa y nueva confirmación. Aprobaciones contienen hash, versiones y fingerprint de política; evidencia nueva o procedimientos vencidos invalidan efectos.
- Decisión humana, job de reanudación y evento de auditoría se confirman en una transacción. La prueba nueva fuerza un job aún activo: devuelve 409 y conserva la revisión pendiente. Reintentar después genera un único job/evento.
- Idempotencia concurrente, último cupo, cancelación y replay del ledger pasaron. No se encontraron slots con capacidad negativa o excedida.
- Un fallo de notificación conserva pedido/ledger y permite reintentar outbox; solo existe bandeja local.
- Sin inspección/conformidad no se libera. Sin plan autorizado y evidencia posterior no se cierra. Vencer o guardar silencio deja pendiente.
- Archivos falsos, tamaño/páginas excesivos, extensión discordante y acceso por otro caso se rechazan. Originales quedan en volumen, con hash; checkpoints conservan referencias.
- `.env` se excluye del repositorio/contexto Docker y tiene permisos 0600. El escaneo buscó la clave configurada sin imprimirla; encontró **cero coincidencias** en artefactos y mensajes/eventos/checkpoints/blobs examinados. Ver [auditoría con fecha y conteos](security-and-data-audit.json).
- El rol DB runtime carece de superusuario, creación de bases y roles. Se comprobó origen/host y 404 JSON de una API inexistente.

Los mensajes de sistema ayudan a delimitar responsabilidades; estos controles también se aplican fuera del modelo. La prueba real adversaria fue satisfactoria para ese caso, sin acreditar resistencia universal. [Detalle de límites y prompts](../SEGURIDAD.md).

## Datos que quedan poblados

| Dataset | Resultado comprobado |
|---|---|
| Histórico operativo **sintético** | 3.000 pedidos/casos, 150 clientes adicionales y 12.750 eventos, fechas Lima 2024-10-16–2026-10-08; correos `example.invalid` y procedencia explícita |
| Referencias públicas **reales** | 151 avisos CPSC, 1974-02-15–2026-09-17, corte 2026-10-16, enlaces primarios y hashes; esquema `reference` separado |
| RAG aprobado demo | 4 documentos, 14 fragmentos con vectores Gemini reales de 768 dimensiones; colección `a44e84e1d47828aaa8a874ba` |
| Casos QA | Se conservan ejecuciones reales de la aplicación con datos de negocio sintéticos, incluidos los IDs anteriores |

Repetir `seed-history`, `import-public-history` e `ingest-demo` devolvió respectivamente **0 pedidos/casos/eventos/clientes insertados**, **0 avisos insertados** y **0 fragmentos escritos**. La consulta real de calidad recuperó el fragmento `demo:p3-calidad:a44e84e1d47828aaa8a874ba:2`, distancia coseno aproximada 0,2802. No hay vectores fake en la colección de la base demo. La auditoría no encontró eventos históricos fuera de la cronología de sus casos.

En el informe JSON las fechas internas están en UTC; `2026-10-09 02:00:00+00:00` corresponde a `2026-10-08 21:00:00` en Lima. Las fechas CPSC son fechas de aviso sin hora inventada. [Fuentes, checksum del snapshot y tres escenarios históricos verificables](../FUENTES_Y_DATOS.md).

## Evidencia visual y límites de entrega

[Escritorio, tema oscuro](ui-desktop.png), [móvil, tema oscuro](ui-mobile.png) y [P1 confirmado tras recargar](ui-p1-persisted.png). Se midieron 12 pares de tokens claro/oscuro; todos superaron 4,5:1, con mínimo aproximado 5,21:1. [Mediciones](contrast-product.json). Esto no sustituye una auditoría completa de accesibilidad o pruebas en todos los navegadores.

El alcance entregado es **local y de demostración**. No hay autenticación real, separación de funciones entre empleados, envío SMTP, pagos, acciones sobre máquinas, integración n8n/Sheets activa ni políticas empresariales ratificadas. Las tareas físicas son declaraciones del operador. Los datos internos reales de Aqua Clean no fueron proporcionados ni importados; las referencias públicas no prueban operaciones de la empresa. La IA externa requiere cuota y conectividad, y el razonamiento necesita evaluación continua. Los eventos registran uso de tokens cuando existe, pero el coste monetario es desconocido (`cost_usd=null`), sin cifras estimadas presentadas como facturación.

No se atribuye seguridad absoluta ni preparación para producción. La extensión autenticada y un piloto con procedimientos/datos autorizados quedan fuera del perfil solicitado y se documentan como trabajo posterior, sin bloquear el funcionamiento local comprobado.
