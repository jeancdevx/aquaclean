from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RoutingDecision(AgentContract):
    process: Literal["P1", "P2", "P3", "P4"]
    needs_clarification: bool
    rationale_summary: str = Field(max_length=1000)


class RequestFields(AgentContract):
    cliente_id: str | None = None
    solicitante: str | None = None
    correo: str | None = None
    fecha_recojo: str | None = None
    turno: Literal["manana", "tarde"] | None = None
    tipo_ropa: Literal["manteleria", "toallas", "uniformes", "mixto"] | None = None
    bolsas: int | None = None
    direccion_recojo: str | None = None
    observaciones: str | None = None
    canal: str | None = None


class BaseProposal(AgentContract):
    response: str = Field(max_length=6000)
    rationale_summary: str = Field(max_length=1500)
    missing_fields: list[str] = Field(
        description="Datos concretos que faltan o se contradicen. Vacío si solo falta confirmación humana."
    )
    source_ids: list[str] = Field(
        description="chunk_id EXACTOS de context.sources usados. Una disposición/solución requiere al menos un procedimiento recuperado; no dejar vacío ni inventar IDs."
    )
    evidence_refs: list[str] = Field(default_factory=list)


class RequestDraft(BaseProposal):
    action: Literal["clarify", "register", "cancel", "answer"]
    fields: RequestFields
    field_sources: dict[str, str] = Field(default_factory=dict)


class ScheduleProposal(BaseProposal):
    action: Literal["clarify", "reserve", "cancel", "answer"]
    option_ids: list[str] = Field(default_factory=list)
    operation: Literal["pickup", "delivery"] = "pickup"


class QualityRecommendation(BaseProposal):
    action: Literal["clarify", "release", "reprocess", "open_incident", "answer"]
    findings: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_sources_for_disposition(self):
        if self.action in {"release", "reprocess", "open_incident"} and not self.source_ids:
            raise ValueError(
                "Una disposición necesita source_ids de procedimientos recuperados; sin ellos use clarify."
            )
        return self


class ResolutionProposal(BaseProposal):
    action: Literal["clarify", "resolve_incident", "close_incident", "answer"]
    facts: list[str] = Field(default_factory=list)
    discrepancies: list[str] = Field(default_factory=list)
    plan: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_sources_for_resolution(self):
        if self.action in {"resolve_incident", "close_incident"} and not self.source_ids:
            raise ValueError(
                "Una solución/cierre necesita source_ids recuperados; sin procedimiento use clarify."
            )
        return self
