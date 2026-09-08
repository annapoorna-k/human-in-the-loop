import logging
from typing import Literal

from langgraph.types import Command

from ..events import event
from ..state import WorkflowState
from ..tools.issue_refund_tool import issue_refund

logger = logging.getLogger(__name__)


def execution_agent(state: WorkflowState) -> Command[Literal["completed", "failed"]]:
    """Agent 4: execute Tool 4 only after an approved graph state."""
    if state.get("approval_status") not in {"approved", "modified"}:
        return Command(update={"error": "Security gate blocked Tool 4 because approval is missing"}, goto="failed")
    try:
        result = issue_refund(
            state["proposed_action"]["arguments"],
            state.get("reviewer_note", ""),
            state["approval_status"],
        )
        trace = state["tool_trace"] + [{
            "agent": "Execution Agent",
            "tool": "issue_refund",
            "input": state["proposed_action"]["arguments"],
            "output": result,
        }]
        return Command(
            update={
                "tool_result": result,
                "tool_trace": trace,
                "events": state["events"] + [event("Execution Agent", f"Executed Tool 4 and stored {result['id']}")],
            },
            goto="completed",
        )
    except Exception as exc:
        logger.error("Protected refund tool failed: %s", exc)
        return Command(
            update={"error": str(exc), "events": state["events"] + [event("Execution Agent", "Tool 4 failed safely")]},
            goto="failed",
        )
