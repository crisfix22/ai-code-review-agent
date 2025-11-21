"""
RAG Service Builder Functions

Centralizes the dispatch pattern for RAG service implementations using dictionary-based lookup.
"""
from typing import Callable, Optional, Dict

from service.rag_service import RAGService, ChromaRAGService
from main import logger


RAGBuilder = Callable[[], Optional[RAGService]]


def build_chroma_service() -> Optional[RAGService]:
    """
    Build ChromaDB RAG service.
    
    Returns:
        ChromaRAGService instance if successful, None otherwise
    """
    try:
        return ChromaRAGService()
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize ChromaRAGService: {e}")
        return None


def build_pinecone_service() -> Optional[RAGService]:
    """
    Build Pinecone RAG service (placeholder for future implementation).
    
    Returns:
        None (not yet implemented)
    """
    logger.warning("⚠️ Pinecone not yet implemented")
    return None


RAG_IMPLEMENTATIONS: Dict[str, RAGBuilder] = {
    "chroma": build_chroma_service,
    "pinecone": build_pinecone_service,
}
