from abc import ABC, abstractmethod
from datetime import datetime, timezone
import logging
from typing import Any
import uuid

import psycopg

from .config import settings

logger = logging.getLogger(__name__)


class ApprovalAuditRepository(ABC):
    @abstractmethod
    def save_approval(self, record: dict[str, Any]) -> dict[str, Any]: ...


class MemoryApprovalAuditRepository(ApprovalAuditRepository):
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def save_approval(self, record: dict[str, Any]) -> dict[str, Any]:
        saved = {**record, "audit_id": f"AUD-{uuid.uuid4().hex[:10].upper()}", "created_at": datetime.now(timezone.utc).isoformat()}
        self.records.append(saved)
        return saved


class PostgresApprovalAuditRepository(ApprovalAuditRepository):
    def save_approval(self, record: dict[str, Any]) -> dict[str, Any]:
        audit_id = f"AUD-{uuid.uuid4().hex[:10].upper()}"
        try:
            with psycopg.connect(settings.database_url) as connection:
                connection.execute(
                    """CREATE TABLE IF NOT EXISTS approval_audit (
                        audit_id TEXT PRIMARY KEY,
                        case_id TEXT NOT NULL,
                        refund_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        decision TEXT NOT NULL,
                        reviewer_note TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )"""
                )
                row = connection.execute(
                    """INSERT INTO approval_audit
                       (audit_id, case_id, refund_id, action, decision, reviewer_note)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       RETURNING created_at""",
                    (audit_id, record["case_id"], record["refund_id"], record["action"], record["decision"], record.get("reviewer_note", "")),
                ).fetchone()
                connection.commit()
            return {**record, "audit_id": audit_id, "created_at": row[0].isoformat()}
        except psycopg.Error as exc:
            logger.error("PostgreSQL audit write failed: %s", exc)
            raise RuntimeError("PostgreSQL audit storage is unavailable; the refund was not finalized") from exc


memory_audit_repository = MemoryApprovalAuditRepository()


def get_audit_repository() -> ApprovalAuditRepository:
    if settings.audit_backend == "postgres":
        return PostgresApprovalAuditRepository()
    return memory_audit_repository
