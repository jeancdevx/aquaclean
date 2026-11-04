# Arquitectura implementada · V2 al detalle

La especificación vigente es PLAN_ARQUITECTURA.md y BPMN `*-v2.bpmn`. V1 corporativa se conserva en antecedentes; los resultados históricos no validan automáticamente V2.

| Capa de software | Archivos y responsabilidad |
|---|---|
| Dominio | `domain/retail.py`: CustomerInput, ReceptionInput, PickupInput, Decimal PEN, cotización y transiciones; `entities.py`, `policies.py`: actor, reloj, hashes y reglas. Sin IA/HTTP/SQL. |
| Aplicación | `application/ports.py`, `command_executor.py`, `presentation.py`: puertos inyectados y presentación del efecto confirmado. |
| Agentes y grafos | `agents/chains.py`: ChatPromptTemplate + MessagesPlaceholder + modelo estructurado; `supervisor.py`, `specialists.py`: invocaciones reales por el puerto; `deep_incidents/factory.py`: SDK P4. `graphs/main.py`, `specialist_flow.py`, `state.py`: estado tipado, fase/permisos, aclaración, subgrafos, stage/review/execute/respond. |
| Infraestructura | `llm/provider.py`: única construcción del modelo/SDK; `persistence/retail.py`, `retail_operations.py`, `retail_logistics.py`, `commands.py`: tablas y transacciones; `repositories.py`: evidencia, versiones y revisiones; `knowledge/retrieval.py`: pgvector filtrado; `observability/tracing.py`: LangSmith/correlación. |
| Interfaces | `interfaces/api/retail_routes.py`: borradores y hitos humanos; `app.py`: API, SSE y archivos; `web/`: chat, tarjetas, formularios y actividad persistida. |

PostgreSQL es la autoridad de pedidos. `app.orders.kind=legacy_v1` identifica registros V1 intactos. Órdenes retail_v2 usan estados RECEIVED → IN_PROCESSING → QUALITY_PENDING → READY → DELIVERY_PENDING/DELIVERED → CLOSED; REPROCESS_PENDING vuelve a QUALITY_PENDING solo con evento humano autorizado. PickupRequest y sus reservas no sustituyen el ciclo de ServiceOrder. Tablas aditivas: líneas, registros de pago declarado, entregas, comprobantes demo, eventos, solicitudes, reservas, alertas, investigación y correlación. Nada reconstruye retrospectivamente hechos ausentes.

Toda propuesta de escritura pasa por schema, alcance, permisos, evidencia/fuentes vigentes y stage; `interrupt()` guarda checkpoint en PostgreSQL. Revisión valida hash, política, versión y selección; `Command(resume=...)` continúa el mismo `org:<organization>:case:<id>`. El nodo review no produce efectos antes de interrupt. El ejecutor revalida bajo lock y confirma negocio, ledger y outbox. Reintento con mismo ID devuelve resultado; mismo ID con otro contenido es conflicto. Los hitos de producción/cobro/entrega son comandos explícitos del operador, también idempotentes y versionados.

P3 crea caso P4 separado con parent_case_id y order_id. La orden permanece retenida hasta liberar calidad. Un plan P4 aprobado conserva incidencia abierta hasta aceptación/cumplimiento/conformidad posteriores y aprobación de cierre. Un caso bloqueante impide liberación/cierre comercial. No hay conformidad por silencio.

El worker consume jobs persistentes con leases y lock por caso. Outbox solo entrega a app.inbox y registra reintentos; READY tiene ID estable por orden. Alerta 24 h configurable no cambia IN_PROCESSING y se registra una vez. La ventana 48 h corporativa no se aplica al detalle; no se declara seguimiento postventa opcional implementado.

## Ecosistema de IA

LCEL: `structured_chain` devuelve RunnableSequence; prompt parametrizado y MessagesPlaceholder preceden al Runnable estructurado del proveedor. El parser del proveedor devuelve JSON y usage/raw; provider.structured valida después el schema Pydantic completo con reparación acotada. infrastructure/llm/schema.py simplifica solo las restricciones del schema de generación que Gemini rechazaba; el dominio conserva todos los límites. `ainvoke` se usa en el chat. `provider.stream` ofrece `astream` nativo, evaluado aparte; el chat SSE transmite texto ya validado y no tokens JSON privados. No se añadió parser de texto ni paralelismo ornamental.

LangGraph orquesta supervisor, aclaración y subgrafos. Exportaciones y grados se calculan desde `get_graph()` y `get_graph(xray=True)`, sin copiar cifras auditadas. Stage permite respond/review; execute permite respond/review para reconfirmación de excepción V1. Solo un especialista por ciclo. Errores de proveedor, conflicto, cancelación y presupuesto se gestionan por el worker fuera del grafo y dejan el caso pendiente; no son aristas de éxito.

Deep Agents 0.7.30: investigador P4, Evidencias y Procedimientos. Planificación opt-in habilitada, general-purpose deshabilitado, backend StateBackend fresco, FS limitado a read_file virtual; sin shell, host, store, memoria global o escritura de negocio. Herramientas sin argumentos libres revalidan alcance. Presupuesto compartido de llamadas/tiempo, contexto acotado, salida ResolutionProposal y citas verificadas. `app.deep_investigations` registra herramientas y resultados públicos; no razonamiento privado. Tests con modelo controlado ejecutan el SDK; evaluación Gemini real se reporta aparte.

Observabilidad local transversal: `app.events`/`app.runs` y `app.deep_investigations` conservan actividad pública e investigación. `scripts/export_local_observability.py` proyecta campos permitidos a JSON/JSONL/CSV y HTML; `scripts/local_log_report.py` separa tiempo de ejecución y espera HITL, conserva IDs locales y evita duplicar el uso P4 reflejado desde el journal canónico Deep Agents. No reconstruye spans, uso ni costes ausentes. Playwright captura el reporte exacto y la actividad real. Ver `../OBSERVABILIDAD_LOCAL.md`. Es evidencia auxiliar; no sustituye el requisito de LangSmith de la semana 10.

LangSmith transversal (requerido para evidencia semana 10, desactivable en operación local): configuración explícita proyecto O agente/entorno, región/workspace y clave backend. Trazas automáticas LCEL/grafo/herramientas más spans SDK directo de percepción/embeddings, recuperación y ejecutor. `app.trace_links` almacena IDs reales del RunTree, distintos de app_run_id; las reanudaciones son trazas independientes correlacionadas por thread_id. No queda traza abierta durante espera humana. Acceso externo no acreditado sin evidencias.

## RAG, medios y demo

Corpus sintético aprobado V2 en knowledge; ingesta real Gemini, dimensión/modelo/colección consistentes y coseno pgvector con filtros organización, cliente, roles y vigencia. CPSC se mantiene en reference, sin autoridad operativa. Adjuntos cliente nunca se convierten automáticamente en política. Imagen/PDF/audio conservan originales/hash y observaciones editables; percepción no acredita inspección física.

Compose conserva DB, API, worker y migración temporal, volúmenes y healthchecks. El actor demo fijo reúne capacidades y no acredita separación de empleados. n8n tiene adaptador explícito en `infrastructure/integrations/n8n.py`; convierte/valida campos corporativos sin ejecutar webhooks ni Sheets. No hay una segunda fuente de pedidos. LangSmith/Gemini son servicios externos; no se implementó facturación fiscal, pago bancario ni entrega física automatizada.
