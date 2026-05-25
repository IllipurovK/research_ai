from typing import List, Optional
from pydantic import BaseModel

class Step(BaseModel):
    step_id: int
    description: str
    expected_keywords: Optional[List[str]] = None
    query: str
    normalized_query: str
    tool: Optional[str] = None
    result_text: str = ""
    urls: List[str] = []
    success: bool = False
    error_msg: Optional[str] = None
    retry_count: int = 0
    start_time: float = 0.0
    end_time: float = 0.0