from pydantic import BaseModel
from typing import Literal, Optional

class AnalysisRequest(BaseModel):
    pr_number: int
    repo: str
    title: str
    url: str
    author: str
    diff_b64: str
    provider: Optional[Literal["openai", "gemini", "claude"]] = None
    language: Optional[str] = None
    use_rag: Optional[bool] = True