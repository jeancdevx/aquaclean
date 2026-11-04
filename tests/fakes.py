import hashlib
import math

from aquaclean.agents.schemas import (
    RequestDraft,
    ResolutionProposal,
    RoutingDecision,
    ScheduleProposal,
)
from aquaclean.domain.errors import ProviderUnavailable


class FakeEmbeddings:
    model = "fake-test-only-sha256"
    dimension = 768

    async def embed(self, texts, task):
        vectors = []
        for text in texts:
            hashed = hashlib.sha256(text.encode()).digest()
            values = [(hashed[i % 32] - 127.5) / 128 for i in range(self.dimension)]
            norm = math.sqrt(sum(x * x for x in values))
            vectors.append([x / norm for x in values])
        return vectors


class FakeProvider:
    """Explicit test double. Never imported by src; no runtime fake mode exists."""

    def __init__(self, clock):
        self.clock = clock
        self.process = "P1"
        self.action = "register"
        self.fail = False
        self.overrides = {}

    async def structured(self, schema, messages, tools=None):
        if self.fail:
            raise ProviderUnavailable("Proveedor caído (fake de prueba explícito)")
        if schema is RoutingDecision:
            return schema(
                process=self.process,
                needs_clarification=False,
                rationale_summary="Intención sintética de prueba",
            )
        import json

        context = json.loads(messages[-1][1])
        base = {
            "missing_fields": [],
            "action": self.action,
            "response": "Propuesta sintética de prueba; requiere confirmación.",
            "rationale_summary": "Campos de fixture y herramientas reales de PostgreSQL.",
            "source_ids": [s["chunk_id"] for s in context.get("sources", [])[:1]],
            "evidence_refs": [],
        }
        if schema is RequestDraft:
            base["fields"] = {
                "cliente_id": context["case"]["client_id"] or "CLI-0001",
                "solicitante": "Operador sintético",
                "correo": "demo@example.invalid",
                "fecha_recojo": str(self.clock.now().date()),
                "turno": "manana",
                "tipo_ropa": "manteleria",
                "bolsas": 3,
            }
            base["field_sources"] = {
                k: "fixture de prueba confirmado por operador" for k in base["fields"]
            }
        if schema is ScheduleProposal:
            base["option_ids"] = [o["id"] for o in context.get("schedule_options", [])[:2]]
        if schema is ResolutionProposal:
            base["plan"] = ["Verificación física de la guía sintética"]
        base.update(self.overrides)
        return schema.model_validate(base)

    async def perceive(self, content, mime):
        if self.fail:
            raise ProviderUnavailable()
        return "Observación de fake de prueba explícito: no es percepción Gemini real."

    async def stream(self, messages):
        if self.fail:
            raise ProviderUnavailable()
        for part in messages[-1][1].split(" "):
            yield part + " "
