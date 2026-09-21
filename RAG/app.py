"""
Streamlit chat interface for the JW Marriott Bengaluru hotel assistant.

Launch:
    streamlit run app.py

First-time setup (run once to build the vector DB):
    python ingest.py
"""

import os
import streamlit as st
from rag_chain import HotelRAG

st.set_page_config(
    page_title="JW Marriott Bengaluru — Hotel Assistant",
    page_icon="🏨",
    layout="wide",
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/JW_Marriott_logo.svg/320px-JW_Marriott_logo.svg.png",
        width=160,
    )
    st.markdown("## JW Marriott Bengaluru\n**Hotel Concierge Assistant**")
    st.markdown("---")
    st.markdown(
        "Ask me anything about:\n"
        "- 🛏️ Room types & prices\n"
        "- 🍽️ Dining options\n"
        "- 🏊 Amenities & Spa\n"
        "- 📍 Location & transport\n"
        "- 📋 Hotel policies\n"
        "- 🎉 Events & packages"
    )
    st.markdown("---")

    with st.expander("⚙️ Settings"):
        hf_token_input = st.text_input(
            "HuggingFace token (optional, free)",
            type="password",
            placeholder="hf_... — get free at huggingface.co/settings/tokens",
            help=(
                "Paste a free HuggingFace token for LLM-generated answers "
                "(uses google/flan-t5-base hosted on HF — no download). "
                "Without a token the assistant uses smart retrieval mode."
            ),
        )
        show_sources = st.toggle("Show source documents", value=False)

    st.markdown("---")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.caption("Powered by HuggingFace · ChromaDB · LangChain")

# ── Load RAG (cached across reruns) ───────────────────────────────────────────
@st.cache_resource(show_spinner="Loading hotel knowledge base...")
def load_rag() -> HotelRAG:
    chroma_dir = "chroma_db"
    if not os.path.exists(chroma_dir):
        st.error(
            "Vector database not found. Run `python ingest.py` first to build it.",
            icon="⚠️",
        )
        st.stop()
    return HotelRAG()


rag = load_rag()

# ── Chat history ───────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Welcome to JW Marriott Bengaluru! 🏨\n\n"
                "I'm your virtual concierge. How may I assist you today? "
                "Feel free to ask about our rooms, dining, spa, amenities, or anything else about the hotel."
            ),
        }
    ]

# ── Main area ─────────────────────────────────────────────────────────────────
st.title("🏨 JW Marriott Bengaluru — Hotel Concierge")
st.caption("Your AI-powered hotel assistant — ask anything about the hotel")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if show_sources and msg.get("sources"):
            with st.expander("📄 Source documents used"):
                for i, src in enumerate(msg["sources"], 1):
                    st.markdown(f"**[{i}] {src['name']} ({src['category']})**")
                    st.code(src["content"], language=None)

# ── User input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about rooms, dining, amenities, location..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Looking up hotel information..."):
            answer, source_docs = rag.ask(prompt, hf_token=hf_token_input)

        st.markdown(answer)

        sources_data = [
            {
                "name": doc.metadata.get("name", "Unknown"),
                "category": doc.metadata.get("category", ""),
                "content": doc.page_content[:600] + ("..." if len(doc.page_content) > 600 else ""),
            }
            for doc in source_docs
        ]

        if show_sources and sources_data:
            with st.expander("📄 Source documents used"):
                for i, src in enumerate(sources_data, 1):
                    st.markdown(f"**[{i}] {src['name']} ({src['category']})**")
                    st.code(src["content"], language=None)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": sources_data}
    )
