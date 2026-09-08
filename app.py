from pathlib import Path
import sys
import uuid

import streamlit as st
from langgraph.types import Command


# --------------------------------------------------
# Add src folder to Python path BEFORE project imports
# --------------------------------------------------

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))


# --------------------------------------------------
# Project imports
# --------------------------------------------------

from hitl_refund.config import settings  # noqa: E402
from hitl_refund.data import DUMMY_CASES  # noqa: E402
from hitl_refund.logging_config import configure_logging  # noqa: E402
from hitl_refund.workflow import graph  # noqa: E402
from hitl_refund.langfuse_config import langfuse_handler  # noqa: E402


# --------------------------------------------------
# Application setup
# --------------------------------------------------

configure_logging()

st.set_page_config(
    page_title="HITL Refund Operations",
    page_icon="H",
    layout="wide"
)


# --------------------------------------------------
# Session State
# --------------------------------------------------

def initialize_state() -> None:
    for key, value in {
        "config": None,
        "result": None,
        "proposal": None
    }.items():
        if key not in st.session_state:
            st.session_state[key] = value


# --------------------------------------------------
# Start LangGraph Workflow + Langfuse Tracing
# --------------------------------------------------

def run_request(case: dict, request: str) -> None:

    config = {
        "configurable": {
            "thread_id": str(uuid.uuid4())
        },

        # Langfuse callback
        "callbacks": [langfuse_handler]
    }

    initial_state = {
        "request": request,
        "case": case,
        "events": []
    }

    # Start LangGraph workflow
    result = graph.invoke(
        initial_state,
        config=config
    )

    # Get workflow state after interrupt
    snapshot = graph.get_state(config)

    # Save state in Streamlit session
    st.session_state.config = config
    st.session_state.result = result

    # Check whether LangGraph paused for human approval
    st.session_state.proposal = (
        snapshot.interrupts[0].value["proposed_action"]
        if snapshot.interrupts
        else None
    )


# --------------------------------------------------
# Resume LangGraph Workflow + Langfuse Tracing
# --------------------------------------------------

def resume(decision: dict) -> None:

    # The same config already contains:
    # - thread_id
    # - Langfuse callback

    st.session_state.result = graph.invoke(
        Command(resume=decision),
        config=st.session_state.config
    )

    st.session_state.proposal = None


# --------------------------------------------------
# Reset Application
# --------------------------------------------------

def reset() -> None:
    st.session_state.config = None
    st.session_state.result = None
    st.session_state.proposal = None


# --------------------------------------------------
# Initialize Streamlit state
# --------------------------------------------------

initialize_state()


# --------------------------------------------------
# UI Header
# --------------------------------------------------

st.title("Human-in-the-Loop Refund Operations")

st.caption(
    "Multi-agent planning with mandatory human control before financial execution"
)


# --------------------------------------------------
# Status Metrics
# --------------------------------------------------

status_col, storage_col, audit_col, safety_col = st.columns(4)

status_col.metric(
    "Planner",
    "OpenRouter" if settings.openrouter_api_key else "Offline fallback"
)

storage_col.metric(
    "Storage",
    settings.storage_backend.title()
)

audit_col.metric(
    "Approval audit",
    settings.audit_backend.title()
)

safety_col.metric(
    "Sensitive action",
    "Approval required"
)


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:

    st.header("Workflow")

    st.write(
        "Planner Agent -> Router Agent -> "
        "Refund Agent -> Human Review -> Execution Agent"
    )

    if st.button(
        "Start new review",
        use_container_width=True
    ):
        reset()
        st.rerun()


# --------------------------------------------------
# Select Refund Case
# --------------------------------------------------

selected_id = st.selectbox(
    "Refund case",

    options=[
        case["case_id"]
        for case in DUMMY_CASES
    ],

    format_func=lambda case_id: next(
        (
            f"{c['case_id']} | "
            f"{c['customer']} | "
            f"INR {c['paid_amount']:.2f}"
        )
        for c in DUMMY_CASES
        if c["case_id"] == case_id
    ),

    disabled=st.session_state.config is not None
)


case = next(
    item
    for item in DUMMY_CASES
    if item["case_id"] == selected_id
)


# --------------------------------------------------
# Case Details
# --------------------------------------------------

detail_cols = st.columns(4)

detail_cols[0].metric(
    "Customer",
    case["customer"]
)

detail_cols[1].metric(
    "Order",
    case["order_id"]
)

detail_cols[2].metric(
    "Paid",
    f"INR {case['paid_amount']:.2f}"
)

detail_cols[3].metric(
    "Purchase age",
    f"{case['days_since_purchase']} days"
)


st.write(
    f"**Item:** {case['item']} | "
    f"**Reason:** {case['reason']}"
)


# --------------------------------------------------
# User Request
# --------------------------------------------------

request = st.text_area(
    "Request",

    value=f"Review and refund case {case['case_id']}",

    disabled=st.session_state.config is not None
)


# --------------------------------------------------
# Run Workflow Button
# --------------------------------------------------

if st.button(
    "Run agent workflow",

    type="primary",

    disabled=(
        st.session_state.config is not None
        or not request.strip()
    )
):

    try:

        run_request(
            case,
            request.strip()
        )

        st.rerun()

    except Exception as exc:

        st.error(
            f"Workflow failed to start: {exc}"
        )


# --------------------------------------------------
# Show Agent Results
# --------------------------------------------------

result = st.session_state.result


if result:

    st.divider()

    st.subheader("Agent plan")


    # Planner status
    if result.get("llm_status"):

        st.info(
            f"Planner mode: "
            f"{result['llm_status']}"
        )


    # Plan
    for index, step in enumerate(
        result.get("plan", []),
        1
    ):

        st.write(
            f"{index}. {step}"
        )


    # Tool trace
    if result.get("tool_trace"):

        with st.expander(
            "Tool calls and data",
            expanded=True
        ):

            for call in result["tool_trace"]:

                st.markdown(
                    f"**{call['agent']} -> "
                    f"`{call['tool']}`**"
                )

                input_col, output_col = st.columns(2)


                input_col.caption(
                    "Tool input"
                )

                input_col.json(
                    call["input"]
                )


                output_col.caption(
                    "Tool output"
                )

                output_col.json(
                    call["output"]
                )


# --------------------------------------------------
# Human Approval Section
# --------------------------------------------------

if st.session_state.proposal:

    proposal = st.session_state.proposal


    st.warning(
        "Execution is paused. No refund has been issued."
    )


    st.subheader(
        "Proposed sensitive action"
    )


    st.json(proposal)


    approve_tab, modify_tab, reject_tab = st.tabs(
        [
            "Approve",
            "Modify",
            "Reject"
        ]
    )


    # ----------------------------------------------
    # APPROVE
    # ----------------------------------------------

    with approve_tab:

        approval_note = st.text_input(
            "Approval note",
            key="approval_note"
        )


        if st.button(
            "Approve and execute",
            type="primary"
        ):

            try:

                resume(
                    {
                        "decision": "approve",
                        "note": approval_note
                    }
                )

                st.rerun()

            except Exception as exc:

                st.error(
                    f"The workflow could not resume: {exc}"
                )


    # ----------------------------------------------
    # MODIFY
    # ----------------------------------------------

    with modify_tab:

        modified_amount = st.number_input(

            "Approved amount (INR)",

            min_value=1.0,

            max_value=float(
                proposal["arguments"]["paid_amount"]
            ),

            value=float(
                proposal["arguments"]["amount"]
            ),

            step=100.0
        )


        modification_note = st.text_input(
            "Reason for modification",
            key="modification_note"
        )


        if st.button(
            "Apply modification and execute",

            disabled=not modification_note.strip()
        ):

            try:

                resume(
                    {
                        "decision": "modify",

                        "arguments": {
                            "amount": modified_amount
                        },

                        "note": modification_note
                    }
                )

                st.rerun()

            except Exception as exc:

                st.error(
                    f"The workflow could not resume: {exc}"
                )


    # ----------------------------------------------
    # REJECT
    # ----------------------------------------------

    with reject_tab:

        rejection_note = st.text_input(
            "Reason for rejection",
            key="rejection_note"
        )


        if st.button(
            "Reject action",

            disabled=not rejection_note.strip()
        ):

            try:

                resume(
                    {
                        "decision": "reject",
                        "note": rejection_note
                    }
                )

                st.rerun()

            except Exception as exc:

                st.error(
                    f"The workflow could not resume: {exc}"
                )


# --------------------------------------------------
# Final Workflow Result
# --------------------------------------------------

if result and result.get("final_response"):

    if result.get("tool_result"):

        st.success(
            result["final_response"]
        )

        st.json(
            result["tool_result"]
        )


    elif result.get("error"):

        st.error(
            result["final_response"]
        )


    else:

        st.info(
            result["final_response"]
        )


# --------------------------------------------------
# Execution Timeline
# --------------------------------------------------

if result:

    st.subheader(
        "Execution timeline"
    )


    for item in result.get("events", []):

        st.write(
            f"**{item['agent']}** | "
            f"{item['message']}"
        )