> Antecedente V1 corporativo, superado para el alcance seleccionado. Versión vigente: [descripciones V2](../DESCRIPCIONES_PROCESOS.md). Original conservado en [antecedentes](../antecedentes/v1/descripciones/06-orquestacion.md).

# Orquestación técnica del sistema multiagente

**Diagrama:** `bpmn/06-orquestacion-multiagente.bpmn`. **Proceso:** `Process_Orquestacion`. **Implementación futura:** `graphs/main.py`, subgrafos P1–P4 y casos de uso de aplicación.

## Descripción

Un evento de negocio autenticado inicia o reanuda el caso. La aplicación valida su identidad, deduplica el evento y carga el estado persistente. El supervisor propone una intención y el especialista adecuado con una salida tipada. Una política independiente comprueba que el dominio es compatible con la fase del pedido, el acceso del actor y el presupuesto de ejecución.

Una compuerta exclusiva activa atención, logística, calidad o incidencias. Se ejecuta el especialista y se consolida una propuesta. El modelo representa una delegación principal por ciclo; los procesos interdependientes se enlazan mediante eventos y nuevos casos. No implica ejecutar siempre los cuatro agentes ni esperar un resultado paralelo de todos.

La política verifica esquema, evidencia, restricciones, permisos y versiones. Una acción ordinaria que satisface todas las condiciones puede pasar al ejecutor. Las acciones críticas, ambiguas o carentes de evidencia se pausan para revisión humana. La persona ve los hechos, la propuesta y las fuentes; aprueba, corrige, rechaza o solicita información. El servidor verifica su rol y que la propuesta siga vigente.

El ejecutor recibe un comando autorizado y lo ejecuta de forma idempotente. Se guarda el resultado, se actualiza el caso y se prepara la notificación mediante outbox. Un fallo técnico, conflicto de versión o ausencia de autorización deja un caso pendiente con responsable. Una ejecución del grafo no significa que se haya ejecutado un cambio de negocio.

## Correspondencia BPMN y LangGraph

| BPMN | Implementación conceptual |
|---|---|
| Evento de inicio | Endpoint/evento autenticado y validado |
| Tarea de servicio de agente | Nodo que invoca `create_agent` de LangChain o un subgrafo |
| Compuerta exclusiva | `add_conditional_edges` con resultado validado |
| Tarea de regla de negocio | Función de dominio determinista |
| Tarea de usuario | Nodo de revisión con `interrupt()` e interfaz de aprobación |
| Reanudación | `Command(resume=...)`, mismo `thread_id` y actor validado |
| Tarea de ejecución | Caso de uso con ledger, transacción y permisos |
| Temporizador de un proceso | Deadline persistido y worker que publica evento |
| Fin pendiente | Checkpoint/caso conservado, próximo paso y responsable |

La compuerta no evalúa directamente una probabilidad inventada por el modelo. El MVP utiliza condiciones verificables y revisión por riesgo. Una clasificación probabilística calibrada es una ampliación evaluable con datos etiquetados.

Los fallos de un agente, un esquema o una lectura también se capturan en los adaptadores/nodos y terminan en pendiente cuando se agota la recuperación. El borde de error dibujado sobre el ejecutor destaca el fallo que puede dejar efectos inciertos; no es un catálogo exhaustivo de cada excepción Python.

## Estado y aprendizaje

La percepción parte de mensajes/documentos autorizados. La memoria de corto plazo es el estado del caso conservado por checkpoints. La de largo plazo incluye hechos persistidos y conocimiento aprobado con versión. Las herramientas recuperan evidencia o calculan alternativas; el razonamiento produce propuestas. El plan es una siguiente acción permitida por el grafo. El actuador es el ejecutor determinista. El aprendizaje inicial se limita a evaluación y mejoras revisadas de prompts/políticas; no existe modificación autónoma de las reglas de la lavandería.

Cada aprobación se registra como dato de evaluación, pero no se indexa automáticamente como procedimiento general. El feedback de un caso no autoriza repetir su excepción en otro cliente.
