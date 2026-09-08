from typing import Any


def evaluate_refund_policy(order: dict[str, Any]) -> dict[str, Any]:
    """Tool 3: evaluate the deterministic 30-day demo policy."""
    eligible = order["days_since_purchase"] <= 30 and order["delivery_status"] == "delivered"
    return {
        "eligible": eligible,
        "policy": "Delivered orders are refundable within 30 days",
        "risk": "high" if order["paid_amount"] >= 10000 or order["account_status"] == "review" else "standard",
    }

