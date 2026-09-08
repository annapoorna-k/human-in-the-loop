import json
import uuid

from langgraph.types import Command

from .data import DUMMY_CASES
from .workflow import graph


def show_cases() -> None:
    print("\nDummy refund cases")
    for number, case in enumerate(DUMMY_CASES, 1):
        print(f"  {number}. {case['case_id']} | {case['customer']} | {case['item']} | INR {case['paid_amount']:.2f}")


def read_decision(proposal: dict) -> dict:
    print("\nHUMAN APPROVAL REQUIRED")
    print(json.dumps(proposal, indent=2))
    while True:
        choice = input("Decision [A]pprove, [M]odify, [R]eject: ").strip().lower()
        if choice in {"a", "approve"}:
            return {"decision": "approve", "note": input("Approval note (optional): ").strip()}
        if choice in {"m", "modify"}:
            while True:
                try:
                    amount = float(input("Modified refund amount (INR): ").strip())
                    break
                except ValueError:
                    print("Enter a valid numeric amount.")
            return {"decision": "modify", "arguments": {"amount": amount}, "note": input("Reason for modification: ").strip()}
        if choice in {"r", "reject"}:
            note = input("Reason for rejection: ").strip()
            if note:
                return {"decision": "reject", "note": note}
            print("A rejection reason is required.")


def main() -> None:
    print("Human-in-the-Loop Multi-Agent Refund System")
    show_cases()
    while True:
        try:
            selected = int(input("\nSelect a case (1-5): ").strip()) - 1
            case = DUMMY_CASES[selected]
            break
        except (ValueError, IndexError):
            print("Select a number from 1 to 5.")
    request = input("Request (press Enter for the case refund): ").strip() or f"Review and refund case {case['case_id']}"
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke({"request": request, "case": case, "events": []}, config=config)
    snapshot = graph.get_state(config)
    if snapshot.interrupts:
        decision = read_decision(snapshot.interrupts[0].value["proposed_action"])
        result = graph.invoke(Command(resume=decision), config=config)
    print("\nExecution timeline")
    for item in result.get("events", []):
        print(f"  [{item['agent']}] {item['message']}")
    print(f"\nFinal response: {result['final_response']}")

