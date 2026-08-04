from pydantic import BaseModel, Field
from Rag_backend.llm_client import call_llm_structured, TaskType, cap_tokens
from Rag_backend.config.prompts import ANSWER_RELEVANCE_SYSTEM_PROMPT


class AnswerRelevanceResult(BaseModel):
    relevance_score: float = Field(ge=0.0, le=1.0)
    reason: str


def check_answer_relevance(query: str, answer: str) -> AnswerRelevanceResult:
    prompt=f"Query:\n{query}\n\nAnswer to evaluate:\n{answer}"
    prompt = cap_tokens(prompt)
    return call_llm_structured(
        prompt = prompt,
        schema=AnswerRelevanceResult,
        system=ANSWER_RELEVANCE_SYSTEM_PROMPT,
        task=TaskType.JUDGE,
        temperature=0.0,
    )