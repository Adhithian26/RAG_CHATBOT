# simple_rag_engine.py
import os
import logging
import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class SimpleRAGEngine:
    """
    Simplified RAG Engine without LlamaIndex
    Uses ChromaDB + Sentence Transformers directly
    """
    
    def __init__(self, vector_db_path: str = "data/chroma_db_simple"):
        self.vector_db_path = vector_db_path
        os.makedirs(self.vector_db_path, exist_ok=True)
        
        logger.info("🚀 Initializing Simple RAG Engine")
        
        try:
            # Initialize ChromaDB
            self.client = chromadb.PersistentClient(path=vector_db_path)
            self.collection = self.client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"}
            )
            
            # Initialize Embeddings
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Track documents
            self.document_metadata = {}
            
            logger.info("✅ Simple RAG Engine initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Simple RAG Engine: {e}")
            raise
    
    def process_pdf(self, pdf_path: str, pdf_name: str) -> Tuple[bool, str]:
        """Process PDF file (simplified - you'll need to add PDF text extraction)"""
        try:
            # For now, create dummy content
            # You'll need to integrate your PDF text extraction here
            dummy_content = f"Content from {pdf_name}. Add proper PDF text extraction."
            
            # Split into chunks
            chunks = self._split_text(dummy_content)
            
            # Generate embeddings
            embeddings = self.embedder.encode(chunks).tolist()
            
            # Add to ChromaDB
            ids = [f"{pdf_name}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [{"pdf_name": pdf_name, "chunk_id": i} for i in range(len(chunks))]
            
            self.collection.add(
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            
            self.document_metadata[pdf_name] = {
                "chunk_count": len(chunks),
                "processed": True
            }
            
            return True, f"Processed {pdf_name} with {len(chunks)} chunks"
            
        except Exception as e:
            return False, f"Error processing {pdf_name}: {e}"
    
    def _split_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
            
        return chunks
    
    def search(self, query: str, n_results: int = 3) -> Tuple[str, List[str], str]:
        """Search documents"""
        try:
            # Generate query embedding
            query_embedding = self.embedder.encode([query]).tolist()
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results
            )
            
            if not results['documents'] or not results['documents'][0]:
                return "No relevant documents found.", [], "N/A"
            
            documents = results['documents'][0]
            source_texts = documents
            
            # Generate simple answer
            context = " ".join(documents)
            answer = f"I found this information: {context[:500]}..."
            
            # Determine source
            source_pdf = "Multiple sources"
            if results['metadatas'] and results['metadatas'][0]:
                pdf_names = [meta.get('pdf_name', 'Unknown') for meta in results['metadatas'][0]]
                if pdf_names:
                    source_pdf = max(set(pdf_names), key=pdf_names.count)
            
            return answer, source_texts, source_pdf
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return "Sorry, I encountered an error during search.", [], "N/A"
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        try:
            count = self.collection.count()
            return {
                "system_status": "✅ Operational",
                "rag_engine": "Simple ChromaDB + Sentence Transformers",
                "documents_indexed": count,
                "embedding_model": "all-MiniLM-L6-v2",
                "vector_db": "ChromaDB"
            }
        except Exception as e:
            return {
                "system_status": "❌ Error",
                "error": str(e)
            }

# Test the simple engine
def test_simple_engine():
    logging.basicConfig(level=logging.INFO)
    
    try:
        rag = SimpleRAGEngine()
        print("✅ Simple RAG Engine working!")
        
        # Test with dummy data
        success, msg = rag.process_pdf("dummy.pdf", "test_document")
        print(f"Processing: {success} - {msg}")
        
        # Test search
        answer, sources, pdf = rag.search("test query")
        print(f"Search: {answer}")
        
        status = rag.get_system_status()
        print(f"Status: {status}")
        
    except Exception as e:
        print(f"❌ Simple engine failed: {e}")

if __name__ == "__main__":
    test_simple_engine()