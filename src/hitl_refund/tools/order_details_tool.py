from typing import Any

from ..database import get_repository


def get_order_details(order_id: str) -> dict[str, Any]:
    """Tool 2: retrieve order and refund-case details."""
    order = get_repository().get_order(order_id)
    if not order:
        raise ValueError(f"Order {order_id} was not found")
    return order

