"""
Code analysis service with support for multiple AI providers.
Optimized for CI/CD environments and GitHub Actions.
"""
import os
import json
import re
from typing import Optional, Tuple
from pathlib import Path
from openai import OpenAI
import google.generativeai as genai
from anthropic import Anthropic
from dotenv import load_dotenv

from main import logger
from service.rag_service import create_rag_service, RAGService
from service.ai_provider_builders import build_provider_analyzers

load_dotenv()


class CodeAnalysisService:
    """Service for code analysis using different AI providers."""

    def __init__(self):
        # === Load prompts ===
        prompts_path = Path(__file__).parent.parent / "prompts" / "prompts.json"
        if not prompts_path.exists():
            raise FileNotFoundError(f"prompts.json not found at {prompts_path}")
        with open(prompts_path, "r", encoding="utf-8") as f:
            self.prompts = json.load(f)

        # === Initialize clients ===
        self.openai_client = None
        self.gemini_client = None
        self.claude_client = None

        if key := os.getenv("OPENAI_API_KEY"):
            self.openai_client = OpenAI(api_key=key)
        if key := os.getenv("GEMINI_API_KEY"):
            genai.configure(api_key=key)
            self.gemini_client = genai
        if key := os.getenv("ANTHROPIC_API_KEY"):
            self.claude_client = Anthropic(api_key=key)

        # === Models ===
        self.models = {
            "openai": os.getenv("OPENAI_MODEL", "gpt-4o"),
            "gemini": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            "claude": os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5"),
        }
        
        # === Initialize provider analyzers dictionary ===
        self.provider_analyzers = build_provider_analyzers(self)
        
        # === Initialize RAG Service ===
        self.rag_service = create_rag_service()
        if self.rag_service:
            logger.info("✅ RAG service initialized")
        else:
            logger.info("ℹ️ RAG service not available (will proceed without RAG)")

    # -------------------------------------------------------------------------
    # 🔍 Automatic language detection
    # -------------------------------------------------------------------------
    def _detect_language_from_diff(self, diff_text: str) -> str:
        """Detects the programming language based on the diff."""
        extensions = set(re.findall(r'\.(\w+)(?=["\'\s]|$)', diff_text))
        python_exts = {"py", "pyi"}
        react_exts = {"jsx", "tsx"}
        js_exts = {"js", "ts"}

        if extensions & python_exts:
            return "python"
        if extensions & react_exts:
            return "react"
        if extensions & js_exts:
            if re.search(r"react(-native)?", diff_text, re.IGNORECASE):
                return "react-native"
            return "javascript"
        return "python"  # safe fallback

    # -------------------------------------------------------------------------
    # 🧩 Prepare prompt
    # -------------------------------------------------------------------------
    def _get_prompt(
        self,
        language: str,
        title: str,
        repo: str,
        author: str,
        url: str,
        diff_text: str,
        provider: str = "openai",
        use_rag: bool = True,
    ) -> Tuple[str, str]:
        """Gets the appropriate prompt for the detected language, optionally enriched with RAG context."""
        language = language.lower()
        prompt_cfg = self.prompts.get(language) or self.prompts.get("python")
        system_prompt = prompt_cfg["system"]
        
        # Get RAG context if enabled
        rag_context = ""
        if use_rag and self.rag_service:
            try:
                # Search for similar documents
                similar_docs = self.rag_service.search_similar(
                    query=diff_text[:1000],  # Use first 1000 chars as query
                    provider=provider,
                    top_k=5,
                    language=language,
                )
                
                if similar_docs:
                    # Build context from similar documents
                    context_parts = []
                    for doc in similar_docs:
                        doc_type = doc["metadata"].get("type", "unknown")
                        doc_content = doc["content"][:500]  # Limit content length
                        context_parts.append(
                            f"[{doc_type.upper()}] {doc_content}"
                        )
                    
                    rag_context = "\n\n## Context from Previous Reviews and Documentation:\n" + "\n---\n".join(context_parts)
                    logger.info(f"✅ RAG context retrieved: {len(similar_docs)} documents")
            except Exception as e:
                logger.warning(f"⚠️ Error retrieving RAG context: {e}")
        
        # Format user prompt with RAG context if available
        base_user_prompt = prompt_cfg["user_template"].format(
            title=title, repo=repo, author=author, url=url, diff_text=diff_text
        )
        
        if rag_context:
            user_prompt = f"{base_user_prompt}\n\n{rag_context}"
        else:
            user_prompt = base_user_prompt
        
        return system_prompt, user_prompt

    # -------------------------------------------------------------------------
    # 🤖 Providers
    # -------------------------------------------------------------------------
    def _analyze_openai(self, diff_text, title, repo, author, url, language, use_rag: bool = True) -> str:
        if not self.openai_client:
            raise RuntimeError("OpenAI not configured.")
        system_prompt, user_prompt = self._get_prompt(
            language, title, repo, author, url, diff_text, provider="openai", use_rag=use_rag
        )
        response = self.openai_client.chat.completions.create(
            model=self.models["openai"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()

    def _analyze_gemini(self, diff_text, title, repo, author, url, language, use_rag: bool = True) -> str:
        if not self.gemini_client:
            raise RuntimeError("Gemini not configured.")
        system_prompt, user_prompt = self._get_prompt(
            language, title, repo, author, url, diff_text, provider="gemini", use_rag=use_rag
        )
        prompt = f"{system_prompt}\n\n{user_prompt}"
        model = genai.GenerativeModel(self.models["gemini"])
        response = model.generate_content(prompt)
        return response.text.strip()

    def _analyze_claude(self, diff_text, title, repo, author, url, language, use_rag: bool = True) -> str:
        if not self.claude_client:
            raise RuntimeError("Claude not configured.")
        system_prompt, user_prompt = self._get_prompt(
            language, title, repo, author, url, diff_text, provider="claude", use_rag=use_rag
        )
        message = self.claude_client.messages.create(
            model=self.models["claude"],
            system=system_prompt,
            max_tokens=4096,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text.strip()

    # -------------------------------------------------------------------------
    # 🚀 Main analysis
    # -------------------------------------------------------------------------
    def analyze_code(
        self,
        diff_text: str,
        title: str,
        repo: str,
        author: str,
        url: str,
        provider: str = "auto",
        language: Optional[str] = None,
        use_rag: bool = True,
    ) -> str:
        """Analyzes the code using the specified provider."""
        language = language or self._detect_language_from_diff(diff_text)
        provider = provider.lower()

        # Automatic selection of available provider
        if provider == "auto":
            # Map provider names to their client instances
            provider_clients = {
                "openai": self.openai_client,
                "claude": self.claude_client,
                "gemini": self.gemini_client,
            }
            provider = next(
                (p for p in self.provider_analyzers.keys() if provider_clients.get(p)),
                None,
            )
            if not provider:
                logger.error("No AI providers configured")
                raise RuntimeError("No AI providers configured.")
            logger.info(f"🔍 Provider auto-selected: {provider}")

        logger.info(f"📝 Language detected: {language}")
        logger.info(f"🤖 Starting analysis with provider: {provider} (model: {self.models.get(provider, 'N/A')})")
        logger.info(f"🔍 RAG enabled: {use_rag}")

        try:
            # Use dictionary dispatch pattern
            if provider in self.provider_analyzers:
                analyzer = self.provider_analyzers[provider]
                logger.info(f"🔄 Analyzing code with {provider.capitalize()} using model: {self.models.get(provider, 'N/A')}")
                result = analyzer(diff_text, title, repo, author, url, language, use_rag)
            else:
                raise ValueError(f"Unknown provider: {provider}")
            
            # Store the analysis result in RAG if enabled
            if use_rag and self.rag_service:
                try:
                    self.rag_service.store_document(
                        content=result,
                        doc_type="review",
                        language=language,
                        repo=repo,
                        author=author,
                        metadata={"title": title, "url": url, "provider": provider},
                    )
                    logger.info("✅ Analysis result stored in RAG")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to store analysis result in RAG: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error with provider {provider} (model: {self.models.get(provider, 'N/A')}): {e}", exc_info=True)
            # Fallback to OpenAI if another API is available
            if provider != "openai" and self.openai_client:
                logger.warning(f"⚠️ Fallback to OpenAI (model: {self.models['openai']}) due to error with {provider}")
                return self._analyze_openai(diff_text, title, repo, author, url, language, use_rag)
            raise
