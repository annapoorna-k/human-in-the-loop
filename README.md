# Human-in-the-Loop Multi-Agent Refund System

A locally runnable Streamlit demonstration built with Python, LangChain, LangGraph, OpenRouter, four agents, four tools, Azure Cosmos DB, and PostgreSQL. Customer and refund cases are dummy data; the orchestration and human approval boundary are functional.

## Architecture

```text
User -> Streamlit UI -> Planner Agent
                         |
                  Customer Verification Agent -> Tool 1: get_customer_profile
                         |
                  Refund Assessment Agent -> Tool 2: get_order_details
                                          -> Tool 3: evaluate_refund_policy
                         |
                  Proposed Tool 4: issue_refund
                         |
                  LangGraph interrupt
             +-----------+-----------+
          Approve      Modify       Reject
             |           |             |
             +-> Execution Agent      Stop
                       |
                 Tool 4 executes
                       |
         Cosmos DB + PostgreSQL audit
```

The graph pauses inside `human_review` before the only data-changing tool. It resumes using the same LangGraph `thread_id` and `Command(resume=...)`.

## Folder structure

```text
app.py                         Streamlit entry point
main.py                        Optional CLI entry point
src/hitl_refund/agents/        Four separate agent modules
src/hitl_refund/workflow.py    Graph edges, interrupt and resume
src/hitl_refund/tools/         Four separate validated tool modules
src/hitl_refund/database.py    Memory and Azure Cosmos repositories
src/hitl_refund/audit_database.py  Memory and PostgreSQL approval audit
src/hitl_refund/state.py       LangGraph state contract
src/hitl_refund/data.py        Dummy customer and order records
src/hitl_refund/prompts.py     LLM planner prompt
tests/test_workflow.py         HITL safety tests
Dockerfile                     Streamlit application image
docker-compose.yml             App and Cosmos emulator services
```

## Run locally on Windows

Requires Python 3.11.

```powershell
cd C:\Users\sasap\Desktop\human-loop
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Open `http://127.0.0.1:8501`.

The default `.env` can run with memory fallbacks. To enable real LLM planning, add your OpenRouter key:

```dotenv
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

If the key or API is unavailable, the application reports deterministic fallback mode instead of crashing.

## Azure Cosmos DB

For an Azure account, set these values in `.env`:

```dotenv
STORAGE_BACKEND=cosmos
COSMOS_ENDPOINT=https://YOUR-ACCOUNT.documents.azure.com:443/
COSMOS_KEY=your_real_key
COSMOS_DATABASE=hitl-refund-demo
COSMOS_CONTAINER=workflow-records
COSMOS_VERIFY_SSL=true
```

For the local Cosmos emulator, start Docker Desktop and run:

```powershell
docker compose up -d cosmos
```

Open `http://localhost:11234`, place the well-known emulator key in `.env`, set `STORAGE_BACKEND=cosmos`, and restart Streamlit. The local vNext endpoint is `http://localhost:18082/`.

Cosmos automatically receives dummy `case` documents. Approved refunds create `refund` and `audit` documents. Rejected actions create no refund document.

## PostgreSQL approval audit

PostgreSQL stores a relational approval ledger separately from operational Cosmos documents. Start it with:

```powershell
docker compose up -d postgres
```

Then configure:

```dotenv
AUDIT_BACKEND=postgres
DATABASE_URL=postgresql://hitl_user:hitl_password@localhost:5434/hitl_audit
```

The `approval_audit` table is created on the first approved or modified refund. Inspect it with:

```powershell
docker compose exec postgres psql -U hitl_user -d hitl_audit -c "SELECT * FROM approval_audit ORDER BY created_at DESC;"
```

Optional containerized app:

```powershell
docker compose --profile full up --build
```

## Test scenarios

```powershell
$env:PYTHONPATH="src"
python -m pytest -q
```

1. Enter a non-refund request to skip sensitive execution.
2. Run a refund and approve it; Tool 4 executes after approval.
3. Modify the amount and provide a reason; the changed amount is validated and saved.
4. Reject with a reason; Tool 4 never executes.
5. Try an excessive modified amount through the automated test; validation blocks it safely.

## Interview explanation

`app.py` starts the UI and creates a unique graph thread. `planner_agent` calls OpenRouter through `ChatOpenAI` when configured. The graph routes refund requests through customer verification and refund assessment. These agents use three read-only tools and display their inputs and outputs. The refund proposal reaches `human_review`, where LangGraph creates a real interrupt. Streamlit displays Approve, Modify, and Reject controls. Approve resumes unchanged; Modify replaces only allowed arguments; Reject routes to the end without calling the write tool. `execution_agent` independently checks approval state before calling `issue_refund`. Cosmos DB stores operational case/refund documents and PostgreSQL stores the approval audit ledger.

This is an interview-quality local demonstration. Production deployment additionally needs identity and role authorization, durable LangGraph checkpoints, payment-provider idempotency, encrypted secret management, immutable audit retention, monitoring, rate limiting, and formal database migrations.
