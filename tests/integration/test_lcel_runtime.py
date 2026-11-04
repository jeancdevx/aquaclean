import json
from types import SimpleNamespace

from langchain_core.runnables import Runnable, RunnableSequence
from pydantic import SecretStr

from aquaclean.agents.chains import structured_chain
from aquaclean.agents.schemas import RequestDraft, RoutingDecision
from aquaclean.config import Settings
from aquaclean.infrastructure.llm.provider import GeminiProvider
from tests.integration.test_graphs import start


class StructuredModelDouble:
    def __init__(self):
        self.prompts = []

    def with_structured_output(self, schema, **kwargs):
        if isinstance(schema, dict):
            schema = {"RoutingDecision": RoutingDecision, "RequestDraft": RequestDraft}[
                schema["title"]
            ]
        parent = self

        class Output(Runnable):
            def invoke(self, value, config=None, **kwargs):
                messages = value.to_messages()
                parent.prompts.append((schema, messages))
                json.loads(messages[-1].content)  # actual parametrized context reached model
                parsed = (
                    schema(
                        process="P1",
                        needs_clarification=False,
                        rationale_summary="Clasificación controlada",
                    )
                    if schema is RoutingDecision
                    else schema(
                        action="answer",
                        fields={},
                        response="Respuesta controlada sin efectos",
                        rationale_summary="Prueba de integración LCEL",
                        source_ids=[],
                        missing_fields=[],
                    )
                )
                return {
                    "parsed": parsed,
                    "raw": SimpleNamespace(usage_metadata={"input_tokens": 1}),
                    "parsing_error": None,
                }

        return Output()


async def test_application_invokes_project_lcel_for_supervisor_and_specialist(rt, case):
    provider = GeminiProvider(Settings(gemini_api_key=SecretStr("")))
    provider.client = object()  # no SDK/network; controlled model only
    model = StructuredModelDouble()
    provider.model = model
    rt.provider = provider
    assert isinstance(structured_chain(model, RoutingDecision), RunnableSequence)
    snapshot = await start(rt, case["id"], "Consulta sintética sin efectos")
    assert snapshot["runs"][-1]["status"] == "completed"
    assert [schema for schema, _ in model.prompts] == [RoutingDecision, RequestDraft]
    assert all(
        messages[0].type == "system" and messages[-1].type == "human"
        for _, messages in model.prompts
    )
    assert not snapshot["orders"] and not snapshot["approvals"]
