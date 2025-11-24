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

The system uses a priority-based selection for embeddings (only one embedding function is used, shared by all providers):

**Priority Order:**
1. **Google Gemini** (highest priority): `models/embedding-001`
   - Used if `GEMINI_API_KEY` is configured
2. **OpenAI** (fallback): `text-embedding-3-small` (default) or `text-embedding-3-large`
   - Used if Gemini is not available and `OPENAI_API_KEY` is configured
   - Configurable with `OPENAI_EMBEDDING_MODEL`
3. **Anthropic** (not available): Anthropic does not provide a dedicated embeddings API
   - If only Anthropic API key is configured, the system will fall back to OpenAI embeddings (if available)
   - If neither Gemini nor OpenAI are available, embeddings will not work

**Note:** The embedding function is initialized once and shared across all AI providers (OpenAI, Gemini, Claude) for consistency in the vector database.

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
    "doc_type": "documentation",  # optional: review | code_snippet | documentation
    "language": "python",  # optional
    "repo": "my-repo",  # optional
    "author": "developer"  # optional
}
```

### Complete Example: Storing Code Analysis Results

This example demonstrates how to store a code analysis result in the vector database using the `/store` endpoint. This is useful for preserving important code review insights, best practices, and patterns that can be retrieved later to improve future code reviews.

#### Scenario

After analyzing a Python file that uses an anti-pattern (long if/elif chain), we want to store the analysis result and recommendations in the vector database so that similar patterns can be detected and improved in future code reviews.

#### 1. Code Being Analyzed

The following code was analyzed and found to have an anti-pattern issue:

```python
from enum import Enum

class BotType(str, Enum):
    TWITTER = "twitter"
    BLUESKY = "bluesky"
    X = "x"
    LINKEDIN = "linkedin"
    LINKEDIN_BUSINESS = "linkedin_business"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    PINTEREST = "pinterest"
    REDDIT = "reddit"

class BotAnalizer:
    def __init__(self):
        self.bot_type = BotType.TWITTER
    
    async def analize_bot(self, bot_type: BotType):
        self.bot_type = bot_type
        if self.bot_type == BotType.TWITTER:
            return self.analize_twitter()
        elif self.bot_type == BotType.BLUESKY:
            return self.analize_bluesky()
        elif self.bot_type == BotType.X:
            return self.analize_x()
        elif self.bot_type == BotType.LINKEDIN:
            return self.analize_linkedin()
        elif self.bot_type == BotType.LINKEDIN_BUSINESS:
            return self.analize_linkedin_business()
        elif self.bot_type == BotType.TIKTOK:
            return self.analize_tiktok()
        elif self.bot_type == BotType.INSTAGRAM:
            return self.analize_instagram()
        elif self.bot_type == BotType.FACEBOOK:
            return self.analize_facebook()
        elif self.bot_type == BotType.YOUTUBE:
            return self.analize_youtube()
        elif self.bot_type == BotType.PINTEREST:
            return self.analize_pinterest()
        elif self.bot_type == BotType.REDDIT:
            return self.analize_reddit()
        else:
            raise ValueError(f"Bot type {self.bot_type} not supported")
    
    async def analize_twitter(self):
        return "Twitter"
    
    # ... other methods ...
```

#### 2. Analysis Result Summary

The AI code review identified a critical anti-pattern: **If/Elif Chain Instead of Dictionary Dispatch**. The analysis found:

**Problem:**
- Long if/elif chain (11+ conditions) violates factory pattern best practices
- O(n) time complexity for lookups
- Difficult to extend with new bot types
- High cyclomatic complexity (18, recommended max: 10)

**Recommended Solution:**
Replace the if/elif chain with a registry-based factory pattern using a dictionary lookup:

```python
class BotAnalyzer:
    def __init__(self):
        self._analyzers = {
            BotType.TWITTER: self.analyze_twitter,
            BotType.BLUESKY: self.analyze_bluesky,
            BotType.X: self.analyze_x,
            BotType.LINKEDIN: self.analyze_linkedin,
            # ... etc
        }
    
    async def analyze_bot(self, bot_type: BotType) -> str:
        analyzer = self._analyzers.get(bot_type)
        if analyzer is None:
            raise ValueError(f"Bot type {bot_type} not supported")
        return await analyzer()
```

**Benefits:**
- O(1) lookup instead of O(n) comparison
- Easier to extend with new bot types
- More maintainable and testable
- Reduces cyclomatic complexity to ~2

#### 3. Storing the Analysis in Vector Database

To store this analysis result and recommendation in the vector database for future reference, use the `/store` endpoint:

**Request Body:**

```json
{
    "content": "### Improving Python Factory Patterns to Avoid Infinite If/Else\n\nWhen reviewing Python code that implements a factory function using multiple `if/elif` checks such as:\n\n```python\nif vector_db_type == \"chroma\":\n    return ChromaRAGService()\nelif vector_db_type == \"pinecone\":\n    return PineconeRAGService()\nelse:\n    return None\n```\n\nRecommend replacing the `if/elif` chain with a more scalable and maintainable pattern, such as a registry-based factory or a dictionary lookup, similar to how JavaScript uses an object map instead of switch/if-else.\n\nThis avoids code duplication, improves extensibility, and makes it easy to add new providers without touching the core factory logic.\n\n### Example Python improvement\n\nUse a provider map:\n\n```python\nPROVIDERS = {\n    \"chroma\": ChromaRAGService,\n    \"pinecone\": PineconeRAGService,\n}\n\ndef create_rag_service() -> Optional[RAGService]:\n    vector_db_type = os.getenv(\"VECTOR_DB_TYPE\", \"chroma\").lower()\n    use_rag = os.getenv(\"USE_RAG\", \"true\").lower() == \"true\"\n\n    if not use_rag:\n        logger.info(\"RAG disabled\")\n        return None\n\n    provider = PROVIDERS.get(vector_db_type)\n\n    if provider is None:\n        logger.warning(f\"Unknown vector DB type: {vector_db_type}\")\n        return None\n\n    try:\n        return provider()\n    except Exception as e:\n        logger.warning(f\"Failed to initialize provider {vector_db_type}: {e}\")\n        return None\n```\n\n### Equivalent JavaScript pattern (for cross-language consistency)\n\n```ts\nexport enum RAG_TYPE {\n  CHROMA = \"chroma_db\",\n  PINECONE = \"pinecone\"\n}\n\nexport const RAGS_IMPL = {\n  [RAG_TYPE.CHROMA]: {\n    ragProvider: () => chromaRAGService(),\n  },\n  [RAG_TYPE.PINECONE]: {\n    ragProvider: () => console.log(\"Not implemented\"),\n  },\n};\n```\n\n### Review Recommendation\nWhenever the model detects a Python factory using multiple `if/elif` statements, suggest switching to a registry/dictionary-based provider map, referencing the JS implementation pattern as a clean and extensible example.",
    "doc_type": "documentation",  // optional: review | code_snippet | documentation
    "language": "python",  // optional
    "repo": "my-repo",  // optional
    "author": "developer"  // optional
}
```

**Using curl:**

*Note: All fields except `content` are optional (`doc_type`, `language`, `repo`, `author`).*

```bash
curl -X POST "http://localhost:8080/store" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "### Improving Python Factory Patterns to Avoid Infinite If/Else\n\nWhen reviewing Python code that implements a factory function using multiple `if/elif` checks such as:\n\n```python\nif vector_db_type == \"chroma\":\n    return ChromaRAGService()\nelif vector_db_type == \"pinecone\":\n    return PineconeRAGService()\nelse:\n    return None\n```\n\nRecommend replacing the `if/elif` chain with a more scalable and maintainable pattern, such as a registry-based factory or a dictionary lookup, similar to how JavaScript uses an object map instead of switch/if-else.\n\nThis avoids code duplication, improves extensibility, and makes it easy to add new providers without touching the core factory logic.\n\n### Example Python improvement\n\nUse a provider map:\n\n```python\nPROVIDERS = {\n    \"chroma\": ChromaRAGService,\n    \"pinecone\": PineconeRAGService,\n}\n\ndef create_rag_service() -> Optional[RAGService]:\n    vector_db_type = os.getenv(\"VECTOR_DB_TYPE\", \"chroma\").lower()\n    use_rag = os.getenv(\"USE_RAG\", \"true\").lower() == \"true\"\n\n    if not use_rag:\n        logger.info(\"RAG disabled\")\n        return None\n\n    provider = PROVIDERS.get(vector_db_type)\n\n    if provider is None:\n        logger.warning(f\"Unknown vector DB type: {vector_db_type}\")\n        return None\n\n    try:\n        return provider()\n    except Exception as e:\n        logger.warning(f\"Failed to initialize provider {vector_db_type}: {e}\")\n        return None\n```\n\n### Equivalent JavaScript pattern (for cross-language consistency)\n\n```ts\nexport enum RAG_TYPE {\n  CHROMA = \"chroma_db\",\n  PINECONE = \"pinecone\"\n}\n\nexport const RAGS_IMPL = {\n  [RAG_TYPE.CHROMA]: {\n    ragProvider: () => chromaRAGService(),\n  },\n  [RAG_TYPE.PINECONE]: {\n    ragProvider: () => console.log(\"Not implemented\"),\n  },\n};\n```\n\n### Review Recommendation\nWhenever the model detects a Python factory using multiple `if/elif` statements, suggest switching to a registry/dictionary-based provider map, referencing the JS implementation pattern as a clean and extensible example.",
    "doc_type": "documentation",
    "language": "python",
    "repo": "my-repo",
    "author": "developer"
  }'
```

**Response:**

```json
{
    "success": true,
    "document_id": "unique-uuid-here",
    "message": "Document stored successfully"
}
```

#### 4. How This Helps Future Reviews

Once stored, this documentation will be automatically retrieved by RAG when analyzing similar code patterns. For example:

- When a new PR contains code with long if/elif chains, the RAG system will retrieve this stored documentation
- The AI model will use this context to provide consistent recommendations about using registry patterns
- This ensures that best practices are consistently applied across all code reviews

The stored document will be searched based on semantic similarity, so even if the code structure is slightly different, the relevant pattern and recommendation will be retrieved.

#### 5. How the Stored Content Instructs the AI

The key to making RAG work effectively is the **specific content** that gets stored in the vector database. The content field contains explicit instructions and examples that guide the AI's analysis:

**Critical Content Elements:**

1. **Pattern Detection Instructions**: The stored content explicitly mentions:
   - "When reviewing Python code that implements a factory function using multiple `if/elif` checks"
   - This tells the AI to look for this specific pattern

2. **Example Code Patterns**: The content includes examples of the anti-pattern:
   ```python
   if vector_db_type == "chroma":
       return ChromaRAGService()
   elif vector_db_type == "pinecone":
       return PineconeRAGService()
   ```
   When the AI analyzes new code, it can match similar patterns semantically

3. **Explicit Recommendations**: The content contains direct instructions:
   - "Recommend replacing the `if/elif` chain with a more scalable and maintainable pattern"
   - "Whenever the model detects a Python factory using multiple `if/elif` statements, suggest switching to a registry/dictionary-based provider map"

4. **Solution Examples**: The stored content provides concrete solutions that the AI can reference and adapt

**How It Works:**

1. When analyzing new code, the RAG system generates an embedding of the code diff
2. It searches the vector database for semantically similar documents
3. The stored content about "if/elif chains" will be retrieved because:
   - The embedding of the new code (with if/elif chains) is semantically similar to the stored content
   - The stored content explicitly mentions "if/elif" patterns, making it highly relevant
4. The retrieved content is added to the AI's prompt as context
5. The AI reads the instructions in the retrieved content and applies them to the current code review

**Why This Approach Works:**

The stored content acts as **custom instructions** for the AI. Instead of relying solely on the AI's general knowledge, you're providing:
- **Domain-specific patterns** to detect
- **Team-specific best practices** to enforce
- **Concrete examples** of problems and solutions
- **Explicit recommendations** to follow

This is why the content field is so important - it's not just documentation, it's **active instructions** that guide the AI's code review process. The more specific and detailed the content, the better the AI can detect patterns and provide relevant recommendations.

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

**Note:** The `doc_type` field is optional when storing documents. If not provided, the document will still be stored and can be retrieved, but it won't be categorized by type.

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

The factory function uses a dictionary dispatch pattern (not if/elif chains) for better maintainability:

**Step 1:** Create a builder function in `service/rag_service_builders.py`:

```python
def build_pinecone_service() -> Optional[RAGService]:
    """
    Build Pinecone RAG service.
    
    Returns:
        PineconeRAGService instance if successful, None otherwise
    """
    try:
        return PineconeRAGService()
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize PineconeRAGService: {e}")
        return None
```

**Step 2:** Add it to the `RAG_IMPLEMENTATIONS` dictionary:

```python
RAG_IMPLEMENTATIONS: Dict[str, RAGBuilder] = {
    "chroma": build_chroma_service,
    "pinecone": build_pinecone_service,  # New implementation
}
```

**Step 3:** The factory function in `service/rag_service.py` will automatically use it:

```python
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
```

**Benefits of this pattern:**
- O(1) lookup instead of O(n) comparison
- Easier to extend with new providers
- More maintainable and testable
- No risk of missing cases

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
