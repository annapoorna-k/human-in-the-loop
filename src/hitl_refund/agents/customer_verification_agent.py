import logging

from ..events import event
from ..state import WorkflowState
from ..tools.customer_profile_tool import get_customer_profile

logger = logging.getLogger(__name__)


def customer_verification_agent(state: WorkflowState) -> WorkflowState:
    """Agent 2: verify the customer with the customer-profile tool."""
    customer_id = state["case"]["customer_id"]
    profile = get_customer_profile(customer_id)
    trace = state["tool_trace"] + [{
        "agent": "Customer Verification Agent",
        "tool": "get_customer_profile",
        "input": {"customer_id": customer_id},
        "output": profile,
    }]
    logger.info("Verified customer=%s", customer_id)
    return {
        "customer_profile": profile,
        "tool_trace": trace,
        "events": state["events"] + [event("Customer Verification Agent", "Verified the customer using Tool 1")],
    }

