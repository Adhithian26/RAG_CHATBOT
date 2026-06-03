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

    # ──────────────────────────────────────────────────────────────
    # General Conversation Detection
    # ──────────────────────────────────────────────────────────────
    def _is_general_conversation(self, query: str) -> bool:
        """
        Detect if the message is general chat (not a document question).
        These should be handled by the LLM directly, bypassing RAG.
        """
        q = query.lower().strip()

        # Very short exclamations / reactions
        if len(q.split()) <= 4 and not any(
            kw in q for kw in ["what", "how", "why", "when", "where", "who", "which",
                                "explain", "tell me", "describe", "define", "summarize"]
        ):
            return True

        general_patterns = [
            # Greetings & farewells
            "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
            "good night", "bye", "goodbye", "see you", "take care",
            # Bot-directed feelings
            "you are", "you're", "ur ", "you suck", "you're useless", "you're stupid",
            "you're great", "you're awesome", "i hate you", "i love you",
            "trash", "garbage", "useless bot", "bad bot", "good bot",
            # Small talk
            "how are you", "how r u", "what's up", "wassup", "whats up",
            "who are you", "what are you", "tell me about yourself",
            "are you an ai", "are you a bot", "are you real",
            # Emotions / reactions
            "lol", "haha", "ok", "okay", "fine", "cool", "nice", "great",
            "thanks", "thank you", "thx", "ty", "no problem", "sure",
            "yes", "no", "maybe", "i see", "got it", "understood",
            # Frustration venting (not questions)
            "this is bad", "this doesn't work", "fix this", "ugh", "argh",
            "not working", "broken", "terrible", "horrible", "awful",
        ]

        return any(pattern in q for pattern in general_patterns)

    def _handle_general_conversation(
        self,
        query: str,
        chat_history: Optional[List[Dict]] = None,
        sentiment: str = "neutral"
    ) -> str:
        """Answer general/casual chat using Ollama without document context."""
        if not self.ollama_available:
            # Friendly fallback if Ollama is offline
            responses = {
                "positive": "Thank you! 😊 I'm here to help you with your documents.",
                "frustrated": "I'm sorry you feel that way! 😔 Let me try to help you better. "
                              "You can ask me anything about your uploaded documents.",
                "confused": "No worries! 😊 Feel free to ask me anything about your documents.",
                "neutral": "I'm your document assistant. Ask me anything about your PDFs!",
            }
            return responses.get(sentiment, responses["neutral"])

        system_prompt = (
            "You are a friendly, helpful AI assistant. You can chat casually "
            "and also help users query their uploaded PDF documents. "
            "If someone is frustrated or upset, be empathetic and kind. "
            "Keep responses concise and warm."
            + self._sentiment_system_prompt(sentiment)
        )

        messages: List[Dict] = [{"role": "system", "content": system_prompt}]

        # Include recent history for context
        if chat_history:
            for turn in chat_history[-4:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": query})

        try:
            payload = {
                "model": self.ollama_model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.8}
            }
            response = requests.post(
                f"{self.ollama_base_url}/api/chat",
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                return response.json()["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"General conversation Ollama call failed: {e}")

        # Fallback responses
        if sentiment == "frustrated":
            return ("I'm sorry to hear you're frustrated! 😔 I'm doing my best. "
                    "Try asking me something about your uploaded documents and I'll help.")
        return "I'm here to help! Feel free to ask me anything about your documents. 📄"

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        chat_history: Optional[List[Dict]] = None
    ) -> Tuple[str, List[str], str, float, str]:
        """
        Main search function.

        Returns: (answer, contexts, source_doc, confidence_pct, sentiment)
        """
        if top_k is None:
            top_k = self.top_k

        # FEATURE 2: Detect sentiment early (needed for both paths)
        sentiment = self._detect_sentiment(query)

        # ── Route 1: General casual conversation ─────────────────────────────
        if self._is_general_conversation(query):
            answer = self._handle_general_conversation(query, chat_history, sentiment)
            return answer, [], "Assistant", 100.0, sentiment

        # ── Route 2: No docs uploaded yet ────────────────────────────────────
        if not self.processed_pdfs:
            return (
                "I'm ready to help! Please upload some PDF documents first. "
                "Once documents are uploaded, I can answer detailed questions from them.",
                [], "System", 0.0, "neutral"
            )

        # ── Route 3: Document RAG search ─────────────────────────────────────
        try:
            q_emb = self._embed_query(query)
            results = self.collection.query(
                query_embeddings=[q_emb.tolist()],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )

            docs      = results.get("documents",  [[]])[0]
            metadatas = results.get("metadatas",  [[]])[0]
            distances = results.get("distances",  [[]])[0]

            contexts = [doc for doc in docs if isinstance(doc, str) and doc.strip()]

            # FEATURE 3: Compute confidence from best distance score
            # ChromaDB L2 distance: 0 = perfect, typical range 0-2+
            if distances:
                best_dist = float(distances[0])
                confidence_pct = max(0.0, min(100.0, (1.0 - best_dist / 2.0) * 100))
            else:
                confidence_pct = 0.0

            if not contexts:
                # Still try Ollama as general assistant
                answer = self._handle_general_conversation(query, chat_history, sentiment)
                return answer, [], "Assistant", 0.0, sentiment

            # FEATURE 5: SOFTENED out-of-scope guard
            # Instead of hard-blocking, answer via Ollama with a gentle note
            if confidence_pct < 20.0:
                if self.ollama_available:
                    general_answer = self._handle_general_conversation(
                        query, chat_history, sentiment
                    )
                    note = ("\n\n📌 *Note: This answer isn't directly from your documents — "
                            "I couldn't find a strong match. For document-specific answers, "
                            "try rephrasing your question.*")
                    return general_answer + note, contexts, "Assistant", confidence_pct, sentiment
                else:
                    return (
                        "I'm not fully sure about that from the documents. "
                        "Try rephrasing or ask a more specific question.",
                        contexts, "Assistant", confidence_pct, sentiment
                    )

            # Generate answer with memory + sentiment tone
            if self.ollama_available:
                final_answer = self._generate_ollama_answer(
                    query, contexts,
                    chat_history=chat_history,
                    sentiment=sentiment
                )
            else:
                final_answer = self._simple_fallback(query, contexts)

            # Determine dominant source doc
            source_doc = "Multiple Documents"
            try:
                pdf_names = [m.get("pdf_name") for m in metadatas if isinstance(m, dict)]
                if pdf_names:
                    source_doc = max(set(pdf_names), key=pdf_names.count)
            except Exception:
                pass

            return final_answer, contexts, source_doc, confidence_pct, sentiment

        except Exception as e:
            logger.error(f"Search error: {e}")
            return f"Error processing your question: {str(e)}", [], "System", 0.0, "neutral"


    # ──────────────────────────────────────────────────────────────
    # FEATURE 2: Sentiment / Tone Detection
    # ──────────────────────────────────────────────────────────────
    def _detect_sentiment(self, text: str) -> str:
        """Classify user sentiment from keywords (no extra library needed)"""
        text_lower = text.lower()
        frustrated_kw = ["not working", "wrong", "useless", "bad", "terrible",
                         "broken", "awful", "doesn't work", "fail", "hate",
                         "frustrated", "annoying", "stupid", "horrible"]
        confused_kw   = ["confused", "don't understand", "unclear", "what do you mean",
                         "not sure", "help me", "explain", "how does", "what is",
                         "i don't get", "clarify", "makes no sense"]
        positive_kw   = ["thanks", "thank you", "great", "awesome", "perfect",
                         "excellent", "good", "love it", "appreciate", "helpful"]

        if any(k in text_lower for k in frustrated_kw):
            return "frustrated"
        if any(k in text_lower for k in confused_kw):
            return "confused"
        if any(k in text_lower for k in positive_kw):
            return "positive"
        return "neutral"

    def _sentiment_system_prompt(self, sentiment: str) -> str:
        """Return a system-prompt suffix based on detected sentiment"""
        if sentiment == "frustrated":
            return (" The user seems frustrated. Be extra patient, empathetic, and apologetic if "
                    "the information is limited. Acknowledge their concern before answering.")
        if sentiment == "confused":
            return (" The user seems confused. Explain step by step in simple language. "
                    "Avoid jargon and use examples where possible.")
        if sentiment == "positive":
            return " The user is happy. Keep the positive energy and be warm and friendly."
        return ""  # neutral — no change

    # ──────────────────────────────────────────────────────────────
    # FEATURE 1: Conversation Memory + answer generation
    # ──────────────────────────────────────────────────────────────
    def _generate_ollama_answer(
        self,
        query: str,
        contexts: List[str],
        chat_history: Optional[List[Dict]] = None,
        sentiment: str = "neutral"
    ) -> str:
        """Generate answer using Ollama with conversation memory & sentiment tone"""
        # Clean contexts
        clean_contexts = []
        for context in contexts[:3]:
            clean = re.sub(r'\s+', ' ', context).strip()
            if clean and len(clean) > 150:
                clean_contexts.append(clean)

        if not clean_contexts:
            return self._simple_fallback(query, contexts)

        context_text = "\n\n".join(clean_contexts)

        base_system = (
            "You are a helpful AI assistant that answers questions based on the "
            "provided document content. Answer directly and naturally."
        )
        system_prompt = base_system + self._sentiment_system_prompt(sentiment)

        # Build messages: system → history → current
        messages: List[Dict] = [{"role": "system", "content": system_prompt}]

        # Inject last 4 conversation turns (2 pairs) for memory
        if chat_history:
            for turn in chat_history[-4:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        # Current question with context
        user_prompt = (
            f"Based on this document content:\n\n{context_text}\n\n"
            f"Question: {query}\n\n"
            "Please provide a helpful answer based on the content:"
        )
        messages.append({"role": "user", "content": user_prompt})

        try:
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
                return response.json()["message"]["content"].strip()
            raise Exception(f"Ollama API error: {response.status_code}")
        except Exception:
            return self._simple_fallback(query, contexts)

    # ──────────────────────────────────────────────────────────────
    # FEATURE 4: Follow-up Question Generation
    # ──────────────────────────────────────────────────────────────
    def generate_followup_questions(
        self,
        query: str,
        answer: str,
        contexts: List[str]
    ) -> List[str]:
        """Ask Ollama to suggest 3 follow-up questions. Returns list of strings."""
        if not self.ollama_available:
            return []
        try:
            context_snippet = contexts[0][:400] if contexts else ""
            prompt = (
                f"A user asked: '{query}'\n"
                f"The AI answered: '{answer[:300]}'\n"
                f"Document context: '{context_snippet}'\n\n"
                "Generate EXACTLY 3 short follow-up questions the user might ask next. "
                "Return ONLY the 3 questions, one per line, no numbering, no extra text."
            )
            raw = self._call_ollama(prompt, "You generate concise follow-up questions.")
            # Parse lines, drop empty / very long ones
            questions = [
                line.strip().lstrip("0123456789.-) ")
                for line in raw.splitlines()
                if line.strip() and len(line.strip()) < 120
            ][:3]
            return questions
        except Exception as e:
            logger.warning(f"Follow-up generation failed: {e}")
            return []

    def _simple_fallback(self, query: str, contexts: List[str]) -> str:
        """Simple fallback answer"""
        if not contexts:
            return f"I couldn't find information about '{query}' in the documents."
        best_context = contexts[0]
        sentences = [s.strip() for s in best_context.split('. ') if len(s.strip()) > 20]
        if sentences:
            return sentences[0]
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

    def get_all_chunks(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve all chunks from the database organized by PDF
        
        Returns:
            Dictionary with PDF names as keys and list of chunk data as values
        """
        try:
            all_data = self.collection.get()
            
            if not all_data or not all_data.get("ids"):
                return {}
            
            chunks_by_pdf = {}
            
            for id_, doc, metadata in zip(
                all_data.get("ids", []),
                all_data.get("documents", []),
                all_data.get("metadatas", [])
            ):
                pdf_name = metadata.get("pdf_name", "Unknown")
                
                if pdf_name not in chunks_by_pdf:
                    chunks_by_pdf[pdf_name] = []
                
                chunks_by_pdf[pdf_name].append({
                    "chunk_id": metadata.get("chunk_id", 0),
                    "content": doc,
                    "length": len(doc),
                    "id": id_
                })
            
            return chunks_by_pdf
        
        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
            return {}

    def get_chunks_for_pdf(self, pdf_name: str) -> List[Dict[str, Any]]:
        """
        Retrieve all chunks for a specific PDF
        
        Args:
            pdf_name: Name of the PDF to retrieve chunks for
            
        Returns:
            List of chunks with content and metadata
        """
        try:
            all_chunks = self.get_all_chunks()
            return all_chunks.get(pdf_name, [])
        except Exception as e:
            logger.error(f"Error retrieving chunks for {pdf_name}: {e}")
            return []

    def display_chunks(self, pdf_name: Optional[str] = None) -> str:
        """
        Display chunks in a formatted way (for debugging/inspection)
        
        Args:
            pdf_name: Specific PDF to display (optional). If None, shows all PDFs summary
            
        Returns:
            Formatted string representation of chunks
        """
        try:
            all_chunks = self.get_all_chunks()
            
            if not all_chunks:
                return "❌ No chunks found in database"
            
            output = ""
            
            if pdf_name:
                if pdf_name not in all_chunks:
                    return f"❌ PDF '{pdf_name}' not found"
                
                chunks = all_chunks[pdf_name]
                output += f"\n{'='*80}\n"
                output += f"📄 Chunks for PDF: {pdf_name}\n"
                output += f"{'='*80}\n"
                output += f"Total Chunks: {len(chunks)}\n\n"
                
                for chunk in sorted(chunks, key=lambda x: x.get("chunk_id", 0)):
                    chunk_id = chunk.get("chunk_id", "?")
                    content = chunk.get("content", "")
                    output += f"\n[Chunk {chunk_id}] Content length: {chunk.get('length', 0)} characters\n"
                    output += f"{'-'*80}\n"
                    output += content[:500] + ("...\n" if len(content) > 500 else "\n")
                    output += "\n"
            else:
                # Summary of all PDFs
                output += f"\n{'='*80}\n"
                output += f"📚 All Processed PDFs and Their Chunks\n"
                output += f"{'='*80}\n\n"
                
                for pdf_name_, chunks in sorted(all_chunks.items()):
                    total_chars = sum(c.get("length", 0) for c in chunks)
                    output += f"📄 {pdf_name_}\n"
                    output += f"   Total Chunks: {len(chunks)}\n"
                    output += f"   Total Size: {total_chars:,} characters\n"
                    output += f"   {'-'*76}\n"
                    
                    for chunk in sorted(chunks, key=lambda x: x.get("chunk_id", 0))[:3]:
                        preview = chunk.get("content", "")[:80].replace("\n", " ")
                        output += f"   [Chunk {chunk.get('chunk_id', '?')}] {chunk.get('length', 0)} chars | {preview}...\n"
                    
                    if len(chunks) > 3:
                        output += f"   ... and {len(chunks) - 3} more chunks\n"
                    output += "\n"
            
            return output
        
        except Exception as e:
            logger.error(f"Error displaying chunks: {e}")
            return f"❌ Error: {e}"

if __name__ == "__main__":
    rag = AdvancedRAGEngine()
    print(rag.get_system_status())