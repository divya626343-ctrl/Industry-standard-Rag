import pytest

from Rag_backend.guardrails import hallucination


@pytest.fixture
def sample_context():

    return [
        {
            "payload": {
                "chunk_text": "Paris is the capital of France."
            }
        },
        {
            "payload": {
                "chunk_text": "The Eiffel Tower is located in Paris."
            }
        },
    ]


def test_check_hallucination_faithful(
    monkeypatch,
    sample_context,
):

    expected = hallucination.HallucinationCheckResult(
        is_faithful=True,
        category="faithful",
        reason="Supported by context.",
    )

    captured = {}

    def fake_call_llm_structured(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        hallucination,
        "call_llm_structured",
        fake_call_llm_structured,
    )

    result = hallucination.check_hallucination(
        query="What is the capital of France?",
        answer="Paris is the capital of France.",
        context_chunks=sample_context,
    )

    assert result == expected

    assert "Query:" in captured["prompt"]

    assert "Generated answer to verify:" in captured["prompt"]

    assert "[1] Paris is the capital of France." in captured["prompt"]

    assert "[2] The Eiffel Tower is located in Paris." in captured["prompt"]

    assert (
        captured["schema"]
        == hallucination.HallucinationCheckResult
    )

    assert (
        captured["system"]
        == hallucination.HALLUCINATION_SYSTEM_PROMPT
    )

    assert (
        captured["task"]
        == hallucination.TaskType.JUDGE
    )

    assert captured["temperature"] == 0.0


@pytest.mark.parametrize(
    "category",
    [
        "unsupported_claim",
        "contradicts_context",
        "no_citation",
    ],
)
def test_check_hallucination_failure_categories(
    monkeypatch,
    sample_context,
    category,
):

    expected = hallucination.HallucinationCheckResult(
        is_faithful=False,
        category=category,
        reason="Detected issue.",
    )

    monkeypatch.setattr(
        hallucination,
        "call_llm_structured",
        lambda **kwargs: expected,
    )

    result = hallucination.check_hallucination(
        "query",
        "answer",
        sample_context,
    )

    assert result.is_faithful is False

    assert result.category == category

    assert result.reason == "Detected issue."


def test_check_hallucination_empty_context(
    monkeypatch,
):

    captured = {}

    expected = hallucination.HallucinationCheckResult(
        is_faithful=False,
        category="unsupported_claim",
        reason="No evidence.",
    )

    def fake_call(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        hallucination,
        "call_llm_structured",
        fake_call,
    )

    result = hallucination.check_hallucination(
        "query",
        "answer",
        [],
    )

    assert result == expected

    assert "Context chunks:\n" in captured["prompt"]


def test_check_hallucination_single_chunk(
    monkeypatch,
):

    expected = hallucination.HallucinationCheckResult(
        is_faithful=True,
        category="faithful",
        reason="OK",
    )

    captured = {}

    def fake_call(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        hallucination,
        "call_llm_structured",
        fake_call,
    )

    hallucination.check_hallucination(
        "query",
        "answer",
        [
            {
                "payload": {
                    "chunk_text": "Only one chunk."
                }
            }
        ],
    )

    assert "[1] Only one chunk." in captured["prompt"]


def test_check_hallucination_propagates_exception(
    monkeypatch,
    sample_context,
):

    monkeypatch.setattr(
        hallucination,
        "call_llm_structured",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("LLM unavailable")
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="LLM unavailable",
    ):
        hallucination.check_hallucination(
            "query",
            "answer",
            sample_context,
        )


def test_hallucination_result_model():

    result = hallucination.HallucinationCheckResult(
        is_faithful=True,
        category="faithful",
        reason="Supported.",
    )

    assert result.is_faithful is True

    assert result.category == "faithful"

    assert result.reason == "Supported."