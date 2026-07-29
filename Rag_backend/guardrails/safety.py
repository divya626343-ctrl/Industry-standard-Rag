from typing import Literal
from pydantic import BaseModel
from Rag_backend.llm_client import call_llm_structured, TaskType
from Rag_backend.config.prompts import SAFETY_SYSTEM_PROMPT

class SafetyCheckResult(BaseModel):
    is_safe: bool
    category: Literal["safe", "prompt_injection", "harmful_content_request", "cross_sessin_exfiltration_attempt", "other_unsafe_reason"]
    reason: str


def check_safety(rewritten_query: str) -> SafetyCheckResult:
    return call_llm_structured(
        prompt=f"Query to classify:\n{rewritten_query}",
        schema=SafetyCheckResult,
        system=SAFETY_SYSTEM_PROMPT,
        task=TaskType.JUDGE,
        temperature=0.0,
    )

