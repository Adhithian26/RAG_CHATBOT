# 📚 Complete Function Documentation

## 🏠 **main.py** - Main Application File

### Fallback Classes (if imports fail)
- `AdvancedAuthSystem.__init__()` - Initialize basic auth system
- `AdvancedAuthSystem.authenticate()` - Authenticate user
- `AdvancedAuthSystem.get_user_role()` - Get user role
- `AdvancedAuthSystem._verify_jwt_token()` - Verify JWT token
- `AdminOperations.__init__()` - Initialize admin operations
- `AdvancedChatManager.__init__()` - Initialize chat manager
- `AdvancedChatManager.create_new_chat()` - Create new chat
- `AdvancedChatManager.get_user_chats()` - Get user chats
- `AdvancedChatManager.load_chat()` - Load chat messages
- `AdvancedChatManager.add_message()` - Add message to chat
- `AdvancedChatManager.delete_chat()` - Delete a chat

### Session Management Functions
- `initialize_session_state(cookies_manager)` - Initialize and restore session state
  - Checks URL parameters for session restoration
  - Sets all session state variables to default values
  - Returns early if session is restored from URL

- `render_login(auth_system_param, cookies_manager)` - Render login interface
  - Shows login form with username/password inputs
  - Authenticates user on button click
  - Sets session state and URL parameters
  - Saves session to file

- `render_user_management(auth_system)` - Render user management (Manager Portal)
  - Display user statistics
  - Add new user form
  - User list management
  - Role updates and deletions

- `render_admin_interface_fallback(admin_ops, auth_system)` - Fallback admin interface
  - PDF upload interface
  - Processed documents section
  - File deletion capabilities

### Session File Functions
- `save_session_to_file(username, token, role)` - Save session to JSON file
- `load_session_from_file()` - Load session from JSON file
- `clear_session_file()` - Clear session file

### Component Initialization
- `initialize_components()` - Initialize all application components
  - Creates required directories
  - Initializes AdvancedAuthSystem
  - Initializes AdvancedRAGEngine
  - Initializes AdminOperations
  - Initializes AdvancedChatManager
  - Returns tuple: (auth_system, rag_engine, admin_ops, chat_manager)

### UI Rendering Functions
- `render_sidebar(cookies_manager)` - Render sidebar navigation
  - Displays current user and role
  - Shows system status metrics
  - Chat history section with load/delete buttons
  - New chat button
  - Logout button
  - System actions (refresh, clear cache)

- `render_user_interface()` - Render user chat portal
  - Displays chat with documents
  - Checks Ollama AI engine status
  - Creates new or loads existing chat
  - Displays chat messages with sources
  - Handles user queries and AI responses
  - Displays sources with relevance scores

### Main Controller
- `main()` - Main application entry point
  - Initializes session state
  - Shows login if not authenticated
  - Routes to appropriate portal based on user role:
    - Admin → render_admin_interface()
    - Manager → render_user_management()
    - User → render_user_interface()

---

## 🔐 **auth.py** - Authentication System

### AdvancedAuthSystem Class

#### Initialization & Setup
- `__init__(users_file, secret_key)` - Initialize authentication system
- `_initialize_system()` - Create required directories and files
- `_initialize_default_users()` - Create default users (admin, manager, user1)

#### Password & Security
- `_hash_password(password)` - Hash password with SHA256
- `_validate_password_strength(password)` - Validate password strength requirements
- `_is_account_locked(username)` - Check if account is locked due to failed attempts
- `_record_failed_attempt(username)` - Record failed login attempt
- `_clear_failed_attempts(username)` - Clear failed attempts on successful login

#### JWT Token Management
- `_generate_jwt_token(username, role)` - Generate JWT session token
- `_verify_jwt_token(token)` - Verify and decode JWT token

#### User File Management
- `_load_users()` - Load users from JSON file
- `_save_users(users)` - Save users to JSON file
- `_save_data(data, filepath)` - Generic data saver
- `_load_data(filepath)` - Generic data loader

#### Audit & Logging
- `_audit_log(username, action, details)` - Log security events to audit file

#### User Authentication
- `authenticate(username, password)` - Main authentication method
  - Checks account lock status
  - Validates username exists
  - Verifies password
  - Returns: (success, role, message)

#### User Management
- `create_user(username, password, role, email)` - Create new user with validation
- `update_user_role(username, new_role)` - Update user role
- `delete_user(username)` - Delete user (except admin)
- `change_password(username, old_password, new_password)` - Change password

#### User Queries
- `get_all_users()` - Get all users dictionary
- `get_user_stats()` - Get user statistics (total, active, recent logins, roles)
- `validate_session(token)` - Validate JWT session token

#### UI Rendering
- `render_login(auth_system)` - Render login form
  - Centered login interface
  - Demo credentials display
  - Session restoration logic

- `render_user_management(auth_system)` - Render user management interface (Manager Portal)
  - User statistics display (Total Users, Active Users, Recent Logins, Roles)
  - Add new user form with validation
  - Users list with role management and deletion options
  - Real-time updates using Streamlit rerun

### Manager Portal - User Management Functions

#### Add User Section
- **Form Fields:**
  - `Username` - Text input with validation (3-20 chars, alphanumeric + underscore)
  - `Email` - Email input with validation
  - `Password` - Secure password input with strength requirements
  - `Role` - Dropdown selector (user, manager, admin)

- **Add User Process:**
  1. Manager enters user details in form
  2. Form validates all required fields are filled
  3. Calls `auth_system.create_user(new_username, new_password, new_role, new_email)`
  4. On success: Shows success message and reruns page
  5. On failure: Shows error message with reason

- **Validation Requirements:**
  - Username: 3-20 characters, letters/numbers/underscores only
  - Password: Min 8 chars, uppercase, lowercase, digit, special character
  - Email: Standard email format (optional but recommended)

#### User Statistics Section
- `Total Users` - Metric card showing count of all users
- `Active Users` - Metric card showing users with is_active = true
- `Recent Logins` - Metric card showing users who logged in last 7 days
- `Roles` - Metric card showing number of different role types

#### Users List Management Section
- **For Each User:**
  - Display username and role in expandable section
  - Show metadata:
    - Email address
    - Account creation date
    - Last login timestamp
    - Account status (Active/Inactive)
  
- **Role Update:**
  - Dropdown selector showing current role
  - Options: user, manager, admin
  - "Update Role" button triggers `auth_system.update_user_role(username, new_role)`
  - Restricted: Cannot modify self (current logged-in user)
  - Success message shown on role change

- **User Deletion:**
  - Red "Delete" button with trash icon
  - Restricted: Cannot delete self
  - Restricted: Cannot delete last admin account (auto-prevented)
  - Cannot delete the "admin" default account
  - Calls `auth_system.delete_user(username)`
  - Removes user and reruns page

#### Admin Portal Access (for Admin Users)
- When user role is "admin", main() routes to admin portal instead
- Admin has full system control plus all manager capabilities
- Admin can manage PDFs, view system status, and manage users

---

## 👨‍💼 **admin_ops.py** - Admin Operations

### AdminOperations Class

#### Initialization
- `__init__(rag_engine, pdf_storage_folder)` - Initialize admin operations

#### File Management
- `_clean_filename(filename)` - Clean and sanitize filenames
- `save_uploaded_pdf(uploaded_file)` - Save uploaded PDF file
  - Validates file is PDF
  - Saves to storage folder
  - Returns: (success, message, file_path)

#### PDF Processing
- `process_pdf(pdf_file_path, pdf_name_for_db)` - Process PDF through RAG engine
  - Extracts text
  - Creates embeddings
  - Stores in ChromaDB
  - Returns: (success, message)

#### Document Management
- `get_list_of_processed_pdfs()` - Get list of all processed PDFs
- `delete_processed_pdf(pdf_name_for_db)` - Delete PDF from database
- `validate_pdf_processing(pdf_name)` - Validate PDF was processed correctly

#### System Status
- `get_system_status()` - Get overall system status
- `get_system_analytics()` - Get detailed analytics about PDFs and system
- `debug_pdf_storage()` - Debug info about PDF storage and database

#### Batch Operations
- `batch_process_pdfs()` - Process multiple PDFs at once

#### UI Rendering
- `render_admin_interface(admin_ops, auth_system)` - Render admin portal
  - PDF upload interface (Tab 1)
  - Document management interface (Tab 2)
  - System status display (Tab 3)
  - Quick actions sidebar

#### Testing
- `test_admin_operations()` - Test admin operations (mock RAG engine)

---

## 🤖 **core_rag.py** - RAG Engine

### AdvancedRAGEngine Class

#### Initialization
- `__init__(chroma_db_path, chunk_size, chunk_overlap, top_k)` - Initialize RAG engine
  - Initializes ChromaDB
  - Loads embeddings model
  - Checks Ollama connection

#### Connection & Status
- `_check_ollama_connection()` - Verify Ollama is running
- `get_system_status()` - Get system status
  - Documents processed count
  - Chunks indexed count
  - Ollama connection status
  - AI engine name

#### PDF Processing
- `_extract_pdf_text(pdf_path)` - Extract text from PDF file
- `_split_text(text, chunk_size, overlap)` - Split text into overlapping chunks
- `process_pdf(pdf_path, pdf_name)` - Full PDF processing pipeline
  - Extracts text
  - Splits into chunks
  - Generates embeddings
  - Stores in ChromaDB

#### Embedding & Query
- `_embed_query(query)` - Create embedding for query

#### AI Integration
- `_call_ollama(prompt, system_prompt)` - Call Ollama API for AI responses
- `_generate_ollama_answer(query, contexts)` - Generate answer using Ollama
- `_simple_fallback(query, contexts)` - Simple fallback search when AI unavailable

#### Search & Retrieval
- `search(query, top_k)` - Main search function
  - Embeds query
  - Retrieves similar chunks from ChromaDB
  - Calls Ollama for answer generation
  - Returns: (answer, contexts, source_doc)

#### Document Management
- `delete_pdf(pdf_name)` - Delete PDF and its chunks from database
- `get_processed_pdfs()` - List all processed PDFs
- `get_processed_documents()` - Get processed documents with metadata
- `get_document_info(doc_name)` - Get info about specific document
  - Chunk count
  - Processing status

#### Cache Management
- `clear_cache()` - Clear internal caches

#### Document Metadata
- `_load_processed_documents()` - Load document metadata from JSON
- `_save_processed_documents()` - Save document metadata to JSON

---

## 💬 **utils.py** - Utility Functions & Chat Management

### AdvancedChatManager Class (Primary Chat Manager)

#### Initialization
- `__init__(base_path)` - Initialize chat manager
  - Default path: `data/chat_history`

#### File Management
- `_user_folder(username)` - Get/create user's chat folder
- `_chat_path(username, chat_id)` - Get full path to chat file

#### Chat Operations
- `create_new_chat(username, topic)` - Create new chat
  - Generates chat_id with timestamp
  - Creates initial chat JSON file
  - Returns chat_id

- `get_user_chats(username)` - Get all chats for user
  - Returns sorted list by creation date (newest first)
  - Includes: id, topic, created_at

- `load_chat(username, chat_id)` - Load chat messages
  - Returns list of messages from JSON file

- `add_message(username, chat_id, role, content, sources)` - Add message to chat
  - Saves role, content, sources, and timestamp
  - Creates chat file if doesn't exist
  - Returns: bool (success)

- `delete_chat(username, chat_id)` - Delete chat file
  - Removes chat JSON file
  - Returns: bool (success)

### AdvancedMemoryAgent Class
- `__init__(memory_path)` - Initialize memory agent for context learning
- `_load_memory()` - Load memory from storage
- `_save_memory()` - Save memory to storage
- `add_conversation_context(user_id, query, answer, contexts)` - Store conversation context
- `_extract_and_cache_facts(query, answer, contexts)` - Extract and cache facts
- `_learn_query_pattern(query, answer, confidence)` - Learn query patterns
- `get_relevant_context(user_id, current_query)` - Get relevant past context
- `get_cached_facts(query)` - Retrieve cached facts
- `get_query_suggestions(partial_query)` - Get query suggestions

### VoiceCommandProcessor Class
- `__init__(default_language)` - Initialize voice processor
- `_initialize_advanced_tts()` - Setup text-to-speech
- `process_voice_command(text)` - Process voice commands
- `_stop_listening(text)` - Stop listening command
- `_clear_chat(text)` - Clear chat command
- `_read_last_answer(text)` - Read last answer command
- `_search_command(text)` - Search command

### Quality Analysis Functions
- `analyze_response_quality(answer, contexts)` - Analyze response quality metrics
- `enhance_response(answer, metrics)` - Enhance response based on metrics
- `generate_response_summary(answer, confidence)` - Generate response summary
- `display_agent_metrics(metrics)` - Display metrics in Streamlit
- `display_thinking_process(reasoning_steps)` - Display AI reasoning steps

### ChatHistoryManager Class (Legacy)
- Placeholder class for backward compatibility

---

## 🔍 **Function Call Flow**

### Login Flow:
1. `main()` → `initialize_session_state()` → Check URL/session
2. If not authenticated → `render_login()` 
3. User enters credentials → `auth_system.authenticate()`
4. On success → Save session → Redirect to portal

### Admin Portal Flow:
1. `main()` → Check `user_role == "admin"`
2. Calls `render_admin_interface()`
3. User uploads PDF → `admin_ops.save_uploaded_pdf()`
4. Click Process → `admin_ops.process_pdf()` → `rag_engine.process_pdf()`

### User Portal Flow:
1. `main()` → Check `user_role` is "user"
2. Calls `render_user_interface()`
3. Display chat history → `chat_manager.get_user_chats()`
4. Load chat → `chat_manager.load_chat()`
5. User query → `rag_engine.search()` → `_call_ollama()`
6. Save response → `chat_manager.add_message()` with sources

### Manager Portal Flow:
1. `main()` → Check `user_role == "manager"`
2. Calls `render_user_management()`
3. Display users → `auth_system.get_all_users()`
4. Manage users → `auth_system.create_user()`, `update_user_role()`, `delete_user()`

---

## 🗂️ **Data Storage**

### JSON Files Structure:
- `data/users.json` - User credentials and metadata
- `data/sessions.json` - Session tracking
- `data/failed_attempts.json` - Failed login tracking
- `data/current_session.json` - Active session (file-based backup)
- `data/audit.log` - Security audit log
- `data/chat_history/<username>/<chat_id>.json` - Chat messages with sources
- `data/processed_documents.json` - PDF metadata

### ChromaDB:
- `data/chroma_db_fixed/` - Vector database with embeddings
- Stores PDF chunks and their embeddings
- Indexed for similarity search

---

## 🎯 **Key Decorators**

- `@st.cache_resource` - Cache components on line 343 (initialize_components)

---

## 📝 **Notes**

- All functions use proper type hints (Python typing)
- Error handling with try/except blocks
- Logging for debugging and audit trail
- Session management via URL parameters (primary) and file backup
- Multi-role system: admin > manager > user
- Real-time chat with document context
- JWT token-based authentication
- Password hashing with salt
- Account locking after failed attempts
