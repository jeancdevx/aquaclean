def describe_result(result: dict) -> str:
    status = result["status"]
    if status == "registered_notification_pending":
        return f"Pedido {result['number']} registrado. La confirmación está preparada para la bandeja local."
    if status == "scheduled":
        shift = "mañana" if result["shift"] == "manana" else "tarde"
        return f"Agenda reservada para el {result['day']}, turno {shift}. El operador debe documentar el recojo o entrega física."
    return {
        "cancelled": "Solicitud cancelada. Las reservas existentes se liberaron.",
        "released": "Lote liberado por decisión humana de calidad, con inspección y conformidad registradas.",
        "closed": "Reclamo cerrado con aprobación y evidencia humana de aceptación, cumplimiento y conformidad.",
        "awaiting_physical_reprocess": "Reproceso autorizado. El lote espera la ejecución y verificación físicas del operador.",
        "incident_open": "Incidencia abierta. El lote permanece retenido y requiere seguimiento.",
        "awaiting_customer_acceptance_and_fulfillment": "Plan de solución autorizado. El reclamo sigue abierto hasta registrar aceptación, cumplimiento y conformidad.",
    }.get(status, "Resultado guardado en el expediente.")
