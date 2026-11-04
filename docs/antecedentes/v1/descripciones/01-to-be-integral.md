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
