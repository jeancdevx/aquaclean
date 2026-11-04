# P3 · Calidad al detalle · Laboratorio sintético V2

Analizar orden QUALITY_PENDING con procesamiento terminado declarado por operador e inspección humana documentada. Recuperar recepción, observaciones y procedimientos aprobados vigentes, filtrados por organización/cliente/roles. Una foto no certifica material ni inspección. No indicar químicos, dosis o parámetros de máquina desde IA.

Liberación exige inspección y conformidad física humanas, procedimiento vigente y aprobación HITL. Cambia orden a READY y crea un aviso único por outbox a bandeja local. No afirmar correo o WhatsApp enviados. La IA solo recomienda y no lava, inspecciona ni libera físicamente.

Un reproceso requiere inspección, procedimiento y autorización previa; máximo un ciclo de laboratorio. La orden queda REPROCESS_PENDING hasta ejecución física declarada y vuelve a QUALITY_PENDING para verificación nueva. Daño, pérdida o persistencia abre caso P4 separado, vinculado a la misma orden y al caso P3. El caso de calidad no se convierte silenciosamente en reclamo.

Alerta de procesamiento a 24 h es parámetro de laboratorio no interruptor. No cambia IN_PROCESSING, no suspende máquinas ni acredita fin de producción. La ventana corporativa 48 h no se aplica como política al detalle ni como conformidad por silencio.
