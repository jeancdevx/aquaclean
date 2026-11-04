# Matriz BPMN–código V1

Los BPMN de `docs/bpmn/01`–`06` siguen siendo la especificación de procesos. La implementación usa tareas humanas declaradas y herramientas Python. Una tarea manual del modelo nunca se presenta como trabajo físico realizado por un agente.

| BPMN / nodos | Código y comportamiento | Evidencia de prueba |
|---|---|---|
| Integral `Integral_P1`, `Integral_P2R`, `Integral_P3`, `Integral_P4`, `Integral_P2E`, `Integral_P4C` | `graphs/main.py` delega un especialista por ciclo; casos vinculables a un pedido; historial autorizado del pedido | `scripts/run_demo.py`, `test_graphs.py` |
| Integral `Recoger`, `Procesar`, `Empacar`, `Entregar`, `Cargo`, `Cerrar` | Formulario de eventos de operador e inspector; no ejecución física, facturación o firma digital por IA | Guía T10–T12; eventos `pickup`, `delivery`, inspección/cumplimiento |
| P1 `Interpretar`, `Consultar`, `Datos`, `Preguntar` | Contrato `RequestDraft`, prompt P1 y herramientas `customer_registry`/`case_evidence`; validación de siete campos, borrador parcial y límite | A01/A02, T02/T03 |
| P1 `Resumen`, `Confirmar`, `Acepta` | `stage_proposal`, tarjeta y `interrupt`; aprobar/corregir/rechazar por API; un borrador completo no ejecuta efectos | A03, U07 |
| P1 `Validar`, `Permiso`, `Humano`, `Autoriza` | Política comercial determinista; cliente bloqueado requiere administración y reconfirmación | A05, prueba HITL bloqueado |
| P1 `Registrar`, `Resultado`, `Informar`, `Error` | `application/command_executor.py`, `persistence/commands.py`; pedido/ledger/outbox en una transacción y resultado real | A03/A04, recuperación después de commit |
| P1 `Timeout`, `Pendiente`, `Avisar` | Deadline persistido y `workers/outbox.expire`; pendiente, responsable y notificación local | A14 |
| P2 `Contexto`, `Opciones`, `Viable` | `Repository.slots`, agenda/capacidad actuales; filtros de ventana futura y cupos | A06 |
| P2 `Analizar`, `Proponer`, `Respuesta`, `Eleccion` | `ScheduleProposal`, prompt P2, subgrafo especializado y tarjeta de opciones calculadas; presupuesto/límite de negociación | M08 P2, T06 |
| P2 `Validar`, `Revision`, `Humano`, `Autoriza` | Revisión logística por límites piloto, selección y hash/versiones; no crea capacidad | Pruebas de opción inválida, selección y concurrencia |
| P2 `Reservar`, `Error`, `Confirmar` | Lock y actualización atómica de reservas/capacidad; cancelación libera cupo; resultado confirmado solo después del commit | Último cupo concurrente y cancelación |
| P3 `Inspeccion`, `Completar`, `Nueva` | Eventos humanos, adjuntos autorizados y percepción editables; sin evidencia/procedimiento queda pendiente | A07 |
| P3 `Evidencia`, `Analizar`, `Suficiente`, `Validar` | Contrato `QualityRecommendation`, RAG vigente filtrado, fuentes verificadas al proponer y ejecutar | Procedimiento expirado/ajeno, T09 |
| P3 `Revisar`, `Decision` | Revisión humana por rol calidad con propuesta/hash y versión | M08 P3 |
| P3 `Reproceso`, `Verificar`, `Conforme` | Autorización previa, comando que deja esperando tarea física, evento humano y nueva conformidad; máximo configurable | `test_reprocess_requires_authorization_and_new_conformity` |
| P3 `Registrar`, `Incidencia` | Ejecutor libera con evidencia o abre incidencia P4; no acciona máquinas | P3 real y pruebas de evidencia insuficiente |
| P4 `Expediente`, `Analizar`, `Suficiente` | `ResolutionProposal`, evidencia del caso e historial del pedido, hechos/discrepancias y conocimiento recuperado | A08, T11 |
| P4 `Solicitar`, `Respuesta`, `Timeout` | Aclaración limitada, deadline y pendiente con responsable; no se inventa conformidad | A09/A14 |
| P4 `Alternativas`, `Politica`, `Humano`, `Aprobada` | Propuesta de plan, validación de procedimiento, aprobación administrativa; sin herramientas de pagos | M08 P4, pruebas de permisos |
| P4 `Proponer`, `Elegir`, `Acepta` | Plan autorizado persiste como abierto; aceptación expresa se documenta por operador, contrapropuesta necesita nuevo análisis/revisión | Guía T11/T12 |
| P4 `Ejecutar`, `Error`, `Cumplimiento`, `Cumple`, `Cerrar` | Ledger/outbox; solo cierra con plan previo y evidencia posterior de aceptación, cumplimiento y conformidad | A09, cierre real en demo completa |
| Orquestación `Cargar`, `Ruta`, `ValidarRuta`, `Elegir`, especialistas | API/actor backend, run ID/hash, permisos, supervisor y cuatro subgrafos. P2 sin pedido vinculado deriva a P1 para aclarar una nueva solicitud o pedir vinculación; no ejecuta logística ni eleva permisos | A11/A12, M08; `test_new_pickup_suggestion_collects_fields_before_logistics`, `test_pickup_routing_cannot_grant_attention_role` |
| Orquestación `Policy`, `HITL`, `Revisar`, `Autorizada` | Contratos/allowlist, hash y versiones, `interrupt()` y `Command(resume=...)` en thread estable | A10/A13 |
| Orquestación `Ejecutar`, `Resultado`, `Error`, `Cola` | Ejecutor idempotente, recuperación de checkpoint/job, outbox y estado pendiente explícito | A03/A04/A10, M06 |

Temporizadores y tareas físicas son semántica de aplicación/operador, no capacidad automática del saver. El worker deriva los vencimientos a pendiente y conserva el checkpoint para resolución explícita. Los resultados realizados y las limitaciones están separados de esta matriz en `docs/validacion/PRODUCTO_V1.md`.
