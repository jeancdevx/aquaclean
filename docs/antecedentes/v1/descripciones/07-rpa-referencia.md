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
