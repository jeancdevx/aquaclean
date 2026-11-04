# Corrección: enviar «Programar un recojo» sin pedido previo

**16/10/2026, America/Lima.** El reporte del usuario era correcto: existía un error en la aplicación. La guía anterior probaba que la sugerencia rellenaba el compositor sin efectos, pero no enviaba ese texto incompleto. La prueba de P1 empezaba con los siete campos completos, por lo que no detectó esta entrada.

## Reproducción y causa

1. Abrir una conversación nueva.
2. Pulsar **Programar un recojo**.
3. Conservar `Quiero programar un recojo. Ayúdame a revisar los datos necesarios.`.
4. Seleccionar `CLI-0001` y enviar.

Antes de corregir se reprodujo con Gemini real: caso QA `778bd0ac-0b65-435e-9024-e37f197ad032`, ejecución fallida y respuesta «Logística necesita un pedido registrado en este caso». El modelo clasificaba «programar» como P2, y el supervisor convertía la ausencia de pedido en un error. El mensaje aparecía en el historial persistido y también en la alerta de error.

## Comportamiento corregido

- Una solicitud nueva de recojo comienza en Atención (P1), que pide los campos faltantes. El cliente seleccionado ya aporta `cliente_id`.
- El mensaje de sistema distingue captura de solicitud y coordinación logística. El backend aplica además la precondición: P2 sin pedido vinculado deriva a P1, con validación del permiso de Atención. El evento conserva la ruta propuesta y la efectiva.
- No se crea ni reserva nada al pedir los datos. Completar los campos en la misma conversación prepara una tarjeta; confirmar crea un solo pedido.
- Si se pide reprogramar un pedido existente sin vínculo, se indica abrir su conversación o **Actividad → Caso → Vincular pedido verificado**. No se crea un sustituto ni se elige automáticamente un pedido del cliente.
- No se cambia la exigencia de un pedido real para ejecutar logística, ni sus controles de capacidad, selección y aprobación.

## Evidencia

El caso QA que había fallado se reintentó con el mismo texto y un nuevo ID de ejecución: terminó correctamente en `P1 / awaiting_information`, solicitando nombre, correo, fecha, turno, tipo de ropa y bolsas; cero pedidos/aprobaciones. También se comprobó por HTTP real la orientación para una entrega existente sin vínculo. Ver [`pickup-routing-regression.json`](pickup-routing-regression.json).

La prueba Chromium se amplió para ejecutar exactamente los pasos reportados, comprobar la aclaración y ausencia de errores/efectos, recargar, completar los datos, confirmar y comprobar un pedido persistido. Ver [`pickup-suggestion-real.json`](pickup-suggestion-real.json), [captura de la aclaración](pickup-suggestion-fields.png) y [`tests-browser.xml`](tests-browser.xml).

Dos pruebas parametrizadas fuerzan que el clasificador proponga P1 o P2: ambas terminan en Atención y después permiten registrar con confirmación. Otra prueba comprueba que la derivación no concede permisos a un actor que solo tiene logística. El flujo P2 con pedido registrado sigue cubierto por su prueba de reserva.

Durante la verificación hubo una llamada externa fallida al supervisor; un intento posterior completó el flujo con Gemini real. La aplicación conserva el caso ante un error del proveedor, sin fallback. También se corrigió la preparación de la prueba de outbox para drenar avisos acumulados exclusivamente en `_test`: ahora comprueba que su propio aviso registra el intento fallido antes de reintentar. Los resultados finales se recogen en [`PRODUCTO_V1.md`](PRODUCTO_V1.md); no se consideran pasados los intentos anteriores fallidos.

## Repetir la prueba manual

Recargar http://localhost:8000 y repetir los cuatro pasos iniciales. Debe preguntar los datos faltantes. Responder, usando una fecha futura dentro del límite piloto:

> Solicitante Operador Demo; correo demo@example.invalid; fecha_recojo FECHA_MAÑANA; turno manana; tipo_ropa toallas; bolsas 3. Prepara el borrador para confirmar.

Debe mostrar la tarjeta de siete campos y seguir sin pedido hasta pulsar **Confirmar**. Se puede continuar una conversación anterior al error después de recargar y enviar de nuevo; los mensajes de error antiguos se conservan como historial, sin indicar que la ejecución nueva haya fallado. No es necesario borrar datos ni volúmenes.
