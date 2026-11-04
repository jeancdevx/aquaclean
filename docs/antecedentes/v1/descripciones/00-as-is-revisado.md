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
