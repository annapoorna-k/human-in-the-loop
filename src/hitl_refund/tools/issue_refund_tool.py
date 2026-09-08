from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from ..database import get_repository
from ..audit_database import get_audit_repository


class RefundArguments(BaseModel):
    case_id: str = Field(min_length=3)
    order_id: str = Field(min_length=3)
    customer_id: str = Field(min_length=3)
    customer: str = Field(min_length=2)
    amount: Decimal = Field(gt=0)
    paid_amount: Decimal = Field(gt=0)


def issue_refund(arguments: dict[str, Any], reviewer_note: str, decision: str) -> dict[str, Any]:
    """Tool 4: persist a human-approved refund and its audit document."""
    try:
        validated = RefundArguments.model_validate(arguments)
    except ValidationError as exc:
        raise ValueError(f"Invalid refund arguments: {exc.errors()[0]['msg']}") from exc
    if validated.amount > validated.paid_amount:
        raise ValueError("Refund amount cannot exceed the amount paid")
    repository = get_repository()
    saved = repository.save_refund({
        "case_id": validated.case_id,
        "order_id": validated.order_id,
        "customer_id": validated.customer_id,
        "customer": validated.customer,
        "amount": float(validated.amount),
        "reviewer_note": reviewer_note,
        "human_decision": decision,
    })
    audit = {
        "case_id": validated.case_id,
        "action": "issue_refund",
        "decision": decision,
        "refund_id": saved["id"],
        "reviewer_note": reviewer_note,
    }
    repository.save_audit(audit)
    postgres_audit = get_audit_repository().save_approval(audit)
    return {**saved, "approval_audit_id": postgres_audit["audit_id"]}
