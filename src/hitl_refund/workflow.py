import logging
from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .agents import (
    customer_verification_agent,
    execution_agent,
    planner_agent,
    refund_assessment_agent,
)
from .events import event
from .state import WorkflowState

logger = logging.getLogger(__name__)


def route_request(state: WorkflowState) -> Literal["customer_verification_agent", "general_response"]:
    return "customer_verification_agent" if state["route"] == "refund" else "general_response"


def human_review(state: WorkflowState) -> Command[Literal["execution_agent", "rejected"]]:
    """Pause before the data-changing tool and resume with a human decision."""
    logger.info("Human approval requested for tool=issue_refund")
    decision = interrupt({
        "message": "A human decision is required before the refund is written",
        "proposed_action": state["proposed_action"],
        "customer_profile": state["customer_profile"],
        "policy_result": state["policy_result"],
    })
    status = str(decision.get("decision", "reject")).lower()
    note = str(decision.get("note", "")).strip()
    if status == "modify":
        arguments = {**state["proposed_action"]["arguments"], **decision.get("arguments", {})}
        action = {**state["proposed_action"], "arguments": arguments}
        return Command(
            update={
                "approval_status": "modified",
                "reviewer_note": note,
                "proposed_action": action,
                "events": state["events"] + [event("Human Reviewer", "Modified and approved the proposal")],
            },
            goto="execution_agent",
        )
    if status == "approve":
        return Command(
            update={
                "approval_status": "approved",
                "reviewer_note": note,
                "events": state["events"] + [event("Human Reviewer", "Approved the proposal")],
            },
            goto="execution_agent",
        )
    return Command(
        update={
            "approval_status": "rejected",
            "reviewer_note": note,
            "events": state["events"] + [event("Human Reviewer", "Rejected the proposal; Tool 4 remains blocked")],
        },
        goto="rejected",
    )


def completed(state: WorkflowState) -> WorkflowState:
    result = state["tool_result"]
    return {"final_response": f"Refund {result['id']} for INR {result['amount']:.2f} completed after human approval."}


def rejected(state: WorkflowState) -> WorkflowState:
    return {"final_response": f"Rejected by the human reviewer. No refund was written. Reason: {state.get('reviewer_note') or 'Not provided'}"}


def ineligible(state: WorkflowState) -> WorkflowState:
    return {"final_response": "The case is outside the demo policy. No sensitive tool was proposed or executed."}


def failed(state: WorkflowState) -> WorkflowState:
    return {"final_response": f"The refund was not completed. Error: {state['error']}"}


def general_response(state: WorkflowState) -> WorkflowState:
    return {
        "final_response": "This request does not require a refund, so the sensitive tool and approval step were skipped.",
        "events": state["events"] + [event("Planner Agent", "Completed a non-sensitive request without tools")],
    }


builder = StateGraph(WorkflowState)
builder.add_node("planner_agent", planner_agent)
builder.add_node("customer_verification_agent", customer_verification_agent)
builder.add_node("refund_assessment_agent", refund_assessment_agent)
builder.add_node("human_review", human_review)
builder.add_node("execution_agent", execution_agent)
builder.add_node("completed", completed)
builder.add_node("rejected", rejected)
builder.add_node("ineligible", ineligible)
builder.add_node("failed", failed)
builder.add_node("general_response", general_response)
builder.add_edge(START, "planner_agent")
builder.add_conditional_edges("planner_agent", route_request)
builder.add_edge("customer_verification_agent", "refund_assessment_agent")
for terminal in ("completed", "rejected", "ineligible", "failed", "general_response"):
    builder.add_edge(terminal, END)

graph = builder.compile(checkpointer=InMemorySaver())
