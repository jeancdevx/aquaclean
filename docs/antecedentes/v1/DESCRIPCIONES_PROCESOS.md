# Descripciones de los procesos de Aqua Clean S.A.C.

Diseño propuesto para el alcance corporativo. Cada sección remite a su BPMN editable.


---

# AS IS revisado: atención del pedido corporativo

**Diagrama:** `bpmn/00-as-is-revisado.bpmn`. **Origen:** modelo corporativo adjunto. **Estado:** revisión documental, no nueva observación de campo.

## Descripción del proceso

El proceso comienza cuando el cliente corporativo solicita el recojo de ropa. El asesor anota la solicitud en el cuaderno de pedidos y revisa si el cliente está habilitado. Cuando hay deuda o contrato vencido, administración decide si se autoriza excepcionalmente la atención. Si no se autoriza, la solicitud termina como rechazada. Si se habilita, el asesor programa el recojo y comunica el turno al cliente.

El chofer espera la salida de la ruta y recoge las prendas. Si la ropa no está lista, se reprograma el recojo y se comunica la nueva coordinación. Cuando las prendas llegan a planta, se reciben, pesan y registran. La planta lava, seca y plancha el lote. El modelo original incluye una alerta no interruptora por 24 horas sin cerrar el lote: se comunica el retraso sin detener por ese motivo el procesamiento físico.

Control de calidad compara las prendas con la guía. Las observadas pueden reprocesarse y volver a revisión. Un daño o extravío deriva a gestión de incidencia. Luego se coordinan el empaque y el registro del cargo, se entrega el pedido y se obtiene la firma de recepción. Si no hay receptor, se reprograma la entrega. El asesor espera una observación del cliente o el vencimiento de la ventana de 48 horas del modelo y finalmente archiva la guía y cierra el registro.

## Revisión realizada

Se conservan las tareas, los carriles, las excepciones y la diagramación del archivo recibido. Se retira la anotación que presentaba una espera de 6,4 horas y eficiencia de 4,1 % como línea base: el Laboratorio 01 suministrado mide atención al detalle y no respalda una línea base del proceso corporativo. Se añade una nota de procedencia y validación pendiente.

No se incorporan agentes, una agenda digital, fotografías obligatorias ni expedientes electrónicos dentro del AS IS. Son mejoras futuras de los TO BE. La corrección documental evita representar una propuesta como si fuera el funcionamiento observado de la empresa.

## Validaciones pendientes del AS IS

1. Ratificar el alcance corporativo y reconciliarlo con la selección del Laboratorio 01.
2. Confirmar los tiempos y condiciones de espera. `P1D` representa una duración de un día; no implementa por sí solo el calendario del «siguiente día hábil» que aparece en algunas etiquetas del original.
3. Verificar qué autoriza el retorno del lote a empaque después de una incidencia. El original regresa al flujo sin detallar la condición de liberación. El integral TO BE exige evidencia de solución y lote liberado.
4. Confirmar cuándo y cómo termina un reproceso. El original contiene un retorno repetido a control de calidad sin límite explícito. El piloto TO BE limita el ciclo y exige nueva decisión humana si persiste la observación.
5. Validar el cierre, las condiciones comerciales y la documentación de reclamos. El vencimiento de una ventana interna no implica que ya no puedan recibirse reclamos posteriores.

## Cómo se relaciona con la mejora

P1 amplía la captura y aclaración de solicitudes; P2 cubre coordinación y reprogramaciones; P3 desarrolla el análisis de observaciones de calidad; P4 desarrolla la investigación y resolución de incidencias y reclamos. Estas mejoras se basan en puntos de decisión que ya aparecen en los modelos entregados, con requisitos futuros claramente identificados.


---

# TO BE integral: atender el pedido corporativo

**Diagrama:** `bpmn/01-to-be-integral.bpmn`. **Proceso:** `Process_Integral`. **Tipo:** coordinación de negocio. **Responsable:** atención, planta, logística, calidad y administración.

## Descripción del proceso propuesto

El proceso comienza con una solicitud corporativa. El sistema ejecuta P1 para interpretar el mensaje, aclarar campos, confirmar la intención del cliente y registrar el pedido mediante el servicio determinista. Solo un pedido realmente registrado o recuperado como existente avanza. Las solicitudes rechazadas o que requieren revisión conservan su estado y responsable.

P2 coordina el recojo utilizando opciones de agenda que cumplen las restricciones de capacidad y contrato. Un temporizador espera la fecha/hora realmente confirmada, el chofer ejecuta físicamente el recojo y las prendas ingresan a planta. Si el recojo falla, se inicia una reprogramación en P2; el modelo piloto permite una reprogramación antes de derivar el caso. La espera se materializa con evento de agenda/worker, sin mantener una llamada LLM esperando.

La planta procesa las prendas mediante procedimientos aprobados. Se conserva la alerta no interruptora de 24 horas del AS IS para comunicar retraso y revisar el compromiso mientras planta continúa; esa duración necesita ratificación. P3 registra la inspección humana, analiza las observaciones y ayuda a justificar una disposición. Un lote liberado pasa a empaque. Un lote con incidencia inicia P4 y permanece retenido. El proceso solo permite continuar hacia empaque si la solución se ha cumplido y se ha autorizado liberar el lote. Si la resolución no incluye entrega o permanece abierta, finaliza esta instancia con ese estado explícito y el expediente continúa bajo su responsable.

El personal empaca y etiqueta las prendas liberadas. Administración registra el cargo y la documentación comercial; esa actividad se conserva en el flujo, sin convertir la cobranza mensual en un nuevo dominio agentic. P2 coordina la entrega. El chofer la ejecuta y obtiene la firma de recepción. Si no hay receptor, se tramita una reprogramación y se aplica el mismo límite piloto.

Tras una entrega efectuada, el asesor espera la observación del cliente o el vencimiento de la ventana documental de 48 horas que figuraba en el AS IS. La duración requiere ratificación. Una observación inicia P4. Un reclamo abierto impide cerrar como conforme ese caso; un reclamo resuelto y documentado permite continuar. Finalmente se comprueba la guía y se cierra el registro operativo del pedido. El cierre del pedido no equivale a cobrar la factura mensual corporativa.

## Entradas, salidas y estados

| Elemento | Contenido |
|---|---|
| Entrada | Solicitud autenticada, padrón, contrato, agenda y datos del pedido |
| Resultado satisfactorio | Pedido entregado, guía documentada y observaciones resueltas o ventana finalizada |
| Resultados alternos | Solicitud pendiente/no autorizada, coordinación pendiente, lote retenido, incidencia abierta o cierre sin entrega |
| Excepción de entrega | Pedido entregado con reclamo abierto y siguiente acción asignada |
| Fuera del alcance | Lavado robotizado, control químico por IA, contabilidad, mantenimiento y cobranza mensual completa |

## Relación entre los diagramas

| Actividad del integral | Archivo que contiene el detalle | Resultado que permite avanzar |
|---|---|---|
| `Integral_P1` | `02-to-be-solicitudes.bpmn` | `registrado` o `ya_registrado` |
| `Integral_P2R` | `03-to-be-coordinacion-logistica.bpmn` | Reserva de recojo confirmada |
| `Integral_P3` | `04-to-be-calidad.bpmn` | Lote liberado o expediente de incidencia |
| `Integral_P4` | `05-to-be-reclamos-incidencias.bpmn` | Solución cumplida con disposición del lote |
| `Integral_P2E` | `03-to-be-coordinacion-logistica.bpmn` | Reserva de entrega confirmada |
| `Integral_P4C` | `05-to-be-reclamos-incidencias.bpmn` | Reclamo resuelto con evidencia |

P2 se reutiliza con `operation_type=recojo|entrega` y diferentes restricciones. P4 puede iniciarse desde planta o por un reclamo del cliente. La aplicación enlaza los casos con `order_id`, sin mezclar sus historiales ni convertir un cierre de una instancia en eliminación del expediente.

## Condiciones de control

La existencia de un pedido, la capacidad, la liberación del lote y el cumplimiento de una solución son hechos del sistema o decisiones humanas documentadas. El agente no puede generarlos mediante una afirmación textual. Si se recibe un reclamo después del cierre documental, se abre un nuevo caso P4 vinculado al pedido: las 48 horas no bloquean ese canal.


---

# P1. Interpretar y registrar solicitudes de recojo

**Diagrama:** `bpmn/02-to-be-solicitudes.bpmn`. **Proceso:** `Process_P1`. **Especialista:** agente de atención. **Reutilización:** servicio determinista `registrar_recojo` del RPA existente.

## Descripción textual del TO BE

El proceso comienza cuando un cliente corporativo envía una solicitud de recojo en lenguaje natural por un canal habilitado. La aplicación identifica al remitente y crea o recupera el caso. El agente de atención interpreta la intención, extrae únicamente información sustentada en el mensaje y consulta el padrón a través de una herramienta autorizada. Su función es transformar una conversación incompleta en una solicitud explícita y confirmada.

En la V1 local, «programar un recojo» sin pedido vinculado comienza aquí, aunque la clasificación inicial sugiera logística. El supervisor valida esa precondición y delega en Atención con sus permisos propios: pide los campos faltantes, sin exigir un pedido previo ni reservar. Si el mensaje se refiere a modificar un pedido existente, pide abrir su conversación o vincularlo expresamente; no crea un sustituto. Elegir un cliente no registra ni vincula automáticamente ninguno de sus pedidos.

Si un campo falta o admite más de una interpretación, el agente formula una pregunta concreta. No completa códigos, correos, direcciones, fechas ni cantidades por su cuenta. Las fechas relativas se convierten con el reloj de la aplicación en la zona America/Lima y se presentan como fechas exactas. El cliente confirma la fecha y el resto del resumen antes de registrar. Una corrección conserva los campos ya verificados y vuelve a la interpretación. El piloto admite hasta dos rondas; una identidad no resuelta, una cancelación o el límite agotado se derivan al asesor.

Con los datos confirmados, el sistema valida el contrato de siete campos y la situación comercial. Un cliente habilitado puede continuar. Una excepción por deuda o contrato requiere administración; una aprobación humana solo permite avanzar si los datos quedaron completos y el actor tiene competencia. Después de la revisión se vuelve al resumen, a la confirmación del cliente y a la validación del contrato. La autorización no salta esos controles. Una cancelación del cliente termina la solicitud.

La aplicación invoca `registrar_recojo` con un comando idempotente. El servicio devuelve el pedido creado, uno existente, una derivación o un rechazo. La respuesta al cliente se construye con ese resultado real. Si ocurre un fallo técnico o queda una revisión pendiente, se registra el motivo y se comunica que el recojo todavía no está confirmado. Un vencimiento de 24 horas sin aclaración, propuesto para el piloto, también deja un caso pendiente con responsable.

## Contrato y condiciones

| Campo | Requisito heredado |
|---|---|
| `cliente_id` | `CLI-####`; existente en padrón y vinculado al remitente por autenticación |
| `solicitante` | Texto de 1 a 120 caracteres |
| `correo` | Formato válido; confirmado por el solicitante |
| `fecha_recojo` | `AAAA-MM-DD`; entre hoy Lima y hoy + 30 días, según el contrato existente |
| `turno` | `manana` o `tarde` |
| `tipo_ropa` | `manteleria`, `toallas`, `uniformes` o `mixto` |
| `bolsas` | Entero entre 1 y 40 |
| Opcionales | `direccion_recojo`, `observaciones`, `canal`; defaults documentados y visibles al cliente |

Estos límites proceden del instrumento del RPA y deben ratificarse para el piloto. Los datos administrativos son leídos del padrón; no son memoria confiable del agente.

## Secuencia y trazabilidad del BPMN

| Elementos | Función | Módulo futuro |
|---|---|---|
| `P1_Interpretar` | Extracción y selección de aclaración | `agents/attention.py` |
| `P1_Consultar` | Datos filtrados de cliente | Puerto `CustomerRepository` |
| `P1_Datos`, `P1_Acepta` | Suficiencia, corrección y límites | `graphs/attention_flow.py` y política |
| `P1_Preguntar`, `P1_Respuesta`, `P1_Timeout` | Pregunta, pausa y vencimiento | Canal, checkpoint y worker |
| `P1_Resumen`, `P1_Confirmar` | Consentimiento sobre datos exactos | Casos de uso de confirmación |
| `P1_Validar`, `P1_Permiso` | Contrato y competencia comercial | `domain/policies.py` |
| `P1_Humano`, `P1_Autoriza` | Revisión del asesor/administración | Interfaz de aprobaciones |
| `P1_Registrar`, `P1_Resultado` | Registro y evaluación de resultado | `application/command_executor.py` |
| `P1_Pendiente`, `P1_Avisar` | Incidencia o derivación sin falsa confirmación | Repositorio de casos y outbox |

## Por qué califica para automatización multiagente

La extracción contextual, la comprensión de correcciones y la elección de la pregunta de aclaración son variables y requieren interpretación. El supervisor decide si la conversación pertenece a P1 o debe pasar a logística/incidencias, mientras el especialista conoce el contrato de entrada. Los validadores, la clave, el registro y la asignación normal por horario son deterministas y permanecen como herramientas.

El antiguo «agente registrador» no se replica como un LLM adicional: la tarea de validar y registrar se representa como servicio. Esto conserva el trabajo útil del RPA y evita delegar a un modelo una decisión completamente especificada por reglas.

## Ejemplo sintético y aceptación

Mensaje: «Necesito recojo mañana en la mañana, son varias bolsas de manteles». El agente reconoce un recojo, expresa la fecha exacta del reloj de prueba y pregunta por la cantidad; obtiene identidad y contacto del canal/padrón autorizado. Solo después del resumen confirmado envía el contrato completo. No presume un número de bolsas ni genera un pedido de ejemplo como si fuera real.

Debe probarse una solicitud completa, una ambigua, un reenvío, solicitudes concurrentes, cliente bloqueado, vencimiento y fallo de notificación después del registro. El indicador principal del razonamiento es extracción correcta y aclaración útil; el de ejecución es registro único sin campos inventados.


---

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


---

# P3. Analizar observaciones de calidad y recomendar tratamiento

**Diagrama:** `bpmn/04-to-be-calidad.bpmn`. **Proceso:** `Process_P3`. **Especialista:** agente de calidad. **Responsable humano:** personal de planta y control de calidad.

## Descripción textual del TO BE

El proceso comienza cuando planta o control de calidad detecta prendas observadas. El operario realiza la inspección física y registra hallazgos concretos, referencias a la guía y evidencia disponible. Las fotografías pueden incorporarse si el personal dispone de ellas y existe un procedimiento de captura; no se supone que ya haya cámaras o un modelo de visión desplegado.

El sistema recupera guía, historial de tratamiento y procedimientos aprobados vigentes. El agente contrasta esas fuentes con la descripción de planta, diferencia hechos de hipótesis y propone una disposición: verificar más información, liberar un lote físicamente conforme, reprocesar según un procedimiento autorizado o abrir una incidencia por daño, pérdida o riesgo.

Si la evidencia es insuficiente, el personal completa los datos o descarta la evaluación automática. El piloto admite una solicitud adicional antes de dejar el caso pendiente de evaluación técnica. El agente no inventa el material de una prenda, la causa de una mancha ni la responsabilidad de la empresa.

La aplicación comprueba que la recomendación cite fuentes vigentes y respete las restricciones conocidas. Control de calidad revisa la propuesta y autoriza la disposición. Si existe verificación física conforme, el sistema registra la liberación. Si se autoriza reproceso, el operario lo ejecuta físicamente según el procedimiento. Después se verifica el resultado. El piloto admite un ciclo de reproceso; una nueva observación abre una incidencia o requiere otra evaluación humana, evitando un bucle automático de tratamientos.

Un daño, pérdida, riesgo o reproceso no conforme abre un expediente para P4 y conserva el lote retenido. La apertura no equivale a reconocer responsabilidad ni a autorizar compensación. El resultado que habilita el empaque es una liberación humana registrada con evidencia.

## Datos y conocimiento necesarios

| Categoría | Contenido requerido |
|---|---|
| Identidad | Pedido, lote y prendas identificables |
| Observación | Quién inspeccionó, fecha, hallazgos y referencias de evidencia |
| Historial | Tratamiento ejecutado, observaciones previas y contador de reprocesos |
| Conocimiento | Procedimientos y criterios de calidad aprobados, con versión/vigencia |
| Resultado agentic | Hipótesis diferenciadas de hechos, disposición propuesta y evidencia |
| Resultado humano | Disposición autorizada, verificación física y responsable |

El AS IS incluye inspección, reproceso y derivación por prendas dañadas o extraviadas. El registro estructurado y la recuperación de procedimientos son mejoras propuestas. Antes del piloto deben obtenerse y aprobarse las fuentes de dominio, ya que el expediente actual no suministra criterios suficientes para recomendar tratamientos reales.

## Por qué se emplea un especialista

Las observaciones en lenguaje natural pueden admitir interpretaciones diferentes y requerir contraste con historial y procedimientos. El especialista aporta recuperación de evidencia y una recomendación explicada; el supervisor coordina el caso y deriva incidencias. Los conteos, las incompatibilidades conocidas y los cambios de estado se aplican en código.

Un lote que no presenta observaciones puede seguir una verificación por reglas y control humano sin invocar al LLM. La especialización se reserva para los casos que necesitan análisis contextual, evitando cargar todo pedido con razonamiento innecesario.

## Trazabilidad del BPMN

| Elementos | Función | Código futuro |
|---|---|---|
| `P3_Inspeccion` | Observación física real | Formulario de calidad |
| `P3_Evidencia` | Fuentes vigentes y permitidas | `KnowledgeRepository`, `EvidenceRepository` |
| `P3_Analizar` | Propuesta con citas | `agents/quality.py` |
| `P3_Suficiente`, `P3_Completar`, `P3_Nueva` | Pedir evidencia y limitar el retorno | Grafo y política |
| `P3_Validar`, `P3_Revisar`, `P3_Decision` | Restricciones y autorización | Dominio y panel de calidad |
| `P3_Reproceso`, `P3_Verificar`, `P3_Conforme` | Operación y comprobación físicas | Eventos registrados por operario |
| `P3_Registrar` | Disposición conforme persistida | Ejecutor determinista |
| `P3_Incidencia` | Expediente enlazado a P4 | Evento `QualityIncidentOpened` |

## Aceptación y límites

Ejemplo sintético: una mancha persiste después del lavado y la descripción del material no está documentada. El agente identifica el dato faltante y cita el procedimiento disponible; no prescribe una sustancia ni una dosis. Si el operario verifica el material y aprueba un reproceso compatible, se ejecuta y se documenta el resultado. Si no se puede verificar, se retiene el lote y se deriva.

Pruebas mínimas: evidencia insuficiente, procedimiento vencido, hipótesis contradictorias, recomendación fuera de restricciones, reproceso autorizado, reproceso persistente y pérdida de prenda. Ninguna tarea del agente acciona máquinas. Ningún resultado textual reemplaza la inspección ni libera automáticamente un lote observado.


---

# P4. Investigar y resolver reclamos e incidencias

**Diagrama:** `bpmn/05-to-be-reclamos-incidencias.bpmn`. **Proceso:** `Process_P4`. **Especialista:** agente de incidencias. **Responsable humano:** asesor y administración. **Inicio del piloto:** supervisado, después de habilitar el registro de expedientes.

## Descripción textual del TO BE

El proceso comienza con un reclamo del cliente o una incidencia registrada por planta. La aplicación abre un expediente vinculado al pedido y consolida las guías, mensajes, inspecciones e historial permitidos. El agente reconstruye una cronología de hechos y expone las discrepancias, sin dar por probado lo que solo aparece como una afirmación de una de las partes.

Si falta evidencia concreta, se solicita al interlocutor o al personal responsable. El piloto admite una solicitud adicional y una espera de 24 horas. Si el dato no llega o no se puede sustentar una resolución, el expediente permanece abierto con responsable y siguiente acción. No se inventa una guía, una foto ni una conformidad para completar el flujo.

Con evidencia suficiente, el agente formula alternativas sustentadas en contrato, política e historial: verificación física adicional, búsqueda de una prenda, un reproceso autorizado, coordinación de entrega o propuesta de compensación dentro de las competencias documentadas. La aplicación valida las fuentes, los costos obtenidos del sistema y los límites. Administración aprueba, corrige o rechaza la propuesta. Toda compensación y toda atribución de responsabilidad requieren decisión humana.

La solución autorizada se comunica al cliente. Se recoge su aceptación o una contrapropuesta; una contrapropuesta devuelve el caso a evaluación y aprobación una vez en el piloto. El silencio, el rechazo, la falta de acuerdo o el límite agotado dejan el expediente pendiente, sin considerarlo conforme.

La aplicación ejecuta el plan aprobado mediante servicios o crea las órdenes humanas/físicas correspondientes. Si un servicio falla, el caso queda pendiente y no se repite la compensación sin comprobar el comando. El responsable verifica el cumplimiento de la solución y documenta la conformidad o el criterio de cierre aprobado. El sistema cierra el reclamo únicamente cuando esa evidencia existe. Si la solución aún no se ha cumplido, el expediente continúa abierto.

## Entradas y salidas

| Elemento | Requisito |
|---|---|
| Reclamo | Tipo, relato, fecha, cliente/pedido y canal verificado |
| Expediente | Evidencias identificadas, origen, vigencia y permisos |
| Conocimiento | Contrato y política de atención aprobados |
| Propuesta | Hechos, discrepancias, alternativas, fuentes y acciones que requieren autorización |
| Autorización | Usuario competente, propuesta/hash y versiones |
| Resultado | Solución ejecutada, evidencia de cumplimiento y estado de cierre o pendiente |

La matriz del Laboratorio 01 calificó reclamos como no viables para RPA por falta de datos. Por eso P4 no se presenta como una automatización autónoma lista para operar. Primero se registra un expediente mínimo y se usan casos sintéticos o anonimizados para evaluar las recomendaciones bajo revisión humana. No se estima rentabilidad ni precisión sin esa evidencia.

## Decisiones y automatización

La investigación de relatos contradictorios, el contraste de documentos y la explicación de alternativas requieren interpretación. El especialista conoce el expediente y las políticas, mientras el supervisor coordina P3 cuando hace falta inspección o P2 cuando la solución requiere recojo/entrega. Las autorizaciones y efectos permanecen separados.

Una alternativa de compensación debe usar un monto recuperado/calculado por un servicio autorizado. No se asigna un monto de indemnización dentro del prompt. Una propuesta «compensar» es una solicitud de revisión y nunca una transferencia, descuento o nota emitida.

## Trazabilidad del BPMN

| Elementos | Función | Código futuro |
|---|---|---|
| `P4_Expediente` | Consolidar fuentes permitidas | Repositorio de evidencia/casos |
| `P4_Analizar`, `P4_Suficiente` | Hechos, hipótesis y suficiencia | `agents/incidents.py` y validación |
| `P4_Solicitar`, `P4_Respuesta`, `P4_Timeout` | Aportación de evidencia | Canal, checkpoint y worker |
| `P4_Alternativas`, `P4_Politica` | Propuesta y restricciones verificadas | Agente y dominio |
| `P4_Humano`, `P4_Aprobada` | Autorización administrativa | API de aprobación |
| `P4_Proponer`, `P4_Elegir`, `P4_Acepta` | Acuerdo con el cliente | Grafo de negociación |
| `P4_Ejecutar`, `P4_Error` | Plan autorizado o resultado incierto | Ejecutor y ledger |
| `P4_Cumplimiento`, `P4_Cumple`, `P4_Cerrar` | Verificar y cerrar con evidencia | Revisión humana y servicio de cierre |
| `P4_Pendiente` | Mantener expediente y próxima acción | Repositorio y cola de atención |

## Ejemplo y aceptación

Ejemplo sintético: el cliente afirma que falta una prenda, mientras la guía de recepción tiene un conteo diferente. El agente reconstruye ambas versiones, identifica la evidencia que falta y propone búsqueda/verificación. Administración decide la solución; si implica entrega, se abre P2. El cierre espera evidencia de cumplimiento y no usa la respuesta del LLM como comprobante.

Pruebas mínimas: reclamo con y sin evidencia, documentos contradictorios, solicitud de compensación no autorizada, contrapropuesta, silencio del cliente, ejecución incierta y falta de cumplimiento. Deben comprobarse también el acceso entre clientes y la apertura de un reclamo después de la ventana documental del pedido.


---

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


---

# RPA determinista existente: referencia de integración

**Diagrama:** `bpmn/07-rpa-determinista-referencia.bpmn`. **Origen:** copia íntegra del TO BE de recojo entregado por el equipo. **Estado:** referencia previa, no flujo corregido ni vuelto a ejecutar en esta entrega.

El flujo valida el contrato, normaliza la solicitud, comprueba duplicados, consulta el padrón y decide por reglas si el cliente está habilitado. Asigna el turno normal, registra el pedido y comunica el resultado. Los datos inválidos y fallos técnicos se envían a la cola de fallidos; los clientes bloqueados se derivan a administración.

La arquitectura nueva reutiliza su capacidad de registro detrás de `PickupRegistrationPort`. El agente de atención prepara y confirma los datos. El servicio sigue controlando el contrato y la escritura. El nuevo grafo no llama al coordinador n8n con LLM para volver a ejecutar otro circuito conversacional.

## Compatibilidad que debe probarse

1. Mantener los siete obligatorios y los enumerados del contrato.
2. Conservar los estados de salida y sus identificadores reales.
3. Comprobar idempotencia con solicitudes consecutivas y concurrentes; buscar antes de append no demuestra atomicidad.
4. Separar resultado del registro y resultado del envío. En los insumos, el subflujo registra y devuelve estado, mientras el principal y el coordinador tienen rutas de notificación diferentes. Elegir una sola autoridad de envío al integrar.
5. Diferenciar la carga del pedido de los seis campos de la cola de fallidos; no describir el pedido como un contrato de seis datos.
6. Verificar la hora Lima, los turnos y el uso de un calendario hábil cuando la regla lo requiera.

El original es importable, pero puede contener estados administrativos que finalizan después de «decidir» sin modelar el regreso del caso autorizado al registro. P1 detalla ese retorno y sus condiciones; la nueva aplicación debe implementarlas expresamente.

Esta copia sirve para comparar y construir el adaptador. No certifica que credenciales, hojas, URLs o IDs de workflow del export n8n estén configurados actualmente. Los registros de pruebas del Excel se consideran evidencia documental del equipo, no pruebas repetidas por esta entrega.
