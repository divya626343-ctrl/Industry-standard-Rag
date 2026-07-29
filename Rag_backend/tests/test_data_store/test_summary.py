import pytest

from Rag_backend.data_stores import conversation_summary


def test_summarize_fold_without_existing_summary(monkeypatch):

    captured = {}

    def fake_call_llm_raw(**kwargs):
        captured.update(kwargs)
        return "new summary"

    monkeypatch.setattr(
        conversation_summary,
        "call_llm_raw",
        fake_call_llm_raw,
    )

    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]

    result = conversation_summary.summarize_fold(
        None,
        messages,
    )

    assert result == "new summary"

    assert "(no summary yet)" in captured["prompt"]

    assert "user : Hello" in captured["prompt"]

    assert "assistant : Hi" in captured["prompt"]

    assert captured["temperature"] == 0.0

    assert captured["task"] == conversation_summary.TaskType.JUDGE


def test_summarize_fold_with_existing_summary(monkeypatch):

    captured = {}

    def fake_call_llm_raw(**kwargs):
        captured.update(kwargs)
        return "updated summary"

    monkeypatch.setattr(
        conversation_summary,
        "call_llm_raw",
        fake_call_llm_raw,
    )

    result = conversation_summary.summarize_fold(
        "Existing conversation summary",
        [
            {
                "role": "user",
                "content": "New question",
            }
        ],
    )

    assert result == "updated summary"

    assert "Existing conversation summary" in captured["prompt"]

    assert "New question" in captured["prompt"]


def test_get_conversation_context(monkeypatch):

    expected = (
        "summary",
        [
            {
                "role": "user",
                "content": "Hello",
            }
        ],
    )

    captured = {}

    def fake_get_context(session_id, summarizer_fn):
        captured["session_id"] = session_id
        captured["summarizer_fn"] = summarizer_fn
        return expected

    monkeypatch.setattr(
        conversation_summary.redis_store,
        "get_context_for_query",
        fake_get_context,
    )

    result = conversation_summary.get_conversation_context(
        "session123",
    )

    assert result == expected

    assert captured["session_id"] == "session123"

    assert captured["summarizer_fn"] == conversation_summary.summarize_fold


def test_record_turn(monkeypatch):

    calls = []

    monkeypatch.setattr(
        conversation_summary.redis_store,
        "append_turn",
        lambda session, role, content: calls.append(
            ("append", session, role, content)
        ),
    )

    monkeypatch.setattr(
        conversation_summary.redis_store,
        "heartbeat",
        lambda session: calls.append(
            ("heartbeat", session)
        ),
    )

    conversation_summary.record_turn(
        "session1",
        "user",
        "Hello",
    )

    assert calls == [
        (
            "append",
            "session1",
            "user",
            "Hello",
        ),
        (
            "heartbeat",
            "session1",
        ),
    ]


def test_record_turn_propagates_append_error(monkeypatch):

    monkeypatch.setattr(
        conversation_summary.redis_store,
        "append_turn",
        lambda *args: (_ for _ in ()).throw(
            RuntimeError("append failed")
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="append failed",
    ):
        conversation_summary.record_turn(
            "session1",
            "user",
            "Hello",
        )


def test_record_turn_propagates_heartbeat_error(monkeypatch):

    monkeypatch.setattr(
        conversation_summary.redis_store,
        "append_turn",
        lambda *args: None,
    )

    monkeypatch.setattr(
        conversation_summary.redis_store,
        "heartbeat",
        lambda *args: (_ for _ in ()).throw(
            RuntimeError("heartbeat failed")
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="heartbeat failed",
    ):
        conversation_summary.record_turn(
            "session1",
            "assistant",
            "Hi",
        )