import pytest

from Rag_backend.guardrails import answer_relevance


def test_check_answer_relevance_success(monkeypatch):

    expected = answer_relevance.AnswerRelevanceResult(
        relevance_score=0.95,
        reason="The answer directly addresses the question.",
    )

    captured = {}

    def fake_call_llm_structured(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        answer_relevance,
        "call_llm_structured",
        fake_call_llm_structured,
    )

    result = answer_relevance.check_answer_relevance(
        query="What is AI?",
        answer="AI stands for Artificial Intelligence.",
    )

    assert result == expected

    assert (
        captured["prompt"]
        == "Query:\nWhat is AI?\n\nAnswer to evaluate:\nAI stands for Artificial Intelligence."
    )

    assert (
        captured["schema"]
        == answer_relevance.AnswerRelevanceResult
    )

    assert (
        captured["system"]
        == answer_relevance.ANSWER_RELEVANCE_SYSTEM_PROMPT
    )

    assert (
        captured["task"]
        == answer_relevance.TaskType.JUDGE
    )

    assert captured["temperature"] == 0.0


@pytest.mark.parametrize(
    "score",
    [
        0.0,
        0.25,
        0.5,
        0.75,
        1.0,
    ],
)
def test_answer_relevance_scores(monkeypatch, score):

    expected = answer_relevance.AnswerRelevanceResult(
        relevance_score=score,
        reason="Test",
    )

    monkeypatch.setattr(
        answer_relevance,
        "call_llm_structured",
        lambda **kwargs: expected,
    )

    result = answer_relevance.check_answer_relevance(
        "query",
        "answer",
    )

    assert result.relevance_score == score


def test_check_answer_relevance_empty_strings(monkeypatch):

    captured = {}

    expected = answer_relevance.AnswerRelevanceResult(
        relevance_score=0.0,
        reason="Empty input.",
    )

    def fake_call(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        answer_relevance,
        "call_llm_structured",
        fake_call,
    )

    result = answer_relevance.check_answer_relevance(
        "",
        "",
    )

    assert result == expected

    assert captured["prompt"] == "Query:\n\n\nAnswer to evaluate:\n"


def test_check_answer_relevance_exception(monkeypatch):

    monkeypatch.setattr(
        answer_relevance,
        "call_llm_structured",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("LLM unavailable")
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="LLM unavailable",
    ):
        answer_relevance.check_answer_relevance(
            "query",
            "answer",
        )


def test_answer_relevance_model():

    result = answer_relevance.AnswerRelevanceResult(
        relevance_score=0.8,
        reason="Relevant",
    )

    assert result.relevance_score == 0.8
    assert result.reason == "Relevant"


def test_answer_relevance_model_validation():

    with pytest.raises(Exception):

        answer_relevance.AnswerRelevanceResult(
            relevance_score=1.5,
            reason="Invalid",
        )

    with pytest.raises(Exception):

        answer_relevance.AnswerRelevanceResult(
            relevance_score=-0.1,
            reason="Invalid",
        )