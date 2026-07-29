import pytest

from Rag_backend.guardrails import safety


def test_check_safety_safe(monkeypatch):

    expected = safety.SafetyCheckResult(
        is_safe=True,
        category="safe",
        reason="Query is safe.",
    )

    captured = {}

    def fake_call_llm_structured(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        safety,
        "call_llm_structured",
        fake_call_llm_structured,
    )

    result = safety.check_safety(
        "What is machine learning?"
    )

    assert result == expected

    assert (
        captured["prompt"]
        == "Query to classify:\nWhat is machine learning?"
    )

    assert (
        captured["schema"]
        == safety.SafetyCheckResult
    )

    assert (
        captured["system"]
        == safety.SAFETY_SYSTEM_PROMPT
    )

    assert (
        captured["task"]
        == safety.TaskType.JUDGE
    )

    assert captured["temperature"] == 0.0


@pytest.mark.parametrize(
    "category",
    [
        "prompt_injection",
        "harmful_content_request",
        "cross_sessin_exfiltration_attempt",
        "other_unsafe_reason",
    ],
)
def test_check_safety_unsafe_categories(
    monkeypatch,
    category,
):

    expected = safety.SafetyCheckResult(
        is_safe=False,
        category=category,
        reason="Unsafe request.",
    )

    monkeypatch.setattr(
        safety,
        "call_llm_structured",
        lambda **kwargs: expected,
    )

    result = safety.check_safety(
        "malicious query"
    )

    assert result.is_safe is False
    assert result.category == category
    assert result.reason == "Unsafe request."


def test_check_safety_empty_query(monkeypatch):

    expected = safety.SafetyCheckResult(
        is_safe=True,
        category="safe",
        reason="Empty query.",
    )

    captured = {}

    def fake_call(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        safety,
        "call_llm_structured",
        fake_call,
    )

    result = safety.check_safety("")

    assert result == expected

    assert (
        captured["prompt"]
        == "Query to classify:\n"
    )


def test_check_safety_propagates_exception(
    monkeypatch,
):

    monkeypatch.setattr(
        safety,
        "call_llm_structured",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("LLM unavailable")
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="LLM unavailable",
    ):
        safety.check_safety(
            "hello"
        )


def test_safety_result_model():

    result = safety.SafetyCheckResult(
        is_safe=True,
        category="safe",
        reason="OK",
    )

    assert result.is_safe is True
    assert result.category == "safe"
    assert result.reason == "OK"