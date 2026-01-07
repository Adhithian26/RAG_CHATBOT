# core_rag.py (Ollama Setup!!!!!)
import os
import time
import json
import logging
import re
import requests
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import chromadb
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class AdvancedRAGEngine:
    def __init__(self, 
                 vector_db_path: str = "data/chroma_db",
                 collection_name: str = "documents",
                 embed_model_name: str = "all-MiniLM-L6-v2",
                 ollama_base_url: str = "http://localhost:11434",
                 ollama_model: str = "llama3.1",  # Your working model
                 top_k: int = 5,
                 chunk_size: int = 800,
                 chunk_overlap: int = 200):
        
        os.makedirs(vector_db_path, exist_ok=True)
        self.vector_db_path = vector_db_path
        self.collection_name = collection_name
        self.top_k = top_k
        self.ollama_base_url = ollama_base_url
        self.ollama_model = ollama_model
        # Chunking defaults 
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize ChromaDB
        try:
            self.client = chromadb.PersistentClient(path=vector_db_path)
            self.collection = self.client.get_or_create_collection(name=collection_name)
        except Exception as e:
            logger.error(f"Chromadb init failed: {e}")
            raise

        # Initialize embeddings
        try:
            logger.info(f"Loading embedding model: {embed_model_name}")
            self.embed_model = SentenceTransformer(embed_model_name)
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

        # Check Ollama connection
        self.ollama_available = self._check_ollama_connection()
        
        if self.ollama_available:
            logger.info(f"✅ Ollama connected with model: {ollama_model}")
        else:
            logger.warning("❌ Ollama not available")

        # Processed docs tracking
        self.persistence_file = os.path.join(vector_db_path, "processed_docs.json")
        self.processed_pdfs = self._load_processed_documents()

        logger.info("✅ RAG Engine with Ollama initialized successfully")

    def _check_ollama_connection(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=10)
            return response.status_code == 200
        except:
            return False

    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF"""
        text = ""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            return text
        except ImportError:
            try:
                import PyPDF2
                with open(pdf_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() or "" + "\n"
                return text
            except Exception as e:
                logger.error(f"PDF extraction failed: {e}")
                return ""

    def _split_text(self, text: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None) -> List[str]:
        """Split text into chunks with overlap.

        This implementation is paragraph-aware: it merges short paragraphs up to
        `chunk_size`, and for very long paragraphs it uses a sliding window with
        `overlap` to ensure long texts are split into multiple chunks instead of
        producing a single huge chunk.
        """
        # Use instance defaults when parameters not provided
        chunk_size = chunk_size or getattr(self, "chunk_size", 1000)
        overlap = overlap or getattr(self, "chunk_overlap", 250)

        # Sanity check
        if overlap >= chunk_size:
            overlap = max(1, chunk_size // 10)

        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) <= chunk_size:
            return [text]

        # Split on paragraph boundaries where available
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

        chunks: List[str] = []
        current_chunk = ""

        for para in paragraphs:
            # If paragraph itself is longer than chunk_size, split it with sliding window
            if len(para) > chunk_size:
                # Flush any existing current chunk first
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                start = 0
                step = max(1, chunk_size - overlap)
                while start < len(para):
                    end = start + chunk_size
                    chunk = para[start:end].strip()
                    if chunk:
                        chunks.append(chunk)
                    start += step
            else:
                # Try to merge paragraph into current chunk
                if current_chunk:
                    if len(current_chunk) + 1 + len(para) <= chunk_size:
                        current_chunk = f"{current_chunk} {para}"
                    else:
                        chunks.append(current_chunk)
                        current_chunk = para
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [text[:chunk_size]]

    def process_pdf(self, pdf_path: str, pdf_name: str) -> Tuple[bool, str]:
        """Process PDF"""
        try:
            if pdf_name in self.processed_pdfs:
                return True, f"✅ Document '{pdf_name}' already processed."

            if not os.path.exists(pdf_path):
                return False, f"File not found: {pdf_path}"

            text = self._extract_pdf_text(pdf_path)
            if not text or len(text.strip()) < 50:
                return False, "No text extracted from PDF"

            chunks = self._split_text(text)
            if not chunks:
                return False, "No chunks created"

            embeddings = self.embed_model.encode(chunks, convert_to_numpy=True)

            ids = [f"{pdf_name}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [{"pdf_name": pdf_name, "chunk_id": i} for i in range(len(chunks))]

            self.collection.add(
                ids=ids,
                documents=chunks,
                metadatas=metadatas,
                embeddings=embeddings.tolist()
            )

            self.processed_pdfs[pdf_name] = {
                "chunk_count": len(chunks),
                "file_path": os.path.abspath(pdf_path),
                "processed_at": time.time()
            }
            self._save_processed_documents()
            
            logger.info(f"✅ Processed '{pdf_name}' ({len(chunks)} chunks)")
            return True, f"✅ Processed '{pdf_name}' with {len(chunks)} chunks."

        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return False, f"❌ Error: {e}"

    def _embed_query(self, query: str) -> np.ndarray:
        """Embed query"""
        return self.embed_model.encode([query], convert_to_numpy=True)[0]

    def _call_ollama(self, prompt: str, system_prompt: str = None) -> str:
        """Call Ollama API"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.ollama_model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.7}
            }
            
            response = requests.post(
                f"{self.ollama_base_url}/api/chat",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['message']['content'].strip()
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            raise

    def search(self, query: str, top_k: Optional[int] = None) -> Tuple[str, List[str], str]:
        """Main search function"""
        if top_k is None:
            top_k = self.top_k

        if not self.processed_pdfs:
            return "I'm ready to help! Please upload some PDF documents first.", [], "System"

        # Handle greetings
        query_lower = query.lower().strip()
        if query_lower in ['hi', 'hello', 'hey']:
            return "Hello! I'm your document assistant. Ask me anything about your uploaded PDFs.", [], "Assistant"

        try:
            # Search for relevant contexts
            q_emb = self._embed_query(query)
            results = self.collection.query(
                query_embeddings=[q_emb.tolist()],
                n_results=top_k
            )
            
            docs = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]

            contexts = [doc for doc in docs if isinstance(doc, str) and doc.strip()]

            if not contexts:
                return f"I couldn't find specific information about '{query}' in your documents.", [], "Assistant"

            # Generate answer using Ollama
            if self.ollama_available:
                final_answer = self._generate_ollama_answer(query, contexts)
            else:
                final_answer = self._simple_fallback(query, contexts)

            # Determine source
            source_doc = "Multiple Documents"
            try:
                pdf_names = [m.get("pdf_name") for m in metadatas if isinstance(m, dict)]
                if pdf_names:
                    source_doc = max(set(pdf_names), key=pdf_names.count)
            except:
                pass

            return final_answer, contexts, source_doc

        except Exception as e:
            logger.error(f"Search error: {e}")
            return f"Error processing your question: {str(e)}", [], "System"

    def _generate_ollama_answer(self, query: str, contexts: List[str]) -> str:
        """Generate answer using Ollama"""
        # Clean contexts
        clean_contexts = []
        for context in contexts[:3]:
            clean = re.sub(r'\s+', ' ', context).strip()
            if clean and len(clean) > 150:
                clean_contexts.append(clean)
        
        if not clean_contexts:
            return self._simple_fallback(query, contexts)

        context_text = "\n\n".join(clean_contexts)

        system_prompt = "You are a helpful AI assistant that answers questions based on the provided document content. Answer directly and naturally."

        user_prompt = f"""Based on this document content:

{context_text}

Question: {query}

Please provide a helpful answer based on the content:"""

        try:
            answer = self._call_ollama(user_prompt, system_prompt)
            return answer
        except:
            return self._simple_fallback(query, contexts)

    def _simple_fallback(self, query: str, contexts: List[str]) -> str:
        """Simple fallback answer"""
        if not contexts:
            return f"I couldn't find information about '{query}' in the documents."
        
        best_context = contexts[0]
        sentences = [s.strip() for s in best_context.split('. ') if len(s.strip()) > 20]
        
        if sentences:
            return sentences[0]
        else:
            return best_context[:500] + "..."

    # UTILITY METHODS
    def _load_processed_documents(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.persistence_file):
                with open(self.persistence_file, "r") as f:
                    return json.load(f) or {}
        except:
            pass
        return {}

    def _save_processed_documents(self):
        try:
            with open(self.persistence_file, "w") as f:
                json.dump(self.processed_pdfs, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save: {e}")

    def get_system_status(self) -> Dict[str, Any]:
        try:
            count = self.collection.count()
            ollama_status = "✅ Ready" if self.ollama_available else "❌ Not available"
            return {
                "system_status": "✅ Ready" if self.processed_pdfs else "⚠ No documents",
                "documents_processed": len(self.processed_pdfs),
                "chunks_indexed": count,
                "ollama_status": ollama_status
            }
        except Exception as e:
            return {"system_status": "❌ Error", "error": str(e)}

    def get_processed_pdfs(self) -> List[str]:
        return list(self.processed_pdfs.keys())

    def delete_pdf(self, pdf_name: str) -> Tuple[bool, str]:
        try:
            if pdf_name not in self.processed_pdfs:
                return False, "PDF not found"
            
            results = self.collection.get(where={"pdf_name": pdf_name})
            if results and results.get("ids"):
                self.collection.delete(ids=results["ids"])
            
            del self.processed_pdfs[pdf_name]
            self._save_processed_documents()
            
            return True, f"Deleted {pdf_name}"
        except Exception as e:
            return False, str(e)

    def clear_cache(self):
        try:
            logger.info("Cache cleared")
        except Exception as e:
            logger.warning(f"Error: {e}")

    def get_processed_documents(self):
        return self.get_processed_pdfs()

    def get_document_info(self, doc_name: str) -> Dict[str, Any]:
        if doc_name in self.processed_pdfs:
            return self.processed_pdfs[doc_name]
        return {"status": "Not found", "chunk_count": 0}

if __name__ == "__main__":
    rag = AdvancedRAGEngine()
    print(rag.get_system_status())