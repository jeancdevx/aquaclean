> Antecedente V1 corporativo, superado para el alcance seleccionado. Versión vigente: [descripciones V2](../DESCRIPCIONES_PROCESOS.md). Original conservado en [antecedentes](../antecedentes/v1/descripciones/02-solicitudes.md).

# P1. Interpretar y registrar solicitudes de recojo

**Diagrama:** `bpmn/02-to-be-solicitudes.bpmn`. **Proceso:** `Process_P1`. **Especialista:** agente de atención. **Reutilización:** servicio determinista `registrar_recojo` del RPA existente.

## Descripción textual del TO BE

El proceso comienza cuando un cliente corporativo envía una solicitud de recojo en lenguaje natural por un canal habilitado. La aplicación identifica al remitente y crea o recupera el caso. El agente de atención interpreta la intención, extrae únicamente información sustentada en el mensaje y consulta el padrón a través de una herramienta autorizada. Su función es transformar una conversación incompleta en una solicitud explícita y confirmada.

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
