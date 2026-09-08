from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    request: str
    case: dict[str, Any]
    plan: list[str]
    route: str
    proposed_action: dict[str, Any]
    approval_status: str
    reviewer_note: str
    tool_result: dict[str, Any]
    final_response: str
    error: str
    events: list[dict[str, str]]
    llm_status: str
    customer_profile: dict[str, Any]
    order_details: dict[str, Any]
    policy_result: dict[str, Any]
    tool_trace: list[dict[str, Any]]
