import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI

from ..config import settings
from ..events import event
from ..prompts import PLANNER_SYSTEM_PROMPT
from ..state import WorkflowState

logger = logging.getLogger(__name__)


def create_plan(request: str, case: dict[str, Any]) -> tuple[list[str], str, str]:
    refund_fallback = ["Verify customer", "Inspect order and policy", "Request human approval"], "refund"
    general_fallback = ["Understand the request", "Respond without a sensitive tool"], "general"
    fallback = refund_fallback if "refund" in request.lower() else general_fallback
    if not settings.openrouter_api_key:
        logger.info("OpenRouter key absent; using deterministic planning")
        return *fallback, "deterministic fallback (API key not configured)"
    try:
        llm = ChatOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            model=settings.openrouter_model,
            temperature=0,
        )
        response = llm.invoke(
            f"{PLANNER_SYSTEM_PROMPT}\nKeys: plan (string array), route (refund or general). "
            f"Request: {request}\nCase: {json.dumps(case)}"
        )
        parsed = json.loads(str(response.content))
        route = parsed.get("route", fallback[1])
        if route not in {"refund", "general"}:
            route = fallback[1]
        return parsed.get("plan", fallback[0]), route, f"OpenRouter: {settings.openrouter_model}"
    except Exception as exc:
        logger.warning("OpenRouter failed; using deterministic planning: %s", exc)
        return *fallback, "deterministic fallback (OpenRouter unavailable)"


def planner_agent(state: WorkflowState) -> WorkflowState:
    """Agent 1: create the plan and route the request."""
    plan, route, llm_status = create_plan(state["request"], state["case"])
    return {
        "plan": plan,
        "route": route,
        "llm_status": llm_status,
        "tool_trace": [],
        "events": [event("Planner Agent", f"Created a {len(plan)}-step plan and selected {route}")],
    }

