from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    storage_backend: str = os.getenv("STORAGE_BACKEND", "memory").lower()
    cosmos_endpoint: str = os.getenv("COSMOS_ENDPOINT", "https://localhost:8081/")
    cosmos_key: str = os.getenv("COSMOS_KEY", "")
    cosmos_database: str = os.getenv("COSMOS_DATABASE", "hitl-refund-demo")
    cosmos_container: str = os.getenv("COSMOS_CONTAINER", "workflow-records")
    cosmos_verify_ssl: bool = os.getenv("COSMOS_VERIFY_SSL", "true").lower() == "true"
    audit_backend: str = os.getenv("AUDIT_BACKEND", "memory").lower()
    database_url: str = os.getenv("DATABASE_URL", "postgresql://hitl_user:hitl_password@localhost:5434/hitl_audit")


settings = Settings()
