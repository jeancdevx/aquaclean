import json

from aquaclean.agents.prompts import COMMON, PROMPTS
from aquaclean.agents.schemas import (
    QualityRecommendation,
    RequestDraft,
    ResolutionProposal,
    ScheduleProposal,
)
from aquaclean.application.ports import ChatProvider

SCHEMAS = {
    "P1": RequestDraft,
    "P2": ScheduleProposal,
    "P3": QualityRecommendation,
    "P4": ResolutionProposal,
}


async def interpret(provider: ChatProvider, process: str, context: dict) -> dict:
    schema = SCHEMAS[process]
    response = await provider.structured(
        schema,
        [
            ("system", COMMON + PROMPTS[process]),
            ("human", json.dumps(context, default=str, ensure_ascii=False)),
        ],
    )
    return response.model_dump(exclude_none=True)
