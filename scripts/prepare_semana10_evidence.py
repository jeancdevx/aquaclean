"""Prepare exact code extracts and measured topology; browser rendering is separate."""

import ast
import json
from pathlib import Path

from export_semana10_graph import export


def main():
    root = Path(Path("artifacts/semana10/CURRENT").read_text().strip())
    export(root / "02-langgraph")
    groups = {
        "01-lcel": [
            ("src/aquaclean/agents/chains.py", "structured_chain"),
            ("src/aquaclean/infrastructure/llm/provider.py", "structured"),
            ("src/aquaclean/agents/supervisor.py", "route"),
            ("src/aquaclean/agents/specialists.py", "interpret"),
        ],
        "06-deepagents": [
            ("src/aquaclean/agents/deep_incidents/factory.py", "create_incident_agent"),
            ("src/aquaclean/agents/deep_incidents/factory.py", "investigate"),
            ("src/aquaclean/agents/deep_incidents/factory.py", "awrap_model_call"),
        ],
    }
    for folder, symbols in groups.items():
        snippets, text = [], []
        for filename, symbol in symbols:
            source = Path(filename).read_text()
            lines = source.splitlines()
            nodes = [
                n
                for n in ast.walk(ast.parse(source))
                if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name == symbol
            ]
            assert len(nodes) == 1
            node = nodes[0]
            snippets.append(
                {
                    "path": filename,
                    "symbol": symbol,
                    "start": node.lineno,
                    "end": node.end_lineno,
                    "lines": lines[node.lineno - 1 : min(node.end_lineno, node.lineno + 43)],
                    "image": symbol + ".png",
                    "label": "extracto renderizado, no captura de VS Code",
                }
            )
            text.append(
                f"### {filename}:{node.lineno}-{node.end_lineno} · {symbol}\n"
                + "\n".join(lines[node.lineno - 1 : node.end_lineno])
            )
        if folder == "06-deepagents":
            filename = "src/aquaclean/agents/deep_incidents/factory.py"
            lines = Path(filename).read_text().splitlines()
            call = next(
                n
                for n in ast.walk(ast.parse("\n".join(lines)))
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "create_deep_agent"
            )
            snippets.append(
                {
                    "path": filename,
                    "symbol": "create_deep_agent: llamada SDK real",
                    "start": call.lineno,
                    "end": call.end_lineno,
                    "lines": lines[call.lineno - 1 : call.end_lineno],
                    "image": "create_deep_agent-llamada.png",
                    "label": "extracto renderizado, no captura de VS Code",
                }
            )
        (root / folder / "extractos.json").write_text(
            json.dumps(snippets, ensure_ascii=False, indent=2)
        )
        (root / folder / "extractos.txt").write_text("\n\n".join(text))
    (root / "01-lcel/flujo-lcel.mmd").write_text("""flowchart TB
 A["supervisor.route / specialists.interpret"] --> B["ChatProvider.structured"]
 B --> C["structured_chain: RunnableSequence"]
 C --> D["ChatPromptTemplate + MessagesPlaceholder"]
 D --> E["Modelo inyectado.with_structured_output"]
 E --> F["Parser schema del proveedor: JSON + raw/usage"]
 F --> G["ainvoke + validación Pydantic completa + reparación acotada"]
 G --> H["Grafo: stage → HITL → ejecutor"]
""")
    (root / "01-lcel/TERMINOS.md").write_text(
        "# Términos usados\n\n`ChatPromptTemplate`, `MessagesPlaceholder`, `RunnableSequence` y `|`: agents/chains.py, structured_chain. `ainvoke`: llm/provider.py, structured; supervisor/especialistas invocan el puerto desde la aplicación, probado en test_lcel_runtime.py. `with_structured_output` ya construía una secuencia interna en V1; V2 añade composición propia. El wire schema elimina límites de generación que Gemini rechaza, pero provider.structured vuelve a validar todo el schema Pydantic y el ejecutor conserva reglas de negocio. No hay StrOutputParser, RunnableLambda ni RunnableParallel ornamental. `astream` existe en provider.stream y se evalúa aparte; el chat entrega texto validado por SSE.\n"
    )
    (root / "06-deepagents/catalogo.json").write_text(
        json.dumps(
            {
                "sdk": "deepagents==0.7.30",
                "factory": "agents/deep_incidents/factory.py:create_incident_agent",
                "main_agent": "P4.investigador",
                "subagents": [
                    {
                        "name": "evidencias",
                        "tool": "case_evidence_read",
                        "scope": "one authorized service order, linked evidence IDs",
                    },
                    {
                        "name": "procedimientos",
                        "tool": "case_procedures_read",
                        "scope": "retrieved approved current sources",
                    },
                ],
                "planning": "TodoListMiddleware explicitly enabled",
                "backend": "new StateBackend per invocation; virtual memory only",
                "filesystem_tools": ["read_file"],
                "main_tools": ["task", "write_todos", "ResolutionProposal"],
                "general_purpose_subagent": False,
                "excluded_capabilities": [
                    "host filesystem",
                    "shell",
                    "SQL",
                    "arbitrary URLs",
                    "money transfers",
                    "business writes",
                    "permissions",
                    "direct closure",
                    "global memory",
                    "unbudgeted summarization",
                ],
                "budget": "shared model-call count, context size, recursion, total timeout; provider transport retry at most 1",
                "result": "ResolutionProposal → verified source/evidence IDs → existing HITL",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
