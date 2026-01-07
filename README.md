# 🚀 Enterprise RAG System with Ollama

An advanced Retrieval-Augmented Generation (RAG) system built for enterprise document intelligence, featuring PDF processing, intelligent chat interface, and role-based access control using Ollama as the AI engine.

✨ Key Features

🔐 **Advanced Authentication System**
- Role-based access (Admin, Manager, User)
- JWT token-based session management
- Password strength validation
- Account locking & security audit logging
- User management interface for admins

### 📚 **Document Processing & Management**
- PDF upload and storage (50MB limit)
- Intelligent text extraction and chunking
- Vector embeddings using Sentence Transformers
- ChromaDB for vector storage
- Batch processing capabilities

### 💬 **AI-Powered Chat Interface**
- Ollama integration (Llama 3.1 support)
- Context-aware document searching
- Source citation with relevance scores
- Chat history management
- Multiple document querying

### 👨‍💼 **Admin Dashboard**
- PDF management interface
- System status monitoring
- User management
- Batch processing operations
- Debug tools and analytics

## 🛠️ Technology Stack

- **Backend**: Python, Streamlit
- **AI Engine**: Ollama (Llama 3.1)
- **Vector Database**: ChromaDB
- **Embeddings**: Sentence Transformers (`all-MiniLM-L6-v2`)
- **PDF Processing**: PyPDF2 / PyMuPDF
- **Authentication**: RBAC-based custom auth system

## 📋 Prerequisites

- Python 3.8+
- Ollama installed and running locally
- Required Python packages (see `requirements.txt`)

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/VishwaPriya-Karthikeyan/Rag-Pdf-ChatBot
cd Rag-Pdf-ChatBot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Ollama
```bash
# Install Ollama (if not already installed)
# Visit: https://ollama.ai/download

# Pull the Llama 3.1 model (or your preferred model)
ollama pull llama3.1

# Start Ollama server
ollama serve
```

### 4. Run the Application
```bash
streamlit run main.py
```

## Project Structure

```
Rag-Pdf-ChatBot/llama/
├── main.py                 # Main application entry point
├── core_rag.py            # RAG engine with Ollama integration
├── auth.py               # Advanced authentication system
├── admin_ops.py          # Admin operations and interface
├── utils.py              # Chat manager and utilities
├── data/                 # Data storage directory
│   ├── uploaded_pdfs/   # Uploaded PDF files
│   ├── chroma_db/       # Vector database
│   ├── chat_history/    # Chat session storage
│   └── users.json       # User database
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## 📊 Usage Guide

### 1. **Login**
Use one of the default credentials:
- **Admin**: `admin` / `Admin123!`
- **Manager**: `manager` / `Manager123!`
- **User**: `user1` / `User123!`

### 2. **Upload Documents** (Admin/Manager)
- Navigate to Admin Portal
- Upload PDF files
- Process documents for indexing
- Monitor processing status

### 3. **Ask Questions** (All Users)
- Use the chat interface to ask questions
- System searches through all uploaded documents
- Provides answers with source citations
- Chat history is saved per user

### 4. **Manage System** (Admin)
- View system status and metrics
- Manage users and roles
- Delete or reprocess documents
- Access debug information

## 🔧 Configuration Options

### RAG Engine Settings (`core_rag.py`)
```python
# Model configuration
ollama_model = "llama3.1"  # Change to your preferred model
ollama_base_url = "http://localhost:11434"

# Chunking settings
chunk_size = 1000
chunk_overlap = 250

# Vector database
vector_db_path = "data/chroma_db"
collection_name = "documents"
```

### Authentication Settings (`auth.py`)
```python
# Security settings
max_login_attempts = 5
lockout_duration = timedelta(minutes=30)
session_duration = timedelta(hours=24)
```

## 🐛 Troubleshooting

### Common Issues:

1. **Ollama Connection Failed**
   ```
   Error: Ollama not available
   ```
   **Solution**: Ensure Ollama is running:
   ```bash
   ollama serve
   ```

2. **PDF Processing Errors**
   - Check PDF file integrity
   - Ensure sufficient disk space
   - Verify PDF is not password-protected

3. **Vector Database Issues**
   - Delete `data/chroma_db` folder to reset
   - Check disk permissions

4. **Authentication Problems**
   - Clear browser cookies
   - Check `data/users.json` file permissions

### Logs:
- Application logs: `data/app.log`
- Audit logs: `data/audit.log`
- Error details in Streamlit interface

## 📈 Performance Optimization

### For Large Document Collections:
1. Increase chunk size for better context
2. Adjust overlap for continuity
3. Monitor memory usage with large PDFs
4. Use batch processing for multiple documents

### Ollama Performance:
- Adjust `temperature` in `core_rag.py` for response creativity
- Consider GPU acceleration for Ollama
- Monitor response times for complex queries

## 🔒 Security Features

- Password hashing with salt
- JWT token expiration
- Account lockout after failed attempts
- Session management
- Audit logging for security events
- Role-based access control

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Authors
Vishwa Priya.K
Sharmila.L
Adhithian.A

## Acknowledgments

- [Ollama](https://ollama.ai/) for the local AI engine
- [ChromaDB](https://www.trychroma.com/) for vector storage
- [Sentence Transformers](https://www.sbert.net/) for embeddings
- [Streamlit](https://streamlit.io/) for the web interface



---

**Note**: This is an enterprise-grade system. Always ensure proper security measures when deploying in production environments. Regularly update dependencies and monitor system logs for suspicious activities.

