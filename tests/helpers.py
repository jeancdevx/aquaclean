from uuid import uuid4


async def approve(
    rt, case_id, approval, selection=None, action="approve", commercial_exception=None
):
    decision_id = str(uuid4())
    decision = {
        "action": action,
        "proposal_hash": approval["proposal_hash"],
        "case_version": approval["case_version"],
        "selection": selection or {},
    }
    if commercial_exception is not None:
        decision["commercial_exception"] = commercial_exception
    await rt.repo.resolve_approval(
        rt.actor, str(case_id), str(approval["id"]), decision_id, decision
    )
    return decision_id, decision


async def stage(rt, case_id, proposal, process="P1", kind="confirmation", role="attention"):
    return await rt.repo.stage_proposal(
        rt.actor, str(case_id), str(uuid4()), process, proposal, role, kind
    )


def fields(rt, client_id="CLI-0001"):
    return {
        "cliente_id": client_id,
        "solicitante": "Operador sintético",
        "correo": "demo@example.invalid",
        "fecha_recojo": str(rt.clock.now().date()),
        "turno": "manana",
        "tipo_ropa": "manteleria",
        "bolsas": 3,
    }


async def registered(rt, case_id, client_id="CLI-0001"):
    proposal = {
        "action": "register",
        "fields": fields(rt, client_id),
        "response": "Registro sintético",
        "rationale_summary": "Fixture confirmado",
        "sources": [],
    }
    approval = await stage(rt, case_id, proposal)
    await approve(rt, case_id, approval)
    result = await rt.executor.execute(
        rt.actor, str(case_id), str(uuid4()), str(approval["id"]), {}
    )
    return result
