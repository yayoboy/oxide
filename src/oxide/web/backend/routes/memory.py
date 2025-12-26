"""
Memory Management API Endpoints

Provides REST API for context memory operations:
- List conversations
- Get conversation details
- Search conversations
- Prune old conversations
- Get memory statistics
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ....memory.context_memory import get_context_memory
from ....utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/memory", tags=["memory"])


# Request/Response models
class ConversationSummary(BaseModel):
    """Summary of a conversation"""
    id: str
    created_at: float
    updated_at: float
    message_count: int
    metadata: Dict[str, Any]


class Message(BaseModel):
    """Single message in a conversation"""
    id: str
    role: str
    content: str
    timestamp: float
    metadata: Dict[str, Any]


class Conversation(BaseModel):
    """Full conversation with messages"""
    id: str
    created_at: float
    updated_at: float
    messages: List[Message]
    metadata: Dict[str, Any]


class SearchResult(BaseModel):
    """Search result with similarity score"""
    conversation_id: str
    similarity: float
    created_at: float
    updated_at: float
    message_count: int
    metadata: Dict[str, Any]


class MemoryStats(BaseModel):
    """Memory statistics"""
    total_conversations: int
    total_messages: int
    average_messages_per_conversation: float
    oldest_conversation: Optional[str]
    newest_conversation: Optional[str]
    storage_path: str


class PruneRequest(BaseModel):
    """Request to prune old conversations"""
    max_age_days: int = 30


class PruneResponse(BaseModel):
    """Response from pruning operation"""
    conversations_removed: int
    message: str


# API Endpoints

@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of conversations to return"),
    offset: int = Query(0, ge=0, description="Number of conversations to skip")
):
    """
    List all conversations.

    Returns a paginated list of conversation summaries.
    """
    try:
        memory = get_context_memory()
        conversations = []

        # Get all conversations
        all_convs = list(memory._memory.values())

        # Sort by updated_at (newest first)
        all_convs.sort(key=lambda x: x["updated_at"], reverse=True)

        # Apply pagination
        paginated = all_convs[offset:offset + limit]

        for conv in paginated:
            conversations.append(ConversationSummary(
                id=conv["id"],
                created_at=conv["created_at"],
                updated_at=conv["updated_at"],
                message_count=len(conv["messages"]),
                metadata=conv.get("metadata", {})
            ))

        logger.info(f"Listed {len(conversations)} conversations (offset={offset}, limit={limit})")
        return conversations

    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """
    Get full conversation by ID.

    Returns all messages in the conversation.
    """
    try:
        memory = get_context_memory()
        conv = memory.get_conversation(conversation_id)

        if not conv:
            raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")

        # Convert to response model
        messages = [
            Message(
                id=msg["id"],
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"],
                metadata=msg.get("metadata", {})
            )
            for msg in conv["messages"]
        ]

        return Conversation(
            id=conv["id"],
            created_at=conv["created_at"],
            updated_at=conv["updated_at"],
            messages=messages,
            metadata=conv.get("metadata", {})
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}/recent", response_model=List[Message])
async def get_recent_messages(
    conversation_id: str,
    max_messages: int = Query(10, ge=1, le=100, description="Maximum number of messages"),
    max_age_hours: Optional[int] = Query(None, ge=1, le=720, description="Maximum age in hours")
):
    """
    Get recent messages from a conversation.

    Returns the most recent messages, optionally filtered by age.
    """
    try:
        memory = get_context_memory()
        messages = memory.get_recent_context(
            conversation_id=conversation_id,
            max_messages=max_messages,
            max_age_hours=max_age_hours
        )

        return [
            Message(
                id=msg["id"],
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"],
                metadata=msg.get("metadata", {})
            )
            for msg in messages
        ]

    except Exception as e:
        logger.error(f"Failed to get recent messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=List[SearchResult])
async def search_conversations(
    query: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(5, ge=1, le=50, description="Maximum results"),
    min_similarity: float = Query(0.5, ge=0.0, le=1.0, description="Minimum similarity score")
):
    """
    Search for conversations similar to query.

    Uses keyword-based similarity matching.
    """
    try:
        memory = get_context_memory()
        results = memory.search_similar_conversations(
            query=query,
            limit=limit,
            min_similarity=min_similarity
        )

        return [
            SearchResult(
                conversation_id=result["conversation_id"],
                similarity=result["similarity"],
                created_at=result["created_at"],
                updated_at=result["updated_at"],
                message_count=result["message_count"],
                metadata=result.get("metadata", {})
            )
            for result in results
        ]

    except Exception as e:
        logger.error(f"Failed to search conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=MemoryStats)
async def get_memory_stats():
    """
    Get memory statistics.

    Returns overall statistics about stored conversations.
    """
    try:
        memory = get_context_memory()
        stats = memory.get_statistics()

        return MemoryStats(**stats)

    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prune", response_model=PruneResponse)
async def prune_old_conversations(request: PruneRequest):
    """
    Prune old conversations.

    Removes conversations older than specified days.
    """
    try:
        memory = get_context_memory()
        removed = memory.prune_old_conversations(max_age_days=request.max_age_days)

        logger.info(f"Pruned {removed} conversations (max_age_days={request.max_age_days})")

        return PruneResponse(
            conversations_removed=removed,
            message=f"Successfully removed {removed} conversations older than {request.max_age_days} days"
        )

    except Exception as e:
        logger.error(f"Failed to prune conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a specific conversation.

    Permanently removes the conversation from memory.
    """
    try:
        memory = get_context_memory()

        if conversation_id not in memory._memory:
            raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")

        del memory._memory[conversation_id]
        memory._save_memory()

        logger.info(f"Deleted conversation: {conversation_id}")

        return {"message": f"Conversation '{conversation_id}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations")
async def clear_all_memory():
    """
    Clear all memory.

    WARNING: This permanently deletes all conversations!
    """
    try:
        memory = get_context_memory()
        memory.clear_all()

        logger.warning("All memory cleared")

        return {"message": "All memory cleared successfully"}

    except Exception as e:
        logger.error(f"Failed to clear memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))
