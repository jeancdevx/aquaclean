# P1 y P1R · Recepción al detalle · Laboratorio sintético V2

P1 empieza con recepción efectiva de prendas en mostrador o después de recojo declarado. Permite cliente nuevo con nombre/contacto necesario o cliente existente verificado por operador. El backend asigna códigos, nunca el modelo. Correo no obligatorio. Registrar prenda, cantidad, servicio, observaciones, evidencia y peso humano si el servicio es por kg; no inferir peso ni ausencia de daños de imágenes.

El tarifario synthetic-retail-2.0 configurable usa Decimal y PEN, cotización y versión verificadas. Fecha prometida por regla sintética 48 h o fecha futura declarada; no política empresarial ratificada. Recepción y adelanto declarado esperan confirmación HITL. Constancia y comprobante son de demostración sin validez fiscal. Ningún agente cobra en banco ni factura a SUNAT.

P1R crea PickupRequest con contacto, dirección, fecha/turno y volumen declarado. Es solicitud logística previa, no ServiceOrder. P2 reserva por pickup_request_id sin exigir orden. Solo después de recojo documentado y recepción de prendas P1 abre la orden y sus líneas. Los siete campos corporativos V1 se conservan exclusivamente en adaptador legado.

La orden RECEIVED pasa por IN_PROCESSING, QUALITY_PENDING y liberación READY. Hitos físicos solo declarados por personas. Cierre exige DELIVERED, conformidad explícita, saldo cero, comprobante demo y ninguna incidencia bloqueante. Silencio no equivale a conformidad.
