from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import Field

from aquaclean.domain.entities import Actor
from aquaclean.domain.errors import DomainError
from aquaclean.domain.retail import PickupInput, ReceptionInput, RetailOperation
from aquaclean.infrastructure.persistence.retail_operations import operate
from aquaclean.interfaces.api.auth import actor
from aquaclean.interfaces.api.schemas import APIContract

router = APIRouter(prefix="/api", tags=["Detalle V2"])


class AttentionSubmission(APIContract):
    run_id: UUID
    action: Literal["receive", "request_pickup"]
    reception: ReceptionInput | None = None
    pickup: PickupInput | None = None
    attachment_ids: list[UUID] = Field(default_factory=list, max_length=5)


@router.get("/retail/tariffs")
async def tariffs(request: Request, current: Annotated[Actor, Depends(actor)]):
    current.require("attention")
    return request.app.state.runtime.retail.tariff()


@router.post("/cases/{case_id}/retail-draft", status_code=202)
async def submit(
    case_id: UUID,
    data: AttentionSubmission,
    request: Request,
    current: Annotated[Actor, Depends(actor)],
):
    rt, cid = request.app.state.runtime, str(case_id)
    current.require("attention")
    case = await rt.repo.case(current, cid)
    if await rt.repo.db.one(
        "SELECT id FROM app.approvals WHERE case_id=%s AND status='pending'", (cid,)
    ):
        raise DomainError("Resuelva o corrija la revisión pendiente.", "review_pending", 409)
    key = "reception" if data.action == "receive" else "pickup"
    value = getattr(data, key)
    if value is None or getattr(data, "pickup" if key == "reception" else "reception") is not None:
        raise DomainError("Envíe solo el contrato de la acción seleccionada.")
    draft = {"action": data.action, key: value.model_dump(mode="json", exclude_none=True)}
    # Validate human input and compute preview before spending provider calls. No business effect.
    prepared = await rt.retail.prepare(current, case, dict(draft))
    if key == "reception":
        draft[key] = prepared[key]  # fix the backend-calculated promised date for review/retry
    for aid in data.attachment_ids:
        await rt.media.get(current, cid, str(aid))
    return await rt.repo.enqueue(
        current,
        cid,
        str(data.run_id),
        {
            "text": "Revisar "
            + (
                "recepción efectiva en mostrador"
                if key == "reception"
                else "solicitud previa de recojo"
            )
            + ". Datos sintéticos declarados por operador en formulario.",
            "retail_draft": draft,
            "attachment_ids": [str(a) for a in data.attachment_ids],
        },
    )


@router.post("/cases/{case_id}/retail-operations")
async def milestone(
    case_id: UUID,
    data: RetailOperation,
    request: Request,
    current: Annotated[Actor, Depends(actor)],
):
    return await operate(request.app.state.runtime.repo, current, str(case_id), data)


class NewIncident(APIContract):
    command_id: UUID
    expected_version: int = Field(ge=1)
    description: str = Field(min_length=8, max_length=2000)


@router.post("/cases/{case_id}/incidents", status_code=201)
async def create_incident(
    case_id: UUID, data: NewIncident, request: Request, current: Annotated[Actor, Depends(actor)]
):
    from aquaclean.infrastructure.persistence.incident_cases import open_incident

    return await open_incident(
        request.app.state.runtime.repo,
        current,
        str(case_id),
        str(data.command_id),
        data.expected_version,
        data.description,
    )
