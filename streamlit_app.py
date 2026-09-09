"""
Streamlit Companion Chat & Query Application for Autorag_champs.

Features:
- Connects to backend FastAPI /query API endpoint.
- Uses Streamlit Chat Elements (st.chat_input, st.chat_message).
- Uses st.status for dynamic step-by-step loading state.
- Renders grounded answers first, followed by expandable source inspection.
- Displays confidence score, refusal notices, and citation markers.
"""

import os
import requests
import streamlit as st

st.set_page_config(
    page_title="Aura Automotive - Diagnostic RAG Hub",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 28px;
        font-weight: 800;
        color: #f8fafc;
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 4px;
    }
    .sub-title {
        font-size: 14px;
        color: #94a3b8;
        margin-bottom: 20px;
    }
    .badge-grounded {
        background-color: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-refusal {
        background-color: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.title("⚙️ RAG Engine Settings")
    api_base_url = st.text_input(
        "RAG Backend URL",
        value=os.getenv("RAG_API_URL", "http://localhost:8000"),
        help="Endpoint for the FastAPI /query backend"
    )

    st.markdown("---")
    st.subheader("📡 Backend Status")

    try:
        status_res = requests.get(f"{api_base_url}/status", timeout=2)
        if status_res.status_code == 200:
            status_data = status_res.json()
            st.success("🟢 Backend Connected & Healthy")
            st.metric("Indexed Documents", status_data.get("indexed_documents", 0))
            st.metric("Corpus Chunks", status_data.get("indexed_chunks", 0))
            st.caption(f"**Chat Model:** {status_data.get('active_chat_model')}")
            st.caption(f"**Embedding Model:** {status_data.get('active_embedding_model')}")
            st.caption(f"**Guardrail Threshold:** {status_data.get('min_top_score')}")
        else:
            st.warning(f"⚠️ Backend returned HTTP {status_res.status_code}")
    except Exception as e:
        st.error("🔴 Backend Disconnected")
        st.caption(f"Could not reach `{api_base_url}`. Please ensure `uvicorn src.api_server:app` is running.")

    st.markdown("---")
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Header
st.markdown('<div class="main-title">🚗 Aura Diagnostic Hub</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">AI-grounded technical diagnostics with traceable source evidence & citations.</div>', unsafe_allow_html=True)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

# Quick Query Starter Chips
col1, col2, col3, col4 = st.columns(4)
starter_query = None

with col1:
    if st.button("🔍 DTC P0300 Misfire", use_container_width=True):
        starter_query = "What is the troubleshooting procedure for DTC P0300 on 2023 SUV Model X?"
with col2:
    if st.button("🔌 Connector C102 Bulletin", use_container_width=True):
        starter_query = "What connector should I inspect for intermittent misfire issues?"
with col3:
    if st.button("🔋 Battery Recall Firmware", use_container_width=True):
        starter_query = "What software version is required for the battery recall RCL-23-088B?"
with col4:
    if st.button("🛡️ Out-of-Scope Refusal", use_container_width=True):
        starter_query = "What is the refund policy for customer sales invoice #8891?"

# Render Past Conversation History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.write(msg["content"])
        else:
            result = msg.get("result", {})
            render_assistant_response(result)

def render_assistant_response(result: dict):
    """Renders structured assistant answer with sources and confidence."""
    answer = result.get("answer", "No answer provided.")
    sources = result.get("sources", [])
    status = result.get("status", "answered")
    confidence = result.get("confidence", result.get("top_score", 0.0))
    confidence_pct = int(confidence * 100)

    # Status & Confidence Badge
    col_stat, col_spacer = st.columns([2, 5])
    with col_stat:
        if status == "refused_weak_context":
            st.markdown(f'<span class="badge-refusal">⚠️ Refused (Weak Context &bull; {confidence_pct}%)</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="badge-grounded">🛡️ Grounded &bull; {confidence_pct}% Confidence</span>', unsafe_allow_html=True)

    # Answer Text (Show answer first)
    st.markdown("### Answer")
    st.write(answer)

    # Sources List (Show sources below so users can verify)
    if sources:
        with st.expander(f"📚 Inspect Verified Sources ({len(sources)} documents)", expanded=False):
            for idx, src in enumerate(sources, start=1):
                source_name = src.get("source", "Unknown Source")
                chunk_id = src.get("chunk_id", "")
                section = src.get("section", "General")
                score = src.get("score")
                score_str = f" &bull; Relevance: {int(score * 100)}%" if score else ""
                
                st.markdown(f"**[{idx}] {source_name}** {f'(`{chunk_id}`)' if chunk_id else ''}{score_str}")
                st.caption(f"Section: {section} | Document Type: {src.get('doc_type', 'N/A')}")
                st.code(src.get("text", "No excerpt available."), language="text")
    elif status == "refused_weak_context":
        st.info("Zero Hallucination Guardrail: System withheld generation because no service manual chunks exceeded the minimum similarity threshold.")

# Handle User Input
user_input = st.chat_input("Ask a technical diagnostic question...")
active_prompt = starter_query or user_input

if active_prompt:
    # 1. Display and append user message
    st.session_state.messages.append({"role": "user", "content": active_prompt})
    with st.chat_message("user"):
        st.write(active_prompt)

    # 2. Call backend API with loading state (st.status)
    with st.chat_message("assistant"):
        with st.status("Thinking & retrieving automotive service context...", expanded=True) as status_box:
            status_box.write("1. Connecting to RAG /query API...")
            try:
                # Prepare conversation history turns
                history_turns = [
                    {"role": m["role"], "content": m["content"] if m["role"] == "user" else m["result"].get("answer", "")}
                    for m in st.session_state.messages[:-1]
                ]

                status_box.write("2. Performing vector similarity search & guardrail gating...")
                res = requests.post(
                    f"{api_base_url}/query",
                    json={"question": active_prompt, "history": history_turns},
                    timeout=30
                )

                if res.status_code == 200:
                    status_box.write("3. Verifying source citations & formatting response...")
                    result_data = res.json()
                    status_box.update(label="Diagnostic Response Ready", state="complete", expanded=False)
                    
                    # Render response
                    render_assistant_response(result_data)
                    st.session_state.messages.append({"role": "assistant", "result": result_data})
                else:
                    error_msg = f"API Error {res.status_code}: {res.text}"
                    status_box.update(label="Diagnostic Query Failed", state="error")
                    st.error(error_msg)
            except Exception as e:
                status_box.update(label="Connection Failure", state="error")
                st.error(f"Failed to communicate with RAG backend at `{api_base_url}`: {e}")
