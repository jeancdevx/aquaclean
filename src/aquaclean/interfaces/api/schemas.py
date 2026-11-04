from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class APIContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NewCase(APIContract):
    title: str = Field(default="Nueva conversación", min_length=1, max_length=120)
    client_id: str | None = None


class NewRun(APIContract):
    run_id: UUID
    text: str = Field(default="", max_length=20000)
    attachment_ids: list[UUID] = Field(default_factory=list, max_length=5)


class CommercialExceptionDecision(APIContract):
    acknowledged: bool = Field(strict=True)
    reason: str = Field(min_length=10, max_length=1000)


class ReviewDecision(APIContract):
    decision_id: UUID
    action: Literal["approve", "reject", "correct"]
    proposal_hash: str
    case_version: int
    selection: dict[str, str] = Field(default_factory=dict)
    commercial_exception: CommercialExceptionDecision | None = None


class OperatorEvent(APIContract):
    event_id: UUID
    kind: Literal[
        "inspection",
        "reprocess",
        "customer_acceptance",
        "fulfillment",
        "conformity",
        "observation",
        "pickup",
        "delivery",
    ]
    note: str = Field(min_length=8, max_length=4000)
    attachment_id: UUID | None = None


class ObservationEdit(APIContract):
    observation: str = Field(max_length=12000)
    expected_version: int


class OrderLink(APIContract):
    order_number: str = Field(min_length=4, max_length=80)
    expected_version: int
