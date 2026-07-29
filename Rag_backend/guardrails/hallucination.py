from typing import Literal
from pydantic import BaseModel
from Rag_backend.llm_client import call_llm_structured, TaskType
from Rag_backend.config.prompts import HALLUCINATION_SYSTEM_PROMPT

class HallucinationCheckResult(BaseModel):
    is_faithful: bool
    category: Literal["faithful", "unsupported_claim", "contradicts_context", "no_citation"]
    reason: str
 
 
def check_hallucination(query: str, answer: str, context_chunks: list[dict]) -> HallucinationCheckResult:
    numbered_context = "\n\n".join(
        f"[{i+1}] {c['payload']['chunk_text']}" for i, c in enumerate(context_chunks)
    )
 
    return call_llm_structured(
        prompt=(
            f"Query:\n{query}\n\n"
            f"Context chunks:\n{numbered_context}\n\n"
            f"Generated answer to verify:\n{answer}"
        ),
        schema=HallucinationCheckResult,
        system=HALLUCINATION_SYSTEM_PROMPT,
        task=TaskType.JUDGE,
        temperature=0.0,
    )