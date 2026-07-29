import pytest

from Rag_backend.guardrails import Pii as pii


def test_redact_pii(monkeypatch):

    class FakeAnalyzer:

        def analyze(self, **kwargs):
            return ["entity"]

    class FakeResult:

        text = "Hello [PERSON]"

    class FakeAnonymizer:

        def anonymize(self, **kwargs):
            return FakeResult()

    monkeypatch.setattr(
        pii,
        "_analyzer",
        FakeAnalyzer(),
    )

    monkeypatch.setattr(
        pii,
        "_anonymizer",
        FakeAnonymizer(),
    )

    result = pii.redact_pii(
        "Hello John"
    )

    assert result == "Hello [PERSON]"


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "Email me at test@example.com",
            "Email me at [REDACTED_EMAIL]",
        ),
        (
            "Call me at 9876543210",
            "Call me at [REDACTED_PHONE]",
        ),
        (
            "SSN 123-45-6789",
            "SSN [REDACTED_SSN]",
        ),
        (
            "Card 4111111111111111",
            "Card [REDACTED_CREDIT_CARD]",
        ),
        (
            "IBAN GB29NWBK60161331926819",
            "IBAN [REDACTED_IBAN]",
        ),
    ],
)
def test_redact_pii_regex_fallback(
    text,
    expected,
):

    assert (
        pii.redact_pii_regex_fallback(text)
        == expected
    )


def test_redact_pii_layered_presidio(
    monkeypatch,
):

    monkeypatch.setattr(
        pii,
        "redact_pii",
        lambda text: "presidio output",
    )

    result, method = pii.redact_pii_layered(
        "hello"
    )

    assert result == "presidio output"

    assert method == "presidio"


def test_redact_pii_layered_regex_fallback(
    monkeypatch,
):

    def presidio_fail(text):
        raise RuntimeError()

    monkeypatch.setattr(
        pii,
        "redact_pii",
        presidio_fail,
    )

    monkeypatch.setattr(
        pii,
        "redact_pii_regex_fallback",
        lambda text: "regex output",
    )

    result, method = pii.redact_pii_layered(
        "hello"
    )

    assert result == "regex output"

    assert method == "regex_fallback"


def test_redact_pii_layered_complete_failure(
    monkeypatch,
):

    monkeypatch.setattr(
        pii,
        "redact_pii",
        lambda text: (_ for _ in ()).throw(
            RuntimeError()
        ),
    )

    monkeypatch.setattr(
        pii,
        "redact_pii_regex_fallback",
        lambda text: (_ for _ in ()).throw(
            RuntimeError()
        ),
    )

    result, method = pii.redact_pii_layered(
        "hello"
    )

    assert result is None

    assert method == "failed"


def test_regex_fallback_no_pii():

    text = "This sentence contains no private information."

    assert (
        pii.redact_pii_regex_fallback(text)
        == text
    )


def test_default_entities():

    assert "PERSON" in pii.DEFAULT_ENTITIES

    assert "EMAIL_ADDRESS" in pii.DEFAULT_ENTITIES

    assert "PHONE_NUMBER" in pii.DEFAULT_ENTITIES

    assert "CREDIT_CARD" in pii.DEFAULT_ENTITIES


def test_regex_patterns():

    assert "EMAIL" in pii.REGEX_PATTERNS

    assert "PHONE" in pii.REGEX_PATTERNS

    assert "SSN" in pii.REGEX_PATTERNS

    assert "CREDIT_CARD" in pii.REGEX_PATTERNS

    assert "IBAN" in pii.REGEX_PATTERNS