# Plan alineado de Aqua Clean para la semana 10

Versión 2.0 vigente, 3 de noviembre de 2026. Esta especificación corrige el alcance y añade requisitos académicos. No certifica que el código actual ya los cumpla. Reemplaza como objetivo el alcance corporativo de la especificación 1.2; esta se conserva como antecedente.

## Alcance obligatorio

El proceso principal es **Gestionar el pedido de lavandería al detalle**, seleccionado en la matriz de idoneidad de la semana 1. Empieza con la atención al cliente y la recepción efectiva de sus prendas, con canal previo opcional de recojo; termina con prendas entregadas, conformidad documentada, saldo cobrado y comprobante de demostración emitido. La solicitud previa de recojo no abre una orden de servicio antes de recibir las prendas.

El mostrador debe poder iniciar el caso sin pedido existente y sin obligar a programar un recojo. El cliente puede existir o ser nuevo. La IA no inventa un código de cliente: lo asigna el servicio determinista. Los servicios corporativos por contrato quedan como antecedente; no justifican afirmar alineación con la matriz al detalle.

## Catálogo objetivo y agentes

| Modelo | Función | Agente o ejecutor |
|---|---|---|
| Integral | Recepción, procesamiento, calidad, aviso, entrega y cierre del pedido al detalle | Aplicación, operador y subprocesos |
| P1R | Interpretar una solicitud previa de recojo, confirmar contacto/dirección/fecha y registrar la solicitud logística | Especialista Atención P1; no crea orden de servicio |
| P1 | Asistir la recepción de prendas y abrir la orden de servicio con detalle e importes | Especialista Atención P1 y ejecutor determinista |
| P2 | Coordinar recojo de una solicitud o entrega de una orden liberada | Especialista Logística |
| P3 | Analizar observaciones y recomendar una disposición con verificación física humana | Especialista Calidad |
| P4 | Investigar incidencias y proponer solución con Deep Agents, autorización y cumplimiento | Especialista Incidencias con harness y subagentes |
| Orquestación | Percibir, clasificar con fase y permisos, delegar, validar, pausar y ejecutar | Supervisor LangGraph |

P1R es una variante funcional de Atención, no un quinto especialista. Los cálculos, precios, registros, cobros declarados, estados y avisos no necesitan un agente independiente. Se conserva un monolito modular.

## Entidades y contratos mínimos

| Entidad | Datos y reglas |
|---|---|
| Customer | ID asignado por backend, nombre y contacto necesario. No exigir correo a todo cliente si no es necesario para el servicio. Distinguir dato declarado de identidad autenticada. |
| PickupRequest | ID propio, cliente/contacto, dirección, fecha/turno y volumen declarado. No requiere una orden previa. Estados propios de solicitud y recojo. |
| ServiceOrder | ID/número propio, cliente, recepción efectiva, canal/origen, fecha prometida, estado del servicio, versión y moneda. Referencia opcional a PickupRequest. |
| OrderItem | Tipo y cantidad de prendas, peso cuando aplique, servicio solicitado, observaciones de recepción, evidencia y precio calculado. No inferir pesos ni ausencia de daños desde una foto. |
| Tariff y Quote | Tarifario sintético configurable, unidad, vigencia y versión; importes Decimal en PEN, sin flotantes ni precios inventados por el LLM. |
| PaymentRecord | Registro idempotente de cobro declarado por operador: importe, fecha, concepto y evidencia. No ejecuta transferencias ni pasarela. Saldo calculado por el backend. |
| DeliveryEvidence | Fecha, receptor declarado, evidencia de entrega y conformidad explícita. La nota genérica no sustituye todos los campos exigidos. |
| IncidentCase | Caso separado vinculado a la orden; plan autorizado, aceptación, cumplimiento y conformidad posteriores. No reutilizar silenciosamente el caso de calidad si el contrato prescribe separación. |
| DemoReceipt | Comprobante local marcado como demostración. No afirmar emisión fiscal/SUNAT ni cobro bancario real. |

Los siete campos de recojo de V1 son un contrato legado de P1R, no el esquema completo de una orden al detalle. Crear adaptadores de compatibilidad y migraciones aditivas; no renombrar registros históricos y afirmar que contienen prendas o pagos que nunca se registraron.

## Estados y controles del negocio

La coordinación logística y la incidencia deben tener estados propios; no sobrescribir todo el ciclo de servicio con el último nombre de una acción.

| Transición de orden | Evidencia mínima |
|---|---|
| Nueva a RECEIVED | Prendas recibidas realmente, cliente, líneas/servicios, observaciones, cotización determinista y confirmación del operador/cliente registrada según el perfil demo. |
| RECEIVED a IN_PROCESSING | Inicio declarado por operador autorizado. |
| IN_PROCESSING a QUALITY_PENDING | Fin de procesamiento declarado; no lo acredita la IA. |
| QUALITY_PENDING a REPROCESS_PENDING | Inspección, procedimiento y autorización humana de reproceso. |
| QUALITY_PENDING a READY | Inspección y conformidad física, procedimiento vigente y aprobación de calidad. |
| READY a DELIVERY_PENDING | Retiro en mostrador o reserva válida de entrega. El despacho requiere liberación. |
| READY o DELIVERY_PENDING a DELIVERED | Evidencia estructurada de entrega y recepción. |
| DELIVERED a CLOSED | Conformidad explícita, saldo cero, comprobante demo y ausencia de incidencia que bloquee cierre. |

El aviso de prendas listas se genera una vez desde READY mediante outbox/bandeja local; se conserva su estado de entrega y reintento. Responde al problema observado de avisos sin responsable ni trazabilidad. No declarar envío WhatsApp o correo si solo se entrega a una bandeja local.

Un SLA de procesamiento de 24 horas puede mantenerse como parámetro de laboratorio con alerta no interruptora: avisa sin simular fin de procesamiento ni suspender automáticamente la tarea física. La ventana de 48 horas del modelo corporativo no se incorpora como condición histórica del cierre al detalle. Si se conserva como seguimiento postventa opcional, usar un job independiente y no convertir silencio en conformidad. Estos valores no son políticas empresariales ratificadas.

## IA y ecosistema exigidos

1. **LangChain y LCEL:** fábrica de cadenas utilizada por supervisor y especialistas; prompts parametrizados, mensajes, modelo inyectado y salida estructurada. Documentar términos realmente presentes con rutas y funciones. No agregar clases sin uso para aparentar cumplimiento.
2. **LangGraph:** estado tipado y separación del estado del negocio; rutas explícitas para exportación, subgrafos, checkpoint PostgreSQL, límites y recuperación. Exportar el grafo real después de cambiarlo y calcular grados de entrada/salida automáticamente.
3. **HITL:** recepción/confirmación cuando corresponda, excepciones y disposiciones sensibles. `interrupt()` con checkpoint durable; reanudar con `Command(resume=...)` y el mismo hilo. La aprobación se vincula a propuesta, versiones, selección y política. No ejecutar efectos antes de reanudación validada.
4. **Deep Agents SDK:** usar de verdad `create_deep_agent` en P4 con subagentes Evidencias y Procedimientos, herramientas acotadas y salida adaptada a `ResolutionProposal`. Habilitar planificación según la versión instalada; demostrar planificación/delegación. El harness propone y no escribe en el negocio.
5. **LangSmith requerido:** usar el plan gratuito y trazas reales de la aplicación. Consultar ejecuciones existentes primero y reutilizarlas sin nuevas inferencias; si no existen, ejecutar el recorrido mínimo con proveedor real, herramientas, Deep Agents y HITL correlacionado. Exportar IDs/URLs/métricas disponibles y capturar la interfaz autenticada con Playwright. Los logs locales son auxiliares y no sustituyen LangSmith. Ver `LANGSMITH.md`.
6. **Multimodal:** texto, imagen, PDF y audio con validación y percepción reales. Mantener observación editable, fuente, original y hash. La salida multimodal no acredita por sí sola una inspección física.
7. **RAG:** conservar PostgreSQL + pgvector, embeddings reales y búsqueda coseno filtrada. Evaluar recuperación con preguntas de procesos al detalle; actualizar corpus sintético aprobado y reingerir. No mezclar referencias públicas con reglas autorizantes.

Las cuatro responsabilidades del ecosistema son LangChain/LCEL, LangGraph, Deep Agents y LangSmith como observabilidad transversal. LangSmith puede desactivarse para operación local, pero su ejecución real es obligatoria para acreditar este punto de la semana 10. Los logs locales son auxiliares. Esta clasificación del ecosistema es distinta de dominio, aplicación, infraestructura e interfaces.

## Arquitectura de software

Conservar Python/FastAPI, el proveedor inyectado, contratos Pydantic, ejecutor determinista, PostgreSQL, outbox y worker. Dominio no importa LangChain, LangGraph, HTTP ni SQL. Aplicación define casos de uso/puertos. Agentes y grafos coordinan propuestas. Infraestructura implementa modelos, persistencia, vectores y medios. Interfaces exponen API y chat.

Añadir módulos por responsabilidad real: recepción, tarifas, registros de cobro, entrega/cierre, cadenas LCEL, investigación Deep Agents, observabilidad y exportación de evidencias. No concentrar todo en `graphs/main.py`, `interfaces/api/app.py` o `persistence/commands.py`; dividirlos gradualmente conservando pruebas y transacciones.

Mantener Astro + React + TypeScript + Tailwind + shadcn/ui. Sin login en `demo_local`, con actor fijo del backend y datos sintéticos. Sugerencias iniciales: recibir prendas en mostrador, solicitar recojo, consultar estado, coordinar entrega e investigar incidencia. Mostrar formularios de confirmación para datos estructurados y actividad real; nunca pensamiento privado. Se conservan Inter, JetBrains Mono, teal #0F766E, slate #0F172A/#F8FAFC y superficies blancas.

Docker Compose conserva API, worker, PostgreSQL/pgvector y migración temporal. No introducir un microservicio por agente ni otra base vectorial sin necesidad. No eliminar volúmenes para migrar. El proveedor de IA y LangSmith son externos: chat local no significa inferencia sin conexión.

## Criterios de aceptación

- Un cliente nuevo puede llegar al mostrador y terminar con una orden persistida sin pedido ni recojo previos.
- WhatsApp puede crear una solicitud de recojo sin orden; la orden solo se crea tras recepción y confirmación de prendas.
- El cálculo de importes/saldo es determinista; dos confirmaciones/reintentos no duplican orden, cobro ni aviso.
- Las transiciones rechazan entrega/despacho sin liberación y cierre con saldo, falta de conformidad o incidencia bloqueante.
- P4 ejecuta el harness, delega a subagentes y devuelve una propuesta sustentada que espera HITL antes del efecto.
- Reiniciar durante HITL conserva el caso, medios y aprobación; reanudar no duplica efectos.
- LCEL aparece en módulos ejecutados; los términos del informe corresponden a esas líneas reales.
- Grafo y grados se exportan del código final. No usar los 12 nodos/16 aristas actuales después de cambiar la topología.
- Una ejecución con proveedor real está verificada en LangSmith: IDs/URLs reales, árbol, modelo, herramientas, Deep Agents y pausa/reanudación del mismo hilo. Usar plan gratuito y trazas existentes cuando estén disponibles. Si no se pudo acceder o capturar, mantener el punto pendiente; logs locales no lo acreditan.
- Pruebas con DB real separada, pruebas fake, evaluación LLM real y evidencia Playwright se reportan por separado.
- El informe académico final se redactará después de recibir las evidencias verificadas, sin presentar esta especificación como código ya implementado.

## Precedencia documental

Codex debe incorporar esta versión en los documentos activos del repositorio, actualizar `AGENTS.md`, descripción de procesos, contratos, corpus, matriz BPMN–código y guías. Conservar V1 en una carpeta de antecedentes o en historial Git y marcarla como superada para el alcance al detalle. Los resultados anteriores conservan fecha y commit; no se reescriben como nuevas pruebas pasadas.
