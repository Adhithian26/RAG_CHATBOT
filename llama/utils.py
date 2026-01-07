# utils.py - ENHANCED with AI Agent Utilities
import streamlit as st
import speech_recognition as sr
import pyttsx3
import tempfile
import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import threading
import queue
import time
from datetime import datetime
import numpy as np
import re

logger = logging.getLogger(__name__)

# ==================== AGENT MEMORY SYSTEM ====================

class AgentMemory:
    """
    Advanced memory system for AI Agent:
    - Short-term conversation memory
    - Long-term topic memory
    - Fact verification memory
    - Query pattern learning
    """
    
    def __init__(self, memory_path: str = "data/agent_memory"):
        self.memory_path = Path(memory_path)
        self.memory_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory caches
        self.conversation_context = {}
        self.fact_cache = {}
        self.query_patterns = {}
        
        # Load existing memory
        self._load_memory()
        
        logger.info("🧠 Agent Memory System initialized")
    
    def _load_memory(self):
        """Load persistent memory from disk"""
        try:
            memory_file = self.memory_path / "agent_memory.json"
            if memory_file.exists():
                with open(memory_file, 'r', encoding='utf-8') as f:
                    memory_data = json.load(f)
                    self.fact_cache = memory_data.get("fact_cache", {})
                    self.query_patterns = memory_data.get("query_patterns", {})
        except Exception as e:
            logger.warning(f"Could not load memory: {e}")
    
    def _save_memory(self):
        """Save memory to disk"""
        try:
            memory_data = {
                "fact_cache": self.fact_cache,
                "query_patterns": self.query_patterns,
                "last_saved": datetime.now().isoformat()
            }
            
            memory_file = self.memory_path / "agent_memory.json"
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump(memory_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Could not save memory: {e}")
    
    def add_conversation_context(self, user_id: str, query: str, answer: str, 
                                contexts: List[str], confidence: float):
        """Add conversation context to memory"""
        if user_id not in self.conversation_context:
            self.conversation_context[user_id] = []
        
        context_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "answer": answer[:500],  # Store excerpt
            "context_count": len(contexts),
            "confidence": confidence,
            "top_context": contexts[0][:200] if contexts else ""
        }
        
        self.conversation_context[user_id].append(context_entry)
        
        # Keep only last 10 conversations per user
        if len(self.conversation_context[user_id]) > 10:
            self.conversation_context[user_id] = self.conversation_context[user_id][-10:]
        
        # Extract and cache key facts
        self._extract_and_cache_facts(query, answer, contexts)
        
        # Learn query patterns
        self._learn_query_pattern(query, answer, confidence)
    
    def _extract_and_cache_facts(self, query: str, answer: str, contexts: List[str]):
        """Extract and cache factual information"""
        try:
            # Extract dates, numbers, names
            dates = re.findall(r'\b\d{4}\b|\b\d{1,2}/\d{1,2}/\d{4}\b', answer)
            numbers = re.findall(r'\b\d+(?:\.\d+)?\b', answer)
            
            # Simple entity extraction
            entities = []
            for context in contexts[:2]:
                # Look for capitalized phrases (potential names/entities)
                caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', context)
                entities.extend(caps[:3])  # Take top 3
            
            # Cache facts
            fact_key = query.lower()[:50]
            self.fact_cache[fact_key] = {
                "query": query,
                "dates": list(set(dates)),
                "numbers": list(set(numbers[:5])),  # Limit to 5 numbers
                "entities": list(set(entities[:5])),  # Limit to 5 entities
                "cached_at": datetime.now().isoformat(),
                "source_contexts": len(contexts)
            }
            
            # Save memory periodically
            if len(self.fact_cache) % 10 == 0:
                self._save_memory()
                
        except Exception as e:
            logger.debug(f"Fact extraction failed: {e}")
    
    def _learn_query_pattern(self, query: str, answer: str, confidence: float):
        """Learn patterns from successful queries"""
        query_lower = query.lower()
        words = query_lower.split()
        
        if len(words) >= 3 and confidence > 70:
            # Extract query patterns (starting phrases)
            for i in range(min(3, len(words))):
                pattern = " ".join(words[:i+1])
                if pattern not in self.query_patterns:
                    self.query_patterns[pattern] = {
                        "count": 0,
                        "avg_confidence": 0,
                        "successful_answers": []
                    }
                
                self.query_patterns[pattern]["count"] += 1
                current_avg = self.query_patterns[pattern]["avg_confidence"]
                count = self.query_patterns[pattern]["count"]
                
                # Update moving average confidence
                self.query_patterns[pattern]["avg_confidence"] = (
                    (current_avg * (count - 1) + confidence) / count
                )
                
                # Store successful answer pattern
                if confidence > 80:
                    answer_start = answer[:100].lower()
                    if answer_start and answer_start not in self.query_patterns[pattern]["successful_answers"]:
                        self.query_patterns[pattern]["successful_answers"].append(answer_start)
    
    def get_relevant_context(self, user_id: str, current_query: str) -> List[str]:
        """Get relevant context from previous conversations"""
        if user_id not in self.conversation_context:
            return []
        
        relevant = []
        current_lower = current_query.lower()
        
        for conv in self.conversation_context[user_id][-5:]:  # Last 5 conversations
            prev_query = conv["query"].lower()
            prev_answer = conv.get("answer", "")
            
            # Check similarity
            common_words = set(current_lower.split()) & set(prev_query.split())
            if len(common_words) >= 2 and len(prev_answer) > 20:
                relevant.append(f"Previous query about similar topic: '{conv['query']}'. Previous answer: {prev_answer[:200]}...")
        
        return relevant[:2]  # Return top 2 relevant contexts
    
    def get_cached_facts(self, query: str) -> Dict:
        """Get cached facts for similar queries"""
        query_lower = query.lower()[:50]
        
        # Check exact match first
        if query_lower in self.fact_cache:
            return self.fact_cache[query_lower]
        
        # Check for similar queries
        for cached_query in self.fact_cache:
            if cached_query in query_lower or query_lower in cached_query:
                return self.fact_cache[cached_query]
        
        return {}
    
    def get_query_suggestions(self, partial_query: str) -> List[str]:
        """Get query suggestions based on learned patterns"""
        partial_lower = partial_query.lower()
        suggestions = []
        
        for pattern, data in self.query_patterns.items():
            if pattern.startswith(partial_lower) and data["avg_confidence"] > 70:
                # Get successful answer patterns to suggest completion
                for answer_start in data["successful_answers"][:2]:
                    # Create suggestion
                    suggestion = f"{pattern}..."
                    if suggestion not in suggestions:
                        suggestions.append(suggestion)
        
        return suggestions[:3]

# ==================== ENHANCED VOICE HANDLER WITH AGENT FEATURES ====================

class AgentVoiceHandler:
    """
    Enhanced voice handler with agent integration
    """
    
    def __init__(self, default_language: str = "en-US"):
        self.recognizer = sr.Recognizer()
        self.default_language = default_language
        self.tts_engine = self._initialize_advanced_tts()
        
        # Voice command recognition
        self.voice_commands = {
            "stop listening": self._stop_listening,
            "clear chat": self._clear_chat,
            "read last answer": self._read_last_answer,
            "search for": self._search_command,
        }
        
        logger.info("🎤 Agent Voice Handler initialized")
    
    def _initialize_advanced_tts(self) -> Optional[pyttsx3.Engine]:
        """Your existing TTS initialization"""
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            if voices:
                female_voices = [v for v in voices if 'female' in v.name.lower() or 'zira' in v.name.lower()]
                if female_voices:
                    engine.setProperty('voice', female_voices[0].id)
                else:
                    engine.setProperty('voice', voices[0].id)
            
            engine.setProperty('rate', 160)
            engine.setProperty('volume', 0.9)
            engine.setProperty('pitch', 110)
            
            return engine
        except Exception as e:
            logger.warning(f"⚠ TTS engine initialization failed: {e}")
            return None
    
    def process_voice_command(self, text: str) -> Tuple[bool, str]:
        """Process voice commands for agent control"""
        text_lower = text.lower()
        
        for command, handler in self.voice_commands.items():
            if command in text_lower:
                return True, handler(text_lower)
        
        # Check for query refinement
        if any(phrase in text_lower for phrase in ["more details about", "explain further", "what about"]):
            return True, "REFINE_QUERY"
        
        return False, text
    
    def _stop_listening(self, text: str) -> str:
        return "VOICE_COMMAND:STOP_LISTENING"
    
    def _clear_chat(self, text: str) -> str:
        return "VOICE_COMMAND:CLEAR_CHAT"
    
    def _read_last_answer(self, text: str) -> str:
        return "VOICE_COMMAND:READ_LAST_ANSWER"
    
    def _search_command(self, text: str) -> str:
        # Extract search term after "search for"
        match = re.search(r'search for (.+)', text, re.IGNORECASE)
        if match:
            return f"VOICE_COMMAND:SEARCH:{match.group(1).strip()}"
        return "VOICE_COMMAND:SEARCH"

# ==================== AGENT RESPONSE ANALYZER ====================

class AgentResponseAnalyzer:
    """
    Analyze and enhance agent responses
    """
    
    @staticmethod
    def analyze_response_quality(answer: str, contexts: List[str]) -> Dict:
        """Analyze response quality metrics"""
        metrics = {
            "length_score": min(len(answer) / 500 * 100, 100),  # Optimal ~500 chars
            "structure_score": 0,
            "clarity_score": 0,
            "completeness_score": 0,
        }
        
        # Check structure
        has_bullets = bool(re.search(r'[-•*]\s', answer))
        has_numbers = bool(re.search(r'\d+\.\s', answer))
        has_paragraphs = len(answer.split('\n\n')) > 1
        
        if has_bullets or has_numbers:
            metrics["structure_score"] = 90
        elif has_paragraphs:
            metrics["structure_score"] = 70
        else:
            metrics["structure_score"] = 50
        
        # Check clarity (sentence length variation)
        sentences = re.split(r'[.!?]+', answer)
        if sentences:
            avg_length = np.mean([len(s.split()) for s in sentences if s.strip()])
            if 10 <= avg_length <= 25:
                metrics["clarity_score"] = 90
            else:
                metrics["clarity_score"] = 70
        
        # Check completeness against contexts
        if contexts:
            context_keywords = set()
            for ctx in contexts[:2]:
                context_keywords.update(re.findall(r'\b\w{4,}\b', ctx.lower()))
            
            answer_keywords = set(re.findall(r'\b\w{4,}\b', answer.lower()))
            overlap = len(context_keywords & answer_keywords)
            
            if context_keywords:
                metrics["completeness_score"] = min(overlap / len(context_keywords) * 100, 100)
        
        # Overall score
        metrics["overall_score"] = round(np.mean(list(metrics.values())), 1)
        
        return metrics
    
    @staticmethod
    def enhance_response(answer: str, metrics: Dict) -> str:
        """Enhance response based on analysis"""
        enhanced = answer
        
        # Add structure if missing
        if metrics["structure_score"] < 60 and len(answer) > 300:
            # Try to add bullet points for lists
            sentences = answer.split('. ')
            if len(sentences) > 3:
                # Find list-like sentences
                list_patterns = ["first", "second", "third", "also", "additionally", "furthermore"]
                list_sentences = [s for s in sentences if any(p in s.lower() for p in list_patterns)]
                
                if list_sentences:
                    # Convert to bullet points
                    bulleted = "• " + "\n• ".join(list_sentences)
                    enhanced = bulleted
        
        return enhanced
    
    @staticmethod
    def generate_response_summary(answer: str, confidence: float) -> str:
        """Generate executive summary of response"""
        # Extract key sentence (first sentence or most informative)
        sentences = [s.strip() for s in re.split(r'[.!?]+', answer) if s.strip()]
        
        if not sentences:
            return ""
        
        # Use first sentence if short, else find most informative
        if len(sentences[0]) <= 100:
            summary = sentences[0]
        else:
            # Find sentence with most keywords
            keyword_counts = []
            for sentence in sentences[:3]:
                keywords = re.findall(r'\b\w{5,}\b', sentence.lower())
                keyword_counts.append((len(keywords), sentence))
            
            if keyword_counts:
                summary = max(keyword_counts, key=lambda x: x[0])[1]
            else:
                summary = sentences[0]
        
        # Add confidence indicator
        if confidence > 80:
            confidence_emoji = "🔵"
        elif confidence > 60:
            confidence_emoji = "🟡"
        else:
            confidence_emoji = "🔴"
        
        return f"{confidence_emoji} {summary}"

# ==================== AGENT UI COMPONENTS ====================

class AgentUIComponents:
    """
    Streamlit UI components for agent features
    """
    
    @staticmethod
    def display_agent_metrics(metrics: Dict):
        """Display agent metrics in sidebar"""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🤖 Agent Analytics")
        
        if "confidence" in metrics:
            # Confidence gauge
            confidence = metrics.get("confidence", 0)
            color = "green" if confidence > 80 else "orange" if confidence > 60 else "red"
            st.sidebar.markdown(f"**Confidence:** :{color}[{confidence}%]")
        
        if "reasoning_used" in metrics:
            st.sidebar.markdown(f"**Advanced Reasoning:** {'✅ Enabled' if metrics.get('reasoning_used') else '⚡ Basic'}")
        
        if "context_quality" in metrics:
            quality = metrics.get("context_quality", 0)
            st.sidebar.metric("📚 Context Quality", f"{quality}/100")
    
    @staticmethod
    def display_thinking_process(reasoning_steps: List[str]):
        """Display agent's thinking process (collapsible)"""
        with st.expander("🧠 Agent Thinking Process", expanded=False):
            for step in reasoning_steps:
                st.markdown(step)
    
    @staticmethod
    def display_source_analysis(source_details: List[Dict], agent_metrics: Dict):
        """Enhanced source analysis display"""
        with st.expander("📊 Source Analysis", expanded=False):
            if source_details:
                for source in source_details:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Source {source['source_number']}:** {source['pdf_name']}")
                        st.caption(f"Relevance: {source['relevance_score']}%")
                    with col2:
                        if source['relevance_score'] > 80:
                            st.success("✓ High")
                        elif source['relevance_score'] > 50:
                            st.info("✓ Medium")
                        else:
                            st.warning("⚠ Low")
            
            if agent_metrics:
                st.markdown("---")
                st.markdown("**Agent Assessment:**")
                if agent_metrics.get("verification_passed", True):
                    st.success("✅ Answer verified against sources")
                else:
                    st.warning("⚠ Answer may contain unsupported claims")

# ==================== MAIN INTEGRATION WRAPPER ====================

class AIAgentWrapper:
    """
    Main wrapper to integrate AI Agent features into your existing app
    """
    
    def __init__(self, rag_engine):
        self.rag_engine = rag_engine
        self.memory = AgentMemory()
        self.voice_handler = AgentVoiceHandler()
        self.analyzer = AgentResponseAnalyzer()
        self.ui = AgentUIComponents()
        
        logger.info("🚀 AI Agent Wrapper initialized")
    
    def enhanced_search(self, query: str, user_id: str = "default", 
                       use_advanced_reasoning: bool = True) -> Dict:
        """
        Enhanced search with agent features
        Returns complete response dictionary
        """
        # Get memory context
        memory_context = self.memory.get_relevant_context(user_id, query)
        cached_facts = self.memory.get_cached_facts(query)
        
        # Prepare enhanced query with memory
        enhanced_query = query
        if memory_context:
            enhanced_query = f"{query}\n\nRelevant context from previous conversations:\n" + "\n".join(memory_context)
        
        # Perform search with agent reasoning
        answer, contexts, source_doc, source_details, agent_metrics = self.rag_engine.search(
            enhanced_query, 
            top_k=7, 
            use_agent_reasoning=use_advanced_reasoning
        )
        
        # Analyze response quality
        response_metrics = self.analyzer.analyze_response_quality(answer, contexts)
        
        # Combine metrics
        all_metrics = {**agent_metrics, **response_metrics}
        
        # Enhance response if needed
        if response_metrics["overall_score"] < 70 and len(answer) > 100:
            answer = self.analyzer.enhance_response(answer, response_metrics)
        
        # Generate summary
        summary = self.analyzer.generate_response_summary(
            answer, 
            all_metrics.get("confidence", 70)
        )
        
        # Update memory
        self.memory.add_conversation_context(
            user_id, query, answer, contexts, 
            all_metrics.get("confidence", 70)
        )
        
        # Return complete response
        return {
            "answer": answer,
            "contexts": contexts,
            "source_doc": source_doc,
            "source_details": source_details,
            "metrics": all_metrics,
            "summary": summary,
            "cached_facts": cached_facts,
            "query_suggestions": self.memory.get_query_suggestions(query)
        }

# ==================== BACKWARD COMPATIBILITY ====================

# Keep all your existing classes for backward compatibility
class VoiceHandler(AgentVoiceHandler):
    """Backward compatibility"""
    pass

class AdvancedChatManager:
    """Simple persistent chat manager used by the Streamlit UI.

    Stores chats as JSON files under `base_path/<username>/<chat_id>.json`.
    Provides minimal API expected by `main.py`:
      - create_new_chat(username, topic=None) -> chat_id
      - get_user_chats(username) -> List[dict]
      - load_chat(username, chat_id) -> List[messages]
      - add_message(username, chat_id, role, content) -> bool
      - delete_chat(username, chat_id) -> bool
    """
    def __init__(self, base_path: str = "data/chat_history"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def _user_folder(self, username: str) -> str:
        safe_user = re.sub(r"[^a-zA-Z0-9_\-]", "_", username or "anonymous")
        folder = os.path.join(self.base_path, safe_user)
        os.makedirs(folder, exist_ok=True)
        return folder

    def _chat_path(self, username: str, chat_id: str) -> str:
        return os.path.join(self._user_folder(username), f"{chat_id}.json")

    def create_new_chat(self, username: str, topic: str = None) -> str:
        chat_id = f"chat_{int(time.time())}"
        if topic:
            # keep topic short and safe in filename
            safe_topic = re.sub(r"[^a-zA-Z0-9_\-]", "_", topic)[:50]
            chat_id = f"{safe_topic}_{chat_id}"

        initial = {
            "id": chat_id,
            "topic": topic or "",
            "created_at": time.time(),
            "messages": []
        }

        try:
            path = self._chat_path(username, chat_id)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(initial, f, indent=2)
            return chat_id
        except Exception:
            return chat_id

    def get_user_chats(self, username: str) -> list:
        folder = self._user_folder(username)
        chats = []
        try:
            for fname in os.listdir(folder):
                if not fname.endswith('.json'):
                    continue
                path = os.path.join(folder, fname)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        chats.append({
                            'id': data.get('id', fname.replace('.json', '')),
                            'topic': data.get('topic', ''),
                            'created_at': data.get('created_at')
                        })
                except Exception:
                    continue
            # sort by created_at desc
            chats.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        except Exception:
            pass
        return chats

    def load_chat(self, username: str, chat_id: str) -> list:
        path = self._chat_path(username, chat_id)
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('messages', [])
        except Exception:
            pass
        return []

    def add_message(self, username: str, chat_id: str, role: str, content: str) -> bool:
        path = self._chat_path(username, chat_id)
        try:
            if not os.path.exists(path):
                # create a new chat file
                self.create_new_chat(username, topic=None)

            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data.setdefault('messages', []).append({
                'role': role,
                'content': content,
                'created_at': time.time()
            })

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            return True
        except Exception:
            return False

    def delete_chat(self, username: str, chat_id: str) -> bool:
        path = self._chat_path(username, chat_id)
        try:
            if os.path.exists(path):
                os.remove(path)
                return True
        except Exception:
            pass
        return False

class ChatHistoryManager:
    """Your existing class - unchanged"""
    pass

# Test the agent system
if __name__ == "__main__":
    print("🧪 Testing AI Agent System...")
    
    # Test memory system
    memory = AgentMemory()
    print(f"✅ Memory system: {len(memory.fact_cache)} cached facts")
    
    # Test analyzer
    analyzer = AgentResponseAnalyzer()
    test_answer = "The quick brown fox jumps over the lazy dog. This is a test sentence for analysis."
    metrics = analyzer.analyze_response_quality(test_answer, [test_answer])
    print(f"✅ Response analyzer: {metrics['overall_score']}% quality")
    
    print("🎯 AI Agent utilities ready!")