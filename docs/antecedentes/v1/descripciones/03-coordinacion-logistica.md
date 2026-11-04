# P2. Coordinar recojos, entregas y reprogramaciones

**Diagrama:** `bpmn/03-to-be-coordinacion-logistica.bpmn`. **Proceso:** `Process_P2`. **Especialista:** agente de logística. **Responsable humano:** asesor y responsable de logística.

## Descripción textual del TO BE

El proceso comienza con un pedido registrado o con un evento de cambio: ropa no lista, ausencia del receptor, modificación de la franja solicitada o una restricción de capacidad. El sistema consulta el estado del pedido, agenda, capacidad, ubicación y compromiso comercial. El agente interpreta la urgencia y las preferencias del interlocutor sin atribuir prioridad contractual a una frase del chat.

Un servicio de agenda calcula alternativas que cumplen las restricciones verificadas. Si no existen opciones factibles, el responsable humano analiza el conflicto; el agente no anuncia un cupo inexistente. Cuando existen alternativas, el agente compara las opciones, explica sus consecuencias y pide al cliente elegir. Las respuestas ambiguas o contrapropuestas vuelven al análisis, con hasta dos rondas de negociación en el piloto.

Tras una selección, la aplicación verifica permisos, vigencia de agenda y compatibilidad con el plazo contratado. Los cambios fuera de política necesitan aprobación del responsable de logística. Una aprobación no puede crear capacidad física; el plan autorizado debe seguir siendo factible. Si no hay acuerdo, el caso queda pendiente con motivo y responsable.

Finalmente el servicio reserva o actualiza la agenda de forma atómica y confirma al cliente únicamente la opción realmente persistida. Un conflicto por otro pedido, una versión obsoleta o un fallo del servicio impide emitir esa confirmación y deriva a revisión/recalculo. El chofer realiza el recojo o la entrega en el proceso integral; P2 coordina la operación y no sustituye su ejecución física.

## Entradas y salidas

| Tipo | Datos |
|---|---|
| Entrada | `order_id`, `operation_type`, agenda versionada, capacidad y ventanas disponibles |
| Contexto de cliente | Preferencias confirmadas, dirección verificada y restricciones de recepción |
| Contexto comercial | Compromiso vigente y reglas aprobadas de cambio |
| Propuesta del agente | IDs de opciones calculadas, explicación, evidencia y necesidad de revisión |
| Resultado del servicio | Reserva, horario, versión y estado reales |
| Resultado alterno | Coordinación pendiente, sin promesa de horario |

El padrón actual permite incorporar horarios normales heredados del RPA. Las salidas de 10:30 y 16:00 son reglas del material existente, sujetas a validación. P2 agrega capacidad y acuerdos como requisitos futuros; esos datos no están completos en los adjuntos y deben capturarse antes del piloto.

## Decisión contextual y herramientas deterministas

La parte agentic interpreta expresiones como «antes del almuerzo», contrasta una preferencia con las opciones disponibles y propone una aclaración o alternativa. La parte determinista calcula ventanas, capacidad y restricciones. Si se incorpora optimización de rutas, se utiliza un algoritmo/solver detrás de `ScheduleService`; el LLM no calcula kilómetros ni tiempos garantizados por intuición.

No se entrega una herramienta genérica que permita editar toda la agenda. El agente lee opciones y devuelve una propuesta; el ejecutor reserva después de comprobar selección, política y versiones. Esto permite reutilizar el especialista tanto para recojo como para entrega.

## Trazabilidad del BPMN

| Elementos | Responsabilidad | Código futuro |
|---|---|---|
| `P2_Contexto` | Cargar estado y restricciones | Repositorios de pedido/agenda |
| `P2_Analizar` | Interpretar preferencias con evidencia | `agents/logistics.py` |
| `P2_Opciones`, `P2_Viable` | Calcular y verificar opciones | Puerto `ScheduleService` |
| `P2_Proponer`, `P2_Respuesta`, `P2_Eleccion` | Negociar y confirmar selección | `graphs/logistics_flow.py` |
| `P2_Validar`, `P2_Revision` | Condiciones contractuales y riesgo | Política determinista |
| `P2_Humano`, `P2_Autoriza` | Aprobar cambios fuera de política | API de aprobaciones |
| `P2_Reservar`, `P2_Error` | Escritura atómica o fallo explícito | Ejecutor y adaptador de agenda |
| `P2_Confirmar` | Notificar reserva efectuada | Outbox y canal autorizado |

## Excepciones y aceptación

Un timeout de 24 horas sin elección deriva a atención humana. Las contrapropuestas que agotan el límite también se derivan. Una propuesta imposible nunca se «resuelve» eliminando la restricción del sistema. Si la capacidad cambia después de elegir, se presenta una nueva alternativa y se pide confirmación cuando cambie el horario.

Ejemplo sintético: el cliente cambia una entrega a una franja que no coincide con la ruta normal. El servicio devuelve dos ventanas factibles; el agente explica cuál respeta mejor la preferencia y qué compromiso requeriría autorización. Si el cliente elige una opción, el servicio vuelve a comprobarla antes de reservar.

Pruebas mínimas: opción dentro de política, cambio fuera de SLA, agenda sin capacidad, contrapropuesta, dos reservas concurrentes del último cupo, falla de escritura y ausencia del receptor en el integral. Medir coordinación resuelta, correcciones humanas, conflictos, latencia y costo. No declarar un ahorro de transporte sin distancia y tiempos medidos.
