# RAG (Retrieval Augmented Generation) - Documentation

## What is RAG?

RAG (Retrieval Augmented Generation) is a technique that combines text generation with the retrieval of relevant information from a knowledge base. Instead of the AI model generating responses based solely on its training, RAG allows:

1. **Retrieve** relevant information from a vector database
2. **Augment** the prompt with that context
3. **Generate** more accurate and contextualized responses

### Why use RAG?

- **Improves accuracy**: The model has access to domain-specific information
- **Reduces hallucinations**: The model bases its responses on verified stored information
- **Continuous learning**: Can improve over time by storing new reviews and patterns
- **Specific context**: Can access history of previous reviews, best practices, and technical documentation

## RAG Architecture in this Project

### Main Components

```
┌─────────────────┐
│  Code Analysis  │
│     Request     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  RAG Service    │ ◄─── Langchain (embeddings + vector store)
│  (ChromaDB)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Enriched       │
│  Prompt         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AI Provider    │ ◄─── Official SDKs (OpenAI, Anthropic, Google)
│  (SDK Official) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Analysis       │
│  Result         │
└─────────────────┘
```

### Separation of Responsibilities

- **Langchain**: Used ONLY for RAG (embedding generation and vector store operations)
- **Official SDKs**: Maintained for model calls (OpenAI, Anthropic, Google Generative AI)
- **ChromaDB**: Local vector database for storing and searching documents

## Detailed Workflow

### 1. Document Storage

When a document is stored (review, code snippet, or documentation):

```python
# The document is converted to an embedding using Langchain
embedding = embedding_function.embed_query(content)

# Stored in ChromaDB with metadata
{
    "id": "uuid",
    "content": "full text",
    "metadata": {
        "type": "review|code_snippet|documentation",
        "language": "python|react|react-native",
        "repo": "repo-name",
        "author": "author",
        "timestamp": "2024-01-01T00:00:00"
    }
}
```

### 2. Analysis Process with RAG

When an analysis request arrives:

1. **Diff decoding**: The base64 diff is decoded
2. **RAG search** (if `use_rag=True`):
   - An embedding of the diff is generated using the selected provider
   - The 5 most similar documents are searched in ChromaDB
   - Filtered by language if available
3. **Prompt enrichment**:
   - Retrieved context is added to the original prompt
   - The prompt now includes examples from previous reviews and best practices
4. **AI provider call**:
   - Official SDK is used (OpenAI, Anthropic, or Google)
   - The model generates the response with additional context
5. **Result storage**:
   - The generated review is stored in ChromaDB for future queries

### 3. Enriched Prompt Example

**Without RAG:**
```
Act as an expert code reviewer...
Analyze the following code diff:
{diff_text}
```

**With RAG:**
```
Act as an expert code reviewer...
Analyze the following code diff:
{diff_text}

## Context from Previous Reviews and Documentation:

[REVIEW] Similar issue found in previous review: 
Consider using type hints for better code clarity...

[CODE_SNIPPET] Best practice pattern:
def process_data(data: List[str]) -> Dict[str, Any]:
    # Always validate input
    if not data:
        return {}
    ...

[DOCUMENTATION] Python best practices:
- Use context managers for file operations
- Prefer list comprehensions over loops when appropriate
```

## Configuration

### Environment Variables

```bash
# Enable/disable RAG globally
USE_RAG=true  # default: true

# Vector database type
VECTOR_DB_TYPE=chroma  # default: chroma (future options: pinecone)

# Path to store ChromaDB locally
CHROMA_DB_PATH=./chroma_db  # default: ./chroma_db

# API Keys for embeddings (use the same ones as for models)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
```

### Embedding Models

- **OpenAI**: `text-embedding-3-small` (default) or `text-embedding-3-large`
  - Configurable with `OPENAI_EMBEDDING_MODEL`
- **Anthropic**: Official Claude embeddings
- **Google Gemini**: `models/embedding-001`

## System Usage

### Code Analysis with RAG

```python
POST /analize
{
    "pr_number": 123,
    "repo": "my-repo",
    "title": "Fix bug in authentication",
    "url": "https://github.com/...",
    "author": "developer",
    "diff_b64": "base64-encoded-diff",
    "provider": "openai",
    "language": "python",
    "use_rag": true  # Optional, default: true
}
```

### Manually Store Documents

```python
POST /store
{
    "content": "Documentation about Python best practices...",
    "doc_type": "documentation",  # review | code_snippet | documentation
    "language": "python",
    "repo": "my-repo",  # optional
    "author": "developer"  # optional
}
```

### Disable RAG per Request

```python
POST /analize
{
    ...
    "use_rag": false  # Disables RAG only for this request
}
```

## Data Structure in ChromaDB

Each stored document contains:

```python
{
    "id": "unique-uuid",
    "page_content": "full document text",
    "metadata": {
        "type": "review|code_snippet|documentation",
        "language": "python|react|react-native|javascript",
        "repo": "repository-name",
        "author": "author-name",
        "content": "first 500 characters (for metadata)",
        "timestamp": "2024-01-01T00:00:00",
        # Additional metadata according to document type
    }
}
```

## Document Types

### 1. Review (`type: "review"`)
- Code reviews generated automatically
- Stored after each successful analysis
- Additional metadata: `title`, `url`, `provider`

### 2. Code Snippet (`type: "code_snippet"`)
- Code snippets with best practices
- Common patterns and examples
- Additional metadata: `pattern_type`

### 3. Documentation (`type: "documentation"`)
- Technical documentation
- Style guides
- Team best practices
- Additional metadata: `doc_type`

## Search and Filtering

RAG search allows filtering by:

- **Language**: Only documents of the same language
- **Type**: Only reviews, code snippets, or documentation
- **Repository**: Documents from a specific repository
- **Semantic similarity**: Most relevant documents according to embedding

## Switching from ChromaDB to Other Vector Databases

The architecture is designed to facilitate database changes:

### 1. Implement New RAG Service Class

```python
class PineconeRAGService(RAGService):
    def __init__(self):
        # Initialize Pinecone
        pass
    
    def store_document(self, ...):
        # Implement storage in Pinecone
        pass
    
    def search_similar(self, ...):
        # Implement search in Pinecone
        pass
```

### 2. Update Factory Function

```python
def create_rag_service() -> Optional[RAGService]:
    vector_db_type = os.getenv("VECTOR_DB_TYPE", "chroma").lower()
    
    if vector_db_type == "chroma":
        return ChromaRAGService()
    elif vector_db_type == "pinecone":
        return PineconeRAGService()  # New implementation
    ...
```

### 3. Configure Environment Variables

```bash
VECTOR_DB_TYPE=pinecone
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=code-analysis
```

## Advantages of this Architecture

1. **Clear separation**: RAG (Langchain) vs Model calls (Official SDKs)
2. **Flexibility**: Easy to change vector database
3. **Configurability**: RAG can be enabled/disabled per request or globally
4. **Compatibility**: Maintains all existing functionality
5. **Scalability**: ChromaDB local for development, easy migration to cloud (Pinecone)

## Best Practices

1. **Store important reviews**: Successful reviews are stored automatically
2. **Document patterns**: Store code snippets with best practices
3. **Keep documentation updated**: Update technical documentation regularly
4. **Filter by language**: Ensure relevant documents are retrieved
5. **Review retrieved context**: Verify that RAG context is relevant

## Troubleshooting

### RAG is not working

1. Verify that `USE_RAG=true` in environment variables
2. Verify that embedding API keys are configured
3. Verify that ChromaDB has stored documents
4. Check logs for initialization errors

### Search returns no results

1. Verify that there are documents stored in ChromaDB
2. Verify that the language matches stored documents
3. Increase `top_k` if necessary
4. Verify that embeddings are being generated correctly

### Storage errors

1. Verify write permissions on `CHROMA_DB_PATH`
2. Verify that embedding API keys are valid
3. Check logs for specific errors

## Additional Resources

- [Langchain Documentation](https://python.langchain.com/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [RAG Paper](https://arxiv.org/abs/2005.11401)
