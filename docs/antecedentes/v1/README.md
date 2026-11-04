# Aqua Clean · V1 local

Chat de operaciones para atención (P1), logística (P2), calidad (P3) e incidencias (P4). FastAPI, LangChain, subgrafos LangGraph con revisión humana, PostgreSQL 17 + pgvector y Astro/React/TypeScript/Tailwind/shadcn/ui. El frontend usa **pnpm 10.33.2** y una única isla `ChatWorkspace`.

La demo abre sin login con `demo_operator` y una organización sintética fijados en backend. No acredita la identidad de personas reales. Los datos operativos son sintéticos; las referencias públicas CPSC se guardan separadamente y no constituyen políticas de Aqua Clean.

## Arranque reproducible

Requiere Docker Engine/Desktop y Docker Compose. No necesita Node o Python instalados en el host para ejecutar la aplicación.

```bash
test -f .env || cp .env.example .env
# Editar .env localmente; no compartir ni publicar su contenido.
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose exec api python -m aquaclean.cli seed-demo
docker compose exec api python -m aquaclean.cli seed-history --orders 3000
docker compose exec api python -m aquaclean.cli import-public-history
docker compose exec api python -m aquaclean.cli ingest-demo
docker compose exec api python -m aquaclean.cli verify-vector-store
docker compose exec api python -m aquaclean.cli smoke-local
```

Abrir **http://localhost:8000**. OpenAPI interactivo: **http://localhost:8000/api/docs**; contrato JSON: `/api/openapi.json` y [copia exportada](docs/openapi.json).

`config --quiet` valida Compose sin imprimir variables sensibles. `migrate` es temporal: termina con código 0 antes de arrancar API/worker. API, worker y DB tienen healthchecks; la base no publica un puerto en el host. La API escucha únicamente en `127.0.0.1:8000`. Imágenes base y dependencias están fijadas por digest/lockfiles.

## Configuración

Completar en `.env`:

| Variable | Uso |
|---|---|
| `GEMINI_API_KEY` | Clave solo en backend y worker |
| `GEMINI_CHAT_MODEL` | Selección comprobada: `gemini-3.5-flash-lite` |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` |
| `EMBEDDING_DIMENSION` | `768`; el adaptador comprueba dimensión y normaliza L2 |
| `AUTH_MODE` | `demo_local`; otros perfiles fallan explícitamente |
| `APP_TIMEZONE` | `America/Lima` |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Propietario de migraciones y base local |
| Límites `MAX_*`, `WAIT_HOURS`, `SLOT_CAPACITY`, `PILOT_*` | Límites configurables de laboratorio, no políticas empresariales ratificadas |

Compose construye las conexiones internas a `db`. API/worker usan el rol PostgreSQL `aquaclean_runtime`, sin permisos de superusuario, creación de bases/roles o DDL de negocio. Solo la migración usa el propietario. No cambies el password de un volumen PostgreSQL existente únicamente editando `.env`: PostgreSQL conserva el usuario inicial; cambia su credencial de forma explícita y vuelve a ejecutar la migración.

Sin clave, la UI, historial, clientes y archivos siguen accesibles; la IA y embeddings indican indisponibilidad. No existe modo fake en producción. Cambiar modelo/dimensión de embeddings crea otra colección y exige reingesta; no mezcla espacios vectoriales.

El modelo `gemini-3.8-flash` figuraba disponible y clasificó correctamente, pero mostró errores 429/504 en las pruebas de esta cuenta. `gemini-3.5-flash-lite` pasó las seis modalidades, streaming, contratos y prueba de inyección. El proveedor sigue siendo externo y sujeto a cuota/conectividad. No hay cambio automático de modelo ni proveedor simulado.

## Uso

1. Crear una conversación y seleccionar el cliente demo verificado por el operador, o indicar sus datos en el mensaje. Los códigos no autentican personas.
2. «Programar un recojo» se puede enviar con solo el cliente seleccionado: Atención pide los datos faltantes, sin exigir un pedido previo. En P1, completar siete campos y revisar la fecha exacta, dirección y contacto. **Confirmar** ejecuta el registro; una sugerencia solo rellena texto.
3. En P2, elegir una opción calculada. La capacidad y la versión se verifican otra vez al reservar.
4. Para trabajar otro proceso sobre un pedido existente, abrir su conversación o usar **Actividad → Caso → Vincular pedido verificado** en una conversación creada.
5. En P3/P4, registrar inspecciones, aceptación, cumplimiento y conformidad mediante formularios de operador. Las tareas físicas no las realiza el agente. Las decisiones sensibles esperan aprobación.
6. Adjuntar JPG/PNG/WebP, PDF o MP3/WAV. Se valida contenido, tamaño, páginas/duración y acceso; se conserva el original con hash. La observación/transcripción de Gemini se puede corregir y sus campos se confirman antes del comando.
7. **Cómo se resolvió** y **Actividad/Fuentes** muestran resúmenes públicos y fragmentos realmente recuperados. No contienen pensamiento privado ni prompts del sistema.

Las notificaciones se entregan a una bandeja local del expediente. No se envía correo real. No se emiten pagos ni compensaciones monetarias.

## Históricos y fuentes

- `seed-demo`: dos clientes base; `CLI-0002` está bloqueado para probar revisión comercial. Agenda de 14 días; no sobreescribe reservas.
- `seed-history --orders 3000`: 150 clientes adicionales, 3.000 pedidos y 12.750 eventos sintéticos, con cronología 2024-10-16–2026-10-08 en el dataset creado. IDs estables, contactos `example.invalid`, marca `synthetic_history_v1`. No genera trazas ficticias de agentes ni notificaciones retrospectivas.
- `import-public-history`: 151 avisos históricos reales de CPSC (1974-02-15–2026-09-17), con corte 2026-10-16, enlaces oficiales y hashes. Se almacenan en `reference`, nunca como pedidos/expedientes reales de Aqua Clean ni como procedimientos autorizantes.
- [Procedencia y actualización](docs/FUENTES_Y_DATOS.md). El snapshot permite reconstruir la misma base sin volver a consultar una API pública que puede cambiar.

## Desarrollo y pruebas

```bash
uv sync --frozen
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy
uv run pytest
pnpm --dir web install --frozen-lockfile
pnpm --dir web check
pnpm --dir web build
pnpm --dir web exec playwright install chromium
pnpm --dir web test:ui
```

Las pruebas de integración requieren `TEST_DATABASE_URL` explícita, en una **base separada cuyo nombre termine en `_test`**. [Guía detallada](docs/GUIA_PRUEBAS_DETALLADA.md) explica cómo crearla sin exponer PostgreSQL ni tocar el volumen demo. Sin esa variable se omiten con motivo; no se confunden con pruebas pasadas. Los fakes solo se importan desde `tests/` y sus vectores se identifican por modelo `fake-test-only-sha256`.

Pruebas facturables con Gemini real:

```bash
RUN_REAL_PROVIDER=1 uv run pytest tests/evaluations -v
RUN_REAL_PROVIDER=1 pnpm --dir web test:ui
uv run python scripts/run_demo.py --restart
```

Para desarrollo web, `pnpm --dir web dev` usa proxy explícito de `/api/` hacia FastAPI. El perfil servido por Docker no necesita un servidor Node permanente. Las fuentes Inter/JetBrains Mono se empaquetan con el build y no dependen de Google Fonts.

## Persistencia y recuperación

```bash
docker compose restart api worker
docker compose down
docker compose up -d
```

Los volúmenes nombrados conservan negocio, chat, aprobaciones, checkpoints, vectores y adjuntos. No eliminar volúmenes para recuperarse de errores ordinarios. Los trabajos pendientes llevan leases y se recuperan; las escrituras usan ledger, IDs estables, restricción única, versiones y transacción. Reconectar SSE solo lee eventos. Detener una respuesta no revierte una operación ya confirmada.

## Documentación de entrega

- [Guía detallada de pruebas, prompts y escenarios históricos](docs/GUIA_PRUEBAS_DETALLADA.md), también en [PDF de 16 páginas](docs/GUIA_PRUEBAS_DETALLADA.pdf) y [HTML](docs/GUIA_PRUEBAS_DETALLADA.html).
- [Arquitectura implementada](docs/arquitectura/IMPLEMENTADA.md) y [matriz BPMN–código](docs/arquitectura/MATRIZ_BPMN_CODIGO.md).
- [Seguridad, prompts y límites](docs/SEGURIDAD.md).
- [Resultados reales y limitaciones](docs/validacion/PRODUCTO_V1.md).
- [Estado por cortes](IMPLEMENTATION_STATUS.md).

El perfil autenticado de producción, identidad de empleados reales, datos operativos reales de Aqua Clean, políticas ratificadas, pagos y correo externo no forman parte de esta demo. La aplicación no controla máquinas ni acredita la veracidad de una tarea física: conserva la declaración del operador y exige las autorizaciones del flujo.
