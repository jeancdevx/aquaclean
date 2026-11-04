from typing import Any, TypedDict


class CaseState(TypedDict, total=False):
    case_id: str
    run_id: str
    execution_run_id: str
    process: str
    context: dict[str, Any]
    text: str
    attachment_ids: list[str]
    observations: list[dict]
    proposal: dict[str, Any]
    approval: dict[str, Any]
    human_approval: dict[str, Any]
    result: dict[str, Any]
    response: str
    review_decision: dict[str, Any]
    model_calls: int
    skip_review: bool
    needs_clarification: bool
    retail_draft: dict[str, Any]
