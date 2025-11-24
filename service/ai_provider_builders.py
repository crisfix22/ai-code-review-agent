"""
AI Provider Builder Functions

Centralizes the dispatch pattern for AI provider analyzers using dictionary-based lookup.
"""
from typing import Callable, Dict


# Type alias for analyzer methods
# Parameters: diff_text, title, repo, author, url, language, use_rag
# Returns: str (analysis result)
AIProviderAnalyzer = Callable[[str, str, str, str, str, str, bool], str]


def build_provider_analyzers(service_instance) -> Dict[str, AIProviderAnalyzer]:
    """
    Build dictionary of provider analyzers.
    
    Args:
        service_instance: Instance of CodeAnalysisService containing analyzer methods
        
    Returns:
        Dictionary mapping provider names to their analyzer methods
    """
    return {
        "openai": service_instance._analyze_openai,
        "claude": service_instance._analyze_claude,
        "gemini": service_instance._analyze_gemini,
    }
