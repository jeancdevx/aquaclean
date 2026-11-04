# Descripciones de procesos TO BE al detalle

Versión 2.0 vigente. Los modelos adjuntos son BPMN 2.0 descriptivos para bpmn.io, no workflows ejecutados por LangGraph. Los agentes interpretan y proponen; las personas verifican prendas y las reglas deterministas controlan los efectos.

## Integral Gestionar el pedido de lavandería al detalle

El cliente solicita el servicio en mostrador o mediante un recojo previo. En mostrador, el operador recibe las prendas. Si el canal es remoto, Atención interpreta y confirma una solicitud logística previa P1R; Logística P2 coordina el recojo y el operador registra si se realizó. Una solicitud remota no crea anticipadamente una orden de servicio. Un recojo no realizado queda pendiente para reprogramación explícita.

Una vez recibidas las prendas, P1 identifica o registra al cliente, captura detalle, cantidades, peso cuando corresponda, servicios y observaciones. El sistema calcula importes y fecha prometida con reglas configuradas; una persona revisa y confirma. Solo entonces el ejecutor abre una orden de servicio e identifica el adelanto declarado y el saldo.

El personal inicia y completa lavado, secado y planchado, dejando evidencia de sus hitos. La IA no ejecuta ese trabajo. El control de calidad P3 analiza evidencia y procedimientos, propone y espera autorización. Un reproceso se realiza y verifica físicamente; una incidencia abre un expediente P4 separado y vinculado. La orden solo pasa a lista cuando hay liberación de calidad válida.

El cambio a lista genera un aviso trazable en bandeja local mediante outbox. Para retiro en mostrador se registra entrega; para domicilio P2 coordina la entrega de la orden liberada. Se registra receptor, recepción y conformidad. El sistema calcula el saldo, el operador registra el cobro declarado y el sistema emite un comprobante de demostración. El cierre requiere entrega, conformidad explícita, saldo cero y ausencia de incidencias bloqueantes. Las excepciones quedan pendientes, sin aparentar un cierre satisfactorio.

El modelo incorpora una alerta no interruptora de procesamiento de 24 horas como parámetro propuesto de laboratorio. No detiene la operación física ni implica conformidad. El seguimiento postventa de 48 horas del antecedente corporativo queda fuera de la condición normal de cierre al detalle; si se conserva, se implementa aparte sin inferir aceptación por silencio.

## P1R Interpretar y registrar solicitud previa de recojo

Este proceso opcional empieza con un mensaje, imagen, PDF o audio que solicita recoger prendas. Atención extrae únicamente datos sustentados y pregunta por contacto, dirección, fecha/turno y volumen faltantes. Puede trabajar con un cliente nuevo sin inventar un código. Las observaciones de percepción son editables.

El sistema presenta el resumen y la persona confirma o corrige. Los servicios deterministas validan datos y registran una solicitud logística con identificador propio e idempotencia; no crean una orden de servicio. Los datos incompletos, el rechazo o el vencimiento dejan un pendiente explícito. P2 recibe la solicitud para coordinar recojo. Tras la recepción efectiva, P1 abre la orden con el detalle observado.

El razonamiento no determinista reside en interpretar mensajes, resolver referencias y decidir qué aclarar. Validación, asignación de IDs y registro son deterministas.

## P1 Asistir recepción y registrar orden de servicio

El proceso comienza con prendas realmente recibidas en mostrador o procedentes de un recojo. El operador verifica el cliente o registra sus datos mínimos. Inspecciona y cuenta las prendas, registra peso cuando aplica, observaciones visibles y servicios requeridos. Atención ayuda a estructurar la información y detectar faltantes; no declara inspecciones físicas inexistentes ni deduce un peso exacto de una fotografía.

Una herramienta calcula la cotización con tarifas sintéticas configuradas y versionadas. La fecha prometida procede de reglas del servicio. El agente explica el resumen. El operador/cliente confirma los datos y el alcance de la prestación mediante la interacción de demostración. Si se corrige, se recalcula y solicita una confirmación nueva.

El ejecutor valida permisos, evidencia y versiones y crea atómicamente orden y líneas con número asignado por backend. Registra el adelanto declarado, si existe, con operación idempotente y saldo calculado; emite constancia de demostración. Un reintento devuelve el mismo resultado. Un fallo conserva la recepción pendiente sin simular un pedido creado.

La salida es una orden RECEIVED con prendas, servicios, importes y fecha prometida. Este proceso sustituye como entrada principal el registro de siete campos corporativos de V1; ese contrato se conserva solo como legado de solicitud logística.

## P2 Coordinar recojo y entrega

P2 recibe una solicitud logística para recojo o una orden liberada para entrega. No exige una orden inexistente para recoger prendas. La referencia objetivo y el tipo de operación son explícitos. El servicio calcula alternativas futuras con capacidad y restricciones vigentes. Logística interpreta preferencias y explica opciones reales, sin inventar cupos.

La persona elige o plantea una contrapropuesta. Los cambios fuera de las reglas requieren revisión humana. Una aprobación no crea capacidad: antes de reservar se revalidan versiones y cupos bajo transacción. El sistema persiste reserva y aviso local; cancelación/reprogramación conserva trazabilidad y libera cupos cuando corresponde. No realiza físicamente recojo o entrega.

Si no hay alternativa o acuerdo, el proceso queda pendiente con responsable. El despacho de entrega no procede antes de liberar calidad. Si se opta en el futuro por agenda provisional, su naturaleza y sus restricciones deben aparecer tanto en el BPMN como en el código.

## P3 Analizar calidad y autorizar disposición

Empieza con una orden cuyo procesamiento físico terminó y cuya inspección fue registrada por personal autorizado. Calidad recupera la recepción, evidencias e historial junto con procedimientos vigentes mediante RAG. El agente distingue hallazgos, incertidumbres y recomendaciones. Sin evidencia suficiente solicita completar o deja pendiente.

El responsable de calidad revisa la propuesta. Puede liberar solo con verificación física conforme; autorizar un reproceso dentro del límite configurado; o abrir incidencia P4. El reproceso se declara y verifica físicamente antes de una nueva liberación. El sistema registra la disposición con idempotencia y versiones. Abrir incidencia crea un expediente separado vinculado a la orden; no acredita solución ni cierre.

La salida favorable es READY y desencadena el aviso de prendas listas. La decisión sensible conserva HITL y nunca se sustituye por un umbral de confianza del LLM.

## P4 Investigar y resolver incidencias con Deep Agents

Empieza con una observación o reclamo vinculado a una orden. Un Deep Agent de investigación descompone el análisis en tareas y delega a subagentes de Evidencias y Procedimientos. Cada uno recibe el contexto necesario y herramientas de lectura limitadas. El contexto de trabajo permanece acotado al caso; ninguna instrucción de un adjunto puede cambiar permisos o políticas.

El harness reconstruye hechos, registra contradicciones, recupera conocimiento aprobado y propone alternativas. Las fuentes públicas externas son contexto, no reglas autorizantes. Se normaliza el resultado al contrato de propuesta y el ejecutor valida fuentes, permisos y versiones. Una persona aprueba, corrige o rechaza el plan mediante HITL.

El plan aprobado queda abierto mientras falta aceptación, cumplimiento o conformidad. Las acciones físicas y comerciales las realizan responsables humanos y se documentan con evidencia posterior. El cierre exige esas evidencias y otra decisión válida cuando corresponda. No hay compensación monetaria ejecutada por el modelo. El silencio o vencimiento deja pendiente.

Este uso de Deep Agents es un requisito de V2, no una descripción de la implementación auditada, que todavía no incorpora el SDK.

## Orquestación técnica

La API crea el caso, determina identidad demo del backend y conserva el run. LangGraph carga estado, procesa medios y solicita al supervisor una ruta compatible con intención, fase y permisos. Una intención ambigua provoca aclaración explícita. El especialista obtiene herramientas/conocimiento autorizado y devuelve una propuesta estructurada mediante cadenas LCEL usadas en runtime. P4 invoca además el harness Deep Agents.

El sistema valida evidencia, contrato, estados y política. Una lectura o aclaración puede responder sin escritura. Las acciones de negocio sensibles preparan aprobación y pausan con `interrupt()` y checkpoint PostgreSQL. La decisión validada se reanuda con `Command(resume=...)` en el mismo hilo. El ejecutor vuelve a validar y aplica transacción, ledger y outbox. Los eventos locales persistidos y el journal de Deep Agents permiten correlacionar ejecución, herramientas y revisión. La interfaz muestra actividad y justificación pública resumida. LangSmith aporta instrumentación externa opcional cuando se configura y verifica; no hay ejecución externa acreditada en este entorno.

La estructura detallada del grafo final se exportará del código corregido. El BPMN técnico representa responsabilidades y controles objetivo; no obliga a que cada tarea BPMN sea exactamente un nodo LangGraph.
