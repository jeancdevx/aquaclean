# Aqua Clean · Pedido de lavandería al detalle V2

Demo local sintética del proceso **Gestionar el pedido de lavandería al detalle**: recepción real declarada en mostrador, prendas/servicios, producción e inspección humanas, aviso local, entrega, conformidad, cobro declarado y comprobante de demostración. P1R coordina un recojo previo sin abrir una orden. El alcance corporativo V1 queda en [antecedentes](docs/antecedentes/v1/README.md).

Monolito modular FastAPI/Python, LangChain/LCEL, LangGraph con HITL/checkpoints PostgreSQL, investigación P4 con Deep Agents SDK, pgvector y Astro/React/TypeScript/Tailwind/shadcn. Actor fijo `demo_operator`, sin login ni selector de roles. No acredita separación de empleados reales. Inter, JetBrains Mono y paleta V1 conservadas.

## Arranque Docker

```bash
test -f .env || cp .env.example .env
# Configurar GEMINI_API_KEY localmente; nunca compartir .env.
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose exec api python -m aquaclean.cli seed-demo
docker compose exec api python -m aquaclean.cli ingest-demo
docker compose exec api python -m aquaclean.cli verify-vector-store
docker compose exec api python -m aquaclean.cli smoke-local
```

Abrir http://localhost:8000; OpenAPI http://localhost:8000/api/docs. Migraciones aditivas 005–006 conservan V1 como `legacy_v1`, sin fabricar prendas, pesajes ni pagos. Mantener los volúmenes `postgres` y `media`; no usar `down -v`. La migración temporal usa propietario; API/worker usan `aquaclean_runtime` sin DDL. Puertos solo en localhost. Con un volumen existente conservar su credencial; cambiar `.env` no cambia el password almacenado en PostgreSQL.

## Recorrido

1. Pulsar **Atención al detalle** → recepción en mostrador. Cliente nuevo necesita nombre/contacto, sin correo obligatorio. Capturar prendas, cantidades, servicio, pesaje si aplica, observaciones, evidencia y fecha prometida. Adjuntos desde el compositor se pueden vincular a prendas.
2. **Preparar confirmación** interpreta/explica el formulario y calcula importes con tarifas sintéticas versionadas. La tarjeta no crea cliente/orden/adelanto. Confirmar reanuda el mismo hilo LangGraph y escribe transaccionalmente.
3. En la orden persistida registrar inicio y fin de procesamiento como hitos humanos. En Actividad → Caso registrar inspección/conformidad; pedir «Revisa calidad y propone liberar esta orden». Aprobar la disposición lleva a READY y a un aviso único en bandeja local.
4. Coordinar entrega por chat o registrar retiro en mostrador desde la tarjeta. Se exige liberación, receptor y evidencia. Registrar cobro declarado del saldo y conformidad explícita; cerrar genera comprobante **DEMOSTRACIÓN, SIN VALIDEZ FISCAL**. No hay pasarela bancaria ni emisión SUNAT.
5. Alternativa: solicitud previa de recojo desde el formulario; P2 agenda por `pickup_request_id` sin orden. Declarar recojo efectivo y luego recibir prendas. Solo esa recepción crea ServiceOrder.
6. P3 puede abrir expediente P4 separado vinculado. Abrirlo desde historial, registrar observación y solicitar investigación. Deep Agents planifica y delega a Evidencias/Procedimientos; su propuesta vuelve al HITL. Plan autorizado no cierra: faltan aceptación, cumplimiento y conformidad posteriores.

Ejemplos sintéticos de chat: «Recibí prendas en mostrador de una cliente nueva; ayúdame a registrar la recepción», «Coordina el recojo de esta solicitud», «Revisa la inspección registrada y propone liberar», «Investiga la discrepancia con ambos subagentes y propone un plan sin ejecutarlo». Los datos ausentes se preguntan, nunca se inventan.

## Configuración y límites

`GEMINI_CHAT_MODEL` y embeddings son configurables; construcción de modelos solo en `infrastructure/llm/provider.py`. Sin clave, UI/datos están disponibles y la IA indica indisponibilidad. No hay fake de producción. Tarifario configurable `RETAIL_TARIFF_PATH=config/retail-tariffs-v2.json`, Decimal PEN, versión/hash en cotización. Cambiar tarifa invalida confirmaciones pendientes. Promesa 48 h y alerta de procesamiento 24 h son parámetros de laboratorio; la alerta no interrumpe producción. No hay cierre por silencio ni ventana corporativa postventa aplicada al detalle.

`MAX_MODEL_CALLS=24`, `DEEP_MAX_MODEL_CALLS=16`, `DEEP_TIMEOUT_SECONDS=180` limitan investigación y delegaciones. Deep Agents 0.7.30 recibe modelo inyectado, backend virtual nuevo por caso, solo `read_file` virtual, `write_todos`, `task` y dos lecturas acotadas. Sin disco libre, shell, SQL, pagos o herramientas de cierre. [LangSmith requerido para semana 10](docs/LANGSMITH.md): usar plan gratuito, consultar y reutilizar trazas existentes antes de nuevas inferencias, exportar IDs/URLs reales y capturar su interfaz con Playwright. Falta acceso a la cuenta en este entorno; no se declara cumplido. Los [logs locales](docs/OBSERVABILIDAD_LOCAL.md) solo aportan evidencia auxiliar.

## Desarrollo y validación

```bash
uv sync --frozen
uv run python scripts/write_build_revision.py  # metadatos del código que se copiará en Docker
uv run ruff check .
uv run ruff format --check .
uv run mypy  # dominio, schemas y configuración; alcance explícito en pyproject.toml
# TEST_DATABASE_URL debe terminar en _test; nunca usar la base demo.
uv run pytest -m 'not real_provider'
pnpm --dir web install --frozen-lockfile
pnpm --dir web check
pnpm --dir web build
pnpm --dir web exec playwright test
# Evaluaciones facturables, separadas:
RUN_REAL_PROVIDER=1 uv run pytest tests/evaluations -m real_provider
```

Solo pnpm y pnpm-lock.yaml en frontend. [Contratos](docs/contratos/DETALLE_V2.md), [plan vigente](docs/PLAN_ARQUITECTURA.md), [descripciones](docs/DESCRIPCIONES_PROCESOS.md), [arquitectura](docs/arquitectura/IMPLEMENTADA.md), [matriz BPMN–código–prueba](docs/arquitectura/MATRIZ_BPMN_CODIGO.md), [guía actual](docs/GUIA_PRUEBAS_DETALLADA.md). Los XML BPMN descriptivos no son ejecutados por LangGraph. Los resultados V1 conservan fecha/commit; los nuevos resultados y omisiones se entregan en `artifacts/semana10/` y el ZIP.
