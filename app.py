import streamlit as st
from chatbot import UBCCourseAssistant

# Page config
st.set_page_config(
    page_title="UBC Course Assistant",
    page_icon="🎓",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
.stChatMessage {
    padding: 1rem;
    border-radius: 0.5rem;
}
.source-box {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    margin-top: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'assistant' not in st.session_state:
    with st.spinner("Loading UBC Course Assistant..."):
        st.session_state.assistant = UBCCourseAssistant()

if 'messages' not in st.session_state:
    st.session_state.messages = []

# Header
st.title("🎓 UBC Course Assistant")
st.markdown("Ask me anything about UBC courses!")

# Sidebar
with st.sidebar:
    st.header("About")
    st.markdown("""
    This chatbot uses RAG (Retrieval-Augmented Generation) to answer questions about UBC courses.

    **Features:**
    - 500+ UBC courses indexed
    - Course information lookup
    - Semantic search
    - Source citations
    """)

    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.session_state.assistant.reset_conversation()
        st.rerun()

    st.markdown("---")
    st.markdown("**Example Questions:**")
    st.markdown("- What is CPSC 110 about?")
    st.markdown("- Give me all CPSC courses")
    st.markdown("- List math courses")
    st.markdown("- Tell me about machine learning courses")
    st.markdown("- What are intro CS courses?")

    st.markdown("---")
    st.markdown("**Tips:**")
    st.markdown("- Ask for 'all [DEPT] courses' to see a list")
    st.markdown("- Be specific for detailed info")
    st.markdown("- Check sources for full descriptions")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Show sources if available
        if "sources" in message and message["sources"]:
            with st.expander(f"📚 View {len(message['sources'])} Sources"):
                for i, source in enumerate(message["sources"], 1):
                    # Handle both dict and Document objects
                    if isinstance(source, dict):
                        course_code = source.get('code', 'N/A')
                        content = source.get('content', '')
                    else:
                        course_code = source.metadata.get('course_code', 'N/A')
                        content = source.page_content

                    st.markdown(f"**Source {i}: {course_code}**")
                    st.text(content[:300] + "..." if len(content) > 300 else content)
                    if i < len(message['sources']):
                        st.markdown("---")

# Chat input
if prompt := st.chat_input("Ask about UBC courses..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Get assistant response
    with st.chat_message("assistant"):
        with st.spinner("Searching courses..."):
            result = st.session_state.assistant.ask(prompt)

            st.markdown(result['answer'])

            # Show sources
            if result['sources']:
                with st.expander(f"📚 View {len(result['sources'])} Sources"):
                    for i, source in enumerate(result['sources'], 1):
                        # Handle both dict and Document objects
                        if isinstance(source, dict):
                            course_code = source.get('code', 'N/A')
                            content = source.get('content', '')
                        else:
                            course_code = source.metadata.get('course_code', 'N/A')
                            content = source.page_content

                        st.markdown(f"**Source {i}: {course_code}**")
                        st.text(content[:300] + "..." if len(content) > 300 else content)
                        if i < len(result['sources']):
                            st.markdown("---")

    # Add assistant message
    st.session_state.messages.append({
        "role": "assistant",
        "content": result['answer'],
        "sources": result['sources']
    })