# main.py 
import os
import json
import logging
import traceback
import time
from datetime import datetime
import streamlit as st

#css
st.markdown("""
<style>
    .block-container {
        max-width: 850px;
        margin: auto;
        padding-top: 2rem;
    }
    mark {
        background-color: #fff176;
        padding: 2px 4px;
        border-radius: 3px;
    }
    .source-box {
        background-color: #f8f9fa;
        border-left: 4px solid #4CAF50;
        padding: 12px;
        margin: 10px 0;
        border-radius: 4px;
        font-size: 0.9em;
        color: #111 !important;
    }
    .source-highlight {
        background-color: #fff176 !important;
        color: #111 !important;
        padding: 2px 4px;
        border-radius: 3px;
    }
    @media (prefers-color-scheme: dark) {
        .source-box { background-color: #1e1e1e !important; color: #e6e6e6 !important; border-left-color: #66bb6a !important; }
        .source-highlight { background-color: #444 !important; color: #fff !important; }
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------
# Safe Imports & Fallback Implementations
# ----------------------------------------------
try:
    from auth import AdvancedAuthSystem, initialize_session_state, render_login, render_user_management
    from core_rag import AdvancedRAGEngine 
    from admin_ops import AdminOperations, render_admin_interface
    from utils import AdvancedChatManager
except ImportError as e:
    logging.warning(f"Optional modules missing: {e}")

    # --- Simple Stand-in Classes (if missing) ---
    class AdvancedAuthSystem:
        def __init__(self):
            self.users = {"admin": "admin123", "user": "user123"}
            
        def authenticate(self, username, password):
            return username in self.users and self.users[username] == password
            
        def get_user_role(self, username):
            return "admin" if username == "admin" else "user"

    class AdminOperations:
        def __init__(self, rag_engine, pdf_storage_folder):
            self.rag_engine = rag_engine
            self.pdf_folder = pdf_storage_folder
            os.makedirs(pdf_storage_folder, exist_ok=True)

    class AdvancedChatManager:
        def __init__(self, base_path="data/chat_history"):
            self.base_path = base_path
            os.makedirs(base_path, exist_ok=True)
        
        def create_new_chat(self, username, topic=None):
            chat_id = f"chat_{int(time.time())}"
            if topic:
                chat_id = f"{topic}_{chat_id}"
            return chat_id
        
        def get_user_chats(self, username):
            return []
        
        def load_chat(self, username, chat_id):
            return []
        
        def add_message(self, username, chat_id, role, content):
            # REMOVED 'sources' parameter to fix TypeError
            return True
        
        def delete_chat(self, username, chat_id):
            return True

    # Fallback functions
    def initialize_session_state():
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'current_user' not in st.session_state:
            st.session_state.current_user = None
        if 'user_role' not in st.session_state:
            st.session_state.user_role = 'user'
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'current_chat_id' not in st.session_state:
            st.session_state.current_chat_id = None

    def render_login(auth_system):
        st.title("🔐 Login to Enterprise RAG System")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username and password:
                if auth_system.authenticate(username, password):
                    st.session_state.authenticated = True
                    st.session_state.current_user = username
                    st.session_state.user_role = auth_system.get_user_role(username)
                    st.success("✅ Logged in successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
            else:
                st.error("❌ Please enter both username and password.")

    def render_user_management(auth_system):
        st.title("👥 User Management (Demo)")
        st.info("Add or manage users here. (Feature in progress)")

    def render_admin_interface(admin_ops, auth_system):
        st.title("👨‍💼 Admin Portal - PDF Management")
        
        # PDF Upload Section
        st.subheader("📤 Upload and Process PDF")
        uploaded_file = st.file_uploader(
            "Choose PDF file", 
            type="pdf",
            help="Drag and drop file here • Limit 200MB per file • PDF"
        )
        
        if uploaded_file is not None:
            # Save uploaded file
            file_path = os.path.join(admin_ops.pdf_folder, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Display file info
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("File", uploaded_file.name)
            with col2:
                st.metric("Size", f"{uploaded_file.size / 1024 / 1024:.2f} MB")
            with col3:
                st.metric("Type", "PDF Document")
            
            # Process PDF
            if st.button("🔄 Process PDF", type="primary"):
                with st.spinner("Processing PDF..."):
                    success, message = admin_ops.rag_engine.process_pdf(file_path, uploaded_file.name)
                    if success:
                        st.success(message)
                        st.balloons()
                    else:
                        st.error(message)
        
        # Processed Documents Section
        st.subheader("📚 Processed Documents")
        try:
            processed_docs = admin_ops.rag_engine.get_processed_pdfs()
            
            if processed_docs:
                for doc in processed_docs:
                    doc_info = admin_ops.rag_engine.get_document_info(doc)
                    with st.expander(f"📄 {doc}", expanded=False):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Chunks", doc_info.get('chunk_count', 0))
                        with col2:
                            st.metric("Status", "Processed")
                        with col3:
                            if st.button(f"🗑️ Delete", key=f"delete_{doc}"):
                                success, msg = admin_ops.rag_engine.delete_pdf(doc)
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
            else:
                st.info("📝 No documents processed yet. Upload a PDF to get started!")
                
        except Exception as e:
            st.error(f"Error loading documents: {e}")

# ------------------------------------------
# Logging Setup
# ------------------------------------------
os.makedirs("data", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("data/app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ------------------------------------------
# Streamlit Page Setup
# ------------------------------------------
st.set_page_config(
    page_title="Enterprise RAG System",
    layout="wide",
    page_icon="🚀",
    initial_sidebar_state="expanded"
)

# ------------------------------------------
# Component Initialization - UPDATED for Ollama
# ------------------------------------------
@st.cache_resource(show_spinner="🚀 Initializing Components...")
def initialize_components():
    try:
        os.makedirs("data/uploaded_pdfs", exist_ok=True)
        os.makedirs("data/chroma_db_fixed", exist_ok=True)
        os.makedirs("data/chat_history", exist_ok=True)

        # REMOVED OpenAI API key check - we use Ollama instead
        auth_system = AdvancedAuthSystem()
        rag_engine = AdvancedRAGEngine("data/chroma_db_fixed")
        admin_ops = AdminOperations(rag_engine, "data/uploaded_pdfs")
        chat_manager = AdvancedChatManager()

        logger.info("✅ All components initialized successfully with Ollama")
        return auth_system, rag_engine, admin_ops, chat_manager
    except Exception as e:
        logger.error(f"Component initialization failed: {e}")
        st.error(f"Initialization failed: {e}")
        return None, None, None, None

# Initialize components
auth_system, rag_engine, admin_ops, chat_manager = initialize_components()

# ------------------------------------------
# REMOVED API Key Setup Section - No OpenAI needed
# ------------------------------------------

# ------------------------------------------
# Enhanced Sidebar with Chat History - UPDATED
# ------------------------------------------
def render_sidebar():
    st.sidebar.title("🧭 Navigation")

    st.sidebar.markdown(f"""
    **User:** {st.session_state.get('current_user', 'Unknown')}
    
    **Role:** {st.session_state.get('user_role', 'user').capitalize()}
    """)

    st.sidebar.markdown("---")

    # System Status - UPDATED for Ollama
    if rag_engine:
        try:
            status = rag_engine.get_system_status()
            st.sidebar.metric("Documents", status.get("documents_processed", 0))
            st.sidebar.metric("Chunks", status.get("chunks_indexed", 0))
            
            # Show AI Engine status instead of OpenAI
            ai_engine = status.get("ai_intelligence", "Ollama")
            ollama_status = status.get("ollama_status", "Ready")
            status_color = "🟢" if "Ready" in ollama_status else "🔴"
            st.sidebar.metric("AI Engine", f"{status_color} {ai_engine}")
            
        except Exception as e:
            st.sidebar.error("Status unavailable")
    else:
        st.sidebar.warning("RAG Engine not initialized")

    st.sidebar.markdown("---")
    
    # Chat History Section
    st.sidebar.markdown("### 💬 Chat History")
    
    # New Chat button
    if st.sidebar.button("🆕 New Chat", use_container_width=True, type="primary"):
        # Reset chat state
        if 'current_chat_id' in st.session_state:
            del st.session_state.current_chat_id
        if 'messages' in st.session_state:
            st.session_state.messages = []
        st.rerun()
    
    # Get user chats
    if chat_manager and st.session_state.current_user:
        try:
            user_chats = chat_manager.get_user_chats(st.session_state.current_user)
            
            if user_chats:
                st.sidebar.markdown("**Your Chats:**")
                for chat in user_chats:
                    chat_col, del_col = st.sidebar.columns([4, 1])
                    
                    with chat_col:
                        # Display chat topic as button
                        if st.sidebar.button(
                            f"💬 {chat.get('topic', 'Unknown')[:20]}{'...' if len(chat.get('topic', '')) > 20 else ''}", 
                            key=f"load_{chat.get('id', 'unknown')}",
                            use_container_width=True
                        ):
                            st.session_state.current_chat_id = chat.get('id')
                            st.session_state.messages = chat_manager.load_chat(st.session_state.current_user, chat.get('id'))
                            st.rerun()
                    
                    with del_col:
                        # Delete button
                        if st.sidebar.button("🗑️", key=f"del_{chat.get('id', 'unknown')}"):
                            if chat_manager.delete_chat(st.session_state.current_user, chat.get('id')):
                                st.sidebar.success("Chat deleted!")
                                st.rerun()
            else:
                st.sidebar.info("No previous chats")
        except Exception as e:
            st.sidebar.warning("Chat history unavailable")
    
    st.sidebar.markdown("---")
    
    # System Actions
    if st.sidebar.button("🔄 Refresh System", use_container_width=True):
        st.rerun()

    if rag_engine and st.sidebar.button("🧹 Clear Cache", use_container_width=True):
        try:
            rag_engine.clear_cache()
            st.sidebar.success("Cache cleared!")
            st.rerun()
        except Exception as e:
            st.sidebar.error("Cache clear failed")

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True, type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ------------------------------------------
# Enhanced User Chat Interface - FIXED VERSION
# ------------------------------------------
def render_user_interface():
    st.title("💬 Chat with Your Documents")
    
    # Check if RAG engine is available
    if not rag_engine:
        st.error("❌ RAG Engine not initialized. Please check system configuration.")
        return
    
    # Check AI Engine status - UPDATED for Ollama
    try:
        status = rag_engine.get_system_status()
        ollama_ready = "Ready" in status.get("ollama_status", "")
        ai_engine = status.get("ai_intelligence", "Ollama")
        
        if ollama_ready:
            st.success(f"🚀 {ai_engine} is ready! Asking intelligent questions about your documents.")
        else:
            st.warning("⚠️ Ollama not available. Using basic search mode.")
            st.info("💡 **For AI-powered answers:** Make sure Ollama is running with 'ollama serve'")
    except Exception as e:
        st.error(f"❌ Error checking system status: {e}")
        ollama_ready = False
    
    # Check if documents are available
    try:
        docs_available = status.get("documents_processed", 0) > 0
    except Exception as e:
        st.error(f"❌ Error checking documents: {e}")
        docs_available = False
    
    if not docs_available:
        st.error("📭 No documents available. Please ask an admin to upload PDF files.")
        st.info("💡 **Available actions:**")
        st.write("- Contact administrator to upload documents")
        st.write("- Use demo documents if available")
        # Don't return - allow user to still use the interface
    
    if docs_available:
        st.success(f"✅ {status.get('documents_processed', 0)} documents loaded! Ask me anything about your documents.")
    
    # Initialize or load chat
    if 'current_chat_id' not in st.session_state or not st.session_state.current_chat_id:
        # Create new chat
        chat_topic = st.text_input(
            "🎯 **Chat Topic**", 
            placeholder="e.g., Student Records, Project Discussion, etc.",
            help="Give a name to this conversation"
        )
        if not chat_topic:
            chat_topic = f"Chat {datetime.now().strftime('%H:%M')}"
        
        if chat_manager:
            st.session_state.current_chat_id = chat_manager.create_new_chat(
                st.session_state.current_user, chat_topic
            )
        else:
            st.session_state.current_chat_id = f"chat_{int(time.time())}"
        
        st.session_state.messages = []
    
    # Display current chat topic
    if st.session_state.current_chat_id:
        st.markdown(f"**Current Topic:** `{st.session_state.current_chat_id}`")
    
    # Display chat messages
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display existing messages with sources
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show sources if they exist
            if message["role"] == "assistant" and "sources" in message:
                with st.expander("📚 View Sources", expanded=False):
                    for i, source in enumerate(message["sources"]):
                        st.markdown(f"""
                        <div class="source-box">
                        <b>Source {i+1} (Relevance: {source.get('relevance_score', 0)}%)</b><br>
                        <i>Document: {source.get('pdf_name', 'Unknown')}</i><br><br>
                        {source.get('content_preview', '')}
                        </div>
                        """, unsafe_allow_html=True)
    
    # Chat input
    query = st.chat_input("Ask a question about your documents...")
    
    if query:
        # Add user message to chat
        user_message = {"role": "user", "content": query}
        st.session_state.messages.append(user_message)
        if chat_manager:
            chat_manager.add_message(
                st.session_state.current_user, 
                st.session_state.current_chat_id, 
                "user", 
                query
            )
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(query)
        
        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("🔍 Searching documents..."):
                try:
                    # Get response - FIXED: Handle different return formats
                    search_result = rag_engine.search(query)
                    
                    # Check what format is returned
                    if isinstance(search_result, tuple):
                        if len(search_result) == 4:
                            # New format: (answer, contexts, source_doc, source_details)
                            answer, contexts, source_doc, source_details = search_result
                        elif len(search_result) == 3:
                            # Old format: (answer, chunks, source)
                            answer, contexts, source_doc = search_result
                            source_details = []
                            if contexts:
                                # Create basic source details
                                for i, context in enumerate(contexts[:3]):
                                    source_details.append({
                                        "source_number": i + 1,
                                        "pdf_name": source_doc if source_doc else "Unknown",
                                        "relevance_score": 100 - (i * 20),  # Approximate score
                                        "content_preview": (context[:200] + "...") if len(context) > 200 else context,
                                        "content_length": len(context)
                                    })
                        else:
                            # Unknown format
                            answer = str(search_result[0]) if search_result else "No answer returned"
                            source_details = []
                    else:
                        # Single return value
                        answer = search_result
                        source_details = []
                    
                    # Display answer
                    st.markdown(answer)
                    
                    # Create assistant message with sources
                    assistant_message = {
                        "role": "assistant", 
                        "content": answer,
                        "sources": source_details
                    }
                    
                    # Display sources if available
                    if source_details and len(source_details) > 0:
                        with st.expander("📚 View Sources", expanded=False):
                            for i, source in enumerate(source_details[:3]):
                                st.markdown(f"""
                                <div class="source-box">
                                <b>Source {i+1} (Relevance: {source.get('relevance_score', 0)}%)</b><br>
                                <i>Document: {source.get('pdf_name', 'Unknown')}</i><br>
                                <i>Content Length: {source.get('content_length', 0)} characters</i><br><br>
                                {source.get('content_preview', '')}
                                </div>
                                """, unsafe_allow_html=True)
                    
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.markdown(error_msg)
                    answer = error_msg
                    source_details = []
                    logger.error(f"Search error: {e}")
                    
                    assistant_message = {
                        "role": "assistant", 
                        "content": answer,
                        "sources": []
                    }
        
        # Add assistant response to chat
        st.session_state.messages.append(assistant_message)
        if chat_manager:
            # FIXED: Don't pass 'sources' parameter
            chat_manager.add_message(
                st.session_state.current_user, 
                st.session_state.current_chat_id, 
                "assistant", 
                answer
            )
        
        st.rerun()

# ------------------------------------------
# Main Controller - UPDATED
# ------------------------------------------
def main():
    # Initialize session state
    initialize_session_state()

    if not st.session_state.authenticated:
        render_login(auth_system)
        return

    # REMOVED API key check - no OpenAI needed
    
    render_sidebar()

    if st.session_state.user_role == "admin":
        render_admin_interface(admin_ops, auth_system)
    else:
        render_user_interface()

# ------------------------------------------
# Safe Execution
# ------------------------------------------
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Critical Error: {e}")
        st.error(f"🚨 Application crashed: {e}")
        st.text_area("Traceback", traceback.format_exc(), height=300)