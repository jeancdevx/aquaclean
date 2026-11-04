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
