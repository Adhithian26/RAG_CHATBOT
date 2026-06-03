 # main.py 
import os
import json
import logging
import traceback
import time
from datetime import datetime
import streamlit as st
from streamlit_cookies_manager import CookieManager
import pyttsx3
import threading
from gtts import gTTS
import tempfile
import os
import pygame

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
    from auth import AdvancedAuthSystem, render_user_management, render_manager_portal
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
        
        def _verify_jwt_token(self, token):
            """Fallback JWT verification"""
            try:
                import jwt
                payload = jwt.decode(token, "your-secret-key-change-in-production", algorithms=["HS256"])
                return payload
            except:
                return None

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

# ------------------------------------------
# Text-to-Speech Functions
# ------------------------------------------
tts_engine_global = None
is_speaking = False

@st.cache_resource
def initialize_tts_engine():
    """Initialize pyttsx3 TTS engine"""
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        if voices:
            engine.setProperty('voice', voices[0].id)
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        return engine
    except Exception as e:
        logger.warning(f"TTS initialization failed: {e}")
        return None

def speak_text(text, engine=None):
    """Speak text using TTS"""
    global is_speaking
    
    if is_speaking:
        return False  # Already speaking
    
    try:
        # Clean text: remove markdown, HTML, etc
        clean_text = text.replace('**', '').replace('*', '').replace('##', '').replace('#', '')
        clean_text = clean_text[:500]  # Limit to 500 chars for speed
        
        is_speaking = True
        
        def speak_thread():
            global is_speaking
            try:
                try:
                    pygame.mixer.init()
                except:
                    pass
                tts = gTTS(text=clean_text, lang='en', slow=False)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                    temp_file = f.name
                tts.save(temp_file)
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)
                os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"TTS speak thread failed: {e}")
            finally:
                is_speaking = False
        
        # Start speaking in a separate thread
        thread = threading.Thread(target=speak_thread, daemon=True)
        thread.start()
        
        return True
    except Exception as e:
        logger.warning(f"TTS speak failed: {e}")
        is_speaking = False
        return False

def stop_speak():
    """Stop current TTS playback"""
    global is_speaking, tts_engine_global
    
    if tts_engine_global:
        try:
            tts_engine_global.stop()
            is_speaking = False
            return True
        except Exception as e:
            logger.warning(f"TTS stop failed: {e}")
            return False
    return False

# ------------------------------------------
# Session State & Authentication Functions
# ------------------------------------------
def initialize_session_state(cookies_manager):
    """Initialize and restore session state - SIMPLE AND RELIABLE"""
    global auth_system
    
    # Initialize all session state variables
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
    if 'session_token' not in st.session_state:
        st.session_state.session_token = None
    
    # PRIORITY 1: Check URL query parameters ONLY
    # Do NOT load from file to prevent auto-login
    query_params = st.query_params
    if 'token' in query_params and 'user' in query_params and 'role' in query_params:
        token = query_params.get('token', '')
        username = query_params.get('user', '')
        role = query_params.get('role', 'user')
        
        if token and username:
            st.session_state.authenticated = True
            st.session_state.current_user = username
            st.session_state.user_role = role
            st.session_state.session_token = token
            logger.info(f"✅ Session RESTORED from URL: {username}")
            return
    
    # If we reach here, user is not authenticated - show login page
    logger.info("No valid URL session - user must login")

def render_login(auth_system_param, cookies_manager):
    st.title("🔐 Login to RAG AI System")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username and password:
            auth_result = auth_system_param.authenticate(username, password)
            if isinstance(auth_result, tuple):
                success, role, error_msg = auth_result
            else:
                success = auth_result
                role = auth_system_param.get_user_role(username) if auth_result else None
            
            if success:
                st.session_state.authenticated = True
                st.session_state.current_user = username
                st.session_state.user_role = role or auth_system_param.get_user_role(username)
                
                # Generate and store session token
                try:
                    token = auth_system_param._generate_jwt_token(username, st.session_state.user_role)
                    st.session_state.session_token = token
                    
                    # Save to URL query parameters (PRIMARY - survives refresh)
                    st.query_params['token'] = token
                    st.query_params['user'] = username
                    st.query_params['role'] = st.session_state.user_role
                    
                    # Save to FILE as backup
                    save_session_to_file(username, token, st.session_state.user_role)
                    
                    # Also save to cookie as backup
                    if cookies_manager:
                        try:
                            cookies_manager['session_token'] = token
                            cookies_manager.save()
                        except:
                            pass
                    
                    logger.info(f"✅ Session created for {username} (URL params, file, cookie)")
                except Exception as e:
                    logger.warning(f"Could not generate JWT token: {e}")
                
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
        else:
            st.error("❌ Please enter both username and password.")

def render_manager_portal_fallback(auth_system):
    st.title("👔 Manager Portal (Demo)")
    st.info("Add or manage users here. (Feature in progress)")

def render_admin_interface_fallback(admin_ops, auth_system):
    st.title("👨 Admin Portal - PDF Management")
    
    # PDF Upload Section
    st.subheader(" Upload and Process PDF")
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
        st.success(f" File uploaded: {uploaded_file.name}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("File", uploaded_file.name)
        with col2:
            st.metric("Size", f"{uploaded_file.size / 1024 / 1024:.2f} MB")
        with col3:
            st.metric("Type", "PDF Document")
        
        # Process PDF
        if st.button(" Process PDF", type="primary"):
            with st.spinner("Processing PDF..."):
                success, message = admin_ops.rag_engine.process_pdf(file_path, uploaded_file.name)
                if success:
                    st.success(message)
                    st.balloons()
                else:
                    st.error(message)
    
    # Processed Documents Section
    st.subheader("Processed Documents")
    try:
        processed_docs = admin_ops.rag_engine.get_processed_pdfs()
        
        if processed_docs:
            for doc in processed_docs:
                doc_info = admin_ops.rag_engine.get_document_info(doc)
                with st.expander(f" {doc}", expanded=False):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Chunks", doc_info.get('chunk_count', 0))
                    with col2:
                        st.metric("Status", "Processed")
                    with col3:
                        if st.button(f"👁️ View", key=f"view_{doc}"):
                            st.session_state.view_chunks_pdf = doc
                            st.rerun()
                    with col4:
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
    
    # Chunk Inspection Section
    st.markdown("---")
    st.subheader("📊 View Chunks")
    
    try:
        view_option = st.radio(
            "View chunks from:",
            ["All PDFs", "Specific PDF"],
            horizontal=True
        )
        
        if view_option == "Specific PDF":
            if processed_docs:
                selected_pdf = st.selectbox(
                    "Select PDF to inspect:",
                    processed_docs
                )
                
                if st.button("📖 Display Chunks", use_container_width=True):
                    chunks = admin_ops.rag_engine.get_chunks_for_pdf(selected_pdf)
                    if chunks:
                        st.success(f"Found {len(chunks)} chunks in '{selected_pdf}'")
                        
                        # Display chunks with tabs for easy navigation
                        for idx, chunk in enumerate(sorted(chunks, key=lambda x: x.get("chunk_id", 0))):
                            with st.expander(f"📄 Chunk {chunk.get('chunk_id', idx)} ({chunk.get('length', 0)} chars)", expanded=(idx == 0)):
                                st.markdown(chunk.get("content", ""))
                                st.caption(f"ID: {chunk.get('id', 'unknown')}")
                    else:
                        st.warning(f"No chunks found for {selected_pdf}")
            else:
                st.info("No documents available")
        
        else:  # All PDFs
            all_chunks = admin_ops.rag_engine.get_all_chunks()
            if all_chunks:
                st.success(f"Found {sum(len(chunks) for chunks in all_chunks.values())} total chunks across {len(all_chunks)} PDFs")
                
                for pdf_name in sorted(all_chunks.keys()):
                    chunks = all_chunks[pdf_name]
                    with st.expander(f"📚 {pdf_name} ({len(chunks)} chunks)", expanded=False):
                        total_chars = sum(c.get("length", 0) for c in chunks)
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Chunks", len(chunks))
                        with col2:
                            st.metric("Total Size", f"{total_chars:,} chars")
                        with col3:
                            st.metric("Avg Size", f"{total_chars // len(chunks) if chunks else 0} chars")
                        
                        st.markdown("---")
                        
                        # Display individual chunks
                        for idx, chunk in enumerate(sorted(chunks, key=lambda x: x.get("chunk_id", 0))):
                            with st.expander(f"  Chunk {chunk.get('chunk_id', idx)} ({chunk.get('length', 0)} chars)"):
                                st.markdown(chunk.get("content", ""))
                                st.caption(f"ID: {chunk.get('id', 'unknown')}")
            else:
                st.info("No chunks available yet. Process some PDFs first!")
            
    except Exception as e:
        st.error(f"Error viewing chunks: {e}")

# ------------------------------------------
# Session Management - File-based (Reliable)
# ------------------------------------------
SESSION_FILE = "data/current_session.json"

def save_session_to_file(username, token, role):
    """Save session to file for persistence"""
    try:
        session_data = {
            "username": username,
            "token": token,
            "role": role,
            "created_at": datetime.now().isoformat()
        }
        with open(SESSION_FILE, 'w') as f:
            json.dump(session_data, f)
        logger.info(f"✅ Session saved for {username}")
    except Exception as e:
        logger.error(f"Failed to save session: {e}")

def load_session_from_file():
    """Load session from file"""
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load session: {e}")
    return None

def clear_session_file():
    """Clear saved session"""
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        logger.info("✅ Session cleared")
    except Exception as e:
        logger.warning(f"Failed to clear session: {e}")

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
# Initialize CookieManager (optional backup)
# ------------------------------------------
try:
    cookies = CookieManager()
except Exception as e:
    logger.warning(f"CookieManager not available: {e}")
    cookies = None

# ------------------------------------------
# Streamlit Page Setup
# ------------------------------------------
st.set_page_config(
    page_title="RAG AI System",
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


# Enhanced Sidebar with Chat History - UPDATED
# ------------------------------------------
def render_sidebar(cookies_manager):
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
                # Create a container for chat history with wrapping
                chat_container = st.sidebar.container()
                
                for chat in user_chats:
                    # Display each chat as a row with load and delete buttons
                    col1, col2 = chat_container.columns([5, 1], gap="small")
                    
                    with col1:
                        chat_label = f"💬 {chat.get('topic', 'Unknown')}"
                        if len(chat_label) > 25:
                            chat_label = chat_label[:22] + "..."
                        if chat_container.button(
                            chat_label, 
                            key=f"load_{chat.get('id', 'unknown')}",
                            use_container_width=True
                        ):
                            st.session_state.current_chat_id = chat.get('id')
                            st.session_state.messages = chat_manager.load_chat(st.session_state.current_user, chat.get('id'))
                            st.rerun()
                    
                    with col2:
                        # Delete button
                        if chat_container.button("🗑️", key=f"del_{chat.get('id', 'unknown')}", use_container_width=True):
                            if chat_manager.delete_chat(st.session_state.current_user, chat.get('id')):
                                st.sidebar.success("Chat deleted!")
                                st.rerun()
            else:
                st.sidebar.info("No previous chats")
        except Exception as e:
            st.sidebar.warning("Chat history unavailable")
    
    # Follow-up questions toggle
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ AI Settings")
    if "enable_followups" not in st.session_state:
        st.session_state.enable_followups = True
    st.session_state.enable_followups = st.sidebar.toggle(
        "🔄 Follow-up Suggestions",
        value=st.session_state.enable_followups,
        help="Generate clickable follow-up questions after each answer (adds ~3s)"
    )

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
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Clear URL query parameters
        st.query_params.clear()
        
        # Clear session file
        clear_session_file()
        
        # Clear session cookie
        if cookies_manager:
            try:
                cookies_manager.delete('session_token')
                cookies_manager.save()
            except Exception as e:
                logger.warning(f"Could not clear cookie: {e}")
        
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
    
    # Initialize or load chat - CHATGPT STYLE (no topic input)
    if 'current_chat_id' not in st.session_state or not st.session_state.current_chat_id:
        # Auto-create new chat (title will be generated from first message)
        if chat_manager:
            st.session_state.current_chat_id = chat_manager.create_new_chat(
                st.session_state.current_user
            )
        else:
            st.session_state.current_chat_id = f"chat_{int(time.time())}"
        
        st.session_state.messages = []
        st.session_state.chat_title_generated = False  # Track if title was generated
    
    # Display current chat title dynamically
    if st.session_state.current_chat_id:
        # Check if title was generated or still using timestamp
        if not st.session_state.chat_title_generated and "chat_" in st.session_state.current_chat_id:
            st.markdown("**🆕 New Conversation**")
        else:
            st.markdown(f"**{st.session_state.current_chat_id.replace('_', ' ')}**")
    
    # Display chat messages
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    
    # Display existing messages with sources
    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Add speak button for assistant messages
            if message["role"] == "assistant":
                if st.button("🔊 Speak", key=f"speak_history_{idx}"):
                    if speak_text(message["content"]):
                        st.success("✅ Speaking!")
                    else:
                        st.warning("⚠️ Could not speak")
            
            # Show sources if they exist
            if message["role"] == "assistant" and "sources" in message:
                with st.expander("📚 View Sources", expanded=False):
                    for i, source in enumerate(message["sources"]):
                        st.markdown(f"""
                        <div class="source-box">
                        <b>Source {i+1} (Relevance: {source.get('relevance_score', 0)}%)</b><br>
                        <i>Document: {source.get('pdf_name', 'Unknown')}</i><br><br>
                        
                        </div>
                        """, unsafe_allow_html=True)
    
    # Chat input
    query = st.chat_input("Ask a question about your documents...")
    
    if query:
        # CHATGPT STYLE: If this is first message, generate title from it
        if not st.session_state.get('chat_title_generated', False) and chat_manager:
            # Generate title from first message (first 50 chars or first sentence)
            title = query.split('?')[0].split('.')[0][:50].strip()
            if not title:
                title = query[:50]
            
            # Rename chat file with generated title
            new_chat_id = chat_manager.update_chat_title(
                st.session_state.current_user,
                st.session_state.current_chat_id,
                title
            )
            st.session_state.current_chat_id = new_chat_id
            st.session_state.chat_title_generated = True
        
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
                    # FEATURE 1: Pass conversation history for memory
                    # Defensive call: fall back if cached engine has old signature
                    try:
                        search_result = rag_engine.search(
                            query,
                            chat_history=st.session_state.messages
                        )
                    except TypeError:
                        search_result = rag_engine.search(query)

                    # Handle new 5-tuple format
                    if isinstance(search_result, tuple) and len(search_result) == 5:
                        answer, contexts, source_doc, confidence_pct, sentiment = search_result
                        source_details = []
                        if contexts:
                            for i, context in enumerate(contexts[:3]):
                                source_details.append({
                                    "source_number": i + 1,
                                    "pdf_name": source_doc if source_doc else "Unknown",
                                    "relevance_score": round(confidence_pct),
                                    "content_length": len(context)
                                })
                    elif isinstance(search_result, tuple) and len(search_result) == 4:
                        answer, contexts, source_doc, source_details = search_result
                        confidence_pct, sentiment = 50.0, "neutral"
                    elif isinstance(search_result, tuple) and len(search_result) == 3:
                        answer, contexts, source_doc = search_result
                        confidence_pct, sentiment, source_details = 50.0, "neutral", []
                    else:
                        answer = str(search_result)
                        confidence_pct, sentiment, source_details = 50.0, "neutral", []

                    # Display answer
                    st.markdown(answer)

                    # ── FEATURE 3: Confidence badge ──────────────────────────
                    if confidence_pct >= 65:
                        badge_color, badge_label = "#22c55e", "🟢 High Confidence"
                    elif confidence_pct >= 35:
                        badge_color, badge_label = "#f59e0b", "🟡 Medium Confidence"
                    else:
                        badge_color, badge_label = "#ef4444", "🔴 Low Confidence"

                    # ── FEATURE 2: Sentiment emoji ────────────────────────────
                    sentiment_icon = {
                        "frustrated": "😤", "confused": "🤔",
                        "positive": "😊", "neutral": "😐"
                    }.get(sentiment, "😐")

                    st.markdown(
                        f"""
                        <div style='display:flex; gap:12px; align-items:center; 
                                    margin:6px 0 12px 0; font-size:0.82rem;'>
                            <span style='background:{badge_color}22; color:{badge_color};
                                         border:1px solid {badge_color}55;
                                         border-radius:20px; padding:2px 10px;'>
                                {badge_label} ({confidence_pct:.0f}%)
                            </span>
                            <span title='Detected tone' style='opacity:0.7;'>
                                Tone detected: {sentiment_icon} {sentiment.capitalize()}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if confidence_pct < 35:
                        st.caption(
                            "⚠️ I'm not fully confident in this answer — "
                            "you may want to verify with the source document."
                        )

                    # Add speak button
                    if st.button("🔊 Speak Answer", key=f"speak_{int(time.time())}"):
                        with st.spinner("🗣️ Speaking..."):
                            if speak_text(answer):
                                st.success("✅ Answer spoken!")
                            else:
                                st.warning("⚠️ Could not speak answer")

                    # Display sources if available
                    if source_details:
                        with st.expander("📚 View Sources", expanded=False):
                            for i, source in enumerate(source_details[:3]):
                                st.markdown(f"""
                                <div class="source-box">
                                <b>Source {i+1} (Relevance: {source.get('relevance_score', 0)}%)</b><br>
                                <i>Document: {source.get('pdf_name', 'Unknown')}</i><br>
                                <i>Content Length: {source.get('content_length', 0)} characters</i>
                                </div>
                                """, unsafe_allow_html=True)

                    # ── FEATURE 4: Follow-up question chips ──────────────────
                    if st.session_state.get("enable_followups", True) and contexts:
                        with st.spinner("💡 Generating follow-up suggestions..."):
                            followups = rag_engine.generate_followup_questions(
                                query, answer, contexts
                            )
                        if followups:
                            st.markdown("**💡 You might also ask:**")
                            cols = st.columns(len(followups))
                            for col, fq in zip(cols, followups):
                                with col:
                                    if st.button(
                                        fq,
                                        key=f"fq_{hash(fq)}_{int(time.time())}",
                                        use_container_width=True
                                    ):
                                        st.session_state["_prefill_query"] = fq
                                        st.rerun()

                    assistant_message = {
                        "role": "assistant",
                        "content": answer,
                        "sources": source_details,
                        "confidence": confidence_pct,
                        "sentiment": sentiment
                    }

                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.markdown(error_msg)
                    answer = error_msg
                    source_details = []
                    confidence_pct = 0.0
                    sentiment = "neutral"
                    logger.error(f"Search error: {e}")
                    assistant_message = {
                        "role": "assistant",
                        "content": answer,
                        "sources": [],
                        "confidence": 0.0,
                        "sentiment": "neutral"
                    }

        # Add assistant response to chat
        st.session_state.messages.append(assistant_message)
        if chat_manager:
            chat_manager.add_message(
                st.session_state.current_user,
                st.session_state.current_chat_id,
                "assistant",
                answer,
                sources=source_details
            )

        st.rerun()

# ------------------------------------------
# Main Controller - UPDATED
# ------------------------------------------
def main():
    # Use the global cookies object that was initialized at app startup
    global cookies
    
    # Initialize session state with cookie support
    initialize_session_state(cookies)

    if not st.session_state.authenticated:
        render_login(auth_system, cookies)
        return

    # REMOVED API key check - no OpenAI needed
    
    render_sidebar(cookies)

    if st.session_state.user_role == "admin":
        render_admin_interface(admin_ops, auth_system)
    elif st.session_state.user_role == "manager":
        render_manager_portal(auth_system)
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
        st.error(f" Application crashed: {e}")
        st.text_area("Traceback", traceback.format_exc(), height=300)