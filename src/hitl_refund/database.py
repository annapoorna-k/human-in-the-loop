from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosHttpResponseError

from .config import settings
from .data import DUMMY_CASES

logger = logging.getLogger(__name__)


class WorkflowRepository(ABC):
    @abstractmethod
    def get_customer(self, customer_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def get_order(self, order_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def save_refund(self, record: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def save_audit(self, record: dict[str, Any]) -> dict[str, Any]: ...


class MemoryRepository(WorkflowRepository):
    def __init__(self) -> None:
        self.cases = deepcopy(DUMMY_CASES)
        self.refunds: list[dict[str, Any]] = []
        self.audit: list[dict[str, Any]] = []

    def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        case = next((item for item in self.cases if item["customer_id"] == customer_id), None)
        return None if case is None else {key: case[key] for key in ("customer_id", "customer", "email", "account_status")}

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        case = next((item for item in self.cases if item["order_id"] == order_id), None)
        return deepcopy(case) if case else None

    def save_refund(self, record: dict[str, Any]) -> dict[str, Any]:
        saved = {**record, "id": f"REF-{uuid.uuid4().hex[:10].upper()}", "document_type": "refund", "created_at": _now()}
        self.refunds.append(saved)
        return deepcopy(saved)

    def save_audit(self, record: dict[str, Any]) -> dict[str, Any]:
        saved = {**record, "id": f"AUD-{uuid.uuid4().hex[:10].upper()}", "document_type": "audit", "created_at": _now()}
        self.audit.append(saved)
        return deepcopy(saved)


class CosmosRepository(WorkflowRepository):
    def __init__(self) -> None:
        if not settings.cosmos_key:
            raise RuntimeError("COSMOS_KEY is required when STORAGE_BACKEND=cosmos")
        client = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_key, connection_verify=settings.cosmos_verify_ssl)
        database = client.create_database_if_not_exists(settings.cosmos_database)
        self.container = database.create_container_if_not_exists(settings.cosmos_container, partition_key=PartitionKey(path="/document_type"))
        self._seed_cases()

    def _seed_cases(self) -> None:
        for case in DUMMY_CASES:
            document = {**case, "id": case["case_id"], "document_type": "case"}
            self.container.upsert_item(document)

    def _one(self, query: str, parameters: list[dict[str, Any]]) -> dict[str, Any] | None:
        rows = list(self.container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True, max_item_count=1))
        return rows[0] if rows else None

    def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM c WHERE c.document_type='case' AND c.customer_id=@value", [{"name": "@value", "value": customer_id}])
        return None if row is None else {key: row[key] for key in ("customer_id", "customer", "email", "account_status")}

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM c WHERE c.document_type='case' AND c.order_id=@value", [{"name": "@value", "value": order_id}])

    def save_refund(self, record: dict[str, Any]) -> dict[str, Any]:
        saved = {**record, "id": f"REF-{uuid.uuid4().hex[:10].upper()}", "document_type": "refund", "created_at": _now()}
        return self.container.create_item(saved)

    def save_audit(self, record: dict[str, Any]) -> dict[str, Any]:
        saved = {**record, "id": f"AUD-{uuid.uuid4().hex[:10].upper()}", "document_type": "audit", "created_at": _now()}
        return self.container.create_item(saved)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


memory_repository = MemoryRepository()
_cosmos_repository: CosmosRepository | None = None


def get_repository() -> WorkflowRepository:
    global _cosmos_repository
    if settings.storage_backend != "cosmos":
        return memory_repository
    if _cosmos_repository is None:
        try:
            _cosmos_repository = CosmosRepository()
        except CosmosHttpResponseError as exc:
            logger.error("Cosmos DB connection failed: %s", exc)
            raise RuntimeError("Azure Cosmos DB is unavailable. Check the endpoint, key, and emulator status.") from exc
    return _cosmos_repository
