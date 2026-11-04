"""Read-only evidence/procedure checks for an incident's single authorized order."""

import json

from aquaclean.domain.errors import DomainError


async def incident_evidence(repo, actor, case_id, max_chars):
    actor.require("admin")
    case = await repo.case(actor, case_id)
    if not case["order_id"]:
        raise DomainError("Investigación requiere orden vinculada.", "order_required", 409)
    order = await repo.order(actor, str(case["order_id"]))
    snapshot = await repo.snapshot(actor, case_id)
    events = await repo.db.all(
        "SELECT e.id,e.case_id,e.kind,e.note,e.created_at FROM app.operator_events e JOIN app.cases c ON c.id=e.case_id WHERE c.organization_id=%s AND c.order_id=%s ORDER BY e.created_at DESC LIMIT 100",
        (actor.organization_id, order["id"]),
    )
    attachments = await repo.db.all(
        "SELECT a.id,a.case_id,a.filename,a.hash,a.observation,a.perception_status FROM app.attachments a JOIN app.cases c ON c.id=a.case_id WHERE c.organization_id=%s AND c.order_id=%s ORDER BY a.created_at DESC LIMIT 20",
        (actor.organization_id, order["id"]),
    )
    # These are case-scoped observations and original hashes; no unrelated customer or raw file is exposed.
    payload = {
        "case": case,
        "order": order,
        "events": events,
        "attachments": attachments,
        "retail": snapshot["retail"],
        "command_history": snapshot["command_history"],
        "allowed_evidence_refs": [str(e["id"]) for e in events + attachments],
    }
    encoded = json.dumps(payload, default=str, ensure_ascii=False)
    if len(encoded) > max_chars:
        raise DomainError(
            "Evidencia excede contexto permitido; acote el expediente.", "context_limit", 409
        )
    return json.loads(encoded)
