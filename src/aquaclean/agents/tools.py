from langchain_core.tools import tool

from aquaclean.domain.entities import Actor
from aquaclean.domain.policies import ROLES
from aquaclean.infrastructure.knowledge.public_history import search_history
from aquaclean.infrastructure.knowledge.retrieval import KnowledgeRepository
from aquaclean.infrastructure.persistence.repositories import Repository


def specialist_tools(
    process: str, actor: Actor, case_id: str, repo: Repository, knowledge: KnowledgeRepository
):
    @tool
    async def case_evidence() -> dict:
        """Read authorized messages, operator evidence and current proposal for this case."""
        actor.require(ROLES[process])
        snapshot = await repo.snapshot(actor, case_id)
        return {
            k: snapshot[k]
            for k in (
                "case",
                "messages",
                "attachments",
                "operator_events",
                "orders",
                "linked_order_history",
                "command_history",
            )
        }

    @tool
    async def customer_registry(client_id: str) -> dict:
        """Read a customer in the actor's organization and scope; codes do not authenticate."""
        actor.require("attention")
        return await repo.customer(actor, client_id)

    @tool
    async def schedule_options(order_id: str) -> list[dict]:
        """Calculate feasible capacity options from the current persisted agenda."""
        actor.require("logistics")
        return await repo.slots(actor, order_id)

    @tool
    async def approved_knowledge(query: str) -> list[dict]:
        """Vector search of approved, current knowledge filtered by organization, client and roles."""
        actor.require(ROLES[process])
        case = await repo.case(actor, case_id)
        return await knowledge.search(actor, query, case["client_id"])

    @tool
    async def historical_references(query: str) -> list[dict]:
        """Find public external historical records. These are NOT company policy or case evidence."""
        actor.require(ROLES[process])
        await repo.case(actor, case_id)
        return await search_history(repo.db, query)

    tools = {
        "case_evidence": case_evidence,
        "approved_knowledge": approved_knowledge,
        "historical_references": historical_references,
    }
    if process == "P1":
        tools["customer_registry"] = customer_registry
    if process == "P2":
        tools["schedule_options"] = schedule_options
    return tools
