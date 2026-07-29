from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
import re


nlp_configuration = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
}

nlp_engine = NlpEngineProvider(nlp_configuration=nlp_configuration).create_engine()


_analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
_anonymizer = AnonymizerEngine()

DEFAULT_ENTITIES = [
    "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD",
    "US_SSN", "LOCATION", "IBAN_CODE", "US_BANK_NUMBER",
]


REGEX_PATTERNS = {
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "PHONE": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
}


def redact_pii(text: str) -> str:
    """Primary: Microsoft Presidio (NLP-based, catches names/locations/etc)."""
    results = _analyzer.analyze(text=text, entities=DEFAULT_ENTITIES, language="en")
    return _anonymizer.anonymize(text=text, analyzer_results=results).text


def redact_pii_regex_fallback(text: str) -> str:
    """Fallback: structured-pattern regex only."""

    for label, pattern in REGEX_PATTERNS.items():
        text = pattern.sub(f"[REDACTED_{label}]", text)
    return text


def redact_pii_layered(text: str) -> tuple[str | None, str]:
    """
    Tries Presidio first, falls back to regex if Presidio errors
    """
    try:
        return redact_pii(text), "presidio"
    except Exception:
        pass

    try:
        return redact_pii_regex_fallback(text), "regex_fallback"
    except Exception:
        return None, "failed"