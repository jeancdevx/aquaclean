# Contratos vigentes V2

Especificación: [plan](../PLAN_ARQUITECTURA.md), [descripciones](../DESCRIPCIONES_PROCESOS.md) y `docs/bpmn/*-v2.bpmn`. Modelo descriptivo, no motor XML. Entidades y schema en `domain/retail.py`, propuestas en `agents/schemas.py`, API en `interfaces/api/retail_routes.py`.

| Contrato | Entrada y precondición | Efecto determinista |
|---|---|---|
| P1R | PickupInput: cliente existente o nombre/contacto nuevos, dirección, fecha/turno y volumen declarado; confirmación | PickupRequest con ID backend, REQUESTED. Nunca ServiceOrder. |
| P1 | ReceptionInput: received=true, evidencia efectiva, prendas/cantidades/servicios, observaciones, evidencia referenciada del caso; peso humano para kg; cliente mínimo; fecha futura o regla sintética | Después de HITL, cliente si nuevo, ServiceOrder RECEIVED, líneas, cotización, adelanto declarado opcional y constancia demo en una transacción. |
| Tarifa | JSON configurable sintético, versión/hash y PEN; precio y unidad del servicio del catálogo | Decimal, redondeo ROUND_HALF_UP a dos decimales. El modelo no fija precios/saldos. Cambiar tarifa invalida cotización pendiente. |
| P2 | Recojo por pickup_request_id REQUESTED/SCHEDULED; entrega por service_order_id READY/DELIVERY_PENDING; opción calculada, ventana/cupo/versiones | Reserva idempotente y control de capacidad bajo lock. No transporte físico. No reemplaza ciclo de servicio por estado de agenda. Cancelar entrega libera cupo y vuelve DELIVERY_PENDING a READY; no cancela la orden. |
| Producción | Hitos explícitos del operador, permiso y versión esperada | RECEIVED → IN_PROCESSING → QUALITY_PENDING. Evidencia persistida, no tarea física de IA. |
| P3 | QUALITY_PENDING, inspección humana/procedimiento vigente, HITL | release → READY + aviso único; reprocess → REPROCESS_PENDING hasta evento físico y nueva inspección/conformidad (un ciclo por orden, aunque haya varios casos); open_incident → caso P4 separado vinculado. |
| P4 | Orden vinculada; contexto acotado; planificación y ambas delegaciones SDK; fuentes y evidencia verificadas | ResolutionProposal vuelve a HITL. Plan autorizado permanece abierto. Cierre de incidencia exige aceptación/cumplimiento/conformidad posteriores y otra revisión. |
| Cobro declarado | RetailOperation payment: importe positivo como cadena decimal, evidencia, rol, versión y command_id estable | PaymentRecord; saldo = total − suma de registros. Sin transferencia bancaria ni facturación fiscal. Reintento devuelve ledger sin duplicación. |
| Entrega | READY/DELIVERY_PENDING, receptor y evidencia estructurada; conformidad explícita o posterior | DELIVERED. Entrega no infiere aceptación por silencio. |
| Cierre comercial | DELIVERED, saldo cero, conformidad, ninguna incidencia bloqueante | Comprobante final demo y CLOSED en la misma transacción; fallo conserva estado anterior. |

Los DTO rechazan campos extra. IDs asignados por backend; referencias a IDs existentes se verifican por organización/cliente/rol. Los medios son evidencia editable, nunca políticas. Las fuentes públicas CPSC no autorizan disposiciones. Las propuestas LLM no ejecutan comandos directamente; ledger, hash, versión, política, selección y permisos se vuelven a comprobar al ejecutar.

La UI `demo_local` reúne roles en actor fijo del backend y no acredita empleados reales. La confirmación demo registra la declaración humana; no autentica al cliente. Correo no obligatorio para recepción nueva. Las tareas físicas y cobros se declaran por formularios y no se simulan desde el modelo.

Alerta no interruptora de procesamiento: parámetro `PROCESSING_ALERT_HOURS=24`, worker independiente, un outbox por orden, sin cambiar IN_PROCESSING. El antecedente corporativo de seguimiento 48 h no se aplica al cierre al detalle; no hay seguimiento opcional implementado ni conformidad por silencio.

Legado: app.orders.kind=legacy_v1 mantiene campos, estados y datos V1. No añade prendas/pesos/pagos retrospectivos. `infrastructure/integrations/n8n.py` valida los siete campos corporativos y permite convertirlos a P1R sin webhook/Sheets ni una segunda autoridad de pedidos. Su escritura histórica sigue identificada como legado. Las migraciones son aditivas y no requieren eliminar volúmenes.
