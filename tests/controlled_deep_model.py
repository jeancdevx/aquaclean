"""Controlled chat MODEL driving the real SDK. This is not a provider evaluation."""

import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ControlledDeepModel(BaseChatModel):
    model_name: str = "controlled-deep-test"
    final_action: str = "resolve_incident"
    observed_tools: list = []

    @property
    def _llm_type(self):
        return "controlled-test"

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self.bind(tools=tools, **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs: Any):
        tools = kwargs.get("tools", [])
        names = {
            t.get("function", {}).get("name", t.get("name")) if isinstance(t, dict) else t.name
            for t in tools
        }
        self.observed_tools.append(sorted(names))
        done = {m.name for m in messages if isinstance(m, ToolMessage)}

        def call(name, args):
            return {"name": name, "args": args, "id": "test-call-" + str(len(messages)) + name}

        if "case_evidence_read" in names:
            response = (
                AIMessage(content="Evidencia del caso recuperada; no se ejecutan efectos.")
                if "case_evidence_read" in done
                else AIMessage(content="", tool_calls=[call("case_evidence_read", {})])
            )
        elif "case_procedures_read" in names:
            if "case_procedures_read" in done:
                response = AIMessage(
                    content="Procedimientos y citas: "
                    + " ".join(str(m.content) for m in messages if isinstance(m, ToolMessage))
                )
            else:
                response = AIMessage(content="", tool_calls=[call("case_procedures_read", {})])
        elif "write_todos" not in done:
            response = AIMessage(
                content="",
                tool_calls=[
                    call(
                        "write_todos",
                        {
                            "todos": [
                                {
                                    "content": "Investigar evidencias y procedimientos del caso",
                                    "status": "in_progress",
                                }
                            ]
                        },
                    )
                ],
            )
        elif "task" not in done:
            response = AIMessage(
                content="",
                tool_calls=[
                    call(
                        "task",
                        {
                            "subagent_type": name,
                            "description": "Investigar solo este caso con su herramienta autorizada y devolver resultados/citas.",
                        },
                    )
                    for name in ["evidencias", "procedimientos"]
                ],
            )
        else:
            text = " ".join(str(m.content) for m in messages if isinstance(m, ToolMessage))
            refs = list(dict.fromkeys(re.findall(r'"chunk_id":\s*"([^"]+)"', text)))
            args = {
                "action": self.final_action,
                "response": "Propuesta controlada del SDK real; pendiente de revisión humana.",
                "rationale_summary": "Se recuperaron resultados de ambos subagentes.",
                "missing_fields": [],
                "source_ids": refs[:1],
                "evidence_refs": [],
                "facts": ["Caso sintético bajo prueba"],
                "discrepancies": [],
                "plan": ["Verificar físicamente la observación y documentar cumplimiento"],
            }
            response = AIMessage(content="", tool_calls=[call("ResolutionProposal", args)])
        return ChatResult(generations=[ChatGeneration(message=response)])
