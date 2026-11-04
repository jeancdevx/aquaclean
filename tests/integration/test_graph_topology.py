from langgraph.checkpoint.memory import InMemorySaver

from aquaclean.agents.schemas import RoutingDecision
from aquaclean.graphs.main import build_graph
from tests.integration.test_graphs import start


def test_export_contains_all_conditional_destinations_and_expands_specialists(rt):
    graph = build_graph(rt, InMemorySaver())
    topology = graph.get_graph()
    edges = {(e.source, e.target) for e in topology.edges}
    assert {target for source, target in edges if source == "stage"} == {"review", "respond"}
    assert {target for source, target in edges if source == "execute"} == {"review", "respond"}
    assert {
        ("review", "execute"),
        ("respond", "__end__"),
        ("supervisor", "clarify"),
        ("clarify", "respond"),
    } <= edges
    assert ("stage", "__end__") not in edges
    expanded = graph.get_graph(xray=True)
    assert len(expanded.nodes) > len(topology.nodes)
    assert any("tools" in node for node in expanded.nodes)


async def test_ambiguous_routing_cannot_stage_or_write(rt, case):
    original = rt.provider.structured

    async def ambiguous(schema, messages, tools=None):
        if schema is RoutingDecision:
            return RoutingDecision(
                process="P1",
                needs_clarification=True,
                rationale_summary="Intención ambigua controlada",
            )
        return await original(schema, messages, tools)

    rt.provider.structured = ambiguous
    snapshot = await start(rt, case["id"], "Haz eso con lo de ayer")
    assert snapshot["case"]["status"] == "awaiting_information"
    assert not snapshot["orders"] and not snapshot["approvals"] and not snapshot["inbox"]
    assert snapshot["case"]["proposal"]["action"] == "clarify"
