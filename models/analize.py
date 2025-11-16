from pydantic import BaseModel

class AnalysisRequest(BaseModel):
    pr_number: int
    repo: str
    title: str
    url: str
    author: str
    diff_b64: str