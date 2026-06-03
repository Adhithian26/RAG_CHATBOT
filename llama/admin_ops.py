# admin_ops.py - Debugged and Clean Version
import os
import logging
from typing import List, Tuple, Optional, Dict, Any
import streamlit as st
import re
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdminOperations:
    """
    Advanced AdminOperations with RAG Engine
    """
    
    def __init__(self, rag_engine, pdf_storage_folder: str = "data/uploaded_pdfs"):
        """
        Initialize AdminOperations with RAG engine
        """
        self.rag_engine = rag_engine
        self.pdf_storage_folder = pdf_storage_folder
        
        # Ensure the PDF storage folder exists
        os.makedirs(self.pdf_storage_folder, exist_ok=True)
        
        logger.info("🚀 AdminOperations initialized successfully")
        logger.info(f"PDF Storage: {self.pdf_storage_folder}")
        logger.info(f"RAG Engine Type: {type(rag_engine).__name__}")
    
    def _clean_filename(self, filename: str) -> str:
        """Clean filename to be safe for file system"""
        # Remove extension and clean
        name = os.path.splitext(filename)[0]
        # Replace spaces and special characters with underscores
        name = re.sub(r'[^\w\-_]', '_', name)
        # Remove multiple consecutive underscores
        name = re.sub(r'_+', '_', name)
        return name.strip('_')

    def save_uploaded_pdf(self, uploaded_file) -> Tuple[bool, str, Optional[str]]:
        """
        Save uploaded PDF file to storage
        """
        if uploaded_file is None:
            return False, "No file provided for upload.", None
        
        # Validate file type
        if not uploaded_file.name.lower().endswith('.pdf'):
            return False, "Only PDF files are supported.", None
        
        # Validate file size (50MB limit)
        if uploaded_file.size > 50 * 1024 * 1024:
            return False, "File size exceeds 50MB limit.", None
        
        # Clean the file name with timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_file_name = f"{self._clean_filename(uploaded_file.name)}_{timestamp}.pdf"
        file_path = os.path.join(self.pdf_storage_folder, clean_file_name)
        
        try:
            # Save the file
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            logger.info(f"✅ PDF saved successfully: {clean_file_name}")
            return True, f"File '{clean_file_name}' saved successfully.", file_path
            
        except Exception as e:
            logger.error(f"❌ Error saving PDF '{clean_file_name}': {e}")
            return False, f"Error saving file: {str(e)}", None
        
    def process_pdf(self, pdf_file_path: str, pdf_name_for_db: str) -> Tuple[bool, str]:
        """
        Process PDF using RAG engine
        """
        logger.info(f"🔄 Starting PDF processing: {pdf_name_for_db}")
        
        # Validate file exists and is readable
        if not os.path.exists(pdf_file_path):
            error_msg = f"PDF file not found: {pdf_file_path}"
            logger.error(error_msg)
            return False, error_msg
        
        # Check file size
        file_size = os.path.getsize(pdf_file_path)
        if file_size == 0:
            error_msg = f"PDF file is empty: {pdf_file_path}"
            logger.error(error_msg)
            return False, error_msg
        
        logger.info(f"📄 PDF file size: {file_size / 1024 / 1024:.2f} MB")
        
        try:
            # Clean the PDF name for database
            clean_pdf_name = self._clean_filename(pdf_name_for_db)
            
            logger.info(f"🔧 Processing PDF with RAG: {clean_pdf_name}")
            
            # Process PDF using RAG engine
            if not hasattr(self.rag_engine, 'process_pdf'):
                error_msg = "RAG engine does not have 'process_pdf' method"
                logger.error(error_msg)
                return False, error_msg
            
            success, message = self.rag_engine.process_pdf(pdf_file_path, clean_pdf_name)
            
            if success:
                logger.info(f"✅ PDF processed successfully: {clean_pdf_name}")
                return True, f"PDF '{clean_pdf_name}' processed successfully."
            else:
                logger.error(f"❌ PDF processing failed: {message}")
                return False, f"Processing failed: {message}"
                
        except Exception as e:
            error_msg = f"Unexpected error in PDF processing: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def get_list_of_processed_pdfs(self) -> List[str]:
        """
        Get all processed PDFs from RAG engine
        """
        try:
            # Try different method names for compatibility
            if hasattr(self.rag_engine, 'get_processed_documents'):
                pdfs = self.rag_engine.get_processed_documents()
            elif hasattr(self.rag_engine, 'get_processed_pdfs'):
                pdfs = self.rag_engine.get_processed_pdfs()
            else:
                logger.error("RAG engine does not have processed PDFs method")
                return []
            
            logger.info(f"📚 Found {len(pdfs)} processed PDFs in RAG system")
            return pdfs
            
        except Exception as e:
            logger.error(f"Error getting processed PDFs: {e}")
            return []

    def delete_processed_pdf(self, pdf_name_for_db: str) -> Tuple[bool, str]:
        """Delete processed PDF from RAG system"""
        logger.info(f"🗑 Starting deletion process for: {pdf_name_for_db}")
        
        try:
            # Clean the PDF name
            clean_pdf_name = self._clean_filename(pdf_name_for_db)
            
            # Delete from vector database
            db_success = False
            if hasattr(self.rag_engine, 'delete_pdf'):
                db_success = self.rag_engine.delete_pdf(clean_pdf_name)
            else:
                logger.warning("RAG engine does not have 'delete_pdf' method")
            
            # Delete original PDF file
            file_deleted = False
            file_message = ""
            
            # Find and delete the original PDF file
            for file in os.listdir(self.pdf_storage_folder):
                if file.startswith(clean_pdf_name) and file.endswith('.pdf'):
                    original_pdf_path = os.path.join(self.pdf_storage_folder, file)
                    try:
                        os.remove(original_pdf_path)
                        file_deleted = True
                        file_message = f"Original PDF file '{file}' deleted. "
                        logger.info(f"✅ Deleted PDF file: {original_pdf_path}")
                        break
                    except Exception as e:
                        file_message = f"Warning: Could not delete PDF file: {str(e)} "
                        logger.warning(f"Could not delete PDF file {original_pdf_path}: {e}")
            
            if not file_deleted:
                file_message = "Original PDF file not found. "
                logger.info(f"Original PDF file not found for: {clean_pdf_name}")
            
            if db_success:
                message = f"✅ Successfully deleted '{clean_pdf_name}' from database. {file_message}"
                logger.info(message)
                return True, message
            else:
                message = f"❌ Failed to delete '{clean_pdf_name}' from database. {file_message}"
                logger.warning(message)
                return False, message
                
        except Exception as e:
            error_msg = f"❌ Error during deletion process: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status for sidebar metrics
        """
        try:
            # Get status from RAG engine
            rag_status = self.rag_engine.get_system_status()
            
            # Calculate PDF storage info
            pdf_storage_size = 0
            pdf_files_count = 0
            
            if os.path.exists(self.pdf_storage_folder):
                pdf_files = [f for f in os.listdir(self.pdf_storage_folder) if f.endswith('.pdf')]
                pdf_files_count = len(pdf_files)
                
                for pdf_file in pdf_files:
                    file_path = os.path.join(self.pdf_storage_folder, pdf_file)
                    pdf_storage_size += os.path.getsize(file_path)
            
            # Return simplified status for sidebar
            return {
                "documents_processed": rag_status.get("documents_processed", 0),
                "chunks_indexed": rag_status.get("chunks_indexed", 0),
                "system_status": rag_status.get("system_status", "✅ Ready"),
                "pdf_files_count": pdf_files_count,
                "pdf_storage_size_mb": f"{pdf_storage_size / (1024 * 1024):.2f} MB",
                "rag_engine": rag_status.get("rag_engine", "Working RAG")
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "documents_processed": 0,
                "chunks_indexed": 0,
                "system_status": "❌ Error",
                "pdf_files_count": 0,
                "pdf_storage_size_mb": "0 MB",
                "error": str(e)
            }

    def validate_pdf_processing(self, pdf_name: str) -> Tuple[bool, str]:
        """
        Validate that a PDF was processed correctly
        """
        try:
            # Check if PDF exists in RAG system
            pdfs = self.get_list_of_processed_pdfs()
            clean_name = self._clean_filename(pdf_name)
            
            if clean_name in pdfs:
                # Additional validation through RAG engine
                if hasattr(self.rag_engine, 'get_document_info'):
                    pdf_info = self.rag_engine.get_document_info(clean_name)
                    chunk_count = pdf_info.get('chunk_count', 0)
                    return True, f"PDF '{clean_name}' processed successfully with {chunk_count} chunks."
                else:
                    return True, f"PDF '{clean_name}' found in system."
            else:
                return False, f"PDF '{clean_name}' not found in database."
                
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def get_system_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive system analytics
        """
        try:
            # Get basic system status
            system_status = self.rag_engine.get_system_status()
            
            # Get PDF storage analytics
            pdf_files = []
            total_size = 0
            
            if os.path.exists(self.pdf_storage_folder):
                for file in os.listdir(self.pdf_storage_folder):
                    if file.lower().endswith('.pdf'):
                        file_path = os.path.join(self.pdf_storage_folder, file)
                        file_size = os.path.getsize(file_path)
                        total_size += file_size
                        
                        # Get file modification time
                        mtime = os.path.getmtime(file_path)
                        upload_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                        
                        pdf_files.append({
                            "name": file,
                            "size_mb": round(file_size / (1024 * 1024), 2),
                            "upload_time": upload_time
                        })
            
            # Get processed documents
            processed_docs = self.get_list_of_processed_pdfs()
            
            analytics = {
                **system_status,
                "pdf_storage_folder": self.pdf_storage_folder,
                "pdf_storage_exists": os.path.exists(self.pdf_storage_folder),
                "pdf_storage_size": f"{total_size / (1024 * 1024):.2f} MB",
                "pdf_files_count": len(pdf_files),
                "pdf_files": pdf_files,
                "processed_documents_count": len(processed_docs),
                "processed_documents": processed_docs,
                "vector_db_exists": True,
                "vector_db_size": "0.00 MB",
                "vector_db_type": "ChromaDB",
                "system_health": "✅ Optimal" if system_status.get('system_status') == "✅ Ready" else "⚠️ Needs Attention"
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"❌ Error getting system analytics: {e}")
            return {
                "system_status": "❌ Error",
                "error": str(e)
            }

    def debug_pdf_storage(self) -> Dict[str, Any]:
        """
        Debug method to check PDF storage status
        """
        debug_info = {
            "pdf_storage_folder": self.pdf_storage_folder,
            "folder_exists": os.path.exists(self.pdf_storage_folder),
            "pdf_files": [],
            "rag_engine_type": type(self.rag_engine).__name__,
            "processed_pdfs": []
        }
        
        # Check PDF storage
        if os.path.exists(self.pdf_storage_folder):
            for file in os.listdir(self.pdf_storage_folder):
                if file.endswith('.pdf'):
                    file_path = os.path.join(self.pdf_storage_folder, file)
                    file_size = os.path.getsize(file_path)
                    debug_info["pdf_files"].append({
                        "name": file,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "exists": True,
                        "upload_time": datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                    })
        
        # Get processed PDFs
        debug_info["processed_pdfs"] = self.get_list_of_processed_pdfs()
        
        return debug_info

    def batch_process_pdfs(self) -> Dict[str, Tuple[bool, str]]:
        """
        Batch process all unprocessed PDFs in storage folder
        """
        results = {}
        
        try:
            # Get all PDF files in storage
            pdf_files = [f for f in os.listdir(self.pdf_storage_folder) if f.endswith('.pdf')]
            processed_pdfs = self.get_list_of_processed_pdfs()
            
            for pdf_file in pdf_files:
                clean_name = self._clean_filename(pdf_file)
                
                # Skip if already processed
                if clean_name in processed_pdfs:
                    results[pdf_file] = (False, "Already processed")
                    continue
                
                # Process the PDF
                pdf_path = os.path.join(self.pdf_storage_folder, pdf_file)
                success, message = self.process_pdf(pdf_path, clean_name)
                results[pdf_file] = (success, message)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            return {"error": str(e)}


def render_admin_interface(admin_ops, auth_system=None):
    """
    Render the admin interface for PDF management
    """
    # Initialize session state
    if 'show_detailed_report' not in st.session_state:
        st.session_state.show_detailed_report = False
    if 'show_debug_info' not in st.session_state:
        st.session_state.show_debug_info = False

    st.title("👨‍💼 Admin Portal - PDF Management")
    
    # Quick actions sidebar
    st.sidebar.subheader("🚀 Quick Actions")
    
    if st.sidebar.button("🔄 Refresh All", use_container_width=True):
        st.rerun()
    
    if st.sidebar.button("📊 Batch Process", use_container_width=True):
        with st.spinner("Batch processing PDFs..."):
            results = admin_ops.batch_process_pdfs()
            with st.sidebar.expander("Batch Results", expanded=True):
                for file, (success, message) in results.items():
                    if success:
                        st.success(f"✅ {file}: {message}")
                    else:
                        st.error(f"❌ {file}: {message}")
    
    if st.sidebar.button("🐛 Debug System", use_container_width=True):
        st.session_state.show_debug_info = True

        # Tab-based interface
    tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload PDF", "📚 Manage Documents", "📊 System Status", "🧩 View Chunks"])

    with tab1:
        st.subheader("Upload and Process PDF")
        
        uploaded_file = st.file_uploader(
            "Choose PDF file", 
            type=["pdf"],
            help="Upload a PDF file to add to the knowledge base (max 50MB)"
        )
        
        if uploaded_file is not None:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.info(f"**File:** {uploaded_file.name}")
                st.info(f"**Size:** {uploaded_file.size / 1024 / 1024:.2f} MB")
                st.info(f"**Type:** PDF Document")
            
            with col2:
                if st.button("🚀 Process PDF", type="primary", use_container_width=True):
                    with st.spinner("Processing PDF..."):
                        # Save uploaded file
                        save_success, save_message, file_path = admin_ops.save_uploaded_pdf(uploaded_file)
                        
                        if save_success:
                            # Process PDF
                            pdf_name_for_db = uploaded_file.name
                            process_success, process_message = admin_ops.process_pdf(file_path, pdf_name_for_db)
                            
                            if process_success:
                                st.success(f"✅ {process_message}")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(f"❌ {process_message}")
                        else:
                            st.error(f"❌ {save_message}")

    with tab2:
        st.subheader("Managed Documents")
        
        # Get list of processed PDFs
        processed_pdfs = admin_ops.get_list_of_processed_pdfs()
        
        if not processed_pdfs:
            st.info("📭 No PDFs processed yet. Upload and process PDFs in the Upload tab.")
        else:
            st.success(f"📊 Found {len(processed_pdfs)} processed PDFs")
            
            for pdf_name in processed_pdfs:
                with st.expander(f"📄 {pdf_name}", expanded=False):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        # Validate PDF status
                        valid, message = admin_ops.validate_pdf_processing(pdf_name)
                        if valid:
                            st.success(f"✅ {message}")
                        else:
                            st.error(f"❌ {message}")
                        
                        # Show additional info if available
                        if hasattr(admin_ops.rag_engine, 'get_document_info'):
                            try:
                                pdf_info = admin_ops.rag_engine.get_document_info(pdf_name)
                                if 'chunk_count' in pdf_info:
                                    st.info(f"**Chunks:** {pdf_info['chunk_count']}")
                            except Exception as e:
                                st.warning(f"Could not get document info: {e}")
                    
                    with col2:
                        if st.button("🔍 Validate", key=f"val_{pdf_name}", use_container_width=True):
                            st.info(f"Validation: {message}")
                    
                    with col3:
                        if st.button("🗑 Delete", key=f"del_{pdf_name}", use_container_width=True, type="secondary"):
                            with st.spinner("Deleting PDF..."):
                                success, message = admin_ops.delete_processed_pdf(pdf_name)
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)

    with tab3:
        st.subheader("System Status & Analytics")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🔄 Refresh Status", use_container_width=True):
                st.rerun()
        
        with col2:
            if st.button("📋 Detailed Report", use_container_width=True):
                st.session_state.show_detailed_report = True
    
        try:
            status = admin_ops.get_system_status()
            
            # Display status metrics
            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
            
            with metric_col1:
                st.metric("Processed PDFs", status.get("documents_processed", 0))
            
            with metric_col2:
                st.metric("PDF Files", status.get("pdf_files_count", 0))
            
            with metric_col3:
                st.metric("Chunks Indexed", status.get("chunks_indexed", 0))
            
            with metric_col4:
                st.metric("System Status", status.get("system_status", "❌ Unknown"))
            
            # Show detailed report if requested
            if st.session_state.get('show_detailed_report', False):
                analytics = admin_ops.get_system_analytics()
                with st.expander("📋 Detailed System Report", expanded=True):
                    st.json(analytics)
                    
                if st.button("❌ Close Detailed Report"):
                    st.session_state.show_detailed_report = False
                    st.rerun()
                
        except Exception as e:
            st.error(f"❌ Error getting system status: {str(e)}")

    with tab4:
        st.subheader("Chunk Inspection")

        try:
            view_option = st.radio(
                "View chunks from:",
                ["All PDFs", "Specific PDF"],
                horizontal=True,
                key="admin_view_chunks_option"
            )

            if view_option == "Specific PDF":
                processed_pdfs = admin_ops.get_list_of_processed_pdfs()
                if processed_pdfs:
                    selected_pdf = st.selectbox(
                        "Select PDF to inspect:",
                        processed_pdfs,
                        key="admin_selected_chunks_pdf"
                    )

                    if st.button("Display Chunks", use_container_width=True, key="admin_display_chunks_btn"):
                        chunks = admin_ops.rag_engine.get_chunks_for_pdf(selected_pdf)
                        if chunks:
                            st.success(f"Found {len(chunks)} chunks in '{selected_pdf}'")
                            for idx, chunk in enumerate(sorted(chunks, key=lambda x: x.get("chunk_id", 0))):
                                with st.expander(
                                    f"Chunk {chunk.get('chunk_id', idx)} ({chunk.get('length', 0)} chars)",
                                    expanded=(idx == 0)
                                ):
                                    st.markdown(chunk.get("content", ""))
                                    st.caption(f"ID: {chunk.get('id', 'unknown')}")
                        else:
                            st.warning(f"No chunks found for {selected_pdf}")
                else:
                    st.info("No processed PDFs available yet.")
            else:
                all_chunks = admin_ops.rag_engine.get_all_chunks()
                if all_chunks:
                    total_chunks = sum(len(chunks) for chunks in all_chunks.values())
                    st.success(f"Found {total_chunks} total chunks across {len(all_chunks)} PDFs")

                    for pdf_name in sorted(all_chunks.keys()):
                        chunks = all_chunks[pdf_name]
                        with st.expander(f"{pdf_name} ({len(chunks)} chunks)", expanded=False):
                            total_chars = sum(c.get("length", 0) for c in chunks)
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Chunks", len(chunks))
                            with col2:
                                st.metric("Total Size", f"{total_chars:,} chars")
                            with col3:
                                avg_size = total_chars // len(chunks) if chunks else 0
                                st.metric("Avg Size", f"{avg_size} chars")

                            st.markdown("---")
                            for idx, chunk in enumerate(sorted(chunks, key=lambda x: x.get("chunk_id", 0))):
                                with st.expander(f"Chunk {chunk.get('chunk_id', idx)} ({chunk.get('length', 0)} chars)"):
                                    st.markdown(chunk.get("content", ""))
                                    st.caption(f"ID: {chunk.get('id', 'unknown')}")
                else:
                    st.info("No chunks available yet. Process some PDFs first!")
        except Exception as e:
            st.error(f"Error viewing chunks: {e}")

    # Debug information
    if st.session_state.get('show_debug_info', False):
        with st.expander("🐛 Debug Information", expanded=True):
            debug_info = admin_ops.debug_pdf_storage()
            st.json(debug_info)
            
        if st.button("❌ Close Debug Info"):
            st.session_state.show_debug_info = False
            st.rerun()


# Simple test function
def test_admin_operations():
    """Test function for AdminOperations"""
    class MockRAGEngine:
        def process_pdf(self, path, name):
            return True, f"Mock processed {name}"
        
        def get_processed_documents(self):
            return ["test_document_1", "test_document_2"]
        
        def get_system_status(self):
            return {
                "documents_processed": 2, 
                "chunks_indexed": 25,
                "system_status": "✅ Ready",
                "rag_engine": "Mock RAG"
            }
        
        def get_document_info(self, name):
            return {"chunk_count": 10, "status": "Processed"}
    
    mock_rag = MockRAGEngine()
    admin_ops = AdminOperations(mock_rag)
    
    print("Testing AdminOperations...")
    print("Processed PDFs:", admin_ops.get_list_of_processed_pdfs())
    print("System Status:", admin_ops.get_system_status())

if __name__ == "__main__":
    test_admin_operations()
