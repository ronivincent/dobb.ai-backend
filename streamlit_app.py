import streamlit as st
import requests
import json
import time
from datetime import datetime

# Configure the Streamlit page
st.set_page_config(
    page_title="Dobb.ai Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = "http://127.0.0.1:8000"
CHATBOT_ENDPOINT = f"{API_BASE_URL}/chatbot/"

def check_api_health():
    """Check if the FastAPI server is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def send_message(message, conversation_history=None):
    """Send message to the chatbot API with conversation history"""
    try:
        # Prepare the request payload
        payload = {"message": message}
        
        # Add conversation history if available (exclude the current message)
        if conversation_history:
            # Filter out the current message and convert to API format
            history = []
            for msg in conversation_history[:-1]:  # Exclude the last message (current one)
                if msg["role"] in ["user", "assistant"]:
                    history.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            payload["history"] = history
        
        with st.spinner("🤖 Thinking..."):
            response = requests.post(
                CHATBOT_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
        
        if response.status_code == 200:
            response_data = response.json()
            return {
                "reply": response_data["reply"],
                "sources": response_data.get("sources", [])
            }
        else:
            return {
                "reply": f"❌ Error: {response.status_code} - {response.text}",
                "sources": []
            }
    
    except requests.exceptions.Timeout:
        return {
            "reply": "⏱️ Request timed out. The chatbot might be processing a complex request.",
            "sources": []
        }
    except requests.exceptions.ConnectionError:
        return {
            "reply": "🔌 Connection error. Make sure the FastAPI server is running on http://127.0.0.1:8000",
            "sources": []
        }
    except Exception as e:
        return {
            "reply": f"💥 Unexpected error: {str(e)}",
            "sources": []
        }

def display_sources(sources):
    """Display source information in an expandable section"""
    if sources and len(sources) > 0:
        with st.expander(f"📚 Sources ({len(sources)} documents)", expanded=False):
            for i, source in enumerate(sources):
                st.markdown(f"**Source {source['chunk_id']}:** {source['source']}")
                st.markdown(f"*Preview:* {source['content_preview']}")
                if i < len(sources) - 1:
                    st.divider()

def main():
    # Header
    st.title("🛒 E-commerce Platform Assistant")
    st.markdown("### AI Assistant for Your Online Shopping Platform")
    st.info("🔍 **RAG-Powered** - Ask questions about the e-commerce platform features, functionality, and user experience!")
    
    # Sidebar with help information
    with st.sidebar:
        st.header("🛒 Platform Assistant")
        
        st.markdown("""
        **🛍️ What I Can Help With**
        - Product catalog features
        - Shopping cart functionality
        - User account management
        - Order placement process
        - Platform capabilities
        
        **💡 How It Works**
        - Your question → Search knowledge base
        - Retrieve relevant information
        - Provide clear, user-friendly answers
        
        **🎯 Best Questions**
        - "How does the shopping cart work?"
        - "What user account features are available?"
        - "How do customers place orders?"
        - "What makes the platform secure?"
        
        **⚡ Features**
        - E-commerce focused responses
        - User experience explanations
        - Business value insights
        """)
        
        st.divider()
        
        # API Status
        st.header("📡 API Status")
        if check_api_health():
            st.success("✅ API is running")
        else:
            st.error("❌ API is not accessible")
            st.info("Start the API with: `uvicorn main:app --reload --port 8000`")
        
        st.divider()
        
        # Example prompts
        st.header("💡 Try These Examples")
        example_prompts = [
            "How does the shopping cart work?",
            "What features does the product catalog have?",
            "How do users manage their accounts?",
            "What is the order placement process?",
            "How secure is the platform?",
            "What makes the design user-friendly?",
            "How do customers browse products?",
            "What are the key platform benefits?"
        ]
        
        for prompt in example_prompts:
            if st.button(prompt, key=f"example_{hash(prompt)}", use_container_width=True):
                st.session_state.example_prompt = prompt

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": "Hi! I'm your e-commerce platform assistant. I can help you understand the platform's features, functionality, and user experience. Ask me about the shopping cart, product catalog, user accounts, or any other aspect of the platform!"
            }
        ]

    # Handle example prompts
    if "example_prompt" in st.session_state:
        st.session_state.messages.append({
            "role": "user",
            "content": st.session_state.example_prompt
        })
        
        # Get response with conversation history
        response_data = send_message(st.session_state.example_prompt, st.session_state.messages)
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_data["reply"],
            "sources": response_data.get("sources", []),
            "timestamp": datetime.now()
        })
        
        # Clear the example prompt
        del st.session_state.example_prompt
        st.rerun()

    # Display chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.write(message["content"])
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.write(message["content"])
                    # Display sources if available
                    if "sources" in message:
                        display_sources(message["sources"])
                    if "timestamp" in message:
                        st.caption(f"⏰ {message['timestamp'].strftime('%H:%M:%S')}")

    # Chat input
    if prompt := st.chat_input("Ask me about the e-commerce platform features, shopping experience, or functionality..."):
        # Add user message to chat history
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message immediately
        with st.chat_message("user", avatar="👤"):
            st.write(prompt)
        
        # Get and display assistant response
        with st.chat_message("assistant", avatar="🤖"):
            response_data = send_message(prompt, st.session_state.messages)
            st.write(response_data["reply"])
            # Display sources
            display_sources(response_data.get("sources", []))
            st.caption(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
        
        # Add assistant response to chat history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_data["reply"],
            "sources": response_data.get("sources", []),
            "timestamp": datetime.now()
        })

    # Clear chat button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = [
                {
                    "role": "assistant", 
                    "content": "Chat cleared! What would you like to know about the e-commerce platform?"
                }
            ]
            st.rerun()

    # Footer
    st.divider()
    st.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 0.8em;'>
            🛒 E-commerce Platform Assistant • Powered by Google Gemini & ChromaDB RAG
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
