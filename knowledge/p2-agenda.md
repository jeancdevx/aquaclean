# P2 · Logística al detalle · Laboratorio sintético V2

Para recojo coordinar una PickupRequest REQUESTED o SCHEDULED, por pickup_request_id; no exigir orden. Para entrega coordinar ServiceOrder READY o DELIVERY_PENDING por service_order_id, con liberación humana de calidad. El estado logístico no reemplaza los hitos del servicio. Una solicitud previa de recojo no abre orden.

Las alternativas vienen exclusivamente de slots futuros, capacidad y versión persistidas. La selección humana es explícita. Revalidar cupo, ventana, alcance y versión bajo transacción. Una aprobación no crea capacidad. Reprogramar libera el cupo anterior. Si no hay alternativas, dejar pendiente sin prometer ni inventar.

Una reserva no acredita transporte. El operador declara recojo o entrega efectiva con evidencia. Entrega registra receptor y conformidad explícita. Avisos solo en bandeja local mediante outbox; no existe envío real por correo o WhatsApp.
