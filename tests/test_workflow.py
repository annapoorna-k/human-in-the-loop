import uuid
import importlib

import pytest
from langgraph.types import Command

from hitl_refund.data import DUMMY_CASES
from hitl_refund.database import memory_repository
from hitl_refund.workflow import graph


@pytest.fixture(autouse=True)
def deterministic_planner(monkeypatch):
    def plan(request, _case):
        if "refund" in request.lower():
            return ["Verify customer", "Assess order", "Request approval"], "refund", "test planner"
        return ["Answer non-sensitive request"], "general", "test planner"

    planner_module = importlib.import_module("hitl_refund.agents.planner_agent")
    monkeypatch.setattr(planner_module, "create_plan", plan)


def start(request="Please refund this order"):
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke({"request": request, "case": DUMMY_CASES[0], "events": []}, config=config)
    return config, result


def test_workflow_really_pauses_before_sensitive_tool():
    before = len(memory_repository.refunds)
    config, _ = start()
    assert graph.get_state(config).interrupts
    assert len(memory_repository.refunds) == before


def test_approve_executes_refund():
    config, _ = start()
    result = graph.invoke(Command(resume={"decision": "approve", "note": "Checked"}), config=config)
    assert result["approval_status"] == "approved"
    assert result["tool_result"]["amount"] == 3499.0


def test_modify_uses_human_amount():
    config, _ = start()
    result = graph.invoke(Command(resume={"decision": "modify", "arguments": {"amount": 1200}, "note": "Partial refund"}), config=config)
    assert result["approval_status"] == "modified"
    assert result["tool_result"]["amount"] == 1200.0


def test_reject_never_executes_refund():
    before = len(memory_repository.refunds)
    config, _ = start()
    result = graph.invoke(Command(resume={"decision": "reject", "note": "Evidence missing"}), config=config)
    assert len(memory_repository.refunds) == before
    assert "No refund was written" in result["final_response"]


def test_invalid_modified_amount_fails_safely():
    config, _ = start()
    result = graph.invoke(Command(resume={"decision": "modify", "arguments": {"amount": 999999}, "note": "Test validation"}), config=config)
    assert "cannot exceed" in result["final_response"]


def test_non_refund_request_skips_approval():
    config, result = start("What is the order status?")
    assert not graph.get_state(config).interrupts
    assert "approval step were skipped" in result["final_response"]
