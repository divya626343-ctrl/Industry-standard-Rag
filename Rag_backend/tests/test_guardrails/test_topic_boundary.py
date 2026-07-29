import pytest

from Rag_backend.guardrails import topic_boundary


def test_build_scope_context_without_session(monkeypatch):
    monkeypatch.setattr(
        topic_boundary.settings,
        "CORPUS_DOMAIN_DESCRIPTION",
        "Banking documents",
    )

    result = topic_boundary.build_scope_context(None)

    assert result == "Shared corpus domain:\nBanking documents"


def test_build_scope_context_with_no_doc_summaries(monkeypatch):
    monkeypatch.setattr(
        topic_boundary.settings,
        "CORPUS_DOMAIN_DESCRIPTION",
        "Banking documents",
    )

    monkeypatch.setattr(
        topic_boundary.redis_store,
        "get_doc_topic_summaries",
        lambda session_id: [],
    )

    result = topic_boundary.build_scope_context("session1")

    assert result == "Shared corpus domain:\nBanking documents"


def test_build_scope_context_with_doc_summaries(monkeypatch):
    monkeypatch.setattr(
        topic_boundary.settings,
        "CORPUS_DOMAIN_DESCRIPTION",
        "Banking documents",
    )

    monkeypatch.setattr(
        topic_boundary.redis_store,
        "get_doc_topic_summaries",
        lambda session_id: [
            "Loan Policy",
            "Credit Card Guide",
        ],
    )

    result = topic_boundary.build_scope_context("session1")

    expected = (
        "Shared corpus domain:\nBanking documents\n\n"
        "Session-uploaded document topics:\n"
        "- Loan Policy\n"
        "- Credit Card Guide"
    )

    assert result == expected


def test_check_topic_boundary(monkeypatch):
    monkeypatch.setattr(
        topic_boundary,
        "build_scope_context",
        lambda session_id: "scope text",
    )

    expected = topic_boundary.TopicBoundaryResult(
        in_scope=True,
        category="shared_corpus_match",
        reason="Matches corpus",
    )

    captured = {}

    def fake_call_llm_structured(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        topic_boundary,
        "call_llm_structured",
        fake_call_llm_structured,
    )

    result = topic_boundary.check_topic_boundary(
        "What is a savings account?",
        "session1",
    )

    assert result == expected

    assert (
        captured["prompt"]
        == "Scope:\nscope text\n\nQuery to classify:\nWhat is a savings account?"
    )

    assert captured["schema"] == topic_boundary.TopicBoundaryResult

    assert (
        captured["system"]
        == topic_boundary.TOPIC_BOUNDARY_SYSTEM_PROMPT
    )

    assert captured["task"] == topic_boundary.TaskType.JUDGE

    assert captured["temperature"] == 0.0


@pytest.mark.parametrize(
    "category",
    [
        "shared_corpus_match",
        "session_doc_match",
        "out_of_scope",
    ],
)
def test_topic_boundary_categories(monkeypatch, category):
    monkeypatch.setattr(
        topic_boundary,
        "build_scope_context",
        lambda session_id: "scope",
    )

    expected = topic_boundary.TopicBoundaryResult(
        in_scope=(category != "out_of_scope"),
        category=category,
        reason="reason",
    )

    monkeypatch.setattr(
        topic_boundary,
        "call_llm_structured",
        lambda **kwargs: expected,
    )

    result = topic_boundary.check_topic_boundary(
        "query",
        "session",
    )

    assert result.category == category


def test_check_topic_boundary_exception(monkeypatch):
    monkeypatch.setattr(
        topic_boundary,
        "build_scope_context",
        lambda session_id: "scope",
    )

    monkeypatch.setattr(
        topic_boundary,
        "call_llm_structured",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("LLM failure")
        ),
    )

    with pytest.raises(RuntimeError, match="LLM failure"):
        topic_boundary.check_topic_boundary(
            "query",
            "session1",
        )


def test_topic_boundary_model():
    result = topic_boundary.TopicBoundaryResult(
        in_scope=True,
        category="shared_corpus_match",
        reason="Supported",
    )

    assert result.in_scope is True
    assert result.category == "shared_corpus_match"
    assert result.reason == "Supported"