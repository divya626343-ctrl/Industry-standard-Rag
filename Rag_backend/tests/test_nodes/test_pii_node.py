from datetime import datetime, timezone

import pytest

from Rag_backend.nodes import pii_detection as pii


@pytest.fixture
def base_state():
    return {
        "draft_answer": (
            "John's phone is 9999999999. [1] "
            "Session only information. [2]"
        ),
        "citations": {
            1: {
                "source_collection": "shared",
            },
            2: {
                "source_collection": "session",
            },
        },
        "trace_log": [],
    }


# --------------------------------------------------------------------
# sentence_needs_redaction
# --------------------------------------------------------------------

def test_sentence_needs_redaction_shared():

    citations = {
        1: {"source_collection": "shared"},
    }

    assert pii.sentence_needs_redaction(
        "Answer [1]",
        citations,
    ) is True


def test_sentence_needs_redaction_session():

    citations = {
        2: {"source_collection": "session"},
    }

    assert pii.sentence_needs_redaction(
        "Answer [2]",
        citations,
    ) is False


def test_sentence_needs_redaction_no_citation():

    assert pii.sentence_needs_redaction(
        "No citations here",
        {},
    ) is True


# --------------------------------------------------------------------
# PII node
# --------------------------------------------------------------------

def test_pii_success(monkeypatch, base_state):

    def fake_redact(text):
        return (
            text.replace(
                "9999999999",
                "[REDACTED]",
            ),
            "presidio",
        )

    monkeypatch.setattr(
        pii,
        "redact_pii_layered",
        fake_redact,
    )

    result = pii.PII(base_state)

    assert result["final_answer"] is not None

    assert "[REDACTED]" in result["final_answer"]

    assert "Session only information" in result["final_answer"]

    assert result["trace_log"][-1]["event"] == "success"


def test_pii_withheld(monkeypatch, base_state):

    def fake_redact(text):
        # Only the sentence containing the phone number is withheld.
        if "9999999999" in text:
            return None, "failed"

        return text, "presidio"

    monkeypatch.setattr(
        pii,
        "redact_pii_layered",
        fake_redact,
    )

    result = pii.PII(base_state)

    assert "[content withheld" in result["final_answer"]

    assert (
        result["trace_log"][-1]["detail"]["withheld_count"]
        == 1
    )


def test_pii_non_presidio(monkeypatch, base_state):

    monkeypatch.setattr(
        pii,
        "redact_pii_layered",
        lambda text: (
            text,
            "regex",
        ),
    )

    result = pii.PII(base_state)

    assert result["final_answer"] is not None

    assert result["trace_log"][-1]["event"] == "success"


def test_pii_exception(monkeypatch, base_state):

    def boom(text):
        raise RuntimeError("PII failed")

    monkeypatch.setattr(
        pii,
        "redact_pii_layered",
        boom,
    )

    result = pii.PII(base_state)

    assert result["final_answer"] is None

    assert result["exit_stage"] == "pii_node_error"

    assert result["trace_log"][-1]["event"] == "failed"

    assert (
        result["trace_log"][-1]["detail"]["error"]
        == "PII failed"
    )


# --------------------------------------------------------------------
# trace helper
# --------------------------------------------------------------------

def test_build_trace_entry():

    started = datetime.now(timezone.utc)

    trace = pii.build_trace_entry(
        node="pii",
        event="success",
        started_at=started,
        details={"count": 2},
    )

    assert trace["node"] == "pii"

    assert trace["event"] == "success"

    assert trace["detail"]["count"] == 2

    assert "started_at" in trace

    assert "completed_at" in trace

    assert "elapsed_ms" in trace