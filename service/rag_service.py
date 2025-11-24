"""
RAG Service for storing and retrieving code analysis context.
Uses Langchain for embeddings and vector store operations.
"""
import os
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from utils.logger import logger

load_dotenv()


class RAGService(ABC):
    """Abstract base class for RAG services."""
    
    @abstractmethod
    def store_document(
        self,
        content: str,
        doc_type: str,
        language: Optional[str] = None,
        repo: Optional[str] = None,
        author: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a document in the vector database."""
        pass
    
    @abstractmethod
    def search_similar(
        self,
        query: str,
        top_k: int = 5,
        language: Optional[str] = None,
        doc_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        pass


class ChromaRAGService(RAGService):
    """ChromaDB implementation of RAG service using Langchain."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize ChromaDB RAG service."""
        self.db_path = db_path or os.getenv("CHROMA_DB_PATH", "./chroma_db")
        self.collection_name = "code_analysis"
        
        # Single embedding function and vector store shared by all providers
        self._embedding_function = None
        self._vector_store = None
        
        # Initialize embedding function (priority: Gemini → OpenAI → Anthropic)
        self._initialize_embeddings()
        
        # Initialize single vector store
        self._initialize_vector_store()
        
        logger.info(f"✅ ChromaRAGService initialized with path: {self.db_path}")
    
    def _initialize_embeddings(self):
        """Initialize a single embedding function with priority: Gemini → OpenAI → Anthropic."""
        # Priority 1: Google Gemini embeddings
        if api_key := os.getenv("GEMINI_API_KEY"):
            try:
                self._embedding_function = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001",
                    google_api_key=api_key,
                )
                logger.info("✅ Google Gemini embeddings initialized")
                return
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Google Gemini embeddings: {e}")
        
        # Priority 2: OpenAI embeddings
        if api_key := os.getenv("OPENAI_API_KEY"):
            try:
                openai_embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
                self._embedding_function = OpenAIEmbeddings(
                    model=openai_embedding_model,
                    openai_api_key=api_key,
                )
                logger.info(f"✅ OpenAI embeddings initialized (model: {openai_embedding_model})")
                return
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize OpenAI embeddings: {e}")
        
        # Priority 3: Anthropic embeddings (if available in langchain-anthropic)
        # Note: Anthropic doesn't have a dedicated embeddings API, so we fall back to OpenAI
        # If OpenAI is not available, we log a warning
        if not self._embedding_function:
            logger.warning("⚠️ No embedding function available. Please configure GEMINI_API_KEY or OPENAI_API_KEY")
    
    def _initialize_vector_store(self):
        """Initialize a single vector store shared by all providers."""
        if not self._embedding_function:
            logger.warning("⚠️ No embedding function available. Cannot initialize vector store.")
            return
        
        try:
            self._vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self._embedding_function,
                persist_directory=self.db_path,
            )
            logger.info(f"✅ Vector store initialized (shared by all providers)")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize vector store: {e}")
    
    def get_embedding_function(self):
        """Get the embedding function (shared by all providers)."""
        if not self._embedding_function:
            raise ValueError("No embedding function available. Please configure GEMINI_API_KEY or OPENAI_API_KEY")
        return self._embedding_function
    
    def store_document(
        self,
        content: str,
        doc_type: str,
        language: Optional[str] = None,
        repo: Optional[str] = None,
        author: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a document in ChromaDB (shared vector store)."""
        if not self._vector_store:
            logger.warning("⚠️ No vector store available. Cannot store document.")
            return None
        
        doc_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Prepare metadata
        doc_metadata = {
            "type": doc_type,
            "timestamp": timestamp,
            "content": content[:500],  # Store first 500 chars in metadata
        }
        
        if language:
            doc_metadata["language"] = language
        if repo:
            doc_metadata["repo"] = repo
        if author:
            doc_metadata["author"] = author
        if metadata:
            doc_metadata.update(metadata)
        
        # Store in the single shared vector store
        try:
            document = Document(
                page_content=content,
                metadata=doc_metadata,
            )
            self._vector_store.add_documents([document], ids=[doc_id])
            logger.info(f"✅ Document stored with ID: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"❌ Error storing document: {e}")
            return None
    
    def search_similar(
        self,
        query: str,
        top_k: int = 5,
        language: Optional[str] = None,
        doc_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents in ChromaDB (shared vector store)."""
        if not self._vector_store:
            logger.warning("⚠️ No vector store available. Cannot search documents.")
            return []
        
        try:
            # Build filter if needed
            where_filter = {}
            if language:
                where_filter["language"] = language
            if doc_type:
                where_filter["type"] = doc_type
            
            # Perform similarity search
            if where_filter:
                results = self._vector_store.similarity_search_with_score(
                    query,
                    k=top_k,
                    filter=where_filter,
                )
            else:
                results = self._vector_store.similarity_search_with_score(query, k=top_k)
            
            # Format results
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score),
                })
            
            logger.info(f"✅ Found {len(formatted_results)} similar documents")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Error searching similar documents: {e}", exc_info=True)
            return []


def create_rag_service() -> Optional[RAGService]:
    """Factory function to create RAG service based on configuration."""
    from service.rag_service_builders import RAG_IMPLEMENTATIONS
    
    vector_db_type = os.getenv("VECTOR_DB_TYPE", "chroma").lower()
    use_rag = os.getenv("USE_RAG", "true").lower() == "true"
    
    if not use_rag:
        logger.info("ℹ️ RAG is disabled via USE_RAG environment variable")
        return None
    
    # Use dictionary dispatch pattern
    builder = RAG_IMPLEMENTATIONS.get(vector_db_type)
    if builder:
        return builder()
    else:
        logger.warning(f"⚠️ Unknown vector DB type: {vector_db_type}")
        return None

