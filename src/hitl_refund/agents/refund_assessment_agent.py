from typing import Literal

from langgraph.types import Command

from ..events import event
from ..state import WorkflowState
from ..tools.order_details_tool import get_order_details
from ..tools.refund_policy_tool import evaluate_refund_policy


def refund_assessment_agent(state: WorkflowState) -> Command[Literal["human_review", "ineligible"]]:
    """Agent 3: inspect the order, apply policy, and propose Tool 4."""
    order_id = state["case"]["order_id"]
    order = get_order_details(order_id)
    policy = evaluate_refund_policy(order)
    trace = state["tool_trace"] + [
        {"agent": "Refund Assessment Agent", "tool": "get_order_details", "input": {"order_id": order_id}, "output": order},
        {"agent": "Refund Assessment Agent", "tool": "evaluate_refund_policy", "input": {"order": order}, "output": policy},
    ]
    action = {
        "tool": "issue_refund",
        "arguments": {
            "case_id": order["case_id"],
            "order_id": order["order_id"],
            "customer_id": order["customer_id"],
            "customer": order["customer"],
            "amount": order["paid_amount"],
            "paid_amount": order["paid_amount"],
        },
        "reason": f"{order['reason']}. Policy: {policy['policy']}.",
        "risk": policy["risk"],
        "requires_human_approval": True,
    }
    update = {
        "order_details": order,
        "policy_result": policy,
        "proposed_action": action,
        "tool_trace": trace,
        "events": state["events"] + [event("Refund Assessment Agent", "Used Tools 2 and 3 and proposed protected Tool 4")],
    }
    return Command(update=update, goto="human_review" if policy["eligible"] else "ineligible")

