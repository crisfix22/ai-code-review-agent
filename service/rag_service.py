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
        provider: str,
        top_k: int = 5,
        language: Optional[str] = None,
        doc_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        pass
    
    @abstractmethod
    def get_embedding_function(self, provider: str):
        """Get the embedding function for the specified provider."""
        pass


class ChromaRAGService(RAGService):
    """ChromaDB implementation of RAG service using Langchain."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize ChromaDB RAG service."""
        self.db_path = db_path or os.getenv("CHROMA_DB_PATH", "./chroma_db")
        self.collection_name = "code_analysis"
        
        # Initialize embedding functions for each provider
        self._embedding_functions = {}
        self._vector_stores = {}
        
        # Initialize embeddings if API keys are available
        self._initialize_embeddings()
        
        # Initialize vector stores
        self._initialize_vector_stores()
        
        logger.info(f"✅ ChromaRAGService initialized with path: {self.db_path}")
    
    def _initialize_embeddings(self):
        """Initialize embedding functions for each provider."""
        openai_embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        openai_embedding = OpenAIEmbeddings(
            model=openai_embedding_model,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )
        # OpenAI embeddings
        if api_key := os.getenv("OPENAI_API_KEY"):
            try:
                self._embedding_functions["openai"] = openai_embedding
                logger.info("✅ OpenAI embeddings initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize OpenAI embeddings: {e}")
        
        # Anthropic embeddings
        if api_key := os.getenv("ANTHROPIC_API_KEY"):
            try:
                self._embedding_functions["claude"] = openai_embedding
                logger.info(f"✅ OpenAI embeddings initialized for Claude model : {openai_embedding_model}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize OpenAI embeddings for Claude model: {openai_embedding_model}: {e}")
        
        # Google Gemini embeddings
        if api_key := os.getenv("GEMINI_API_KEY"):
            try:
                self._embedding_functions["gemini"] = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001",
                    google_api_key=api_key,
                )
                logger.info("✅ Google Gemini embeddings initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Google Gemini embeddings: {e}")
    
    def _initialize_vector_stores(self):
        """Initialize vector stores for each provider."""
        for provider, embedding_func in self._embedding_functions.items():
            try:
                # Create collection name per provider
                collection_name = f"{self.collection_name}_{provider}"
                
                self._vector_stores[provider] = Chroma(
                    collection_name=collection_name,
                    embedding_function=embedding_func,
                    persist_directory=self.db_path,
                )
                logger.info(f"✅ Vector store initialized for provider: {provider}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize vector store for {provider}: {e}")
    
    def get_embedding_function(self, provider: str):
        """Get the embedding function for the specified provider."""
        provider = provider.lower()
        if provider not in self._embedding_functions:
            raise ValueError(
                f"Embedding function not available for provider: {provider}. "
                f"Available providers: {list(self._embedding_functions.keys())}"
            )
        return self._embedding_functions[provider]
    
    def store_document(
        self,
        content: str,
        doc_type: str,
        language: Optional[str] = None,
        repo: Optional[str] = None,
        author: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a document in ChromaDB."""
        if not self._vector_stores:
            logger.warning("⚠️ No vector stores available. Cannot store document.")
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
        
        # Store in all available vector stores (using first available provider as default)
        stored_ids = []
        for provider, vector_store in self._vector_stores.items():
            try:
                document = Document(
                    page_content=content,
                    metadata=doc_metadata,
                )
                vector_store.add_documents([document], ids=[doc_id])
                stored_ids.append(provider)
            except Exception as e:
                logger.error(f"❌ Error storing document in {provider} vector store: {e}")
        
        if stored_ids:
            logger.info(f"✅ Document stored with ID: {doc_id} in providers: {stored_ids}")
            return doc_id
        else:
            logger.error("❌ Failed to store document in any vector store")
            return None
    
    def search_similar(
        self,
        query: str,
        provider: str,
        top_k: int = 5,
        language: Optional[str] = None,
        doc_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents in ChromaDB."""
        provider = provider.lower()
        
        if provider not in self._vector_stores:
            logger.warning(
                f"⚠️ Vector store not available for provider: {provider}. "
                f"Available providers: {list(self._vector_stores.keys())}"
            )
            return []
        
        try:
            vector_store = self._vector_stores[provider]
            
            # Build filter if needed
            where_filter = {}
            if language:
                where_filter["language"] = language
            if doc_type:
                where_filter["type"] = doc_type
            
            # Perform similarity search
            if where_filter:
                results = vector_store.similarity_search_with_score(
                    query,
                    k=top_k,
                    filter=where_filter,
                )
            else:
                results = vector_store.similarity_search_with_score(query, k=top_k)
            
            # Format results
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score),
                })
            
            logger.info(f"✅ Found {len(formatted_results)} similar documents for provider: {provider}")
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

