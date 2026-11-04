import re
from datetime import date, timedelta
from typing import Any

from aquaclean.domain.entities import Clock
from aquaclean.domain.errors import DomainError

REQUIRED = ("cliente_id", "solicitante", "correo", "fecha_recojo", "turno", "tipo_ropa", "bolsas")
ROLES = {"P1": "attention", "P2": "logistics", "P3": "quality", "P4": "admin"}
ACTIONS = {
    "P1": frozenset({"register", "receive", "request_pickup", "cancel", "clarify", "answer"}),
    "P2": frozenset({"reserve", "cancel", "clarify", "answer"}),
    "P3": frozenset({"release", "reprocess", "open_incident", "clarify", "answer"}),
    "P4": frozenset({"resolve_incident", "close_incident", "clarify", "answer"}),
}


def validate_action(process: str, action: str) -> None:
    if process not in ACTIONS or action not in ACTIONS[process]:
        raise DomainError("Acción fuera del contrato del especialista.", "action_forbidden", 403)


def validate_commercial_exception(value: Any) -> None:
    if (
        not isinstance(value, dict)
        or set(value) != {"acknowledged", "reason"}
        or value.get("acknowledged") is not True
        or not isinstance(value.get("reason"), str)
        or not 10 <= len(value["reason"].strip()) <= 1000
    ):
        raise DomainError(
            "Cliente bloqueado: la excepción requiere autorización administrativa explícita y un motivo de 10 a 1000 caracteres. El texto del chat no autoriza la excepción.",
            "commercial_authorization_required",
            409,
        )


def validate_request(
    fields: dict[str, Any], clock: Clock, max_bags: int = 40, max_pickup_days: int = 30
) -> dict[str, Any]:
    missing = [key for key in REQUIRED if fields.get(key) in (None, "")]
    if missing:
        raise DomainError("Faltan campos: " + ", ".join(missing))
    if not re.fullmatch(r"CLI-\d{4}", str(fields["cliente_id"])):
        raise DomainError("Código de cliente inválido.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", str(fields["correo"])):
        raise DomainError("Correo inválido.")
    try:
        day = date.fromisoformat(str(fields["fecha_recojo"]))
    except ValueError as exc:
        raise DomainError("Confirme una fecha exacta AAAA-MM-DD.") from exc
    if not clock.now().date() <= day <= clock.now().date() + timedelta(days=max_pickup_days):
        raise DomainError(
            f"La fecha debe estar entre hoy Lima y los próximos {max_pickup_days} días (límite piloto)."
        )
    if fields["turno"] not in {"manana", "tarde"}:
        raise DomainError("Turno inválido.")
    if fields["tipo_ropa"] not in {"manteleria", "toallas", "uniformes", "mixto"}:
        raise DomainError("Tipo de ropa inválido.")
    bags = fields["bolsas"]
    if isinstance(bags, bool) or not isinstance(bags, int) or not 1 <= bags <= max_bags:
        raise DomainError(f"Cantidad de bolsas entre 1 y {max_bags} (límite piloto).")
    if not 2 <= len(str(fields["solicitante"]).strip()) <= 120:
        raise DomainError("Solicitante inválido.")
    return {
        k: fields[k]
        for k in (*REQUIRED, "direccion_recojo", "observaciones", "canal")
        if k in fields
    }


def validate_fulfillment(process: str, events: list[dict[str, Any]]) -> None:
    kinds = {event["kind"] for event in events}
    needed = (
        {"inspection", "conformity"}
        if process == "P3"
        else {"customer_acceptance", "fulfillment", "conformity"}
    )
    if not needed <= kinds:
        raise DomainError(
            "Falta evidencia humana: " + ", ".join(sorted(needed - kinds)),
            "insufficient_evidence",
            409,
        )
