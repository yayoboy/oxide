"""
Context Memory System for Oxide

Manages conversation history and context retrieval for LLM tasks.
Enables continuity across multiple task executions.
"""
import json
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta

from ..utils.logging import get_logger


class ContextMemory:
    """
    Manages context memory for conversations and tasks.

    Features:
    - Store conversation history
    - Retrieve relevant context for new tasks
    - Automatic context pruning based on time/size
    - Semantic similarity search (optional)
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize context memory.

        Args:
            storage_path: Path to memory storage file (default: ~/.oxide/memory.json)
        """
        self.logger = get_logger(__name__)

        if storage_path is None:
            storage_path = Path.home() / ".oxide" / "memory.json"

        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory cache
        self._memory: Dict[str, Any] = {}
        self._load_memory()

        self.logger.info(f"Context memory initialized at {self.storage_path}")

    def _load_memory(self):
        """Load memory from disk"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    self._memory = json.load(f)
                self.logger.debug(f"Loaded {len(self._memory)} memory entries")
            except Exception as e:
                self.logger.warning(f"Failed to load memory: {e}")
                self._memory = {}
        else:
            self._memory = {}

    def _save_memory(self):
        """Save memory to disk"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self._memory, f, indent=2)
            self.logger.debug("Memory saved to disk")
        except Exception as e:
            self.logger.error(f"Failed to save memory: {e}")

    def add_context(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a message to conversation memory.

        Args:
            conversation_id: Unique conversation identifier
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata (task_type, service, etc.)

        Returns:
            Message ID
        """
        timestamp = time.time()
        message_id = f"{conversation_id}_{int(timestamp * 1000)}"

        # Create conversation if doesn't exist
        if conversation_id not in self._memory:
            self._memory[conversation_id] = {
                "id": conversation_id,
                "created_at": timestamp,
                "updated_at": timestamp,
                "messages": [],
                "metadata": metadata or {}
            }

        # Add message
        message = {
            "id": message_id,
            "role": role,
            "content": content,
            "timestamp": timestamp,
            "metadata": metadata or {}
        }

        self._memory[conversation_id]["messages"].append(message)
        self._memory[conversation_id]["updated_at"] = timestamp

        self._save_memory()

        self.logger.debug(f"Added message to conversation {conversation_id}")
        return message_id

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full conversation by ID.

        Args:
            conversation_id: Conversation identifier

        Returns:
            Conversation dict or None if not found
        """
        return self._memory.get(conversation_id)

    def get_recent_context(
        self,
        conversation_id: str,
        max_messages: int = 10,
        max_age_hours: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent messages from a conversation.

        Args:
            conversation_id: Conversation identifier
            max_messages: Maximum number of messages to return
            max_age_hours: Only return messages newer than this (hours)

        Returns:
            List of messages (most recent first)
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []

        messages = conversation["messages"]

        # Filter by age if specified
        if max_age_hours is not None:
            cutoff_time = time.time() - (max_age_hours * 3600)
            messages = [m for m in messages if m["timestamp"] >= cutoff_time]

        # Return most recent N messages
        return list(reversed(messages[-max_messages:]))

    def search_similar_conversations(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search for conversations similar to query.

        Note: This is a simple keyword-based search.
        For production, consider using vector embeddings (e.g., sentence-transformers).

        Args:
            query: Search query
            limit: Maximum results to return
            min_similarity: Minimum similarity score (0-1)

        Returns:
            List of conversations with similarity scores
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        results = []

        for conv_id, conversation in self._memory.items():
            # Calculate simple keyword overlap similarity
            conv_text = ""
            for msg in conversation["messages"]:
                conv_text += msg["content"].lower() + " "

            conv_words = set(conv_text.split())

            if not conv_words:
                continue

            # Jaccard similarity
            intersection = len(query_words & conv_words)
            union = len(query_words | conv_words)
            similarity = intersection / union if union > 0 else 0

            if similarity >= min_similarity:
                results.append({
                    "conversation_id": conv_id,
                    "similarity": similarity,
                    "created_at": conversation["created_at"],
                    "updated_at": conversation["updated_at"],
                    "message_count": len(conversation["messages"]),
                    "metadata": conversation.get("metadata", {})
                })

        # Sort by similarity (descending)
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results[:limit]

    def get_context_for_task(
        self,
        task_type: str,
        prompt: str,
        max_messages: int = 5,
        max_age_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get relevant context for a new task.

        Combines:
        1. Recent messages from current session
        2. Similar past conversations

        Args:
            task_type: Type of task (coding, review, etc.)
            prompt: Task prompt
            max_messages: Max messages per conversation
            max_age_hours: Only consider recent conversations

        Returns:
            List of relevant context messages
        """
        context = []

        # Search for similar past conversations
        similar = self.search_similar_conversations(
            query=prompt,
            limit=3,
            min_similarity=0.3
        )

        cutoff_time = time.time() - (max_age_hours * 3600)

        for item in similar:
            # Only include recent conversations
            if item["updated_at"] < cutoff_time:
                continue

            conv = self.get_conversation(item["conversation_id"])
            if conv:
                # Get last few messages from this conversation
                recent = self.get_recent_context(
                    item["conversation_id"],
                    max_messages=max_messages
                )

                context.extend(recent)

        return context

    def prune_old_conversations(self, max_age_days: int = 30) -> int:
        """
        Remove conversations older than specified days.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of conversations removed
        """
        cutoff_time = time.time() - (max_age_days * 86400)

        to_remove = [
            conv_id for conv_id, conv in self._memory.items()
            if conv["updated_at"] < cutoff_time
        ]

        for conv_id in to_remove:
            del self._memory[conv_id]

        if to_remove:
            self._save_memory()
            self.logger.info(f"Pruned {len(to_remove)} old conversations")

        return len(to_remove)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get memory statistics.

        Returns:
            Statistics dict
        """
        total_conversations = len(self._memory)
        total_messages = sum(
            len(conv["messages"]) for conv in self._memory.values()
        )

        if total_conversations > 0:
            avg_messages = total_messages / total_conversations

            # Find oldest and newest
            timestamps = [conv["created_at"] for conv in self._memory.values()]
            oldest = min(timestamps)
            newest = max(timestamps)
        else:
            avg_messages = 0
            oldest = None
            newest = None

        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "average_messages_per_conversation": round(avg_messages, 2),
            "oldest_conversation": datetime.fromtimestamp(oldest).isoformat() if oldest else None,
            "newest_conversation": datetime.fromtimestamp(newest).isoformat() if newest else None,
            "storage_path": str(self.storage_path)
        }

    def clear_all(self):
        """Clear all memory (use with caution!)"""
        self._memory = {}
        self._save_memory()
        self.logger.warning("All memory cleared")


# Global context memory instance
_context_memory = None


def get_context_memory(storage_path: Optional[Path] = None) -> ContextMemory:
    """Get global context memory instance"""
    global _context_memory
    if _context_memory is None:
        _context_memory = ContextMemory(storage_path)
    return _context_memory
