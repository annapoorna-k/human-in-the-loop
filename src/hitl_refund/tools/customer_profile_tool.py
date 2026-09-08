from typing import Any

from ..database import get_repository


def get_customer_profile(customer_id: str) -> dict[str, Any]:
    """Tool 1: retrieve a customer profile from the repository."""
    customer = get_repository().get_customer(customer_id)
    if not customer:
        raise ValueError(f"Customer {customer_id} was not found")
    return customer

